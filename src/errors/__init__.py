"""
Enhanced Error Handling System for DevClaude_bot

Implements comprehensive error management as recommended by Enhanced Architect Bot:
- Structured error hierarchy
- Automatic retry mechanisms
- Fallback strategies
- Error context tracking
"""

from .exceptions import (
    DevClaudeError,
    ConfigurationError,
    AuthenticationError,
    ClaudeIntegrationError,
    SecurityError,
    RateLimitError,
    StorageError,
    ValidationError,
    TemporaryError,
    PermanentError,
)

from .handlers import (
    ErrorHandler,
    RetryHandler,
    FallbackHandler,
    ErrorContextManager,
)

from .decorators import (
    handle_errors,
    retry_on_failure,
    with_fallback,
    log_errors,
)

__all__ = [
    # Exceptions
    "DevClaudeError",
    "ConfigurationError",
    "AuthenticationError",
    "ClaudeIntegrationError",
    "SecurityError",
    "RateLimitError",
    "StorageError",
    "ValidationError",
    "TemporaryError",
    "PermanentError",

    # Handlers
    "ErrorHandler",
    "RetryHandler",
    "FallbackHandler",
    "ErrorContextManager",

    # Decorators
    "handle_errors",
    "retry_on_failure",
    "with_fallback",
    "log_errors",
]