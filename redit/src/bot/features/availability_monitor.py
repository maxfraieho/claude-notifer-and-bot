"""Claude CLI availability monitoring feature."""

import asyncio
import json
import re
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
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
        self.last_state: Optional[bool] = None
        self.ok_counter = 0
        self.pending_notification: Optional[Dict[str, Any]] = None
        self.last_limit_warning: Optional[datetime] = None  # Track when we last warned about approaching limits
        self.consecutive_limit_hits = 0  # Count consecutive rate limit hits for pattern detection

        # Ensure state files exist
        self._init_state_files()

    def _get_localized_text(self, key: str, **kwargs) -> str:
        """Get localized text using Ukrainian as default language for notifications."""
        try:
            localization = self.application.bot_data.get("localization")
            if localization:
                result = localization.get(key, language="uk", **kwargs)
                # Safe fallback if key is missing
                return result or f"[{key}]"
            else:
                # Fallback if localization not available
                return f"[{key}]"
        except Exception as e:
            logger.warning(f"Failed to get localized text for {key}: {e}")
            return f"[{key}]"

    def _init_state_files(self):
        """Initialize state files if they don't exist."""
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)
        
        self.state_file = data_dir / ".claude_last_cmd.json"
        self.transitions_log = data_dir / "transitions.jsonl"
        
        if not self.state_file.exists():
            self.state_file.write_text(json.dumps({"available": False, "last_check": None}))
        if not self.transitions_log.exists():
            self.transitions_log.touch()

    def parse_limit_message(self, output: str) -> Optional[datetime]:
        """Parse limit message from Claude CLI output and extract reset time.
        
        Args:
            output: Combined stdout/stderr output from Claude CLI
            
        Returns:
            datetime in UTC if reset time found, None otherwise
            
        Examples:
            "5-hour limit reached ∙ resets 2pm" -> datetime for 2pm today in Europe/Kyiv -> UTC
            "limit reached ∙ resets 11:30am" -> datetime for 11:30am today in Europe/Kyiv -> UTC
            "limit reached ∙ resets 14:00" -> datetime for 14:00 today in Europe/Kyiv -> UTC
        """
        # Regex pattern to match various time formats after "resets"
        pattern = r"resets\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)"
        
        match = re.search(pattern, output, re.IGNORECASE)
        if not match:
            return None
            
        time_str = match.group(1).strip().lower()
        
        try:
            # Parse different time formats
            if 'am' in time_str or 'pm' in time_str:
                # Handle 12-hour format: "2pm", "11:30am", "2:00 pm"
                time_str = time_str.replace(' ', '')  # Remove spaces
                if ':' in time_str:
                    # "11:30am" format
                    time_obj = datetime.strptime(time_str, "%I:%M%p").time()
                else:
                    # "2pm" format  
                    time_obj = datetime.strptime(time_str, "%I%p").time()
            else:
                # Handle 24-hour format: "14:00", "2" (assume 24-hour if no am/pm)
                if ':' in time_str:
                    # "14:00" format
                    time_obj = datetime.strptime(time_str, "%H:%M").time()
                else:
                    # Single digit like "2" - assume 24-hour format
                    time_obj = datetime.strptime(time_str, "%H").time()
            
            # Create datetime for today in Europe/Kyiv timezone
            kyiv_tz = ZoneInfo("Europe/Kyiv")
            today = datetime.now(kyiv_tz).date()
            reset_time_kyiv = datetime.combine(today, time_obj, tzinfo=kyiv_tz)
            
            # If the time is in the past today, assume it means tomorrow
            if reset_time_kyiv <= datetime.now(kyiv_tz):
                from datetime import timedelta
                reset_time_kyiv = reset_time_kyiv + timedelta(days=1)
            
            # Convert to UTC
            reset_time_utc = reset_time_kyiv.astimezone(ZoneInfo("UTC"))
            
            logger.debug(f"Parsed reset time: {time_str} -> {reset_time_utc.isoformat()}")
            return reset_time_utc
            
        except ValueError as e:
            logger.warning(f"Failed to parse time '{time_str}': {e}")
            return None

    async def health_check(self) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """Perform health check by running `claude --version`.
        
        Returns:
            Tuple of (is_available, reason, reset_time):
            - is_available: True if Claude CLI is working
            - reason: None if available, "daily_limit"/"hourly_limit"/"request_limit"/"error" for specific issues
            - reset_time: UTC datetime when limit resets, None if not applicable
        
        ⚠️ For Claude CLI to work inside the container:
        - Authentication must be done on the host and the ~/.claude directory must be mounted
          to /home/claudebot/.claude in the container.
        - The target project directory must be mounted to /app/target_project.
        - See README.md for instructions.
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
            
            if proc.returncode == 0:
                logger.debug("Claude CLI check: available")
                return True, None, None
            
            # Decode output for analysis
            stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
            combined_output = f"{stdout_text}\n{stderr_text}"
            
            # Check if this is a limit-related error and classify the type
            reset_time = self.parse_limit_message(combined_output)
            if reset_time:
                # Classify limit type based on reset time pattern
                limit_type = self._classify_limit_type(combined_output, reset_time)
                logger.debug(f"Claude CLI {limit_type} limit reached, resets at: {reset_time.isoformat()}")
                return False, limit_type, reset_time
            
            # Check for other common error patterns
            if "authentication" in combined_output.lower() or "login" in combined_output.lower():
                logger.debug(f"Claude CLI authentication error: {combined_output}")
                return False, "auth_error", None
            elif "network" in combined_output.lower() or "connection" in combined_output.lower():
                logger.debug(f"Claude CLI network error: {combined_output}")
                return False, "network_error", None
            
            # Other error
            logger.debug(f"Claude CLI check: unavailable (exit_code={proc.returncode})")
            return False, "error", None
            
        except (asyncio.TimeoutError, FileNotFoundError, Exception) as e:
            logger.warning(f"Claude CLI unavailable: {e}")
            return False, "error", None

    async def _save_state(self, available: bool, reason: Optional[str] = None, reset_expected: Optional[datetime] = None):
        """Save current state to file asynchronously."""
        state = {
            "available": available,
            "last_check": datetime.now(ZoneInfo("Europe/Kyiv")).isoformat()
        }
        
        # Add reason and reset_expected for limited state  
        if not available and reason:
            state["reason"] = reason
            if reset_expected and reason in ["daily_limit", "hourly_limit", "request_limit", "limit"]:
                state["reset_expected"] = reset_expected.isoformat()
        
        # Use aiofiles for async file writing
        import aiofiles
        async with aiofiles.open(self.state_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(state, ensure_ascii=False, indent=2))

    async def _log_transition(self, from_state: str, to_state: str, 
                            duration: Optional[float] = None, 
                            reset_expected: Optional[datetime] = None,
                            reset_actual: Optional[datetime] = None):
        """Log state transition to transitions.jsonl asynchronously."""
        record = {
            "timestamp": datetime.now(ZoneInfo("UTC")).isoformat(),
            "from": from_state,
            "to": to_state,
            "duration_unavailable": duration,
            "platform": self._get_platform()
        }
        
        # Add reset times for limit-related transitions
        if reset_expected:
            record["reset_expected"] = reset_expected.isoformat()
        if reset_actual:
            record["reset_actual"] = reset_actual.isoformat()
        
        # Use aiofiles for async file writing
        import aiofiles
        async with aiofiles.open(self.transitions_log, "a", encoding="utf-8") as f:
            await f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _get_platform(self) -> str:
        """Get platform information."""
        import platform
        return f"{platform.system()} {platform.machine()}"

    def _classify_limit_type(self, output: str, reset_time: datetime) -> str:
        """Classify the type of rate limit based on output and reset time."""
        output_lower = output.lower()
        
        # Check for specific limit mentions in output
        if "daily" in output_lower or "day" in output_lower:
            return "daily_limit"
        elif "hourly" in output_lower or "hour" in output_lower:
            return "hourly_limit"
        elif "per request" in output_lower or "request" in output_lower:
            return "request_limit"
        
        # Fallback: classify based on reset time patterns
        now_utc = datetime.now(ZoneInfo("UTC"))
        time_until_reset = (reset_time - now_utc).total_seconds()
        
        # If reset is more than 12 hours away, likely daily limit
        if time_until_reset > 12 * 3600:
            return "daily_limit"
        # If reset is 1-12 hours away, could be hourly or daily
        elif time_until_reset > 3600:
            return "hourly_limit"
        # If reset is less than 1 hour, likely request-based
        else:
            return "request_limit"
    
    async def _check_internal_rate_limits(self, user_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """Check internal rate limiter status for early warning."""
        try:
            rate_limiter = self.application.bot_data.get("rate_limiter")
            if not rate_limiter or not user_id:
                return True, None  # Cannot check, assume OK
            
            # Check with minimal cost to see current status
            allowed, message = await rate_limiter.check_rate_limit(user_id, cost=0.1, tokens=1)
            
            if not allowed:
                return False, message
                
            # Check if user is approaching limits (rough estimation)
            current_usage = rate_limiter.cost_tracker.get(user_id, 0.0)
            max_usage = rate_limiter.config.claude_max_cost_per_user
            
            usage_percentage = (current_usage / max_usage) * 100 if max_usage > 0 else 0
            
            if usage_percentage > 80:  # Warn when over 80% usage
                warning_msg = f"⚠️ Ви використали {usage_percentage:.0f}% вашого денного ліміту Claude. Залишилось: {max_usage - current_usage:.1f} кредитів."
                return True, warning_msg
                
            return True, None
            
        except Exception as e:
            logger.warning(f"Failed to check internal rate limits: {e}")
            return True, None  # Assume OK if check fails

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
                await self.bot.send_message(chat_id=chat_id, text=message, parse_mode=None)
                logger.info(f"Availability notification sent to chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {chat_id}: {e}")
                raise  # Retry only for specific error types

    async def _build_availability_message(self, downtime_duration: Optional[float] = None, 
                                        reset_expected: Optional[datetime] = None, 
                                        reset_actual: Optional[datetime] = None) -> str:
        """Build availability message in the specified format."""
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        platform = self._get_platform()
        duration_str = ""
        if downtime_duration:
            hours, remainder = divmod(downtime_duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = self._get_localized_text(
                "availability.downtime_duration", 
                hours=int(hours), 
                minutes=int(minutes)
            )

        message = self._get_localized_text(
            "availability.cli_available",
            timestamp=now.strftime('%Y-%m-%d %H:%M:%S'),
            platform=platform,
            duration=duration_str
        )
        
        # Add reset time information if available
        if reset_expected and reset_actual:
            kyiv_tz = ZoneInfo("Europe/Kyiv")
            expected_local = reset_expected.astimezone(kyiv_tz)
            actual_local = reset_actual.astimezone(kyiv_tz)
            
            reset_info = self._get_localized_text(
                "availability.reset_time_actual",
                actual_time=actual_local.strftime('%H:%M'),
                expected_time=expected_local.strftime('%H:%M')
            )
            message += reset_info
        
        return message

    async def _build_limit_message(self, reset_expected: Optional[datetime] = None, limit_type: str = "limit") -> str:
        """Build limit reached message for Telegram with specific limit type."""
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        
        # Choose appropriate message based on limit type
        if limit_type == "daily_limit":
            limit_description = "денний ліміт досягнуто"
            advice = "\n\n💬 **Поради:**\n• Дочекайтеся скидання ліміту завтра\n• Оптимізуйте запити для економії кредитів\n• Розподіліть завдання на кілька днів"
        elif limit_type == "hourly_limit":
            limit_description = "погодинний ліміт досягнуто"
            advice = "\n\n💬 **Поради:**\n• Дочекайтеся скидання ліміту\n• Використовуйте коротші запити\n• Розподіліть роботу рівномірно"
        elif limit_type == "request_limit":
            limit_description = "ліміт запитів досягнуто"
            advice = "\n\n💬 **Поради:**\n• Зачекайте кілька хвилин\n• Об'єднайте кілька питань в один запит\n• Уникайте частих коротких запитів"
        else:
            limit_description = "ліміт використання досягнуто"
            advice = ""
        
        message = f"🔴 **Claude CLI недоступний ({limit_description})**\n📅 `{now.strftime('%Y-%m-%d %H:%M:%S')}`{advice}"
        
        if reset_expected:
            kyiv_tz = ZoneInfo("Europe/Kyiv")
            reset_local = reset_expected.astimezone(kyiv_tz)
            reset_info = self._get_localized_text(
                "availability.reset_time_expected",
                time=reset_local.strftime('%H:%M')
            )
            message += reset_info
        
        return message

    async def monitor_task(self, context):
        """Main monitoring task that runs periodically."""
        if not self.settings.claude_availability.enabled:
            return  # Feature disabled

        # Get current health status
        current_available, current_reason, current_reset_time = await self.health_check()
        current_time = time.time()

        # Load previous state
        try:
            # Use aiofiles for async file reading
            import aiofiles
            async with aiofiles.open(self.state_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                last_state_data = json.loads(content)
                
            last_available = last_state_data.get("available", False)
            last_reason = last_state_data.get("reason")
            last_reset_expected_str = last_state_data.get("reset_expected")
            last_reset_expected = datetime.fromisoformat(last_reset_expected_str) if last_reset_expected_str else None
            last_check_str = last_state_data.get("last_check")
            last_check = datetime.fromisoformat(last_check_str) if last_check_str else None
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            logger.error(f"Error reading state: {e}")
            last_available = False
            last_reason = None
            last_reset_expected = None
            last_check = None

        # Debounce logic: need N consecutive OK checks for availability
        if current_available:
            self.ok_counter += 1
        else:
            self.ok_counter = 0

        debounce_threshold = self.settings.claude_availability.debounce_ok_count
        confirmed_available = self.ok_counter >= debounce_threshold

        # Determine current state string for logging with more granularity  
        if confirmed_available:
            current_state = "available"
        elif current_reason in ["daily_limit", "hourly_limit", "request_limit"]:
            current_state = f"limited_{current_reason}"
        elif current_reason in ["auth_error", "network_error"]:
            current_state = f"error_{current_reason}"
        else:
            current_state = "unavailable"

        # Determine previous state string for logging with more granularity
        if last_available:
            last_state = "available"
        elif last_reason in ["daily_limit", "hourly_limit", "request_limit"]:
            last_state = f"limited_{last_reason}"
        elif last_reason in ["auth_error", "network_error"]:
            last_state = f"error_{last_reason}"
        else:
            last_state = "unavailable"

        # Check if state changed
        state_changed = (confirmed_available != last_available) or (current_reason != last_reason)

        if state_changed:
            downtime_duration = None
            reset_actual = None
            
            # Calculate downtime duration if recovering from unavailable/limited
            if last_check and not last_available and confirmed_available:
                downtime_duration = (datetime.now(ZoneInfo("Europe/Kyiv")) - last_check).total_seconds()
                if last_state == "limited":
                    reset_actual = datetime.now(ZoneInfo("UTC"))

            # Log the transition
            await self._log_transition(
                from_state=last_state,
                to_state=current_state,
                duration=downtime_duration,
                reset_expected=last_reset_expected if last_state == "limited" and current_state == "available" else current_reset_time,
                reset_actual=reset_actual
            )

            # Save new state
            await self._save_state(confirmed_available, current_reason, current_reset_time)

            # Handle notifications
            if confirmed_available and not last_available:
                # Became available from limited/unavailable
                message = await self._build_availability_message(
                    downtime_duration=downtime_duration,
                    reset_expected=last_reset_expected,
                    reset_actual=reset_actual
                )
                
                if self._is_dnd_time():
                    # Save for sending in the morning
                    self.pending_notification = {
                        "message": message,
                        "prepared_at": current_time
                    }
                    logger.info(f"Transition from {last_state} to available during DND - notification deferred.")
                else:
                    await self._send_notification(message)
                    self.pending_notification = None

            elif not confirmed_available and last_available and current_reason in ["daily_limit", "hourly_limit", "request_limit"]:
                # Became limited from available - track pattern
                self.consecutive_limit_hits += 1
                
                # Build more detailed limit message based on type
                message = await self._build_limit_message(current_reset_time, current_reason)
                
                # Add pattern warning if this is frequent
                if self.consecutive_limit_hits >= 3:
                    pattern_warning = "\n\n⚠️ **Частe досягнення лімітів**\nРозгляньте можливість оптимізації запитів або розподілення навантаження."
                    message += pattern_warning
                
                if not self._is_dnd_time():
                    await self._send_notification(message)
                # Note: We don't defer limit notifications during DND as they are important
            
            # Reset consecutive limit counter when becoming available
            if confirmed_available:
                self.consecutive_limit_hits = 0

            self.last_state = confirmed_available

        # Send proactive notifications about approaching reset times
        await self._check_and_send_proactive_notifications(current_reason, current_reset_time)

        # If there's a pending notification and we're no longer in DND - send it
        if self.pending_notification and not self._is_dnd_time():
            await self._send_notification(self.pending_notification["message"])
            logger.info("Deferred availability notification sent.")
            self.pending_notification = None

        # Always update the last check time
        await self._save_state(confirmed_available, current_reason, current_reset_time)


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

    # Store monitor in application data for potential future use
    application.bot_data["availability_monitor"] = monitor

    logger.info(
        f"✅ Claude CLI monitoring enabled. Interval: {settings.claude_availability.check_interval_seconds}s. "
        f"Notification chats: {settings.claude_availability.notify_chat_ids}"
    )

    async def _check_and_send_proactive_notifications(self, reason: Optional[str], reset_time: Optional[datetime]):
        """Send proactive notifications about approaching reset times."""
        if not reason or not reset_time or reason not in ["daily_limit", "hourly_limit", "request_limit"]:
            return
            
        now_utc = datetime.now(ZoneInfo("UTC"))
        time_until_reset = (reset_time - now_utc).total_seconds()
        
        # Send notification 30 minutes before expected reset for daily limits
        # Send notification 10 minutes before for hourly limits  
        # Send notification 2 minutes before for request limits
        notification_threshold = {
            "daily_limit": 30 * 60,  # 30 minutes
            "hourly_limit": 10 * 60,  # 10 minutes
            "request_limit": 2 * 60   # 2 minutes
        }.get(reason, 10 * 60)
        
        # Check if we should send a proactive notification
        if (notification_threshold - 60) <= time_until_reset <= (notification_threshold + 60):
            # Only send if we haven't sent a warning recently
            if (not self.last_limit_warning or 
                (now_utc - self.last_limit_warning).total_seconds() > notification_threshold):
                
                kyiv_tz = ZoneInfo("Europe/Kyiv")
                reset_local = reset_time.astimezone(kyiv_tz)
                
                if reason == "daily_limit":
                    warning_msg = (f"⚡ **Попередження: Скоро скидання лімітів**\n"
                                  f"🕓 Claude CLI стане доступним о ≈{reset_local.strftime('%H:%M')}\n"
                                  f"🔍 Підготуйте свої задачі зараніе!")
                elif reason == "hourly_limit":
                    warning_msg = (f"⚡ **Попередження: Скоро скидання лімітів**\n"
                                  f"🕓 Claude CLI стане доступним о ≈{reset_local.strftime('%H:%M')}\n"
                                  f"🚀 Приблизно 10 хвилин до відновлення!")
                else:  # request_limit
                    warning_msg = (f"⚡ **Попередження: Скоро скидання лімітів**\n"
                                  f"🕓 Claude CLI стане доступним о ≈{reset_local.strftime('%H:%M')}\n"
                                  f"⏱️ Лише кілька хвилин!")
                
                if not self._is_dnd_time():
                    await self._send_notification(warning_msg)
                    self.last_limit_warning = now_utc
                    logger.info(f"Proactive {reason} reset notification sent")
                    
    # Add the method to the monitor class
    monitor._check_and_send_proactive_notifications = _check_and_send_proactive_notifications.__get__(monitor, ClaudeAvailabilityMonitor)