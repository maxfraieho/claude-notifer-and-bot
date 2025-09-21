"""Claude availability middleware for intercepting requests."""

import structlog
from typing import Optional, Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

from ...config.settings import Settings

logger = structlog.get_logger(__name__)


class ClaudeAvailabilityMiddleware:
    """Middleware для перевірки доступності перед запитами згідно з планом."""

    def __init__(self, settings: Settings):
        """Initialize the middleware."""
        self.settings = settings
        self.enabled = settings.claude_availability.enabled

    def is_claude_request(self, update: Update) -> bool:
        """Перевірити, чи є це запит до Claude."""
        if not update or not update.message:
            return False

        # Пропустити команди (починаються з /)
        if update.message.text and update.message.text.startswith('/'):
            return False

        # Пропустити callback queries
        if update.callback_query:
            return False

        # Текстові повідомлення та документи можуть бути запитами до Claude
        return bool(update.message.text or update.message.document)

    async def handle_unavailable(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                details: dict) -> bool:
        """Обробити ситуацію коли Claude недоступний."""
        try:
            # Отримати локалізований текст
            status_message = details.get("status_message", "🔴 Claude зараз недоступний")

            # Побудувати повідомлення
            message_parts = [status_message]

            if "estimated_recovery" in details:
                message_parts.append(f"\n⏳ {details['estimated_recovery']}")

            message_parts.append("\n\n💡 Я повідомлю в групу, коли Claude стане доступний")
            message_parts.append("📋 Використайте /claude_status для перевірки")

            full_message = "".join(message_parts)

            # Надіслати повідомлення користувачу
            await update.message.reply_text(full_message, parse_mode=None)

            logger.info("Claude unavailable - user notified",
                       user_id=update.effective_user.id,
                       reason=details.get("reason"))

            return True  # Запит оброблено

        except Exception as e:
            logger.error(f"Error handling unavailable Claude: {e}")
            return False

    async def __call__(self, handler: Callable, update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Middleware entry point."""
        if not self.enabled:
            return await handler(update, context)

        # Перевірити, чи це запит до Claude
        if not self.is_claude_request(update):
            return await handler(update, context)

        # Отримати availability monitor
        availability_monitor = context.bot_data.get("claude_availability_monitor")
        if not availability_monitor:
            # Якщо немає монітора, продовжити нормально
            return await handler(update, context)

        try:
            # Перевірити доступність з кешем
            is_available, details = await availability_monitor.is_claude_available_cached()

            if not is_available:
                # Claude недоступний - повідомити користувача
                handled = await self.handle_unavailable(update, context, details)
                if handled:
                    return None  # Запит оброблено, не передавати далі

            # Claude доступний або не вдалося перевірити - продовжити
            return await handler(update, context)

        except Exception as e:
            logger.error(f"Error in Claude availability middleware: {e}")
            # При помилці продовжити нормально
            return await handler(update, context)


async def claude_availability_middleware(handler: Callable, update: Update,
                                       context: ContextTypes.DEFAULT_TYPE) -> Any:
    """Функція middleware для реєстрації в системі."""
    settings: Settings = context.get("settings")
    if not settings:
        return await handler(update, context)

    middleware = ClaudeAvailabilityMiddleware(settings)
    return await middleware(handler, update, context)