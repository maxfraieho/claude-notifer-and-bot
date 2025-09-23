"""
Enhanced Error Handlers for DevClaude_bot

Implements professional error handling strategies as recommended by Enhanced Architect Bot:
- Automatic retry with exponential backoff
- Graceful fallback mechanisms
- Comprehensive error context tracking
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from datetime import datetime, timedelta
import structlog

from .exceptions import DevClaudeError, TemporaryError, PermanentError

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class ErrorContextManager:
    """
    Manages error context across the application.

    Tracks error patterns, frequencies, and provides insights for debugging.
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.error_history: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}

    def record_error(self, error: DevClaudeError, context: Optional[Dict[str, Any]] = None):
        """Record an error occurrence with context."""
        error_record = {
            "timestamp": datetime.utcnow(),
            "error_type": error.__class__.__name__,
            "message": error.message,
            "error_code": error.error_code,
            "context": {**error.context, **(context or {})},
            "is_retryable": error.is_retryable(),
            "user_id": context.get("user_id") if context else None,
        }

        self.error_history.append(error_record)

        # Maintain history size
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)

        # Update counts
        error_type = error.__class__.__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.last_errors[error_type] = datetime.utcnow()

        logger.error(
            "Error recorded",
            error_type=error_type,
            message=error.message,
            context=error_record["context"],
            total_count=self.error_counts[error_type]
        )

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics and patterns."""
        now = datetime.utcnow()
        recent_errors = [
            e for e in self.error_history
            if (now - e["timestamp"]).total_seconds() < 3600  # Last hour
        ]

        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "error_counts": self.error_counts.copy(),
            "most_common": max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None,
            "last_errors": {k: v.isoformat() for k, v in self.last_errors.items()},
        }

    def is_error_frequent(self, error_type: str, threshold: int = 5, window_minutes: int = 10) -> bool:
        """Check if an error type is occurring frequently."""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)

        recent_count = sum(
            1 for e in self.error_history
            if e["error_type"] == error_type and e["timestamp"] >= window_start
        )

        return recent_count >= threshold


class RetryHandler:
    """
    Handles automatic retry logic with exponential backoff.

    Implements intelligent retry strategies based on error types and patterns.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    async def retry_async(
        self,
        func: Callable[..., T],
        *args,
        error_context: Optional[ErrorContextManager] = None,
        retry_on: tuple = (TemporaryError,),
        **kwargs
    ) -> T:
        """Retry an async function with exponential backoff."""
        last_error = None

        for attempt in range(self.max_attempts):
            try:
                logger.debug(f"Attempting function call", attempt=attempt + 1, max_attempts=self.max_attempts)
                result = await func(*args, **kwargs)

                if attempt > 0:
                    logger.info("Function succeeded after retry", attempt=attempt + 1)

                return result

            except Exception as e:
                last_error = e

                # Convert to DevClaudeError if needed
                if not isinstance(e, DevClaudeError):
                    from .exceptions import categorize_error, create_error
                    error_type = categorize_error(e)
                    e = create_error(error_type.replace("Error", "").lower(), str(e), previous_error=e)

                # Record error if context manager provided
                if error_context:
                    error_context.record_error(e, {"attempt": attempt + 1, "function": func.__name__})

                # Check if error is retryable
                if not isinstance(e, retry_on) and not e.is_retryable():
                    logger.error("Non-retryable error encountered", error=str(e), error_type=type(e).__name__)
                    raise e

                # Don't retry on last attempt
                if attempt == self.max_attempts - 1:
                    logger.error("Max retry attempts reached", error=str(e), attempts=self.max_attempts)
                    break

                # Calculate delay
                delay = self._calculate_delay(attempt, e)
                logger.warning(
                    "Retrying after error",
                    error=str(e),
                    attempt=attempt + 1,
                    delay=delay,
                    next_attempt=attempt + 2
                )

                await asyncio.sleep(delay)

        # All retries failed
        raise last_error

    def _calculate_delay(self, attempt: int, error: DevClaudeError) -> float:
        """Calculate retry delay with exponential backoff."""
        # Use error-specific retry_after if available
        if error.retry_after:
            return min(error.retry_after, self.max_delay)

        # Standard exponential backoff
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            delay *= (0.5 + random.random())  # 50-150% of calculated delay

        return delay


