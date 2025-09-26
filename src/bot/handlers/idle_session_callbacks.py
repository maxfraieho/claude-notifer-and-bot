"""Handle idle session callbacks for IdleSessionManager."""

import structlog
from telegram import Update
from telegram.ext import ContextTypes

logger = structlog.get_logger()


async def handle_session_continue_callback(
    query, session_id: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle user decision to continue idle session."""
    user_id = query.from_user.id

    try:
        # Get idle session manager
        idle_session_manager = context.bot_data.get("idle_session_manager")
        if not idle_session_manager:
            logger.error("Idle session manager not available")
            await query.edit_message_text("❌ Сервіс недоступний")
            return

        # Handle session continue
        await idle_session_manager.handle_session_continue(session_id, user_id)

        # Update message
        await query.edit_message_text(
            "✅ **Сесію продовжено**\n\nВи можете продовжити роботу з Claude."
        )

        logger.info("Session continued by user", session_id=session_id, user_id=user_id)

    except Exception as e:
        logger.error("Session continue callback failed", error=str(e),
                    session_id=session_id, user_id=user_id)
        await query.edit_message_text(
            f"❌ **Помилка**\n\n{str(e)}"
        )


async def handle_session_close_callback(
    query, session_id: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle user decision to close idle session."""
    user_id = query.from_user.id

    try:
        # Get idle session manager
        idle_session_manager = context.bot_data.get("idle_session_manager")
        if not idle_session_manager:
            logger.error("Idle session manager not available")
            await query.edit_message_text("❌ Сервіс недоступний")
            return

        # Handle session close
        await idle_session_manager.handle_session_close(session_id, user_id)

        # Update message
        await query.edit_message_text(
            "❌ **Сесію закрито**\n\nВикористовуйте /new для створення нової сесії."
        )

        logger.info("Session closed by user", session_id=session_id, user_id=user_id)

    except Exception as e:
        logger.error("Session close callback failed", error=str(e),
                    session_id=session_id, user_id=user_id)
        await query.edit_message_text(
            f"❌ **Помилка**\n\n{str(e)}"
        )