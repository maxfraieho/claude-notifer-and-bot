"""
Error Handling Decorators for DevClaude_bot

Provides convenient decorators for applying error handling patterns
as recommended by Enhanced Architect Bot analysis.
"""

import functools
from typing import Any, Callable, Optional, Type, Union, List
import structlog

from .exceptions import DevClaudeError, TemporaryError
from .handlers import ErrorHandler, RetryHandler, FallbackHandler, ErrorContextManager

logger = structlog.get_logger(__name__)


def handle_errors(
    retry_count: int = 3,
    fallback: Optional[Callable] = None,
    retry_on: tuple = (TemporaryError,),
    ignore_errors: tuple = (),
    log_errors: bool = True,
    operation_name: Optional[str] = None
):
    """
    Comprehensive error handling decorator.

    Args:
        retry_count: Number of retry attempts
        fallback: Fallback function to call if all retries fail
        retry_on: Exception types to retry on
        ignore_errors: Exception types to ignore (return None)
        log_errors: Whether to log errors
        operation_name: Name for operation identification
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            error_handler = ErrorHandler()

            try:
                return await error_handler.handle_operation(
                    op_name,
                    func,
                    *args,
                    use_retry=retry_count > 1,
                    use_fallback=fallback is not None,
                    **kwargs
                )

            except ignore_errors:
                if log_errors:
                    logger.warning("Ignoring error as configured", operation=op_name)
                return None

            except Exception as e:
                if log_errors:
                    logger.error("Unhandled error in operation", operation=op_name, error=str(e))

                # Try fallback if provided
                if fallback:
                    try:
                        logger.info("Executing fallback function", operation=op_name)
                        if asyncio.iscoroutinefunction(fallback):
                            return await fallback(*args, **kwargs)
                        else:
                            return fallback(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error("Fallback function failed", operation=op_name, error=str(fallback_error))

                raise e

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            import asyncio
            if asyncio.iscoroutinefunction(func):
                raise ValueError("Use async version for coroutines")

            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            for attempt in range(retry_count):
                try:
                    return func(*args, **kwargs)

                except ignore_errors:
                    if log_errors:
                        logger.warning("Ignoring error as configured", operation=op_name)
                    return None

                except retry_on as e:
                    if attempt == retry_count - 1:  # Last attempt
                        if fallback:
                            try:
                                logger.info("Executing fallback function", operation=op_name)
                                return fallback(*args, **kwargs)
                            except Exception as fallback_error:
                                logger.error("Fallback function failed", operation=op_name, error=str(fallback_error))
                        raise e

                    if log_errors:
                        logger.warning("Retrying after error", operation=op_name, attempt=attempt + 1, error=str(e))

                except Exception as e:
                    if log_errors:
                        logger.error("Non-retryable error", operation=op_name, error=str(e))

                    if fallback:
                        try:
                            logger.info("Executing fallback function", operation=op_name)
                            return fallback(*args, **kwargs)
                        except Exception as fallback_error:
                            logger.error("Fallback function failed", operation=op_name, error=str(fallback_error))

                    raise e

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retry_on: tuple = (TemporaryError,),
    jitter: bool = True
):
    """
    Simple retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries
        backoff_factor: Multiplication factor for delay
        max_delay: Maximum delay between retries
        retry_on: Exception types to retry on
        jitter: Add random jitter to delays
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            retry_handler = RetryHandler(
                max_attempts=max_attempts,
                base_delay=delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                jitter=jitter
            )

            return await retry_handler.retry_async(
                func, *args, retry_on=retry_on, **kwargs
            )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            import asyncio
            import time
            import random

            last_error = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except retry_on as e:
                    last_error = e

                    if attempt == max_attempts - 1:
                        break

                    # Calculate delay
                    current_delay = delay * (backoff_factor ** attempt)
                    current_delay = min(current_delay, max_delay)

                    if jitter:
                        current_delay *= (0.5 + random.random())

                    time.sleep(current_delay)

                except Exception as e:
                    # Non-retryable error
                    raise e

            # All retries failed
            raise last_error

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_fallback(fallback_func: Callable, log_errors: bool = True):
    """
    Decorator to provide fallback functionality.

    Args:
        fallback_func: Function to call if primary function fails
        log_errors: Whether to log errors
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.warning(
                        "Primary function failed, using fallback",
                        function=func.__name__,
                        error=str(e)
                    )

                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func(*args, **kwargs)
                else:
                    return fallback_func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.warning(
                        "Primary function failed, using fallback",
                        function=func.__name__,
                        error=str(e)
                    )

                return fallback_func(*args, **kwargs)

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_errors(
    level: str = "error",
    include_traceback: bool = False,
    reraise: bool = True,
    operation_name: Optional[str] = None
):
    """
    Decorator to log errors with context.

    Args:
        level: Log level (debug, info, warning, error, critical)
        include_traceback: Include full traceback in logs
        reraise: Whether to re-raise the exception after logging
        operation_name: Custom operation name for logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log_method = getattr(logger, level.lower(), logger.error)

                log_data = {
                    "operation": op_name,
                    "error_type": type(e).__name__,
                    "error": str(e),
                }

                if include_traceback:
                    import traceback
                    log_data["traceback"] = traceback.format_exc()

                log_method("Error in operation", **log_data)

                if reraise:
                    raise e

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_method = getattr(logger, level.lower(), logger.error)

                log_data = {
                    "operation": op_name,
                    "error_type": type(e).__name__,
                    "error": str(e),
                }

                if include_traceback:
                    import traceback
                    log_data["traceback"] = traceback.format_exc()

                log_method("Error in operation", **log_data)

                if reraise:
                    raise e

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Type[Exception] = Exception
):
    """
    Circuit breaker pattern decorator.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying again
        expected_exception: Exception type to count as failure
    """
    def decorator(func: Callable) -> Callable:
        state = {"failures": 0, "last_failure": None, "open": False}

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            import time

            # Check if circuit is open and should remain open
            if state["open"]:
                if time.time() - state["last_failure"] < recovery_timeout:
                    raise DevClaudeError(
                        f"Circuit breaker open for {func.__name__}",
                        error_code="CIRCUIT_BREAKER_OPEN",
                        retry_after=recovery_timeout
                    )
                else:
                    # Try to close circuit
                    state["open"] = False
                    state["failures"] = 0

            try:
                result = await func(*args, **kwargs)
                # Success - reset failure count
                state["failures"] = 0
                return result

            except expected_exception as e:
                state["failures"] += 1
                state["last_failure"] = time.time()

                if state["failures"] >= failure_threshold:
                    state["open"] = True
                    logger.error(
                        "Circuit breaker opened",
                        function=func.__name__,
                        failures=state["failures"],
                        threshold=failure_threshold
                    )

                raise e

        return wrapper

    return decorator