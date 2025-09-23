"""
Enhanced Error Hierarchy for DevClaude_bot

Implements structured error types as recommended by Enhanced Architect Bot analysis.
Provides clear error classification and context for better error handling.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime
import traceback


class DevClaudeError(Exception):
    """
    Base exception for all DevClaude_bot errors.

    Provides enhanced error context and categorization for better debugging
    and error handling strategies.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        retry_after: Optional[int] = None,
        previous_error: Optional[Exception] = None,
    ):
        super().__init__(message)

        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.user_message = user_message or "An error occurred. Please try again."
        self.retry_after = retry_after
        self.previous_error = previous_error
        self.timestamp = datetime.utcnow()
        self.traceback_str = traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "user_message": self.user_message,
            "retry_after": self.retry_after,
            "timestamp": self.timestamp.isoformat(),
            "previous_error": str(self.previous_error) if self.previous_error else None,
        }

    def is_retryable(self) -> bool:
        """Determine if this error should trigger a retry."""
        return isinstance(self, TemporaryError)

    def requires_user_action(self) -> bool:
        """Determine if this error requires user intervention."""
        return isinstance(self, (AuthenticationError, ValidationError, ConfigurationError))


class TemporaryError(DevClaudeError):
    """Base class for temporary errors that should be retried."""

    def __init__(self, message: str, retry_after: int = 5, **kwargs):
        super().__init__(message, retry_after=retry_after, **kwargs)


class PermanentError(DevClaudeError):
    """Base class for permanent errors that should not be retried."""
    pass


class ConfigurationError(PermanentError):
    """Configuration-related errors."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            context={"config_key": config_key},
            user_message="Configuration error. Please check your settings.",
            **kwargs
        )


class AuthenticationError(PermanentError):
    """Authentication and authorization errors."""

    def __init__(self, message: str, user_id: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            context={"user_id": user_id},
            user_message="Authentication failed. Please check your permissions.",
            **kwargs
        )


class SecurityError(PermanentError):
    """Security-related errors."""

    def __init__(self, message: str, security_context: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            message,
            context={"security": security_context or {}},
            user_message="Security error. Access denied.",
            **kwargs
        )


class ValidationError(PermanentError):
    """Input validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, **kwargs):
        super().__init__(
            message,
            context={"field": field, "value": str(value) if value is not None else None},
            user_message="Invalid input. Please check your data and try again.",
            **kwargs
        )


class RateLimitError(TemporaryError):
    """Rate limiting errors."""

    def __init__(self, message: str, retry_after: int = 60, limit_type: str = "general", **kwargs):
        super().__init__(
            message,
            retry_after=retry_after,
            context={"limit_type": limit_type},
            user_message=f"Rate limit exceeded. Please wait {retry_after} seconds.",
            **kwargs
        )


class ClaudeIntegrationError(DevClaudeError):
    """Claude CLI/SDK integration errors."""

    def __init__(
        self,
        message: str,
        integration_type: str = "cli",
        claude_error: Optional[str] = None,
        **kwargs
    ):
        # Determine if this is retryable based on error type
        is_temporary = "timeout" in message.lower() or "connection" in message.lower()

        super().__init__(
            message,
            context={
                "integration_type": integration_type,
                "claude_error": claude_error,
                "is_temporary": is_temporary
            },
            user_message="Claude integration error. Please try again.",
            retry_after=10 if is_temporary else None,
            **kwargs
        )

    def is_retryable(self) -> bool:
        """Claude errors are retryable if they're connection/timeout related."""
        return self.context.get("is_temporary", False)


class StorageError(DevClaudeError):
    """Database and storage errors."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        # Most storage errors are temporary (connection issues, locks, etc.)
        is_temporary = not any(keyword in message.lower() for keyword in ["constraint", "foreign key", "syntax"])

        super().__init__(
            message,
            context={
                "operation": operation,
                "table": table,
                "is_temporary": is_temporary
            },
            user_message="Storage error. Please try again.",
            retry_after=5 if is_temporary else None,
            **kwargs
        )

    def is_retryable(self) -> bool:
        """Storage errors are retryable unless they're schema/constraint violations."""
        return self.context.get("is_temporary", False)


class MCPError(DevClaudeError):
    """MCP (Model Context Protocol) related errors."""

    def __init__(
        self,
        message: str,
        mcp_provider: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            context={"mcp_provider": mcp_provider, "operation": operation},
            user_message="MCP integration error. Please try again.",
            **kwargs
        )


class ImageProcessingError(DevClaudeError):
    """Image processing related errors."""

    def __init__(
        self,
        message: str,
        image_format: Optional[str] = None,
        file_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            context={"image_format": image_format, "file_size": file_size},
            user_message="Image processing error. Please check your image and try again.",
            **kwargs
        )


class LocalizationError(DevClaudeError):
    """Localization and translation errors."""

    def __init__(
        self,
        message: str,
        language_code: Optional[str] = None,
        key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            context={"language_code": language_code, "key": key},
            user_message="Localization error occurred.",
            **kwargs
        )


# Error Registry for dynamic error handling
ERROR_REGISTRY = {
    "config": ConfigurationError,
    "auth": AuthenticationError,
    "security": SecurityError,
    "validation": ValidationError,
    "rate_limit": RateLimitError,
    "claude": ClaudeIntegrationError,
    "storage": StorageError,
    "mcp": MCPError,
    "image": ImageProcessingError,
    "localization": LocalizationError,
}


def create_error(error_type: str, message: str, **kwargs) -> DevClaudeError:
    """Factory function to create errors by type."""
    error_class = ERROR_REGISTRY.get(error_type, DevClaudeError)
    return error_class(message, **kwargs)


def categorize_error(error: Exception) -> str:
    """Categorize an unknown error into our error hierarchy."""
    error_msg = str(error).lower()

    if isinstance(error, DevClaudeError):
        return error.__class__.__name__

    # Categorize based on error message patterns
    if "config" in error_msg or "setting" in error_msg:
        return "ConfigurationError"
    elif "auth" in error_msg or "permission" in error_msg:
        return "AuthenticationError"
    elif "rate" in error_msg and "limit" in error_msg:
        return "RateLimitError"
    elif "claude" in error_msg:
        return "ClaudeIntegrationError"
    elif "database" in error_msg or "sql" in error_msg:
        return "StorageError"
    elif "timeout" in error_msg or "connection" in error_msg:
        return "TemporaryError"
    else:
        return "DevClaudeError"