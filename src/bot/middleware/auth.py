"""Telegram bot authentication middleware."""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List

import structlog

logger = structlog.get_logger()


def check_user_access(user_id: int, whitelist: List[int]) -> bool:
    """Покращена перевірка доступу користувача"""
    is_allowed = user_id in whitelist
    logger.info("Access check", user_id=user_id, allowed=is_allowed)
    return is_allowed


async def auth_middleware(handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
    """Check authentication before processing messages.

    This middleware:
    1. Checks if user is authenticated
    2. Attempts authentication if not authenticated
    3. Updates session activity
    4. Logs authentication events
    """
    # Extract user information
    user_id = event.effective_user.id if event.effective_user else None
    username = (
        getattr(event.effective_user, "username", None)
        if event.effective_user
        else None
    )

    if not user_id:
        logger.warning("No user information in update")
        return

    # Get dependencies from context
    auth_manager = data.get("auth_manager")
    audit_logger = data.get("audit_logger")

    if not auth_manager:
        logger.error("Authentication manager not available in middleware context")
        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 Authentication system unavailable. Please try again later."
            )
        return

    # Check if user is already authenticated
    if auth_manager.is_authenticated(user_id):
        # Update session activity
        if auth_manager.refresh_session(user_id):
            session = auth_manager.get_session(user_id)
            logger.debug(
                "Session refreshed",
                user_id=user_id,
                username=username,
                auth_provider=session.auth_provider if session else None,
            )

        # Continue to handler
        return await handler(event, data)

    # User not authenticated - attempt authentication once per update
    update_id = str(event.update_id) if hasattr(event, 'update_id') else str(hash(str(event)))
    processed_updates = data.setdefault('_processed_auth_updates', set())

    if update_id in processed_updates:
        logger.debug("Authentication already processed for this update", update_id=update_id)
        return

    processed_updates.add(update_id)

    logger.info(
        "Attempting authentication for user", user_id=user_id, username=username
    )

    # Try to authenticate (providers will check whitelist and tokens)
    authentication_successful = await auth_manager.authenticate_user(user_id)

    # Log authentication attempt
    if audit_logger:
        await audit_logger.log_auth_attempt(
            user_id=user_id,
            success=authentication_successful,
            method="automatic",
            reason="message_received",
        )

    if authentication_successful:
        session = auth_manager.get_session(user_id)
        logger.info(
            "User authenticated successfully",
            user_id=user_id,
            username=username,
            auth_provider=session.auth_provider if session else None,
        )

        # Log authentication success (welcome message handled by /start command)
        logger.info(
            "New user session started",
            user_id=user_id,
            username=username,
            session_time=datetime.utcnow().isoformat()
        )

        # Continue to handler
        return await handler(event, data)

    else:
        # Authentication failed - only send message once per update and not for commands
        logger.warning("Authentication failed", user_id=user_id, username=username)

        # Don't send auth error message if this is a command - let command handler deal with it
        message_text = getattr(event.effective_message, 'text', '') if event.effective_message else ''
        is_command = message_text.startswith('/') if message_text else False

        if event.effective_message and not is_command:
            await event.effective_message.reply_text(
                "🔒 **Authentication Required**\n\n"
                "You are not authorized to use this bot.\n"
                "Please contact the administrator for access.\n\n"
                f"Your Telegram ID: `{user_id}`\n"
                "Share this ID with the administrator to request access."
            )
        return  # Stop processing


async def require_auth(handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
    """Decorator-style middleware that requires authentication.

    This is a stricter version that only allows authenticated users.
    """
    user_id = event.effective_user.id if event.effective_user else None
    auth_manager = data.get("auth_manager")

    if not auth_manager or not auth_manager.is_authenticated(user_id):
        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 Authentication required to use this command."
            )
        return

    return await handler(event, data)


async def admin_required(handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
    """Middleware that requires admin privileges.

    Note: This is a placeholder - admin privileges would need to be
    implemented in the authentication system.
    """
    user_id = event.effective_user.id if event.effective_user else None
    auth_manager = data.get("auth_manager")

    if not auth_manager or not auth_manager.is_authenticated(user_id):
        if event.effective_message:
            await event.effective_message.reply_text("🔒 Authentication required.")
        return

    session = auth_manager.get_session(user_id)
    if not session or not session.user_info:
        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 Session information unavailable."
            )
        return

    # Check for admin permissions (placeholder logic)
    permissions = session.user_info.get("permissions", [])
    if "admin" not in permissions:
        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 **Admin Access Required**\n\n"
                "This command requires administrator privileges."
            )
        return

    return await handler(event, data)
