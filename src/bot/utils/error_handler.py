"""
Покращена система обробки помилок для Claude Bot
"""

import logging
import traceback
from typing import Optional, Dict, Any
from functools import wraps
from telegram import Message
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Клас для централізованої обробки помилок"""

    @staticmethod
    async def handle_error(
        error: Exception,
        message: Optional[Message] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Централізована обробка помилок"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }

        # Логуємо помилку
        logger.error(f"Error occurred: {error_info}")

        # Відправляємо повідомлення користувачу
        if message:
            try:
                user_message = ErrorHandler.get_user_friendly_message(error)
                await message.reply_text(user_message)
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")

    @staticmethod
    def get_user_friendly_message(error: Exception) -> str:
        """Отримати зрозуміле користувачу повідомлення про помилку"""
        error_messages = {
            "ConnectionError": "🌐 Проблема з підключенням. Спробуйте пізніше.",
            "TimeoutError": "⏰ Операція зайняла забагато часу. Спробуйте ще раз.",
            "PermissionError": "🔒 Недостатньо прав для виконання операції.",
            "FileNotFoundError": "📁 Файл не знайдено.",
            "ValueError": "❌ Неправильне значення параметра.",
            "TelegramError": "📡 Помилка Telegram API. Спробуйте пізніше."
        }

        error_type = type(error).__name__
        return error_messages.get(error_type, "❌ Виникла непередбачена помилка. Спробуйте ще раз.")

def error_handler(func):
    """Декоратор для автоматичної обробки помилок"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Спробуємо знайти об'єкт message в аргументах
            message = None
            for arg in args:
                if hasattr(arg, 'reply_text'):
                    message = arg
                    break

            await ErrorHandler.handle_error(e, message, {
                "function": func.__name__,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200]
            })

            # Повторно підіймаємо помилку для обробки на вищому рівні
            raise

    return wrapper

def safe_execute(func):
    """Декоратор для безпечного виконання функцій без підіймання помилок"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Safe execution failed for {func.__name__}: {e}")
            return None

    return wrapper

async def safe_user_error(update_or_message, context_or_text, key_or_exception=None, exception=None):
    """Безпечне відправлення повідомлення про помилку користувачу з покращеним логуванням"""
    try:
        # Детальне логування помилки для діагностики
        if exception:
            logger.error(
                "Error in command execution",
                error=str(exception),
                error_type=type(exception).__name__,
                user_context=f"Update: {type(update_or_message).__name__}" if hasattr(update_or_message, '__class__') else "Unknown"
            )

        # Якщо це старий формат (message, text)
        if isinstance(context_or_text, str) and not hasattr(context_or_text, 'bot'):
            message = update_or_message
            error_text = context_or_text
            await message.reply_text(f"❌ {error_text}")
            logger.info("Error message sent to user", error_type="direct_text")
            return

        # Якщо це новий формат з локалізацією (update, context, key, exception)
        from src.localization.i18n import i18n, _

        # Спробуємо отримати локалізований текст
        try:
            if key_or_exception and isinstance(key_or_exception, str):
                error_text = _(key_or_exception)
                logger.debug("Using localized error message", key=key_or_exception)
            else:
                error_text = "❌ Виникла помилка. Спробуйте ще раз або зверніться до адміністратора."
                logger.warning("Using fallback error message", reason="no_key_provided")
        except Exception as loc_error:
            error_text = "❌ Виникла помилка. Спробуйте ще раз або зверніться до адміністратора."
            logger.error("Localization failed", error=str(loc_error))

        # Відправляємо повідомлення з кращою діагностикою
        message_sent = False
        if hasattr(update_or_message, 'effective_message'):
            await update_or_message.effective_message.reply_text(error_text)
            message_sent = True
        elif hasattr(update_or_message, 'reply_text'):
            await update_or_message.reply_text(error_text)
            message_sent = True
        elif hasattr(update_or_message, 'edit_message_text'):
            await update_or_message.edit_message_text(error_text)
            message_sent = True

        if message_sent:
            logger.info("Error message successfully sent to user")
        else:
            logger.error("Failed to find method to send error message", update_type=type(update_or_message).__name__)

    except Exception as e:
        logger.error("Critical failure in safe_user_error", error=str(e), error_type=type(e).__name__)

async def safe_critical_error(update, context, message, exception=None):
    """Відправка критичної помилки"""
    await safe_user_error(update, context, f"🚨 Критична помилка: {message}", exception)
