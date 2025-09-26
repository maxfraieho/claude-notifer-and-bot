"""Context management commands for persistent conversation memory."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...claude.context_memory import ContextMemoryManager
from ...storage.facade import Storage

logger = structlog.get_logger()


class ContextCommands:
    """Commands for managing persistent context memory."""

    def __init__(self, storage: Storage, context_memory: ContextMemoryManager):
        """Initialize context commands.

        Args:
            storage: Storage facade for data access
            context_memory: Context memory manager
        """
        self.storage = storage
        self.context_memory = context_memory

    async def handle_context_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show context status and statistics."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # DEBUG: Log what's available in bot_data
        approved_dir_from_bot_data = context.bot_data.get("approved_directory")
        logger.debug("Context status debug",
                    approved_dir_from_bot_data=approved_dir_from_bot_data,
                    settings_available=bool(settings),
                    settings_approved_dir=getattr(settings, 'approved_directory', None) if settings else None)

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        logger.info("Context status using project_path", project_path=project_path)

        try:
            # Get context statistics
            user_context = await self.context_memory.get_user_context(user_id, project_path)
            stats = await self.storage.context.get_context_stats(user_id, project_path)

            # Format statistics
            status_lines = [
                "🧠 **Статус контекстної пам'яті**",
                "",
                f"📊 **Статистика:**",
                f"• Всього записів: {stats.get('total_entries', 0)}",
                f"• Сесій з контекстом: {stats.get('sessions_count', 0)}",
                f"• Перший запис: {stats.get('first_entry', 'Немає').split('T')[0] if stats.get('first_entry') else 'Немає'}",
                f"• Останній запис: {stats.get('last_entry', 'Немає').split('T')[0] if stats.get('last_entry') else 'Немає'}",
                "",
                f"📈 **За важливістю:**",
                f"• Високої важливості: {stats.get('high_importance', 0)}",
                f"• Середньої важливості: {stats.get('medium_importance', 0)}",
                f"• Низької важливості: {stats.get('low_importance', 0)}",
                "",
                f"🏗️ **Поточний проект:** `{project_path}`",
                f"🔄 **Останнє оновлення:** {user_context.last_updated.strftime('%Y-%m-%d %H:%M')}"
            ]

            keyboard = [
                [
                    InlineKeyboardButton("📤 Експорт", callback_data="context_export"),
                    InlineKeyboardButton("📥 Імпорт", callback_data="context_import")
                ],
                [
                    InlineKeyboardButton("🔍 Пошук", callback_data="context_search"),
                    InlineKeyboardButton("📋 Список", callback_data="context_list")
                ],
                [
                    InlineKeyboardButton("🗑️ Очистити", callback_data="context_clear"),
                    InlineKeyboardButton("❌ Закрити", callback_data="context_close")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "\n".join(status_lines),
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to show context status", error=str(e))
            await update.message.reply_text(
                "❌ **Помилка отримання статусу контексту**\n\n"
                "Спробуйте пізніше або зверніться до адміністратора.",
                parse_mode="Markdown"
            )

    async def handle_context_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Export user context to file."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        # Determine if this is from callback or direct command
        is_callback = hasattr(update, 'callback_query') and update.callback_query
        message = update.callback_query.message if is_callback else update.message

        try:
            # Export context
            context_data = await self.context_memory.export_context(user_id, project_path)

            if not context_data.get("entries"):
                if is_callback:
                    await update.callback_query.answer("📭 Контекст порожній")
                    await message.reply_text(
                        "📭 **Контекст порожній**\n\n"
                        "Немає збереженого контексту для експорту.",
                        parse_mode="Markdown"
                    )
                else:
                    await message.reply_text(
                        "📭 **Контекст порожній**\n\n"
                        "Немає збереженого контексту для експорту.",
                        parse_mode="Markdown"
                    )
                return

            # Format as readable JSON
            import json
            export_content = json.dumps(context_data, indent=2, ensure_ascii=False)

            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"context_export_{user_id}_{timestamp}.json"

            # Send as document
            from io import BytesIO
            file_obj = BytesIO(export_content.encode('utf-8'))
            file_obj.name = filename

            if is_callback:
                await update.callback_query.answer("📤 Експортую контекст...")

            await message.reply_document(
                document=file_obj,
                caption=(
                    f"📤 **Експорт контексту успішний**\n\n"
                    f"• Записів: {len(context_data.get('entries', []))}\n"
                    f"• Проект: `{project_path}`\n"
                    f"• Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                ),
                parse_mode="Markdown"
            )

            logger.info("Context exported",
                       user_id=user_id,
                       entries_count=len(context_data.get("entries", [])))

        except Exception as e:
            logger.error("Failed to export context", error=str(e))
            await update.message.reply_text(
                "❌ **Помилка експорту контексту**\n\n"
                "Спробуйте пізніше або зверніться до адміністратора.",
                parse_mode="Markdown"
            )

    async def handle_context_import(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle context import request."""
        # Determine if this is from callback or direct command
        is_callback = hasattr(update, 'callback_query') and update.callback_query
        message = update.callback_query.message if is_callback else update.message

        import_text = (
            "📥 **Імпорт контексту**\n\n"
            "Надішліть JSON файл з експортованим контекстом.\n"
            "Файл має бути створений командою експорту контексту.\n\n"
            "⚠️ **Увага:** Імпорт додасть нові записи до існуючого контексту."
        )

        if is_callback:
            await update.callback_query.answer("📥 Імпорт контексту")
            await message.reply_text(import_text, parse_mode="Markdown")
        else:
            await message.reply_text(import_text, parse_mode="Markdown")

        # Set user state for import
        context.user_data["awaiting_context_import"] = True

    async def handle_context_import_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_content: str) -> None:
        """Process imported context file."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        try:
            # Parse JSON content
            import json
            context_data = json.loads(file_content)

            # Validate structure
            if not isinstance(context_data, dict) or "entries" not in context_data:
                await update.message.reply_text(
                    "❌ **Неправильний формат файлу**\n\n"
                    "Файл має бути JSON з експортованим контекстом.",
                    parse_mode="Markdown"
                )
                return

            entries = context_data.get("entries", [])
            if not entries:
                await update.message.reply_text(
                    "📭 **Файл порожній**\n\n"
                    "У файлі немає записів для імпорту.",
                    parse_mode="Markdown"
                )
                return

            # Import context
            success = await self.context_memory.import_context(context_data)

            if success:
                await update.message.reply_text(
                    f"✅ **Імпорт успішний**\n\n"
                    f"• Імпортовано записів: {len(entries)}\n"
                    f"• Проект: `{project_path}`\n"
                    f"• Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode="Markdown"
                )
                logger.info("Context imported",
                           user_id=user_id,
                           entries_count=len(entries))
            else:
                await update.message.reply_text(
                    "❌ **Помилка імпорту**\n\n"
                    "Не вдалося імпортувати контекст. Спробуйте пізніше.",
                    parse_mode="Markdown"
                )

        except json.JSONDecodeError:
            await update.message.reply_text(
                "❌ **Неправильний JSON**\n\n"
                "Файл містить некоректний JSON. Перевірте формат.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error("Failed to import context", error=str(e))
            await update.message.reply_text(
                "❌ **Помилка імпорту контексту**\n\n"
                "Спробуйте пізніше або зверніться до адміністратора.",
                parse_mode="Markdown"
            )

    async def handle_context_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear user context with confirmation."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        # Determine if this is from callback or direct command
        is_callback = hasattr(update, 'callback_query') and update.callback_query

        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Так, очистити", callback_data="context_clear_confirm"),
                InlineKeyboardButton("❌ Скасувати", callback_data="context_clear_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        confirmation_text = (
            "⚠️ **Підтвердження очищення контексту**\n\n"
            "Це дія видалить **весь** збережений контекст розмов з Claude CLI.\n"
            "Відновити дані після цього буде **неможливо**.\n\n"
            "Ви дійсно хочете продовжити?"
        )

        if is_callback:
            await update.callback_query.answer("⚠️ Підтвердження очищення")
            await update.callback_query.message.reply_text(
                confirmation_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                confirmation_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

    async def handle_context_clear_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Confirm and execute context clearing."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        try:
            # Clear context
            success = await self.context_memory.clear_context(user_id, project_path)

            if success:
                await update.callback_query.edit_message_text(
                    "✅ **Контекст успішно очищено**\n\n"
                    "Всі збережені розмови з Claude CLI видалено.\n"
                    "Наступна сесія почнеться з чистого аркуша.",
                    parse_mode="Markdown"
                )
                logger.info("Context cleared", user_id=user_id, project_path=project_path)
            else:
                await update.callback_query.edit_message_text(
                    "❌ **Помилка очищення контексту**\n\n"
                    "Не вдалося очистити контекст. Спробуйте пізніше.",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error("Failed to clear context", error=str(e))
            await update.callback_query.edit_message_text(
                "❌ **Помилка очищення контексту**\n\n"
                "Сталася помилка. Спробуйте пізніше.",
                parse_mode="Markdown"
            )

    async def handle_context_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search context entries by content."""
        # Determine if this is from callback or direct command
        is_callback = hasattr(update, 'callback_query') and update.callback_query
        message = update.callback_query.message if is_callback else update.message

        search_text = (
            "🔍 **Пошук в контексті**\n\n"
            "Надішліть текст для пошуку в збережених розмовах.\n"
            "Наприклад: `помилка база даних` або `функція логування`"
        )

        if is_callback:
            await update.callback_query.answer("🔍 Пошук в контексті")
            await message.reply_text(search_text, parse_mode="Markdown")
        else:
            await message.reply_text(search_text, parse_mode="Markdown")

        # Set user state for search
        context.user_data["awaiting_context_search"] = True

    async def handle_context_search_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Execute context search with user query."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        try:
            # Search context entries
            entries = await self.storage.context.search_context_entries(
                user_id=user_id,
                project_path=project_path,
                search_text=search_text,
                limit=10
            )

            if not entries:
                await update.message.reply_text(
                    f"🔍 **Результати пошуку**\n\n"
                    f"Запит: `{search_text}`\n"
                    f"Знайдено: **0 записів**\n\n"
                    f"Спробуйте інші ключові слова.",
                    parse_mode="Markdown"
                )
                return

            # Format search results
            results_lines = [
                f"🔍 **Результати пошуку**",
                f"",
                f"Запит: `{search_text}`",
                f"Знайдено: **{len(entries)} записів**",
                ""
            ]

            for i, entry in enumerate(entries[:5], 1):  # Show first 5 results
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M")
                content_preview = entry.content[:100] + "..." if len(entry.content) > 100 else entry.content

                results_lines.extend([
                    f"**{i}. [{timestamp}] {entry.message_type.title()}**",
                    f"{content_preview}",
                    ""
                ])

            if len(entries) > 5:
                results_lines.append(f"... і ще {len(entries) - 5} записів")

            keyboard = [
                [InlineKeyboardButton("📤 Експорт результатів", callback_data=f"context_export_search:{search_text}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "\n".join(results_lines),
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Failed to search context", error=str(e))
            await update.message.reply_text(
                "❌ **Помилка пошуку**\n\n"
                "Спробуйте пізніше або зверніться до адміністратора.",
                parse_mode="Markdown"
            )

    async def handle_context_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show recent context entries list."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        # Determine if this is from callback or direct command
        is_callback = hasattr(update, 'callback_query') and update.callback_query
        message = update.callback_query.message if is_callback else update.message

        try:
            # Get recent context entries
            entries = await self.storage.context.get_recent_context_entries(
                user_id=user_id,
                project_path=project_path,
                days=7,
                limit=10
            )

            if not entries:
                list_text = (
                    "📋 **Список контексту**\n\n"
                    "Немає записів за останні 7 днів.\n"
                    "Почніть розмову з Claude CLI, щоб створити контекст."
                )

                if is_callback:
                    await update.callback_query.answer("📋 Список контексту")
                    await message.reply_text(list_text, parse_mode="Markdown")
                else:
                    await message.reply_text(list_text, parse_mode="Markdown")
                return

            # Format entries list
            list_lines = [
                "📋 **Останні записи контексту**",
                f"(за останні 7 днів - {len(entries)} записів)",
                ""
            ]

            for entry in entries:
                timestamp = entry.timestamp.strftime("%m-%d %H:%M")
                importance_icon = "🔥" if entry.importance == 1 else "📝" if entry.importance == 2 else "📄"
                type_icon = "👤" if entry.message_type == "user" else "🤖"

                content_preview = entry.content[:80] + "..." if len(entry.content) > 80 else entry.content

                list_lines.append(f"{type_icon} {importance_icon} [{timestamp}] {content_preview}")

            keyboard = [
                [
                    InlineKeyboardButton("📤 Експорт списку", callback_data="context_export_recent"),
                    InlineKeyboardButton("🔄 Оновити", callback_data="context_list_refresh")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if is_callback:
                await update.callback_query.answer("📋 Список контексту")
                await message.reply_text(
                    "\n".join(list_lines),
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                await message.reply_text(
                    "\n".join(list_lines),
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error("Failed to list context entries", error=str(e))
            await update.message.reply_text(
                "❌ **Помилка отримання списку**\n\n"
                "Спробуйте пізніше або зверніться до адміністратора.",
                parse_mode="Markdown"
            )

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from context management buttons."""
        query = update.callback_query
        data = query.data

        try:
            if data == "context_export":
                await self.handle_context_export(update, context)
            elif data == "context_import":
                await self.handle_context_import(update, context)
            elif data == "context_clear":
                await self.handle_context_clear(update, context)
            elif data == "context_clear_confirm":
                await self.handle_context_clear_confirm(update, context)
            elif data == "context_clear_cancel":
                await query.edit_message_text(
                    "❌ **Очищення скасовано**\n\n"
                    "Контекст залишається незміненим.",
                    parse_mode="Markdown"
                )
            elif data == "context_search":
                await self.handle_context_search(update, context)
            elif data == "context_list":
                await self.handle_context_list(update, context)
            elif data == "context_list_refresh":
                await self.handle_context_list(update, context)
            elif data == "context_close":
                await query.edit_message_text(
                    "🧠 **Управління контекстом завершено**",
                    parse_mode="Markdown"
                )
            elif data.startswith("context_export_search:"):
                search_text = data.split(":", 1)[1]
                await self._export_search_results(update, context, search_text)
            elif data == "context_export_recent":
                await self._export_recent_entries(update, context)

        except Exception as e:
            logger.error("Failed to handle context callback", data=data, error=str(e))
            await query.answer("❌ Помилка обробки команди")

    async def _export_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_text: str) -> None:
        """Export search results to file."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        try:
            # Get search results
            entries = await self.storage.context.search_context_entries(
                user_id=user_id,
                project_path=project_path,
                search_text=search_text,
                limit=50  # Export more results
            )

            # Format as readable text
            export_lines = [
                f"🔍 Результати пошуку: {search_text}",
                f"📅 Дата експорту: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"🏗️ Проект: {project_path}",
                f"📊 Знайдено записів: {len(entries)}",
                "=" * 50,
                ""
            ]

            for entry in entries:
                export_lines.extend([
                    f"📅 {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"👤 {entry.message_type.title()}",
                    f"⭐ Важливість: {entry.importance}",
                    f"📝 {entry.content}",
                    "-" * 30,
                    ""
                ])

            export_content = "\n".join(export_lines)

            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"context_search_{search_text[:20]}_{timestamp}.txt"

            # Send as document
            from io import BytesIO
            file_obj = BytesIO(export_content.encode('utf-8'))
            file_obj.name = filename

            await update.callback_query.message.reply_document(
                document=file_obj,
                caption=f"📤 Експорт результатів пошуку: `{search_text}`",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error("Failed to export search results", error=str(e))
            await update.callback_query.answer("❌ Помилка експорту")

    async def _export_recent_entries(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Export recent context entries to file."""
        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        # Use settings.approved_directory as primary source, fallback to hardcoded path
        if settings and hasattr(settings, 'approved_directory'):
            project_path = str(settings.approved_directory)
        else:
            project_path = "/home/vokov/projects/claude-notifer-and-bot"

        try:
            # Get recent entries
            entries = await self.storage.context.get_recent_context_entries(
                user_id=user_id,
                project_path=project_path,
                days=7,
                limit=100
            )

            # Format as readable text
            export_lines = [
                f"📋 Останні записи контексту",
                f"📅 Дата експорту: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"🏗️ Проект: {project_path}",
                f"📊 Записів: {len(entries)} (за останні 7 днів)",
                "=" * 50,
                ""
            ]

            for entry in entries:
                export_lines.extend([
                    f"📅 {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"👤 {entry.message_type.title()}",
                    f"⭐ Важливість: {entry.importance}",
                    f"📝 {entry.content}",
                    "-" * 30,
                    ""
                ])

            export_content = "\n".join(export_lines)

            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"context_recent_{timestamp}.txt"

            # Send as document
            from io import BytesIO
            file_obj = BytesIO(export_content.encode('utf-8'))
            file_obj.name = filename

            await update.callback_query.message.reply_document(
                document=file_obj,
                caption="📤 Експорт останніх записів контексту",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error("Failed to export recent entries", error=str(e))
            await update.callback_query.answer("❌ Помилка експорту")