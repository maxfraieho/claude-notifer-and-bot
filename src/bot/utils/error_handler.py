"""
Error handling utilities.
New: Resolves all silent failures with user guidance.
"""

import structlog
from telegram import Update
from telegram.ext import ContextTypes
from src.localization.util import t

logger = structlog.get_logger(__name__)

async def safe_user_error(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, exception: Exception = None):
    """Handle errors with localized, helpful messages."""
    try:
        user_id = update.effective_user.id if update.effective_user else None
        error_msg = await t(context, user_id, key) if user_id else "❌ Виникла помилка. Спробуйте пізніше."
        
        if exception:
            guidance_key = f"{key}_guidance"
            try:
                guidance = await t(context, user_id, guidance_key) if user_id else ""
                if guidance and guidance != guidance_key:  # Check if translation exists
                    error_msg += f"\n\n{guidance}"
            except:
                pass  # No guidance available
            
            if user_id:
                logger.error("User error", error=str(exception), user_id=user_id)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        elif update.message:
            await update.message.reply_text(error_msg)
    except Exception as e:
        # Fallback
        fallback = "❌ Виникла помилка. Спробуйте пізніше."
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(fallback)
            elif update.message:
                await update.message.reply_text(fallback)
        except:
            pass  # Ultimate fallback - do nothing
        logger.error("Fallback error handling failed", error=str(e))

async def safe_critical_error(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, exception: Exception = None):
    """Handle critical errors that block functionality."""
    await safe_user_error(update, context, key, exception)