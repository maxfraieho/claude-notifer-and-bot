"""Manager for handling idle session timeouts with user confirmation."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Set
import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from ..localization.wrapper import t

logger = structlog.get_logger()


class IdleSessionManager:
    """Manages idle session detection and user confirmation for session termination."""

    def __init__(self, telegram_app: Application, idle_timeout_minutes: int = 5):
        """Initialize idle session manager.

        Args:
            telegram_app: Telegram bot application for sending messages
            idle_timeout_minutes: Minutes of inactivity before asking for confirmation
        """
        self.app = telegram_app
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self.pending_confirmations: Dict[str, asyncio.Task] = {}
        self.warned_sessions: Set[str] = set()

    async def track_session_activity(self, session_id: str, user_id: int) -> None:
        """Track session activity and reset idle timer.

        Args:
            session_id: Claude session ID
            user_id: Telegram user ID
        """
        # Cancel existing idle timer if any
        if session_id in self.pending_confirmations:
            self.pending_confirmations[session_id].cancel()

        # Remove from warned sessions (user is active again)
        self.warned_sessions.discard(session_id)

        # Start new idle timer
        task = asyncio.create_task(
            self._start_idle_timer(session_id, user_id)
        )
        self.pending_confirmations[session_id] = task

        logger.debug("Session activity tracked",
                    session_id=session_id,
                    user_id=user_id,
                    idle_timeout_minutes=self.idle_timeout.total_seconds() / 60)

    async def _start_idle_timer(self, session_id: str, user_id: int) -> None:
        """Start idle timer for a session.

        Args:
            session_id: Claude session ID
            user_id: Telegram user ID
        """
        try:
            # Wait for idle timeout
            await asyncio.sleep(self.idle_timeout.total_seconds())

            # Check if session is still active and not already warned
            if session_id not in self.warned_sessions:
                await self._send_idle_confirmation(session_id, user_id)

        except asyncio.CancelledError:
            logger.debug("Idle timer cancelled", session_id=session_id)
        except Exception as e:
            logger.error("Error in idle timer", session_id=session_id, error=str(e))
        finally:
            # Clean up
            self.pending_confirmations.pop(session_id, None)

    async def _send_idle_confirmation(self, session_id: str, user_id: int) -> None:
        """Send idle session confirmation message to user.

        Args:
            session_id: Claude session ID
            user_id: Telegram user ID
        """
        try:
            # Mark as warned to avoid duplicate messages
            self.warned_sessions.add(session_id)

            # Get localized text
            try:
                from ..di.container import DIContainer
                container = DIContainer.get_instance()
                localization = await container.get("localization")

                title = await localization.get_text(
                    user_id, "session.idle.title"
                ) or "🕒 Неактивна сесія"

                message = await localization.get_text(
                    user_id, "session.idle.message",
                    timeout_minutes=int(self.idle_timeout.total_seconds() / 60)
                ) or f"Ваша сесія з Claude неактивна вже {int(self.idle_timeout.total_seconds() / 60)} хвилин.\n\nБажаєте продовжити роботу чи закрити сесію?"

                continue_text = await localization.get_text(
                    user_id, "session.idle.continue"
                ) or "✅ Продовжити"

                close_text = await localization.get_text(
                    user_id, "session.idle.close"
                ) or "❌ Закрити сесію"

            except Exception as e:
                logger.warning("Could not get localized text", error=str(e))
                # Fallback to hardcoded Ukrainian text
                title = "🕒 Неактивна сесія"
                message = f"Ваша сесія з Claude неактивна вже {int(self.idle_timeout.total_seconds() / 60)} хвилин.\n\nБажаєте продовжити роботу чи закрити сесію?"
                continue_text = "✅ Продовжити"
                close_text = "❌ Закрити сесію"

            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton(
                        continue_text,
                        callback_data=f"session_continue:{session_id}"
                    ),
                    InlineKeyboardButton(
                        close_text,
                        callback_data=f"session_close:{session_id}"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send confirmation message
            await self.app.bot.send_message(
                chat_id=user_id,
                text=f"**{title}**\n\n{message}",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

            logger.info("Idle session confirmation sent",
                       session_id=session_id,
                       user_id=user_id)

        except Exception as e:
            logger.error("Failed to send idle confirmation",
                        session_id=session_id,
                        user_id=user_id,
                        error=str(e))

    async def handle_session_continue(self, session_id: str, user_id: int) -> None:
        """Handle user decision to continue session.

        Args:
            session_id: Claude session ID
            user_id: Telegram user ID
        """
        # Remove from warned sessions
        self.warned_sessions.discard(session_id)

        # Restart activity tracking
        await self.track_session_activity(session_id, user_id)

        logger.info("Session continued by user",
                   session_id=session_id,
                   user_id=user_id)

    async def handle_session_close(self, session_id: str, user_id: int) -> None:
        """Handle user decision to close session.

        Args:
            session_id: Claude session ID
            user_id: Telegram user ID
        """
        try:
            # Clean up tracking
            self.warned_sessions.discard(session_id)
            if session_id in self.pending_confirmations:
                self.pending_confirmations[session_id].cancel()
                del self.pending_confirmations[session_id]

            # Close the actual session through session manager
            from ..di.container import DIContainer
            container = DIContainer.get_instance()
            claude_integration = await container.get("claude_integration")

            await claude_integration.session_manager.remove_session(session_id)

            logger.info("Session closed by user request",
                       session_id=session_id,
                       user_id=user_id)

        except Exception as e:
            logger.error("Failed to close session",
                        session_id=session_id,
                        user_id=user_id,
                        error=str(e))

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up tracking for a session.

        Args:
            session_id: Claude session ID
        """
        # Cancel pending timer
        if session_id in self.pending_confirmations:
            self.pending_confirmations[session_id].cancel()
            del self.pending_confirmations[session_id]

        # Remove from warned sessions
        self.warned_sessions.discard(session_id)

        logger.debug("Session cleanup completed", session_id=session_id)

    def get_status(self) -> Dict:
        """Get manager status for debugging.

        Returns:
            Dictionary with manager status information
        """
        return {
            "tracked_sessions": len(self.pending_confirmations),
            "warned_sessions": len(self.warned_sessions),
            "idle_timeout_minutes": self.idle_timeout.total_seconds() / 60,
            "active_timers": list(self.pending_confirmations.keys()),
            "warned_session_ids": list(self.warned_sessions)
        }