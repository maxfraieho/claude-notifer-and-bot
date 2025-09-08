"""Claude CLI availability monitoring feature."""

import asyncio
import json
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

import structlog
from telegram import Bot
from telegram.error import RetryAfter, TimedOut, NetworkError
from telegram.ext import Application

from src.config.settings import Settings

# Add retry support
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)


class ClaudeAvailabilityMonitor:
    """Monitors Claude CLI availability and sends notifications."""

    def __init__(self, application: Application, settings: Settings):
        """Initialize the availability monitor."""
        self.application = application
        self.settings = settings
        self.bot: Bot = application.bot
        self.state_file = Path(".claude_last_cmd.json")
        self.transitions_log = Path("transitions.jsonl")
        self.last_state: Optional[bool] = None
        self.ok_counter = 0
        self.pending_notification: Optional[Dict[str, Any]] = None

        # Ensure state files exist
        self._init_state_files()

    def _init_state_files(self):
        """Initialize state files if they don't exist."""
        if not self.state_file.exists():
            self.state_file.write_text(json.dumps({"available": False, "last_check": None}))
        if not self.transitions_log.exists():
            self.transitions_log.touch()

    async def health_check(self) -> bool:
        """Perform health check by running `claude --version`, return True if available.
        
        ⚠️ For Claude CLI to work inside the container, authentication must be done on the host
        and the ~/.claude directory must be mounted to /home/claudebot/.claude in the container.
        See README.md for instructions.
        """
        try:
            # Replace subprocess.run with async call
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Use async timeout
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            
            is_available = proc.returncode == 0
            logger.debug(f"Claude CLI check: exit_code={proc.returncode}, available={is_available}")
            return is_available
        except (asyncio.TimeoutError, FileNotFoundError, Exception) as e:
            logger.warning(f"Claude CLI unavailable: {e}")
            return False

    async def _save_state(self, available: bool):
        """Save current state to file asynchronously."""
        state = {
            "available": available,
            "last_check": datetime.now(ZoneInfo("Europe/Kyiv")).isoformat()
        }
        
        # Use aiofiles for async file writing
        import aiofiles
        async with aiofiles.open(self.state_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(state, ensure_ascii=False, indent=2))

    async def _log_transition(self, from_state: bool, to_state: bool, duration: Optional[float] = None):
        """Log state transition to transitions.jsonl asynchronously."""
        record = {
            "timestamp": datetime.now(ZoneInfo("Europe/Kyiv")).isoformat(),
            "from": "available" if from_state else "unavailable",
            "to": "available" if to_state else "unavailable",
            "duration_unavailable": duration,
            "platform": self._get_platform()
        }
        
        # Use aiofiles for async file writing
        import aiofiles
        async with aiofiles.open(self.transitions_log, "a", encoding="utf-8") as f:
            await f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _get_platform(self) -> str:
        """Get platform information."""
        import platform
        return f"{platform.system()} {platform.machine()}"

    def _is_dnd_time(self) -> bool:
        """Check if current time is within DND window (23:00–08:00 Europe/Kyiv)."""
        now = datetime.now(ZoneInfo("Europe/Kyiv")).time()
        dnd_start = self.settings.claude_availability.dnd_start
        dnd_end = self.settings.claude_availability.dnd_end

        if dnd_start > dnd_end:  # e.g., 23:00–08:00
            return now >= dnd_start or now < dnd_end
        else:
            return dnd_start <= now < dnd_end

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RetryAfter, TimedOut, NetworkError)),
        reraise=True
    )
    async def _send_notification(self, message: str):
        """Send notification to all subscribed chats with retry logic."""
        chat_ids = self.settings.claude_availability.notify_chat_ids
        if not chat_ids:
            logger.warning("No chats configured for Claude CLI availability notifications")
            return

        for chat_id in chat_ids:
            try:
                await self.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                logger.info(f"Availability notification sent to chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {chat_id}: {e}")
                raise  # Retry only for specific error types

    async def _build_availability_message(self, downtime_duration: Optional[float] = None) -> str:
        """Build availability message in the specified format."""
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        platform = self._get_platform()
        duration_str = ""
        if downtime_duration:
            hours, remainder = divmod(downtime_duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f" (перерва: {int(hours)}год {int(minutes)}хв)"

        return (
            f"🟢 **Claude Code CLI Available**\n"
            f"📅 `{now.strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"🖥️ `{platform}`\n"
            f"⏱️ {duration_str}"
        )

    async def monitor_task(self, context):
        """Main monitoring task that runs periodically."""
        if not self.settings.claude_availability.enabled:
            return  # Feature disabled

        current_available = await self.health_check()
        current_time = time.time()

        # Load previous state
        try:
            # Use aiofiles for async file reading
            import aiofiles
            async with aiofiles.open(self.state_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                last_state_data = json.loads(content)
                
            last_available = last_state_data.get("available", False)
            last_check_str = last_state_data.get("last_check")
            last_check = datetime.fromisoformat(last_check_str) if last_check_str else None
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            logger.error(f"Error reading state: {e}")
            last_available = False
            last_check = None

        # Debounce logic: need N consecutive OK checks
        if current_available:
            self.ok_counter += 1
        else:
            self.ok_counter = 0

        debounce_threshold = self.settings.claude_availability.debounce_ok_count
        confirmed_available = self.ok_counter >= debounce_threshold

        # If state changed
        if last_available != confirmed_available:
            downtime_duration = None
            if last_check and not last_available and confirmed_available:
                downtime_duration = (datetime.now(ZoneInfo("Europe/Kyiv")) - last_check).total_seconds()

            await self._log_transition(last_available, confirmed_available, downtime_duration)
            await self._save_state(confirmed_available)

            # If became available - prepare notification (considering DND)
            if confirmed_available and not last_available:
                message = await self._build_availability_message(downtime_duration)
                if self._is_dnd_time():
                    # Save for sending in the morning
                    self.pending_notification = {
                        "message": message,
                        "prepared_at": current_time
                    }
                    logger.info("Transition to available during DND - notification deferred.")
                else:
                    await self._send_notification(message)
                    self.pending_notification = None

            self.last_state = confirmed_available

        # If there's a pending notification and we're no longer in DND - send it
        if self.pending_notification and not self._is_dnd_time():
            await self._send_notification(self.pending_notification["message"])
            logger.info("Deferred availability notification sent.")
            self.pending_notification = None

        # If state didn't change, just update the last check time
        if last_available == confirmed_available:
            await self._save_state(confirmed_available)


async def setup_availability_monitor(application: Application, settings: Settings):
    """Set up Claude CLI availability monitoring."""
    if not settings.claude_availability.enabled:
        logger.info("Claude CLI availability monitoring disabled in settings.")
        return

    monitor = ClaudeAvailabilityMonitor(application, settings)

    # Add periodic task
    application.job_queue.run_repeating(
        monitor.monitor_task,
        interval=settings.claude_availability.check_interval_seconds,
        first=10,  # First check after 10 seconds
        name="claude_availability_monitor"
    )

    logger.info(
        f"✅ Claude CLI monitoring enabled. Interval: {settings.claude_availability.check_interval_seconds}s. "
        f"Notification chats: {settings.claude_availability.notify_chat_ids}"
    )