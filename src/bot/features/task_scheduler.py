"""Task scheduler for automated Claude CLI execution."""

import asyncio
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ...claude.facade import ClaudeIntegration
from ...config.settings import Settings
from ...storage.models import ScheduledTaskModel
from ...storage.repositories.scheduled_task_repository import ScheduledTaskRepository
from .auto_responder import AutoResponder

logger = structlog.get_logger()


class TaskScheduler:
    """System for scheduling and automatically executing Claude CLI tasks."""

    def __init__(
        self,
        repository: ScheduledTaskRepository,
        claude_integration: ClaudeIntegration,
        settings: Settings
    ):
        """Initialize task scheduler."""
        self.repository = repository
        self.claude_integration = claude_integration
        self.settings = settings
        self.auto_responder = AutoResponder()
        self.is_running = False
        self.execution_lock = asyncio.Lock()
        self._execution_tasks: Dict[int, asyncio.Task] = {}

    async def add_scheduled_task(
        self,
        user_id: int,
        task_type: str,
        prompt: str,
        execution_time: Optional[datetime] = None,
        auto_execute: bool = True,
        auto_respond: bool = True,
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a task to the execution queue."""
        task = ScheduledTaskModel(
            user_id=user_id,
            task_type=task_type,
            prompt=prompt,
            created_at=datetime.utcnow(),
            scheduled_for=execution_time,
            auto_execute=auto_execute,
            auto_respond=auto_respond,
            priority=priority,
            metadata=metadata or {}
        )

        task_id = await self.repository.create_task(task)
        logger.info(
            "Scheduled new task",
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
            scheduled_for=execution_time,
            auto_execute=auto_execute
        )
        return task_id

    async def get_pending_tasks(self, user_id: Optional[int] = None) -> List[ScheduledTaskModel]:
        """Get all pending tasks for a user or all users."""
        return await self.repository.get_pending_tasks(user_id, ready_for_execution=True)

    async def get_user_tasks(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ScheduledTaskModel]:
        """Get tasks for a specific user."""
        return await self.repository.get_user_tasks(user_id, status, limit)

    async def cancel_task(self, task_id: int) -> bool:
        """Cancel a pending task."""
        # First try to cancel if it's currently executing
        if task_id in self._execution_tasks:
            self._execution_tasks[task_id].cancel()
            del self._execution_tasks[task_id]

        # Update status in database
        success = await self.repository.update_task_status(task_id, "cancelled")
        if success:
            logger.info("Cancelled task", task_id=task_id)
        return success

    async def delete_task(self, task_id: int) -> bool:
        """Delete a task completely."""
        # Cancel if running
        if task_id in self._execution_tasks:
            self._execution_tasks[task_id].cancel()
            del self._execution_tasks[task_id]

        success = await self.repository.delete_task(task_id)
        if success:
            logger.info("Deleted task", task_id=task_id)
        return success

    async def clear_user_tasks(self, user_id: int, status: Optional[str] = None) -> int:
        """Clear all tasks for a user."""
        # Cancel any running tasks for this user
        tasks_to_cancel = []
        for task_id, execution_task in self._execution_tasks.items():
            # We need a way to map task_id to user_id - let's get the task details
            task = await self.repository.get_task_by_id(task_id)
            if task and task.user_id == user_id:
                tasks_to_cancel.append(task_id)

        for task_id in tasks_to_cancel:
            self._execution_tasks[task_id].cancel()
            del self._execution_tasks[task_id]

        # Delete from database
        return await self.repository.delete_user_tasks(user_id, status)

    async def execute_task_queue(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute all pending tasks for a user or all users."""
        async with self.execution_lock:
            pending_tasks = await self.get_pending_tasks(user_id)

            if not pending_tasks:
                logger.info("No pending tasks to execute", user_id=user_id)
                return {"executed": 0, "failed": 0, "skipped": 0}

            logger.info(f"Executing {len(pending_tasks)} pending tasks", user_id=user_id)

            results = {"executed": 0, "failed": 0, "skipped": 0}

            for task in pending_tasks:
                try:
                    # Skip if already running
                    if task.task_id in self._execution_tasks:
                        results["skipped"] += 1
                        continue

                    # Start execution in background
                    execution_task = asyncio.create_task(
                        self._execute_single_task(task)
                    )
                    self._execution_tasks[task.task_id] = execution_task

                    # For queue execution, we wait for each task to complete
                    success = await execution_task
                    if success:
                        results["executed"] += 1
                    else:
                        results["failed"] += 1

                    # Clean up the task reference
                    if task.task_id in self._execution_tasks:
                        del self._execution_tasks[task.task_id]

                except Exception as e:
                    logger.error(
                        "Error executing task",
                        task_id=task.task_id,
                        error=str(e),
                        exc_info=True
                    )
                    results["failed"] += 1

                    # Clean up on error
                    if task.task_id in self._execution_tasks:
                        del self._execution_tasks[task.task_id]

                    await self.repository.update_task_status(
                        task.task_id,
                        "failed",
                        error_message=f"Execution error: {str(e)}"
                    )

            logger.info("Task queue execution completed", results=results, user_id=user_id)
            return results

    async def _execute_single_task(self, task: ScheduledTaskModel) -> bool:
        """Execute a single task."""
        start_time = datetime.utcnow()

        try:
            # Mark task as running
            await self.repository.update_task_status(task.task_id, "running")

            logger.info(
                "Executing task",
                task_id=task.task_id,
                user_id=task.user_id,
                task_type=task.task_type
            )

            # Get working directory from metadata or use default
            working_directory = self.settings.approved_directory
            if task.metadata and "working_directory" in task.metadata:
                from pathlib import Path
                working_directory = Path(task.metadata["working_directory"])

            # Setup auto-responder if enabled
            original_responder = None
            if task.auto_respond:
                # This would integrate with Claude integration to auto-respond
                # For now, we'll pass it as a parameter
                pass

            # Execute the task through Claude integration
            response = await self.claude_integration.run_command(
                prompt=task.prompt,
                working_directory=working_directory,
                user_id=task.user_id,
                session_id=None,  # Use new session for scheduled tasks
                auto_respond=task.auto_respond
            )

            # Calculate execution duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            if response and response.content:
                # Mark as completed
                await self.repository.update_task_status(
                    task.task_id,
                    "completed",
                    result=response.content,
                    execution_duration_ms=duration_ms
                )

                logger.info(
                    "Task completed successfully",
                    task_id=task.task_id,
                    duration_ms=duration_ms
                )
                return True
            else:
                # No response received
                await self.repository.update_task_status(
                    task.task_id,
                    "failed",
                    error_message="No response received from Claude",
                    execution_duration_ms=duration_ms
                )
                logger.warning("Task failed - no response", task_id=task.task_id)
                return False

        except Exception as e:
            # Calculate duration even for failed tasks
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            await self.repository.update_task_status(
                task.task_id,
                "failed",
                error_message=str(e),
                execution_duration_ms=duration_ms
            )

            logger.error(
                "Task execution failed",
                task_id=task.task_id,
                error=str(e),
                duration_ms=duration_ms,
                exc_info=True
            )
            return False

    async def retry_failed_tasks(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Retry failed tasks that haven't exceeded max retries."""
        failed_tasks = await self.repository.get_failed_tasks_for_retry()

        if user_id:
            failed_tasks = [task for task in failed_tasks if task.user_id == user_id]

        if not failed_tasks:
            logger.info("No failed tasks to retry", user_id=user_id)
            return {"retried": 0, "failed": 0, "skipped": 0}

        logger.info(f"Retrying {len(failed_tasks)} failed tasks", user_id=user_id)

        results = {"retried": 0, "failed": 0, "skipped": 0}

        for task in failed_tasks:
            if not task.can_retry():
                results["skipped"] += 1
                continue

            try:
                # Reset status to pending for retry
                await self.repository.update_task_status(task.task_id, "pending")

                # Execute the task
                success = await self._execute_single_task(task)
                if success:
                    results["retried"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                logger.error(
                    "Error retrying task",
                    task_id=task.task_id,
                    error=str(e),
                    exc_info=True
                )
                results["failed"] += 1

        logger.info("Task retry completed", results=results, user_id=user_id)
        return results

    async def get_task_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get task execution statistics."""
        return await self.repository.get_task_statistics(user_id)

    async def cleanup_old_tasks(self, days_old: int = 30) -> int:
        """Clean up old completed/failed tasks."""
        return await self.repository.cleanup_old_tasks(days_old)

    def get_running_tasks(self) -> List[int]:
        """Get list of currently running task IDs."""
        return list(self._execution_tasks.keys())

    async def start_background_processor(self, check_interval: int = 60) -> None:
        """Start background task processor that checks for pending tasks periodically."""
        if self.is_running:
            logger.warning("Background processor already running")
            return

        self.is_running = True
        logger.info("Starting background task processor", check_interval=check_interval)

        try:
            while self.is_running:
                try:
                    # Execute any pending tasks
                    await self.execute_task_queue()

                    # Retry failed tasks (with backoff)
                    await self.retry_failed_tasks()

                    # Cleanup old tasks daily
                    if datetime.utcnow().hour == 2:  # 2 AM cleanup
                        await self.cleanup_old_tasks()

                except Exception as e:
                    logger.error(
                        "Error in background processor",
                        error=str(e),
                        exc_info=True
                    )

                # Wait for next check
                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.info("Background processor cancelled")
        finally:
            self.is_running = False

    def stop_background_processor(self) -> None:
        """Stop the background task processor."""
        logger.info("Stopping background task processor")
        self.is_running = False

        # Cancel all running tasks
        for task_id, execution_task in self._execution_tasks.items():
            execution_task.cancel()
            logger.info("Cancelled running task", task_id=task_id)

        self._execution_tasks.clear()

    # Predefined task templates
    @staticmethod
    def create_code_analysis_task(
        user_id: int,
        project_path: str,
        analysis_type: str = "full"
    ) -> Dict[str, Any]:
        """Create a code analysis task template."""
        prompts = {
            "full": """Виконайте повний аналіз коду проєкту:

1. **Структура проєкту**: Проаналізуйте архітектуру та організацію файлів
2. **Якість коду**: Перевірте стиль, читабельність та відповідність стандартам
3. **Потенційні проблеми**: Знайдіть можливі баги, уразливості безпеки
4. **Оптимізація**: Запропонуйте покращення продуктивності
5. **Рекомендації**: Дайте конкретні поради щодо поліпшення

Створіть детальний звіт з прикладами та рекомендаціями.""",

            "security": """Проведіть аналіз безпеки коду:

1. **Уразливості**: Знайдіть потенційні загрози безпеки
2. **Аутентифікація**: Перевірте системи авторизації та аутентифікації
3. **Валідація даних**: Оцініть валідацію вхідних даних
4. **Секрети**: Перевірте, чи немає захардкодених паролів/ключів
5. **Звіт**: Створіть звіт з рекомендаціями щодо безпеки""",

            "performance": """Проаналізуйте продуктивність коду:

1. **Вузькі місця**: Знайдіть повільні частини коду
2. **Алгоритми**: Оцініть складність алгоритмів
3. **Бази даних**: Перевірте запити та індекси
4. **Кешування**: Оцініть використання кешу
5. **Рекомендації**: Запропонуйте конкретні оптимізації"""
        }

        return {
            "task_type": "code_analysis",
            "prompt": prompts.get(analysis_type, prompts["full"]),
            "metadata": {
                "working_directory": project_path,
                "analysis_type": analysis_type
            }
        }

    @staticmethod
    def create_documentation_task(user_id: int, doc_type: str = "api") -> Dict[str, Any]:
        """Create a documentation generation task template."""
        prompts = {
            "api": """Згенеруйте API документацію для проєкту:

1. **Ендпоінти**: Опишіть всі API ендпоінти з параметрами
2. **Моделі даних**: Задокументуйте структури даних
3. **Аутентифікація**: Опишіть методи аутентифікації
4. **Приклади**: Додайте приклади запитів та відповідей
5. **Помилки**: Опишіть коди помилок та їх значення

Створіть документацію у форматі Markdown.""",

            "readme": """Оновіть або створіть README.md файл:

1. **Опис проєкту**: Коротко опишіть призначення
2. **Встановлення**: Покрокові інструкції
3. **Використання**: Приклади використання
4. **Конфігурація**: Налаштування та змінні середовища
5. **Контрибуція**: Правила для розробників

Зробіть README зрозумілим та корисним.""",

            "changelog": """Згенеруйте CHANGELOG.md:

1. **Останні зміни**: Проаналізуйте git історію
2. **Категоризація**: Розділіть на Added, Changed, Fixed, Removed
3. **Версії**: Організуйте за версіями
4. **Дати**: Додайте дати релізів
5. **Формат**: Використайте стандарт Keep a Changelog"""
        }

        return {
            "task_type": "documentation",
            "prompt": prompts.get(doc_type, prompts["readme"]),
            "metadata": {"doc_type": doc_type}
        }

    @staticmethod
    def create_refactoring_task(
        user_id: int,
        target_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a code refactoring task template."""
        files_prompt = ""
        if target_files:
            files_prompt = f"\nЦільові файли: {', '.join(target_files)}"

        prompt = f"""Виконайте рефакторинг коду:{files_prompt}

1. **Оптимізація структури**: Поліпшіть організацію коду
2. **Видалення дублювання**: Усуньте повторювані частини
3. **Покращення читабельності**: Зробіть код більш зрозумілим
4. **Виділення функцій**: Розбийте великі функції на менші
5. **Типізація**: Додайте/поліпшіть типи даних
6. **Документація**: Додайте коментарі до складних частин

Збережіть функціональність, поліпшивши якість коду."""

        return {
            "task_type": "refactoring",
            "prompt": prompt,
            "metadata": {"target_files": target_files or []}
        }