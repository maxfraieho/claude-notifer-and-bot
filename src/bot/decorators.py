"""
Bot Command Decorators for DevClaude_bot

Provides decorators for authentication, authorization, and command logging.
Implements RBAC integration as recommended by Enhanced Architect Bot.
"""

import functools
from typing import Callable, Optional, List, Union
import structlog
from telegram import Update
from telegram.ext import ContextTypes

from src.errors import handle_errors, AuthenticationError, SecurityError
from src.security.rbac import Permission
from src.localization.helpers import get_text

logger = structlog.get_logger(__name__)


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for bot commands.

    Checks if user is authenticated and session is valid.
    """
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id

        # Get auth manager from handler instance
        auth_manager = getattr(self, 'auth_manager', None)
        if not auth_manager:
            logger.error("Auth manager not found in handler")
            await update.message.reply_text("❌ Authentication system error")
            return

        # Check authentication
        try:
            session = await auth_manager.get_session(user_id)
            if not session:
                await update.message.reply_text(
                    get_text("error.authentication_required", update.effective_user.language_code)
                )
                return

            # Check if session is expired
            if session.is_expired():
                await auth_manager.end_session(user_id)
                await update.message.reply_text(
                    get_text("error.session_expired", update.effective_user.language_code)
                )
                return

            # Refresh session
            session.refresh()

            # Call original function
            return await func(self, update, context, *args, **kwargs)

        except Exception as e:
            logger.error("Authentication error in decorator", error=str(e), user_id=user_id)
            await update.message.reply_text("❌ Authentication error")

    return wrapper


def require_permission(
    permission: Union[Permission, List[Permission]],
    all_required: bool = True
) -> Callable:
    """
    Decorator to require specific permissions for bot commands.

    Args:
        permission: Single permission or list of permissions
        all_required: If True, user must have ALL permissions. If False, ANY permission is sufficient.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id

            # Get auth manager from handler instance
            auth_manager = getattr(self, 'auth_manager', None)
            if not auth_manager:
                logger.error("Auth manager not found in handler")
                await update.message.reply_text("❌ Authentication system error")
                return

            try:
                # Get user session
                session = await auth_manager.get_session(user_id)
                if not session:
                    await update.message.reply_text(
                        get_text("error.authentication_required", update.effective_user.language_code)
                    )
                    return

                # Check permissions
                permissions_to_check = [permission] if isinstance(permission, Permission) else permission

                if all_required:
                    # User must have ALL permissions
                    for perm in permissions_to_check:
                        if not session.has_permission(perm):
                            await update.message.reply_text(
                                get_text("error.permission_denied", update.effective_user.language_code) +
                                f"\nRequired: {perm.value}"
                            )
                            logger.warning(
                                "Permission denied",
                                user_id=user_id,
                                required_permission=perm.value,
                                user_roles=session.get_roles()
                            )
                            return
                else:
                    # User must have ANY permission
                    has_any = any(session.has_permission(perm) for perm in permissions_to_check)
                    if not has_any:
                        perm_names = [p.value for p in permissions_to_check]
                        await update.message.reply_text(
                            get_text("error.permission_denied", update.effective_user.language_code) +
                            f"\nRequired (any): {', '.join(perm_names)}"
                        )
                        logger.warning(
                            "Permission denied - no matching permissions",
                            user_id=user_id,
                            required_permissions=perm_names,
                            user_roles=session.get_roles()
                        )
                        return

                # All permission checks passed
                return await func(self, update, context, *args, **kwargs)

            except SecurityError as e:
                await update.message.reply_text(e.user_message)
                logger.error("Security error in permission check", error=str(e), user_id=user_id)
            except Exception as e:
                logger.error("Error checking permissions", error=str(e), user_id=user_id)
                await update.message.reply_text("❌ Permission check error")

        return wrapper
    return decorator


def admin_only(func: Callable) -> Callable:
    """
    Decorator to restrict commands to admin users only.

    Shorthand for @require_permission(Permission.ADMIN_SYSTEM)
    """
    return require_permission(Permission.ADMIN_SYSTEM)(func)