class FallbackHandler:
    """
    Handles fallback strategies when primary operations fail.

    Provides graceful degradation and alternative approaches.
    """

    def __init__(self):
        self.fallback_strategies: Dict[str, List[Callable]] = {}

    def register_fallback(self, operation: str, fallback_func: Callable, priority: int = 0):
        """Register a fallback function for an operation."""
        if operation not in self.fallback_strategies:
            self.fallback_strategies[operation] = []

        self.fallback_strategies[operation].append((priority, fallback_func))
        # Sort by priority (higher priority first)
        self.fallback_strategies[operation].sort(key=lambda x: x[0], reverse=True)

    async def execute_with_fallback(
        self,
        operation: str,
        primary_func: Callable,
        *args,
        error_context: Optional[ErrorContextManager] = None,
        **kwargs
    ) -> Any:
        """Execute function with fallback strategies."""
        try:
            logger.debug("Executing primary function", operation=operation)
            return await primary_func(*args, **kwargs)

        except Exception as e:
            logger.warning("Primary function failed, trying fallbacks", operation=operation, error=str(e))

            # Record error
            if error_context and isinstance(e, DevClaudeError):
                error_context.record_error(e, {"operation": operation, "stage": "primary"})

            # Try fallback strategies
            fallbacks = self.fallback_strategies.get(operation, [])

            for priority, fallback_func in fallbacks:
                try:
                    logger.debug("Trying fallback strategy", operation=operation, priority=priority)
                    result = await fallback_func(*args, **kwargs)
                    logger.info("Fallback strategy succeeded", operation=operation, priority=priority)
                    return result

                except Exception as fallback_error:
                    logger.warning(
                        "Fallback strategy failed",
                        operation=operation,
                        priority=priority,
                        error=str(fallback_error)
                    )

                    if error_context and isinstance(fallback_error, DevClaudeError):
                        error_context.record_error(
                            fallback_error,
                            {"operation": operation, "stage": "fallback", "priority": priority}
                        )

            # All fallbacks failed
            logger.error("All fallback strategies failed", operation=operation)
            raise e


class ErrorHandler:
    """
    Main error handler that coordinates retry and fallback strategies.

    Provides a unified interface for comprehensive error handling.
    """

    def __init__(
        self,
        retry_handler: Optional[RetryHandler] = None,
        fallback_handler: Optional[FallbackHandler] = None,
        error_context: Optional[ErrorContextManager] = None
    ):
        self.retry_handler = retry_handler or RetryHandler()
        self.fallback_handler = fallback_handler or FallbackHandler()
        self.error_context = error_context or ErrorContextManager()

    async def handle_operation(
        self,
        operation: str,
        func: Callable,
        *args,
        use_retry: bool = True,
        use_fallback: bool = True,
        **kwargs
    ) -> Any:
        """Handle an operation with comprehensive error handling."""
        logger.debug("Starting operation with error handling", operation=operation)

        try:
            if use_retry:
                # Execute with retry
                return await self.retry_handler.retry_async(
                    func, *args, error_context=self.error_context, **kwargs
                )
            else:
                # Execute without retry
                return await func(*args, **kwargs)

        except Exception as e:
            if use_fallback:
                # Try fallback strategies
                return await self.fallback_handler.execute_with_fallback(
                    operation, func, *args, error_context=self.error_context, **kwargs
                )
            else:
                # No fallback, re-raise error
                raise e

    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary."""
        return {
            "error_stats": self.error_context.get_error_stats(),
            "retry_config": {
                "max_attempts": self.retry_handler.max_attempts,
                "base_delay": self.retry_handler.base_delay,
                "max_delay": self.retry_handler.max_delay,
            },
            "available_fallbacks": list(self.fallback_handler.fallback_strategies.keys()),
        }