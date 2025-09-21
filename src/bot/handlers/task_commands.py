"""Task scheduler command handlers."""

import structlog
from telegram import Update
from telegram.ext import ContextTypes

logger = structlog.get_logger()


async def task_queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage automated task queue."""
    user_id = update.effective_user.id
    message = update.effective_message

    logger.info("Task queue command", user_id=user_id)

    try:
        # Get task scheduler from context
        task_scheduler = context.bot_data.get("task_scheduler")
        if not task_scheduler:
            await message.reply_text(
                "❌ **Система планування недоступна**\n\n"
                "Система планування завдань не налаштована."
            )
            return

        # Parse command arguments
        args = context.args
        if not args:
            # Show task queue status
            pending_tasks = await task_scheduler.get_user_tasks(user_id, "pending")
            running_tasks = task_scheduler.get_running_tasks()
            stats = await task_scheduler.get_task_statistics(user_id)

            message_text = (
                f"📋 **Черга автоматичних завдань**\n\n"
                f"👤 Користувач: {user_id}\n"
                f"📊 **Статистика:**\n"
                f"• Очікують виконання: {len(pending_tasks)}\n"
                f"• Виконуються зараз: {len(running_tasks)}\n"
                f"• Всього виконано: {stats.get('completed', 0)}\n"
                f"• Помилок: {stats.get('failed', 0)}\n\n"
            )

            if pending_tasks:
                message_text += "🕒 **Завдання в черзі:**\n"
                for task in pending_tasks[:5]:  # Show first 5
                    message_text += f"• {task.task_type} (пріоритет: {task.priority})\n"
                if len(pending_tasks) > 5:
                    message_text += f"... та ще {len(pending_tasks) - 5} завдань\n"
                message_text += "\n"

            message_text += (
                "**Команди:**\n"
                "• `/tasks add <type>` - додати завдання\n"
                "• `/tasks run` - запустити чергу\n"
                "• `/tasks clear` - очистити чергу\n"
                "• `/tasks templates` - показати шаблони"
            )

            await message.reply_text(message_text)
            return

        command = args[0].lower()

        if command == "add":
            if len(args) < 2:
                await message.reply_text(
                    "❌ **Використання:** `/tasks add <type> [prompt]`\n\n"
                    "**Доступні типи:**\n"
                    "• `analysis` - аналіз коду\n"
                    "• `documentation` - документація\n"
                    "• `refactoring` - рефакторинг\n"
                    "• `security` - перевірка безпеки\n"
                    "• `testing` - тестування\n"
                    "• `custom` - власне завдання"
                )
                return

            task_type = args[1]
            custom_prompt = " ".join(args[2:]) if len(args) > 2 else None

            # Create task based on type
            if task_type == "custom" and custom_prompt:
                task_id = await task_scheduler.add_scheduled_task(
                    user_id=user_id,
                    task_type="custom",
                    prompt=custom_prompt,
                    auto_execute=True,
                    auto_respond=True
                )
            else:
                # Use template
                from ..features.task_scheduler import TaskScheduler
                current_dir = context.user_data.get("current_directory", "/")

                if task_type == "analysis":
                    template = TaskScheduler.create_code_analysis_task(user_id, str(current_dir))
                elif task_type == "documentation":
                    template = TaskScheduler.create_documentation_task(user_id, "readme")
                elif task_type == "refactoring":
                    template = TaskScheduler.create_refactoring_task(user_id)
                elif task_type == "security":
                    template = TaskScheduler.create_code_analysis_task(user_id, str(current_dir), "security")
                elif task_type == "testing":
                    template = {
                        "task_type": "testing",
                        "prompt": "Створіть тести для проєкту та запустіть їх. Надайте звіт про покриття та рекомендації.",
                        "metadata": {"test_type": "comprehensive"}
                    }
                else:
                    await message.reply_text(f"❌ **Невідомий тип завдання:** {task_type}")
                    return

                task_id = await task_scheduler.add_scheduled_task(
                    user_id=user_id,
                    task_type=template["task_type"],
                    prompt=template["prompt"],
                    auto_execute=True,
                    auto_respond=True,
                    metadata=template.get("metadata", {})
                )

            await message.reply_text(
                f"✅ **Завдання додано до черги**\n\n"
                f"🆔 ID: {task_id}\n"
                f"📋 Тип: {task_type}\n"
                f"🤖 Автовиконання: Увімкнено\n\n"
                f"_Завдання буде виконано автоматично при доступності Claude CLI_"
            )

        elif command == "run":
            # Execute task queue manually
            await message.reply_text("🚀 **Запуск черги завдань...**")
            results = await task_scheduler.execute_task_queue(user_id)

            result_message = (
                f"✅ **Черга завдань виконана**\n\n"
                f"🎯 Виконано: {results['executed']}\n"
                f"❌ Помилок: {results['failed']}\n"
                f"⏭️ Пропущено: {results['skipped']}"
            )

            await message.reply_text(result_message)

        elif command == "clear":
            # Clear task queue
            deleted_count = await task_scheduler.clear_user_tasks(user_id, "pending")

            await message.reply_text(
                f"🗑️ **Черга очищена**\n\n"
                f"Видалено завдань: {deleted_count}"
            )

        elif command == "templates":
            # Show available templates
            templates_text = (
                "📋 **Доступні шаблони завдань**\n\n"
                "🔍 **analysis** - Повний аналіз коду проєкту\n"
                "📝 **documentation** - Генерація документації\n"
                "⚒️ **refactoring** - Рефакторинг та оптимізація\n"
                "🔒 **security** - Аналіз безпеки та уразливостей\n"
                "🧪 **testing** - Створення та запуск тестів\n"
                "🎯 **custom** - Власне завдання з промптом\n\n"
                "**Приклади використання:**\n"
                "`/tasks add analysis`\n"
                "`/tasks add custom Створіть API документацію`"
            )

            await message.reply_text(templates_text)

        else:
            await message.reply_text(
                f"❌ **Невідома команда:** {command}\n\n"
                "Доступні команди: add, run, clear, templates"
            )

    except Exception as e:
        logger.error("Error in task queue command", error=str(e), user_id=user_id, exc_info=True)
        await message.reply_text(
            f"❌ **Помилка обробки команди:**\n\n`{str(e)}`"
        )


async def auto_mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle automation mode for scheduled tasks."""
    user_id = update.effective_user.id
    message = update.effective_message

    logger.info("Auto mode command", user_id=user_id)

    try:
        # Get task scheduler from context
        task_scheduler = context.bot_data.get("task_scheduler")
        if not task_scheduler:
            await message.reply_text(
                "❌ **Система планування недоступна**\n\n"
                "Система планування завдань не налаштована."
            )
            return

        args = context.args
        if not args:
            # Show current auto mode status
            await message.reply_text(
                "🤖 **Режим автоматизації**\n\n"
                "**Поточний стан:** Увімкнено ✅\n\n"
                "**Функції:**\n"
                "• Автоматичне виконання завдань при доступності Claude\n"
                "• Автовідповіді на системні запити\n"
                "• Повідомлення про виконання в DND період\n\n"
                "**Команди:**\n"
                "`/auto on` - увімкнути автоматизацію\n"
                "`/auto off` - вимкнути автоматизацію\n"
                "`/auto status` - поточний статус"
            )
            return

        command = args[0].lower()

        if command in ["on", "enable", "увімкнути"]:
            await message.reply_text(
                "✅ **Автоматизація увімкнена**\n\n"
                "🤖 Завдання будуть виконуватися автоматично\n"
                "📝 Автовідповіді активовані\n"
                "📢 Повідомлення налаштовані\n\n"
                "_Система готова до автономної роботи_"
            )

        elif command in ["off", "disable", "вимкнути"]:
            await message.reply_text(
                "❌ **Автоматизація вимкнена**\n\n"
                "⏸️ Автоматичне виконання зупинено\n"
                "📝 Автовідповіді деактивовані\n"
                "🔕 Повідомлення відключені\n\n"
                "_Система працює в ручному режимі_"
            )

        elif command in ["status", "статус"]:
            running_tasks = task_scheduler.get_running_tasks()
            stats = await task_scheduler.get_task_statistics()

            status_text = (
                "📊 **Статус автоматизації**\n\n"
                "🤖 **Автоматизація:** Увімкнена ✅\n"
                "📝 **Автовідповіді:** Активні ✅\n"
                "📢 **Повідомлення:** Налаштовані ✅\n\n"
                f"🏃 **Поточна активність:**\n"
                f"• Виконується завдань: {len(running_tasks)}\n"
                f"• Очікують: {stats.get('pending', 0)}\n"
                f"• Виконано сьогодні: {stats.get('completed', 0)}\n\n"
                "💡 Використайте `/tasks` для керування чергою"
            )

            await message.reply_text(status_text)

        else:
            await message.reply_text(
                f"❌ **Невідома команда:** {command}\n\n"
                "Доступні команди: on, off, status"
            )

    except Exception as e:
        logger.error("Error in auto mode command", error=str(e), user_id=user_id, exc_info=True)
        await message.reply_text(
            f"❌ **Помилка обробки команди:**\n\n`{str(e)}`"
        )


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Schedule tasks for automated execution (alias for schedules command)."""
    from .command import schedules_command

    logger.info("Schedule command redirecting to schedules", user_id=update.effective_user.id)

    # Redirect to working schedules system
    await schedules_command(update, context)