def user_only(func: Callable) -> Callable:
    """
    Decorator to restrict commands to authenticated users.

    Allows any authenticated user (equivalent to @require_auth).
    """
    return require_auth(func)


def log_command(func: Callable) -> Callable:
    """
    Decorator to log command usage with context.

    Logs command execution, user info, and execution time.
    """
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        import time

        user_id = update.effective_user.id
        username = update.effective_user.username
        command = update.message.text.split()[0] if update.message.text else "unknown"

        start_time = time.time()

        logger.info(
            "Command started",
            command=command,
            user_id=user_id,
            username=username,
            chat_id=update.effective_chat.id
        )

        try:
            result = await func(self, update, context, *args, **kwargs)

            execution_time = time.time() - start_time
            logger.info(
                "Command completed",
                command=command,
                user_id=user_id,
                execution_time=f"{execution_time:.2f}s"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Command failed",
                command=command,
                user_id=user_id,
                execution_time=f"{execution_time:.2f}s",
                error=str(e)
            )
            raise

    return wrapper


def rate_limited(
    calls_per_minute: int = 10,
    burst_limit: int = 20
) -> Callable:
    """
    Decorator to apply rate limiting to commands.

    Args:
        calls_per_minute: Maximum calls per minute per user
        burst_limit: Maximum burst calls before rate limiting kicks in
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id

            # Get rate limiter from handler instance
            rate_limiter = getattr(self, 'rate_limiter', None)
            if not rate_limiter:
                # No rate limiter available, proceed without limiting
                return await func(self, update, context, *args, **kwargs)

            try:
                # Check rate limit
                if not await rate_limiter.check_rate_limit(user_id):
                    await update.message.reply_text(
                        get_text("error.rate_limit_exceeded", update.effective_user.language_code)
                    )
                    return

                return await func(self, update, context, *args, **kwargs)

            except Exception as e:
                logger.error("Rate limiting error", error=str(e), user_id=user_id)
                # Proceed without rate limiting if there's an error
                return await func(self, update, context, *args, **kwargs)

        return wrapper
    return decorator


def development_only(func: Callable) -> Callable:
    """
    Decorator to restrict commands to development mode only.

    Commands decorated with this will only work when the bot is in development mode.
    """
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Get config from handler instance
        config = getattr(self, 'config', None)
        if not config:
            logger.error("Config not found in handler")
            await update.message.reply_text("❌ Configuration error")
            return

        if not config.development_mode:
            await update.message.reply_text(
                "🚫 This command is only available in development mode"
            )
            return

        return await func(self, update, context, *args, **kwargs)

    return wrapper


def with_error_handling(
    retry_count: int = 1,
    fallback_message: str = "❌ Command failed. Please try again."
) -> Callable:
    """
    Decorator to add error handling to bot commands.

    Args:
        retry_count: Number of retry attempts
        fallback_message: Message to send if command fails
    """
    def decorator(func: Callable) -> Callable:
        @handle_errors(retry_count=retry_count, operation_name=f"command.{func.__name__}")
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            try:
                return await func(self, update, context, *args, **kwargs)
            except Exception as e:
                logger.error(f"Unhandled error in command {func.__name__}", error=str(e))
                await update.message.reply_text(fallback_message)
                raise

        return wrapper
    return decorator


# Convenience decorators combining multiple requirements
def admin_command(func: Callable) -> Callable:
    """Decorator for admin-only commands with full error handling and logging."""
    return log_command(
        with_error_handling()(
            admin_only(func)
        )
    )


def user_command(func: Callable) -> Callable:
    """Decorator for user commands with authentication and logging."""
    return log_command(
        with_error_handling()(
            user_only(func)
        )
    )


def public_command(func: Callable) -> Callable:
    """Decorator for public commands (no authentication required)."""
    return log_command(
        with_error_handling()(func)
    )