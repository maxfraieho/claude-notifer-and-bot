"""Scheduled prompts system for automated task execution during DND periods."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo

import structlog
from telegram import Bot
from telegram.ext import Application

from src.config.settings import Settings

logger = structlog.get_logger(__name__)


class ScheduledPromptsManager:
    """Manages automated prompt execution during DND periods."""

    def __init__(self, application: Application, settings: Settings):
        """Initialize the scheduled prompts manager."""
        self.application = application
        self.settings = settings
        self.bot: Bot = application.bot
        self.prompts_file = Path("./data/scheduled_prompts.json")
        self.execution_log = Path("./data/prompt_executions.jsonl")
        self.is_executing = False
        
        # Ensure files exist
        self._init_files()
    
    def _init_files(self):
        """Initialize prompt files if they don't exist."""
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)
        
        if not self.prompts_file.exists():
            default_prompts = {
                "prompts": [
                    {
                        "id": "daily_code_review",
                        "title": "Щоденний огляд коду",
                        "description": "Перевірити код проекту та запропонувати покращення",
                        "prompt": "Проаналізуй останні зміни в проекті та запропонуй покращення архітектури, безпеки та продуктивності",
                        "enabled": True,
                        "schedule": {
                            "type": "daily",
                            "time": "02:00",
                            "timezone": "Europe/Kyiv"
                        },
                        "conditions": {
                            "claude_available": True,
                            "dnd_period": True,
                            "no_user_activity_hours": 2
                        }
                    },
                    {
                        "id": "documentation_update", 
                        "title": "Оновлення документації",
                        "description": "Автоматичне оновлення README та коментарів",
                        "prompt": "Перевір та оновіть документацію проекту, особливо README.md та коментарі в коді",
                        "enabled": True,
                        "schedule": {
                            "type": "weekly",
                            "day": "sunday",
                            "time": "03:00",
                            "timezone": "Europe/Kyiv"
                        },
                        "conditions": {
                            "claude_available": True,
                            "dnd_period": True,
                            "no_user_activity_hours": 4
                        }
                    }
                ],
                "settings": {
                    "max_execution_time_minutes": 30,
                    "retry_attempts": 3,
                    "notification_chat_ids": [],
                    "enabled": True
                }
            }
            self.prompts_file.write_text(json.dumps(default_prompts, ensure_ascii=False, indent=2))
        
        if not self.execution_log.exists():
            self.execution_log.touch()
    
    async def load_prompts(self) -> Dict[str, Any]:
        """Load prompts configuration from file."""
        try:
            import aiofiles
            async with aiofiles.open(self.prompts_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load prompts configuration: {e}")
            return {"prompts": [], "settings": {"enabled": False}}
    
    async def save_prompts(self, config: Dict[str, Any]):
        """Save prompts configuration to file."""
        try:
            import aiofiles
            async with aiofiles.open(self.prompts_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(config, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Failed to save prompts configuration: {e}")
    
    async def log_execution(self, prompt_id: str, status: str, output: Optional[str] = None, error: Optional[str] = None):
        """Log prompt execution result."""
        record = {
            "timestamp": datetime.now(ZoneInfo("UTC")).isoformat(),
            "prompt_id": prompt_id,
            "status": status,  # "started", "completed", "failed", "skipped"
            "output": output,
            "error": error,
            "execution_time": None
        }
        
        try:
            import aiofiles
            async with aiofiles.open(self.execution_log, "a", encoding="utf-8") as f:
                await f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")
    
    def _is_dnd_time(self) -> bool:
        """Check if current time is within DND window."""
        now = datetime.now(ZoneInfo("Europe/Kyiv")).time()
        dnd_start = self.settings.claude_availability.dnd_start
        dnd_end = self.settings.claude_availability.dnd_end

        if dnd_start > dnd_end:  # e.g., 23:00–08:00
            return now >= dnd_start or now < dnd_end
        else:
            return dnd_start <= now < dnd_end
    
    async def _check_claude_availability(self) -> bool:
        """Check if Claude CLI is available."""
        try:
            import os
            env = os.environ.copy()
            env['PATH'] = f"/home/claudebot/.local/bin:{env.get('PATH', '')}"
            
            proc = await asyncio.create_subprocess_shell(
                "claude auth status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
            
        except Exception:
            return False
    
    async def _check_user_activity(self, hours: int) -> bool:
        """Check if there was user activity in the last N hours."""
        # Check recent bot interactions from logs or database
        # For now, simple implementation checking file modification times
        try:
            data_dir = Path("./data")
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            for file_path in data_dir.glob("*.db"):
                if file_path.stat().st_mtime > cutoff_time.timestamp():
                    return True
            
            return False
        except Exception:
            return False
    
    async def _execute_claude_prompt(self, prompt: str, working_dir: str = "/app/target_project") -> tuple[bool, str]:
        """Execute a Claude CLI prompt and return result."""
        try:
            import os
            env = os.environ.copy()
            env['PATH'] = f"/home/claudebot/.local/bin:{env.get('PATH', '')}"
            
            # Change to working directory and execute prompt
            cmd = f"cd {working_dir} && echo '{prompt}' | claude"
            
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            # Set timeout for execution
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=1800)  # 30 minutes
            
            stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            if proc.returncode == 0:
                return True, stdout_text
            else:
                error_msg = f"Exit code {proc.returncode}: {stderr_text}"
                return False, error_msg
                
        except asyncio.TimeoutError:
            return False, "Execution timed out after 30 minutes"
        except Exception as e:
            return False, f"Execution error: {str(e)}"
    
    async def _should_execute_prompt(self, prompt: Dict[str, Any]) -> tuple[bool, str]:
        """Check if a prompt should be executed based on conditions."""
        if not prompt.get("enabled", False):
            return False, "Prompt disabled"
        
        conditions = prompt.get("conditions", {})
        
        # Check Claude availability
        if conditions.get("claude_available", False):
            if not await self._check_claude_availability():
                return False, "Claude CLI not available"
        
        # Check DND period
        if conditions.get("dnd_period", False):
            if not self._is_dnd_time():
                return False, "Not in DND period"
        
        # Check user activity
        no_activity_hours = conditions.get("no_user_activity_hours", 0)
        if no_activity_hours > 0:
            if await self._check_user_activity(no_activity_hours):
                return False, f"User activity detected within {no_activity_hours} hours"
        
        return True, "All conditions met"
    
    def _is_time_to_execute(self, prompt: Dict[str, Any]) -> bool:
        """Check if it's time to execute the prompt based on schedule."""
        schedule = prompt.get("schedule", {})
        if not schedule:
            return False
        
        timezone = ZoneInfo(schedule.get("timezone", "Europe/Kyiv"))
        now = datetime.now(timezone)
        
        schedule_type = schedule.get("type", "daily")
        target_time_str = schedule.get("time", "02:00")
        
        try:
            target_time = datetime.strptime(target_time_str, "%H:%M").time()
        except ValueError:
            logger.error(f"Invalid time format in schedule: {target_time_str}")
            return False
        
        if schedule_type == "daily":
            # Check if we're within 5 minutes of target time
            target_datetime = datetime.combine(now.date(), target_time, tzinfo=timezone)
            time_diff = abs((now - target_datetime).total_seconds())
            return time_diff < 300  # 5 minutes tolerance
            
        elif schedule_type == "weekly":
            target_day = schedule.get("day", "sunday").lower()
            day_map = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6
            }
            
            if target_day not in day_map:
                logger.error(f"Invalid day in schedule: {target_day}")
                return False
            
            if now.weekday() == day_map[target_day]:
                target_datetime = datetime.combine(now.date(), target_time, tzinfo=timezone)
                time_diff = abs((now - target_datetime).total_seconds())
                return time_diff < 300  # 5 minutes tolerance
        
        return False
    
    async def execute_scheduled_prompt(self, prompt: Dict[str, Any]) -> bool:
        """Execute a single scheduled prompt."""
        prompt_id = prompt.get("id", "unknown")
        logger.info(f"Starting execution of scheduled prompt: {prompt_id}")
        
        await self.log_execution(prompt_id, "started")
        
        try:
            # Check conditions
            should_execute, reason = await self._should_execute_prompt(prompt)
            if not should_execute:
                logger.info(f"Skipping prompt {prompt_id}: {reason}")
                await self.log_execution(prompt_id, "skipped", error=reason)
                return False
            
            # Execute the prompt
            prompt_text = prompt.get("prompt", "")
            success, output = await self._execute_claude_prompt(prompt_text)
            
            if success:
                logger.info(f"Successfully executed prompt {prompt_id}")
                await self.log_execution(prompt_id, "completed", output=output[:1000])  # Truncate for logging
                
                # Send notification if configured
                config = await self.load_prompts()
                notification_chats = config.get("settings", {}).get("notification_chat_ids", [])
                if notification_chats:
                    message = (
                        f"🤖 **Автоматичне завдання виконано**\n"
                        f"📋 {prompt.get('title', prompt_id)}\n"
                        f"⏰ {datetime.now(ZoneInfo('Europe/Kyiv')).strftime('%H:%M')}\n"
                        f"✅ Статус: Успішно"
                    )
                    for chat_id in notification_chats:
                        try:
                            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode=None)
                        except Exception as e:
                            logger.error(f"Failed to send notification to {chat_id}: {e}")
                
                return True
            else:
                logger.error(f"Failed to execute prompt {prompt_id}: {output}")
                await self.log_execution(prompt_id, "failed", error=output)
                return False
                
        except Exception as e:
            logger.error(f"Error executing prompt {prompt_id}: {e}")
            await self.log_execution(prompt_id, "failed", error=str(e))
            return False
    
    async def check_and_execute_prompts(self, context):
        """Main task to check and execute scheduled prompts."""
        if self.is_executing:
            logger.debug("Prompt execution already in progress, skipping")
            return
        
        config = await self.load_prompts()
        if not config.get("settings", {}).get("enabled", False):
            return
        
        prompts = config.get("prompts", [])
        if not prompts:
            return
        
        # Check if any prompts need execution
        prompts_to_execute = []
        for prompt in prompts:
            if self._is_time_to_execute(prompt):
                prompts_to_execute.append(prompt)
        
        if not prompts_to_execute:
            return
        
        logger.info(f"Found {len(prompts_to_execute)} prompts ready for execution")
        
        self.is_executing = True
        try:
            for prompt in prompts_to_execute:
                await self.execute_scheduled_prompt(prompt)
                # Add delay between prompts to avoid overwhelming the system
                await asyncio.sleep(30)
        finally:
            self.is_executing = False
    
    async def get_execution_stats(self) -> dict:
        """Get execution statistics."""
        try:
            if not self.execution_log.exists():
                return {
                    "total_executions": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_duration": 0,
                    "last_execution": "Немає",
                    "system_active": False
                }
            
            # Read and parse execution log
            total_executions = 0
            successful = 0
            failed = 0
            durations = []
            last_execution = None
            
            with open(self.execution_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        total_executions += 1
                        
                        if entry.get("status") == "success":
                            successful += 1
                        else:
                            failed += 1
                            
                        if "duration" in entry:
                            durations.append(entry["duration"])
                            
                        if "timestamp" in entry:
                            last_execution = entry["timestamp"]
                            
                    except json.JSONDecodeError:
                        continue
            
            # Calculate average duration
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Format last execution time
            if last_execution:
                try:
                    dt = datetime.fromisoformat(last_execution.replace('Z', '+00:00'))
                    last_execution = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    pass
            
            # Check if system is active (not in DND and Claude available)
            system_active = self._is_dnd_time() and not self.is_executing
            
            return {
                "total_executions": total_executions,
                "successful": successful,
                "failed": failed,
                "avg_duration": avg_duration,
                "last_execution": last_execution or "Немає",
                "system_active": system_active
            }
            
        except Exception as e:
            logger.error(f"Error getting execution stats: {e}")
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "avg_duration": 0,
                "last_execution": "Помилка",
                "system_active": False
            }


async def setup_scheduled_prompts(application: Application, settings: Settings):
    """Set up scheduled prompts system."""
    manager = ScheduledPromptsManager(application, settings)
    
    # Check if job_queue is available
    if application.job_queue is None:
        logger.warning("JobQueue not available - scheduled prompts will not run")
        return
    
    # Add periodic task - check every 5 minutes
    application.job_queue.run_repeating(
        manager.check_and_execute_prompts,
        interval=300,  # 5 minutes
        first=60,  # First check after 1 minute
        name="scheduled_prompts_checker"
    )
    
    logger.info("✅ Scheduled prompts system enabled. Check interval: 5 minutes")
    return manager