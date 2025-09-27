"""Utilities for message management including user preferences."""

import structlog
from telegram import Message
from telegram.ext import ContextTypes

logger = structlog.get_logger()


async def safe_delete_message(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    delay_seconds: float = 3.0
) -> None:
    """
    Safely delete a message respecting user's preserve_messages setting.

    Args:
        message: Telegram message to delete
        context: Bot context
        user_id: User ID to check settings for
        delay_seconds: Delay before deletion (default: 3.0 seconds)
    """
    try:
        # Check user's preserve_messages setting
        user_settings = context.bot_data.get("user_settings", {}).get(user_id, {})
        preserve_messages = user_settings.get("preserve_messages", False)

        # If user wants to preserve messages, don't delete
        if preserve_messages:
            logger.debug(
                "Preserving message due to user setting",
                user_id=user_id,
                message_id=message.message_id
            )
            return

        # Otherwise, delete with delay (default behavior)
        import asyncio
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        await message.delete()
        logger.debug(
            "Message deleted",
            user_id=user_id,
            message_id=message.message_id,
            delay_seconds=delay_seconds
        )

    except Exception as e:
        logger.warning(
            "Failed to delete message",
            error=str(e),
            user_id=user_id,
            message_id=getattr(message, 'message_id', 'unknown')
        )


async def get_user_preserve_setting(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """
    Get user's preserve_messages setting.

    Returns:
        bool: True if user wants to preserve messages, False otherwise
    """
    # First check runtime cache
    user_settings = context.bot_data.get("user_settings", {}).get(user_id, {})
    preserve_messages = user_settings.get("preserve_messages")

    if preserve_messages is not None:
        return preserve_messages

    # If not in cache, load from database
    storage = context.bot_data.get("storage")
    if storage:
        try:
            user_settings = await storage.users.get_user_settings(user_id) or {}
            preserve_messages = user_settings.get("preserve_messages", False)

            # Cache the result for this session
            if "user_settings" not in context.bot_data:
                context.bot_data["user_settings"] = {}
            if user_id not in context.bot_data["user_settings"]:
                context.bot_data["user_settings"][user_id] = {}
            context.bot_data["user_settings"][user_id]["preserve_messages"] = preserve_messages

            return preserve_messages
        except Exception as e:
            logger.warning("Failed to load user preserve setting", error=str(e), user_id=user_id)

    # TEMP: Default preserve messages while debugging context
    return True