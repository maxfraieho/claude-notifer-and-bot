"""Unified button interface for improved user experience."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...storage.facade import Storage
from ...claude.context_memory import ContextMemoryManager

logger = structlog.get_logger()


class UnifiedMenu:
    """Unified menu system with categorized navigation."""

    def __init__(self, storage: Storage, context_memory: ContextMemoryManager):
        """Initialize unified menu.

        Args:
            storage: Storage facade for data access
            context_memory: Context memory manager
        """
        self.storage = storage
        self.context_memory = context_memory

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show main menu with categories."""
        try:
            menu_text = (
                "🏠 **Головне меню DevClaude_bot**\n\n"
                "Оберіть категорію для роботи:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🤖 Claude CLI", callback_data="menu_claude"),
                    InlineKeyboardButton("🧠 Контекст", callback_data="menu_context")
                ],
                [
                    InlineKeyboardButton("📊 Моніторинг", callback_data="menu_monitoring"),
                    InlineKeyboardButton("📁 Файли", callback_data="menu_files")
                ],
                [
                    InlineKeyboardButton("🔧 Git", callback_data="menu_git"),
                    InlineKeyboardButton("⏰ Завдання", callback_data="menu_tasks")
                ],
                [
                    InlineKeyboardButton("⚙️ Налаштування", callback_data="menu_settings"),
                    InlineKeyboardButton("ℹ️ Допомога", callback_data="menu_help")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            if update.callback_query:
                await update.callback_query.edit_message_text(
                    menu_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    menu_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error("Failed to show main menu", error=str(e))
            await self._send_error_message(update, "Помилка відображення головного меню")

    async def show_claude_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show Claude CLI management menu."""
        try:
            # Get current session info
            user_id = update.effective_user.id
            sessions = await self.storage.sessions.get_user_sessions(user_id)
            active_sessions = [s for s in sessions if s.status == "active"]

            session_info = ""
            if active_sessions:
                session = active_sessions[0]
                session_info = f"\n📱 Активна сесія: `{session.session_id[:8]}...`"
            else:
                session_info = "\n📱 Немає активних сесій"

            menu_text = (
                "🤖 **Claude CLI управління**\n"
                f"{session_info}\n\n"
                "Оберіть дію:"
            )

            keyboard = []

            if active_sessions:
                keyboard.extend([
                    [InlineKeyboardButton("💬 Продовжити сесію", callback_data="claude_continue")],
                    [
                        InlineKeyboardButton("🧠 Контекст", callback_data="claude_context"),
                        InlineKeyboardButton("📊 Статус", callback_data="claude_status")
                    ]
                ])
            else:
                keyboard.append([InlineKeyboardButton("🆕 Нова сесія", callback_data="claude_new")])

            keyboard.extend([
                [
                    InlineKeyboardButton("🔑 Авторизація", callback_data="claude_login"),
                    InlineKeyboardButton("📋 Всі сесії", callback_data="claude_sessions")
                ],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="menu_main")]
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                menu_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to show Claude menu", error=str(e))
            await self._send_error_message(update, "Помилка відображення меню Claude")

    async def show_context_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show context memory management menu."""
        try:
            user_id = update.effective_user.id
            project_path = str(context.bot_data.get("approved_directory", "/tmp"))

            # Get context statistics
            user_context = await self.context_memory.get_user_context(user_id, project_path)
            stats = await self.storage.context.get_context_stats(user_id, project_path)

            entries_count = stats.get('total_entries', 0)
            last_update = user_context.last_updated.strftime('%d.%m %H:%M') if user_context.last_updated else 'Ніколи'

            menu_text = (
                "🧠 **Управління контекстом**\n\n"
                f"📊 Записів: {entries_count}\n"
                f"🔄 Останнє оновлення: {last_update}\n"
                f"📂 Проект: `{project_path.split('/')[-1]}`\n\n"
                "Оберіть дію:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("📋 Статус", callback_data="context_status"),
                    InlineKeyboardButton("📝 Список", callback_data="context_list")
                ],
                [
                    InlineKeyboardButton("🔍 Пошук", callback_data="context_search"),
                    InlineKeyboardButton("📤 Експорт", callback_data="context_export")
                ]
            ]

            if entries_count > 0:
                keyboard.append([
                    InlineKeyboardButton("🗑️ Очистити", callback_data="context_clear")
                ])

            keyboard.append([
                InlineKeyboardButton("🏠 Головне меню", callback_data="menu_main")
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                menu_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to show context menu", error=str(e))
            await self._send_error_message(update, "Помилка відображення меню контексту")

    async def show_monitoring_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show monitoring and status menu."""
        try:
            # Check availability monitor status
            availability_monitor = context.bot_data.get("claude_availability_monitor")
            monitor_status = "🟢 Працює" if availability_monitor else "🔴 Недоступний"

            menu_text = (
                "📊 **Моніторинг системи**\n\n"
                f"🤖 Claude CLI: {monitor_status}\n\n"
                "Оберіть дію:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("📈 Статус Claude", callback_data="claude_status"),
                    InlineKeyboardButton("📊 Історія", callback_data="claude_history")
                ],
                [
                    InlineKeyboardButton("🔔 Сповіщення", callback_data="claude_notifications"),
                    InlineKeyboardButton("⚙️ Налаштування", callback_data="monitoring_settings")
                ],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="menu_main")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                menu_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to show monitoring menu", error=str(e))
            await self._send_error_message(update, "Помилка відображення меню моніторингу")

    async def show_files_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show file management menu."""
        try:
            current_dir = str(context.bot_data.get("approved_directory", "/tmp"))
            dir_name = current_dir.split('/')[-1] if current_dir != "/" else "root"

            menu_text = (
                "📁 **Управління файлами**\n\n"
                f"📂 Поточна директорія: `{dir_name}`\n"
                f"🛣️ Повний шлях: `{current_dir}`\n\n"
                "Оберіть дію:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("📋 Список файлів", callback_data="files_list"),
                    InlineKeyboardButton("📍 Поточна папка", callback_data="files_pwd")
                ],
                [
                    InlineKeyboardButton("📂 Змінити папку", callback_data="files_cd"),
                    InlineKeyboardButton("🔍 Пошук файлів", callback_data="files_search")
                ],
                [
                    InlineKeyboardButton("✏️ Редагувати", callback_data="files_edit"),
                    InlineKeyboardButton("▶️ Виконати", callback_data="files_run")
                ],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="menu_main")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                menu_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to show files menu", error=str(e))
            await self._send_error_message(update, "Помилка відображення меню файлів")

    async def show_git_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show Git management menu."""
        try:
            menu_text = (
                "🔧 **Git управління**\n\n"
                "Керування Git репозиторієм:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("📊 Статус", callback_data="git_status"),
                    InlineKeyboardButton("📋 Лог", callback_data="git_log")
                ],
                [
                    InlineKeyboardButton("📤 Push", callback_data="git_push"),
                    InlineKeyboardButton("📥 Pull", callback_data="git_pull")
                ],
                [
                    InlineKeyboardButton("🔄 Commit", callback_data="git_commit"),
                    InlineKeyboardButton("🌿 Гілки", callback_data="git_branches")
                ],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="menu_main")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                menu_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to show Git menu", error=str(e))
            await self._send_error_message(update, "Помилка відображення меню Git")

    async def show_tasks_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show scheduled tasks menu."""
        try:
            # Get tasks count
            user_id = update.effective_user.id
            tasks = await self.storage.tasks.get_user_tasks(user_id)
            active_tasks = [t for t in tasks if t.status == "active"]

            menu_text = (
                "⏰ **Запланові завдання**\n\n"
                f"📊 Всього завдань: {len(tasks)}\n"
                f"🟢 Активних: {len(active_tasks)}\n\n"
                "Оберіть дію:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("📋 Список завдань", callback_data="tasks_list"),
                    InlineKeyboardButton("➕ Додати", callback_data="tasks_add")
                ],
                [
                    InlineKeyboardButton("⚙️ Налаштування", callback_data="tasks_settings"),
                    InlineKeyboardButton("🔄 Авто-режим", callback_data="tasks_auto")
                ],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="menu_main")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                menu_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to show tasks menu", error=str(e))
            await self._send_error_message(update, "Помилка відображення меню завдань")

    async def show_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show help and documentation menu."""
        try:
            menu_text = (
                "ℹ️ **Допомога та інформація**\n\n"
                "Оберіть розділ:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("📖 Команди", callback_data="help_commands"),
                    InlineKeyboardButton("🤖 Про бота", callback_data="help_about")
                ],
                [
                    InlineKeyboardButton("📋 Версія", callback_data="help_version"),
                    InlineKeyboardButton("🔧 Налаштування", callback_data="help_settings")
                ],
                [
                    InlineKeyboardButton("💡 Поради", callback_data="help_tips"),
                    InlineKeyboardButton("🆘 Підтримка", callback_data="help_support")
                ],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="menu_main")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                menu_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to show help menu", error=str(e))
            await self._send_error_message(update, "Помилка відображення меню допомоги")

    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle menu navigation callbacks."""
        query = update.callback_query
        data = query.data

        try:
            await query.answer()  # Acknowledge callback

            if data == "menu_main":
                await self.show_main_menu(update, context)
            elif data == "menu_claude":
                await self.show_claude_menu(update, context)
            elif data == "menu_context":
                await self.show_context_menu(update, context)
            elif data == "menu_monitoring":
                await self.show_monitoring_menu(update, context)
            elif data == "menu_files":
                await self.show_files_menu(update, context)
            elif data == "menu_git":
                await self.show_git_menu(update, context)
            elif data == "menu_tasks":
                await self.show_tasks_menu(update, context)
            elif data == "menu_help":
                await self.show_help_menu(update, context)
            else:
                # Handle specific action callbacks
                await self._handle_action_callback(update, context, data)

        except Exception as e:
            logger.error("Failed to handle menu callback", data=data, error=str(e))
            await query.answer("❌ Помилка обробки команди")

    async def _handle_action_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """Handle specific action callbacks."""
        # Map callbacks to commands
        if data.startswith("claude_"):
            command_name = data.replace("claude_", "")
            if command_name == "new":
                await self._execute_command(update, context, "new")
            elif command_name == "continue":
                await self._execute_command(update, context, "continue")
            elif command_name == "status":
                await self._execute_command(update, context, "claude_status")
            elif command_name == "context":
                await self._execute_command(update, context, "context")
        elif data.startswith("files_"):
            command_name = data.replace("files_", "")
            if command_name == "list":
                await self._execute_command(update, context, "ls")
            elif command_name == "pwd":
                await self._execute_command(update, context, "pwd")
        elif data.startswith("git_"):
            command_name = data.replace("git_", "")
            await self._execute_command(update, context, f"git {command_name}")

    async def _execute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, command: str) -> None:
        """Execute a command by simulating user input."""
        # This would need integration with existing command handlers
        await update.callback_query.edit_message_text(
            f"🔄 Виконання команди: `/{command}`\n\n"
            "Команду буде виконано...",
            parse_mode="Markdown"
        )

    async def _send_error_message(self, update: Update, message: str) -> None:
        """Send error message to user."""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"❌ {message}\n\nСпробуйте пізніше.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"❌ {message}\n\nСпробуйте пізніше.",
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error("Failed to send error message", error=str(e))