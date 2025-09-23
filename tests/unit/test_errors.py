"""
Unit tests for enhanced error handling system.

Tests error hierarchy, handlers, and decorators.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.errors import (
    DevClaudeError,
    TemporaryError,
    PermanentError,
    ConfigurationError,
    AuthenticationError,
    SecurityError,
    ValidationError,
    RateLimitError,
    ClaudeIntegrationError,
    StorageError,
    ErrorHandler,
    RetryHandler,
    FallbackHandler,
    ErrorContextManager,
    handle_errors,
    retry_on_failure,
    with_fallback,
    create_error,
    categorize_error,
)


class TestErrorHierarchy:
    """Test error class hierarchy."""

    def test_devlaude_error_creation(self):
        """Test basic DevClaudeError creation."""
        error = DevClaudeError(
            message="Test error",
            error_code="TEST_ERROR",
            user_message="User friendly message"
        )

        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.user_message == "User friendly message"
        assert error.timestamp is not None
        assert isinstance(error.context, dict)

    def test_error_to_dict(self):
        """Test error serialization."""
        error = DevClaudeError(
            message="Test error",
            error_code="TEST_ERROR",
            context={"key": "value"}
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "DevClaudeError"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["context"]["key"] == "value"
        assert "timestamp" in error_dict

    def test_temporary_error(self):
        """Test TemporaryError behavior."""
        error = TemporaryError("Temporary issue", retry_after=10)

        assert error.is_retryable()
        assert error.retry_after == 10
        assert not error.requires_user_action()

    def test_permanent_error(self):
        """Test PermanentError behavior."""
        error = PermanentError("Permanent issue")

        assert not error.is_retryable()
        assert error.retry_after is None

    def test_configuration_error(self):
        """Test ConfigurationError specifics."""
        error = ConfigurationError(
            "Invalid config",
            config_key="test_key"
        )

        assert error.requires_user_action()
        assert error.context["config_key"] == "test_key"
        assert "configuration error" in error.user_message.lower()

    def test_authentication_error(self):
        """Test AuthenticationError specifics."""
        error = AuthenticationError(
            "Auth failed",
            user_id=123
        )

        assert error.requires_user_action()
        assert error.context["user_id"] == 123
        assert "authentication failed" in error.user_message.lower()

    def test_security_error(self):
        """Test SecurityError specifics."""
        error = SecurityError(
            "Security violation",
            security_context={"action": "forbidden"}
        )

        assert error.requires_user_action()
        assert error.context["security"]["action"] == "forbidden"
        assert "security error" in error.user_message.lower()

    def test_validation_error(self):
        """Test ValidationError specifics."""
        error = ValidationError(
            "Invalid input",
            field="email",
            value="invalid@"
        )

        assert error.requires_user_action()
        assert error.context["field"] == "email"
        assert error.context["value"] == "invalid@"

    def test_rate_limit_error(self):
        """Test RateLimitError specifics."""
        error = RateLimitError(
            "Rate limit exceeded",
            retry_after=60,
            limit_type="api"
        )

        assert error.is_retryable()
        assert error.retry_after == 60
        assert error.context["limit_type"] == "api"

    def test_claude_integration_error(self):
        """Test ClaudeIntegrationError specifics."""
        # Temporary error (connection issue)
        temp_error = ClaudeIntegrationError(
            "Connection timeout",
            integration_type="cli"
        )
        assert temp_error.is_retryable()

        # Permanent error
        perm_error = ClaudeIntegrationError(
            "Invalid API key",
            integration_type="sdk"
        )
        assert not perm_error.is_retryable()

    def test_storage_error(self):
        """Test StorageError specifics."""
        # Temporary error (connection issue)
        temp_error = StorageError(
            "Database connection lost",
            operation="select",
            table="users"
        )
        assert temp_error.is_retryable()

        # Permanent error (constraint violation)
        perm_error = StorageError(
            "Foreign key constraint violation",
            operation="insert",
            table="sessions"
        )
        assert not perm_error.is_retryable()


class TestErrorFactory:
    """Test error factory functions."""

    def test_create_error(self):
        """Test error creation factory."""
        error = create_error("config", "Test config error", config_key="test")

        assert isinstance(error, ConfigurationError)
        assert error.message == "Test config error"
        assert error.context["config_key"] == "test"

    def test_create_unknown_error(self):
        """Test creating unknown error type."""
        error = create_error("unknown", "Test error")

        assert isinstance(error, DevClaudeError)
        assert error.message == "Test error"

    def test_categorize_error(self):
        """Test error categorization."""
        # Test DevClaudeError instances
        config_error = ConfigurationError("Config error")
        assert categorize_error(config_error) == "ConfigurationError"

        # Test standard exceptions
        generic_error = Exception("Some database error occurred")
        category = categorize_error(generic_error)
        assert category == "StorageError"

        timeout_error = Exception("Connection timeout")
        category = categorize_error(timeout_error)
        assert category == "TemporaryError"


class TestErrorContextManager:
    """Test ErrorContextManager functionality."""

    def test_error_recording(self):
        """Test recording errors with context."""
        manager = ErrorContextManager()
        error = DevClaudeError("Test error")

        manager.record_error(error, {"user_id": 123})

        assert len(manager.error_history) == 1
        record = manager.error_history[0]
        assert record["error_type"] == "DevClaudeError"
        assert record["message"] == "Test error"
        assert record["context"]["user_id"] == 123

    def test_error_counts(self):
        """Test error counting."""
        manager = ErrorContextManager()

        # Record multiple errors
        error1 = ConfigurationError("Config error 1")
        error2 = ConfigurationError("Config error 2")
        error3 = AuthenticationError("Auth error")

        manager.record_error(error1)
        manager.record_error(error2)
        manager.record_error(error3)

        assert manager.error_counts["ConfigurationError"] == 2
        assert manager.error_counts["AuthenticationError"] == 1

    def test_error_stats(self):
        """Test error statistics generation."""
        manager = ErrorContextManager()
        error = DevClaudeError("Test error")
        manager.record_error(error)

        stats = manager.get_error_stats()

        assert stats["total_errors"] == 1
        assert "error_counts" in stats
        assert "most_common" in stats
        assert "last_errors" in stats

    def test_frequent_error_detection(self):
        """Test frequent error detection."""
        manager = ErrorContextManager()
        error = DevClaudeError("Frequent error")

        # Record many errors
        for _ in range(6):
            manager.record_error(error)

        assert manager.is_error_frequent("DevClaudeError", threshold=5, window_minutes=10)
        assert not manager.is_error_frequent("DevClaudeError", threshold=10, window_minutes=10)

    def test_history_limit(self):
        """Test error history size limit."""
        manager = ErrorContextManager(max_history=3)

        # Record more errors than limit
        for i in range(5):
            error = DevClaudeError(f"Error {i}")
            manager.record_error(error)

        assert len(manager.error_history) == 3
        # Should keep the most recent errors
        assert manager.error_history[-1]["message"] == "Error 4"


class TestRetryHandler:
    """Test RetryHandler functionality."""

    @pytest.fixture
    def retry_handler(self):
        """Create retry handler for testing."""
        return RetryHandler(max_attempts=3, base_delay=0.01)  # Fast delays for testing

    async def test_successful_retry(self, retry_handler):
        """Test successful operation without retry."""
        async def successful_func():
            return "success"

        result = await retry_handler.retry_async(successful_func)
        assert result == "success"

    async def test_retry_on_temporary_error(self, retry_handler):
        """Test retry on temporary errors."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TemporaryError("Temporary failure")
            return "success"

        result = await retry_handler.retry_async(failing_func)
        assert result == "success"
        assert call_count == 3

    async def test_no_retry_on_permanent_error(self, retry_handler):
        """Test no retry on permanent errors."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise PermanentError("Permanent failure")

        with pytest.raises(PermanentError):
            await retry_handler.retry_async(failing_func)

        assert call_count == 1  # Should not retry

    async def test_max_attempts_reached(self, retry_handler):
        """Test behavior when max attempts are reached."""
        call_count = 0

        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise TemporaryError("Always failing")

        with pytest.raises(TemporaryError):
            await retry_handler.retry_async(always_failing_func)

        assert call_count == 3  # max_attempts

    async def test_delay_calculation(self, retry_handler):
        """Test retry delay calculation."""
        # Test with error-specific retry_after
        error_with_delay = TemporaryError("Error", retry_after=5)
        delay = retry_handler._calculate_delay(0, error_with_delay)
        assert delay == 5

        # Test exponential backoff
        normal_error = TemporaryError("Error")
        delay1 = retry_handler._calculate_delay(0, normal_error)
        delay2 = retry_handler._calculate_delay(1, normal_error)
        assert delay2 > delay1


class TestFallbackHandler:
    """Test FallbackHandler functionality."""

    @pytest.fixture
    def fallback_handler(self):
        """Create fallback handler for testing."""
        return FallbackHandler()

    async def test_successful_primary_function(self, fallback_handler):
        """Test successful primary function execution."""
        async def primary_func():
            return "primary_success"

        result = await fallback_handler.execute_with_fallback(
            "test_operation",
            primary_func
        )
        assert result == "primary_success"

    async def test_fallback_execution(self, fallback_handler):
        """Test fallback function execution when primary fails."""
        async def primary_func():
            raise Exception("Primary failed")

        async def fallback_func():
            return "fallback_success"

        # Register fallback
        fallback_handler.register_fallback("test_operation", fallback_func)

        result = await fallback_handler.execute_with_fallback(
            "test_operation",
            primary_func
        )
        assert result == "fallback_success"

    async def test_multiple_fallbacks_priority(self, fallback_handler):
        """Test multiple fallbacks with priority ordering."""
        async def primary_func():
            raise Exception("Primary failed")

        async def fallback1():
            raise Exception("Fallback 1 failed")

        async def fallback2():
            return "fallback2_success"

        # Register fallbacks with different priorities
        fallback_handler.register_fallback("test_operation", fallback1, priority=10)
        fallback_handler.register_fallback("test_operation", fallback2, priority=5)

        result = await fallback_handler.execute_with_fallback(
            "test_operation",
            primary_func
        )
        assert result == "fallback2_success"

    async def test_all_fallbacks_fail(self, fallback_handler):
        """Test when all fallbacks fail."""
        async def primary_func():
            raise ValueError("Primary failed")

        async def fallback_func():
            raise Exception("Fallback failed")

        fallback_handler.register_fallback("test_operation", fallback_func)

        with pytest.raises(ValueError):  # Should raise original error
            await fallback_handler.execute_with_fallback(
                "test_operation",
                primary_func
            )


class TestErrorHandler:
    """Test ErrorHandler integration."""

    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing."""
        return ErrorHandler()

    async def test_successful_operation(self, error_handler):
        """Test successful operation handling."""
        async def successful_func():
            return "success"

        result = await error_handler.handle_operation(
            "test_op",
            successful_func
        )
        assert result == "success"

    async def test_operation_with_retry(self, error_handler):
        """Test operation with retry enabled."""
        call_count = 0

        async def sometimes_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TemporaryError("Temporary failure")
            return "success"

        result = await error_handler.handle_operation(
            "test_op",
            sometimes_failing_func,
            use_retry=True
        )
        assert result == "success"
        assert call_count == 2

    async def test_operation_with_fallback(self, error_handler):
        """Test operation with fallback enabled."""
        async def failing_func():
            raise Exception("Primary failed")

        async def fallback_func():
            return "fallback_success"

        # Register fallback
        error_handler.fallback_handler.register_fallback("test_op", fallback_func)

        result = await error_handler.handle_operation(
            "test_op",
            failing_func,
            use_retry=False,
            use_fallback=True
        )
        assert result == "fallback_success"


class TestErrorDecorators:
    """Test error handling decorators."""

    async def test_handle_errors_decorator(self):
        """Test handle_errors decorator."""
        call_count = 0

        @handle_errors(retry_count=2)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TemporaryError("Temporary failure")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 2

    async def test_retry_on_failure_decorator(self):
        """Test retry_on_failure decorator."""
        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TemporaryError("Failure")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 3

    async def test_with_fallback_decorator(self):
        """Test with_fallback decorator."""
        async def fallback_func():
            return "fallback_result"

        @with_fallback(fallback_func)
        async def test_func():
            raise Exception("Primary failed")

        result = await test_func()
        assert result == "fallback_result"

    def test_sync_decorators(self):
        """Test decorators with synchronous functions."""
        call_count = 0

        @retry_on_failure(max_attempts=2, delay=0.001)
        def sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TemporaryError("Failure")
            return "success"

        result = sync_func()
        assert result == "success"
        assert call_count == 2