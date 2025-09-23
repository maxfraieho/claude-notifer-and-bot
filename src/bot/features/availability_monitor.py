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

        # Additional tracking fields
        self.last_limit_warning: Optional[datetime] = None
        self.consecutive_limit_hits = 0

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
            current_time_kyiv = datetime.now(kyiv_tz)
            if reset_time_kyiv <= current_time_kyiv:
                # Add one day properly using timedelta
                from datetime import timedelta
                reset_time_kyiv = reset_time_kyiv + timedelta(days=1)
            
            # Convert to UTC
            reset_time_utc = reset_time_kyiv.astimezone(ZoneInfo("UTC"))
            
            logger.debug(f"Parsed reset time: {time_str} -> {reset_time_utc.isoformat()}")
            return reset_time_utc
            
        except ValueError as e:
            logger.warning(f"Failed to parse time '{time_str}': {e}")
            return None

    def _classify_limit_type(self, output: str, reset_time: datetime) -> str:
        """Classify the type of limit hit based on output content and reset time patterns."""
        output_lower = output.lower()
        
        # Check for hourly limits (resets within 2 hours)
        now_utc = datetime.now(ZoneInfo("UTC"))
        time_until_reset = reset_time - now_utc
        hours_until_reset = time_until_reset.total_seconds() / 3600
        
        if "5-hour" in output_lower or "5 hour" in output_lower:
            return "5_hour_limit"
        elif hours_until_reset <= 2:
            return "hourly_limit" 
        elif "daily" in output_lower or hours_until_reset > 12:
            return "daily_limit"
        else:
            return "request_limit"

    async def check_availability_with_details(self) -> Tuple[bool, dict]:
        """Розширена перевірка з деталями про причину недоступності згідно з планом."""
        is_available, reason, reset_time = await self.health_check()

        details = {
            "available": is_available,
            "reason": reason,
            "reset_time": reset_time,
            "last_check": datetime.now(ZoneInfo("UTC")),
            "status_text": "available" if is_available else reason or "unknown"
        }

        # Додати українські повідомлення для різних статусів
        if is_available:
            details["status_message"] = "🟢 Claude доступний"
        elif reason == "limit" or reason == "5_hour_limit" or reason == "hourly_limit":
            details["status_message"] = "⏳ Claude тимчасово обмежений (rate limit)"
        elif reason == "auth":
            details["status_message"] = "🔑 Потрібна повторна авторизація Claude"
        elif reason == "error":
            details["status_message"] = "🌐 Проблеми з мережею"
        else:
            details["status_message"] = "🔴 Claude зараз недоступний"

        # Додати прогноз часу відновлення
        if reset_time and not is_available:
            kyiv_time = reset_time.astimezone(ZoneInfo("Europe/Kyiv"))
            details["estimated_recovery"] = f"Очікується відновлення через: {kyiv_time.strftime('%H:%M')}"

        return is_available, details

    async def is_claude_available_cached(self) -> Tuple[bool, dict]:
        """Кешована перевірка доступності."""
        now = time.time()

        # Перевірити, чи є кеш і чи не застарів він (30 секунд)
        if (hasattr(self, '_last_cache_time') and
            hasattr(self, '_cached_result') and
            now - self._last_cache_time < 30):
            return self._cached_result

        # Виконати нову перевірку
        result = await self.check_availability_with_details()

        # Зберегти в кеш
        self._last_cache_time = now
        self._cached_result = result

        return result

    async def health_check(self) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """Perform health check by running `claude auth status`.
        
        Returns:
            Tuple of (is_available, reason, reset_time):
            - is_available: True if Claude CLI is working
            - reason: None if available, "limit" if rate limited, "auth" for authentication issues, "error" for other issues
            - reset_time: UTC datetime when limit resets, None if not applicable
        
        ⚠️ For Claude CLI to work inside the container:
        - Authentication must be done on the host and the ~/.claude directory must be mounted
          to /home/claudebot/.claude in the container.
        - The target project directory must be mounted to /app/target_project.
        - See README.md for instructions.
        """
        try:
            # Use shell with explicit PATH environment
            import os
            env = os.environ.copy()
            env['PATH'] = f"/home/claudebot/.local/bin:{env.get('PATH', '')}"
            
            proc = await asyncio.create_subprocess_shell(
                "claude auth status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            # Use async timeout
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            
            if proc.returncode == 0:
                logger.debug("Claude CLI check: available and authenticated")
                return True, None, None
            
            # Decode output for analysis
            stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
            combined_output = f"{stdout_text}\n{stderr_text}"
            
            # Debug logging for diagnosis
            logger.debug(f"Claude CLI exit code: {proc.returncode}")
            logger.debug(f"Claude CLI stdout: {stdout_text}")
            logger.debug(f"Claude CLI stderr: {stderr_text}")
            
            # Check for authentication errors first
            auth_errors = [
                "authentication_error",
                "OAuth token has expired",
                "Please run /login",
                "Invalid authentication",
                "Please obtain a new token"
            ]
            
            if any(auth_error in combined_output for auth_error in auth_errors):
                logger.debug("Claude CLI check: authentication error detected")
                return False, "auth", None
            
            # Check if this is a limit-related error and classify the type
            reset_time = self.parse_limit_message(combined_output)
            if reset_time:
                # Classify limit type based on output patterns and timing
                limit_type = self._classify_limit_type(combined_output, reset_time)
                logger.debug(f"Claude CLI {limit_type} reached, resets at: {reset_time.isoformat()}")
                return False, limit_type, reset_time
            
            # Other error
            logger.debug(f"Claude CLI check: unavailable (exit_code={proc.returncode})")
            return False, "error", None
            
        except (asyncio.TimeoutError, FileNotFoundError) as e:
            logger.warning(f"Claude CLI unavailable (timeout/not found): {e}")
            return False, "error", None
        except Exception as e:
            logger.warning(f"Claude CLI unavailable (general error): {e}")
            logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
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
            if reset_expected and reason == "limit":
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
            duration_text = self._get_localized_text("availability.downtime_duration", 
                                                   hours=int(hours), minutes=int(minutes))
            duration_str = f" {duration_text}"

        # Get localized message template
        message = self._get_localized_text("availability.cli_available", 
                                         timestamp=now.strftime('%Y-%m-%d %H:%M:%S'),
                                         platform=platform,
                                         duration=duration_str)
        
        # Add reset time information if available
        if reset_expected and reset_actual:
            kyiv_tz = ZoneInfo("Europe/Kyiv")
            expected_local = reset_expected.astimezone(kyiv_tz)
            actual_local = reset_actual.astimezone(kyiv_tz)
            
            message += (
                f"\n📅 Фактичний час відновлення: {actual_local.strftime('%H:%M')}"
                f"\n⏳ Очікуваний був: {expected_local.strftime('%H:%M')}"
            )
        
        return message

    async def _build_limit_message(self, reset_expected: Optional[datetime] = None) -> str:
        """Build limit reached message for Telegram."""
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        
        message = self._get_localized_text("availability.cli_unavailable", 
                                         timestamp=now.strftime('%Y-%m-%d %H:%M:%S'))
        
        if reset_expected:
            kyiv_tz = ZoneInfo("Europe/Kyiv")
            reset_local = reset_expected.astimezone(kyiv_tz)
            reset_text = self._get_localized_text("availability.reset_time_expected", 
                                                time=reset_local.strftime('%H:%M'))
            message += reset_text
        
        return message

    async def _build_auth_message(self) -> str:
        """Build authentication error message for Telegram."""
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        platform = self._get_platform()
        
        message = (
            f"🔴 **Claude CLI недоступний (помилка автентифікації)**\n"
            f"📅 `{now.strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"🖥️ `{platform}`\n"
            f"⚠️ Токен автентифікації закінчився або невалідний\n"
            f"🔧 Потрібно оновити автентифікацію Claude CLI"
        )
        
        return message

    async def _check_scheduled_prompts(self, context):
        """Check and trigger scheduled prompts if conditions are met."""
        try:
            # Import here to avoid circular imports
            from src.bot.features.scheduled_prompts import ScheduledPromptsManager

            # Check if we have a scheduled prompts manager
            if not hasattr(self, '_prompts_manager'):
                self._prompts_manager = ScheduledPromptsManager(self.application, self.settings)

            # Trigger prompt check
            await self._prompts_manager.check_and_execute_prompts(context)

        except Exception as e:
            logger.error(f"Error checking scheduled prompts: {e}")

    async def _execute_scheduled_tasks(self, context):
        """Execute scheduled tasks when Claude becomes available."""
        try:
            # Get task scheduler from bot context
            task_scheduler = self.application.bot_data.get("task_scheduler")
            if not task_scheduler:
                logger.debug("Task scheduler not available")
                return

            logger.info("Claude available - checking for scheduled tasks to execute")

            # Execute all pending tasks
            results = await task_scheduler.execute_task_queue()

            if results["executed"] > 0 or results["failed"] > 0:
                logger.info(
                    "Executed scheduled tasks",
                    executed=results["executed"],
                    failed=results["failed"],
                    skipped=results["skipped"]
                )

                # Send notification about task execution if configured
                if self.settings.claude_availability.notify_chat_ids:
                    await self._send_task_execution_notification(results)

        except Exception as e:
            logger.error(f"Error executing scheduled tasks: {e}", exc_info=True)

    async def _send_task_execution_notification(self, results: dict):
        """Send notification about automated task execution."""
        try:
            now = datetime.now(ZoneInfo("Europe/Kyiv"))

            message = (
                f"🤖 **Автоматичне виконання завдань**\n"
                f"📅 `{now.strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                f"✅ Виконано: {results['executed']}\n"
                f"❌ Помилок: {results['failed']}\n"
                f"⏭️ Пропущено: {results['skipped']}\n\n"
                f"_Всі заплановані завдання оброблені автоматично_"
            )

            # Send to notification chats during DND only (don't spam during day)
            if self._is_dnd_time():
                await self._send_notification(message)
            else:
                logger.debug("Task execution notification skipped - not DND time")

        except Exception as e:
            logger.error(f"Error sending task execution notification: {e}")

    async def _handle_greeting_check(self) -> bool:
        """Send greeting to Claude to test availability and auto-respond."""
        try:
            # Get Claude integration
            claude_integration = self.application.bot_data.get("claude_integration")
            if not claude_integration:
                logger.debug("Claude integration not available for greeting check")
                return False

            # Send simple greeting that should get auto-response
            greeting_prompt = "Привіт! Це автоматична перевірка доступності. Будь ласка, відповідай 'так' на всі системні запити."

            # Get settings for working directory
            working_directory = self.settings.approved_directory

            logger.debug("Sending greeting to Claude CLI")

            # Execute greeting with auto-respond enabled
            response = await claude_integration.run_command(
                prompt=greeting_prompt,
                working_directory=working_directory,
                user_id=0,  # System user ID for automated checks
                session_id=None,  # Use new session
                auto_respond=True  # Enable auto-responses
            )

            if response and response.content:
                logger.info("Claude greeting check successful", response_length=len(response.content))
                return True
            else:
                logger.warning("Claude greeting check failed - no response")
                return False

        except Exception as e:
            logger.error(f"Error in greeting check: {e}")
            return False

    async def monitor_task(self, context):
        """Main monitoring task that runs periodically."""
        if not self.settings.claude_availability.enabled:
            return  # Feature disabled

        # Get current health status
        current_available, current_reason, current_reset_time = await self.health_check()
        current_time = time.time()
        
        # Check for scheduled prompts and tasks during DND when Claude is available
        if current_available and self._is_dnd_time():
            await self._check_scheduled_prompts(context)
            await self._execute_scheduled_tasks(context)

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

        # Determine current state string for logging
        if confirmed_available:
            current_state = "available"
        elif current_reason == "limit":
            current_state = "limited"
        elif current_reason == "auth":
            current_state = "auth_error"
        else:
            current_state = "unavailable"

        # Determine previous state string for logging
        if last_available:
            last_state = "available"
        elif last_reason == "limit":
            last_state = "limited"
        elif last_reason == "auth":
            last_state = "auth_error"
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

            # Handle notifications and task execution
            if confirmed_available and not last_available:
                # Became available from limited/unavailable
                message = await self._build_availability_message(
                    downtime_duration=downtime_duration,
                    reset_expected=last_reset_expected,
                    reset_actual=reset_actual
                )

                # Execute scheduled tasks immediately when Claude becomes available
                logger.info("Claude became available - executing scheduled tasks")
                await self._execute_scheduled_tasks(context)

                # Send greeting to test and warm up Claude
                greeting_success = await self._handle_greeting_check()
                if greeting_success:
                    logger.info("Claude greeting check successful - system ready for automation")

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

            elif not confirmed_available and last_available and current_reason == "limit":
                # Became limited from available
                message = await self._build_limit_message(current_reset_time)
                
                if not self._is_dnd_time():
                    await self._send_notification(message)
                # Note: We don't defer limit notifications during DND as they are important

            elif not confirmed_available and last_available and current_reason == "auth":
                # Became auth error from available
                message = await self._build_auth_message()
                
                if not self._is_dnd_time():
                    await self._send_notification(message)
                # Note: We don't defer auth error notifications during DND as they are important

            self.last_state = confirmed_available

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

    # Check if job_queue is available
    if application.job_queue is None:
        logger.warning("JobQueue not available - availability monitoring will not run periodic checks")
        logger.warning("To enable periodic monitoring, install python-telegram-bot[job-queue]")
        return

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