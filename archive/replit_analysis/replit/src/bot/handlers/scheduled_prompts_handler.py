"""Handlers for scheduled prompts management commands."""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from src.bot.features.scheduled_prompts import ScheduledPromptsManager

logger = structlog.get_logger(__name__)


class ScheduledPromptsHandler:
    """Handler for scheduled prompts management."""
    
    def __init__(self, prompts_manager: ScheduledPromptsManager):
        self.prompts_manager = prompts_manager
    
    async def list_prompts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all scheduled prompts."""
        try:
            config = await self.prompts_manager.load_prompts()
            prompts = config.get("prompts", [])
            settings = config.get("settings", {})
            
            if not prompts:
                await update.message.reply_text(
                    "📋 **Планованих завдань немає**\n"
                    "Використайте /add_prompt для додавання нового завдання"
                )
                return
            
            message = f"📋 **Планові завдання** ({len(prompts)})\n"
            message += f"🔧 Система: {'✅ Увімкнена' if settings.get('enabled', False) else '❌ Вимкнена'}\n\n"
            
            for i, prompt in enumerate(prompts, 1):
                status_icon = "✅" if prompt.get("enabled", False) else "❌"
                schedule = prompt.get("schedule", {})
                schedule_info = f"{schedule.get('type', 'daily')} о {schedule.get('time', '02:00')}"
                
                message += (
                    f"{i}. {status_icon} **{prompt.get('title', 'Без назви')}**\n"
                    f"   📅 {schedule_info}\n"
                    f"   📝 {prompt.get('description', 'Без опису')}\n\n"
                )
            
            # Add management buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔧 Налаштування", callback_data="prompts_settings"),
                    InlineKeyboardButton("📊 Історія", callback_data="prompts_history")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=None)
            
        except Exception as e:
            logger.error(f"Error listing prompts: {e}")
            await update.message.reply_text("❌ Помилка при завантаженні списку завдань")
    
    async def add_prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a new scheduled prompt - shows usage instructions."""
        usage_text = """
📝 **Додавання нового планового завдання**

Формат команди:
```
/add_prompt "назва" "опис" "промт" час тип
```

**Параметри:**
• `назва` - коротка назва завдання
• `опис` - детальний опис що робить завдання  
• `промт` - текст інструкції для Claude
• `час` - час виконання (ГГ:ХХ, наприклад 02:30)
• `тип` - daily або weekly

**Приклад:**
```
/add_prompt "Перевірка безпеки" "Аналіз безпеки коду" "Проаналізуй код проекту на предмет уразливостей безпеки" 03:00 daily
```

**Для weekly завдань:**
```
/add_prompt "Backup" "Щотижневе резервування" "Створи резервну копію важливих файлів" 02:00 weekly sunday
```
"""
        await update.message.reply_text(usage_text, parse_mode=None)
    
    async def toggle_system_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle the scheduled prompts system on/off."""
        try:
            config = await self.prompts_manager.load_prompts()
            current_status = config.get("settings", {}).get("enabled", False)
            new_status = not current_status
            
            if "settings" not in config:
                config["settings"] = {}
            config["settings"]["enabled"] = new_status
            
            await self.prompts_manager.save_prompts(config)
            
            status_text = "увімкнена" if new_status else "вимкнена"
            icon = "✅" if new_status else "❌"
            
            await update.message.reply_text(
                f"{icon} **Система планових завдань {status_text}**\n"
                f"Використайте /prompts для перегляду завдань"
            )
            
        except Exception as e:
            logger.error(f"Error toggling system: {e}")
            await update.message.reply_text("❌ Помилка при зміні стану системи")
    
    async def prompts_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show execution history of scheduled prompts."""
        try:
            # Read last 10 executions from log
            execution_log = Path("./data/prompt_executions.jsonl")
            if not execution_log.exists():
                await update.message.reply_text("📊 **Історія виконання порожня**")
                return
            
            lines = []
            with open(execution_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Take last 10 entries
            recent_lines = lines[-10:] if len(lines) >= 10 else lines
            
            if not recent_lines:
                await update.message.reply_text("📊 **Історія виконання порожня**")
                return
            
            message = "📊 **Історія виконання** (останні 10)\n\n"
            
            for line in reversed(recent_lines):  # Show newest first
                try:
                    record = json.loads(line.strip())
                    timestamp_str = record.get("timestamp", "")
                    if timestamp_str:
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        local_dt = dt.astimezone(ZoneInfo("Europe/Kyiv"))
                        time_str = local_dt.strftime("%m-%d %H:%M")
                    else:
                        time_str = "???"
                    
                    prompt_id = record.get("prompt_id", "unknown")
                    status = record.get("status", "unknown")
                    
                    status_icons = {
                        "started": "🔄",
                        "completed": "✅", 
                        "failed": "❌",
                        "skipped": "⏭️"
                    }
                    icon = status_icons.get(status, "❓")
                    
                    message += f"{icon} {time_str} - {prompt_id} ({status})\n"
                    
                except json.JSONDecodeError:
                    continue
            
            await update.message.reply_text(message, parse_mode=None)
            
        except Exception as e:
            logger.error(f"Error showing history: {e}")
            await update.message.reply_text("❌ Помилка при завантаженні історії")
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "prompts_settings":
            await self._show_settings(query)
        elif query.data == "prompts_history":
            await self._show_history_inline(query)
        elif query.data.startswith("prompt_toggle_"):
            prompt_id = query.data.replace("prompt_toggle_", "")
            await self._toggle_prompt(query, prompt_id)
    
    async def _show_settings(self, query):
        """Show system settings inline."""
        try:
            config = await self.prompts_manager.load_prompts()
            settings = config.get("settings", {})
            
            enabled = settings.get("enabled", False)
            max_time = settings.get("max_execution_time_minutes", 30)
            retry_attempts = settings.get("retry_attempts", 3)
            
            message = (
                f"🔧 **Налаштування системи**\n\n"
                f"📊 Стан: {'✅ Увімкнена' if enabled else '❌ Вимкнена'}\n"
                f"⏱️ Максимальний час виконання: {max_time} хв\n"
                f"🔄 Спроб повтору: {retry_attempts}\n"
                f"💾 Файл конфігурації: scheduled_prompts.json\n"
                f"📝 Лог виконання: prompt_executions.jsonl"
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "🔄 Перемкнути систему", 
                    callback_data="toggle_prompts_system"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=None)
            
        except Exception as e:
            logger.error(f"Error showing settings: {e}")
            await query.edit_message_text("❌ Помилка при завантаженні налаштувань")
    
    async def _show_history_inline(self, query):
        """Show execution history inline."""
        # Same logic as prompts_history_command but for inline
        await self.prompts_history_command(query, None)


def register_scheduled_prompts_handlers(application, prompts_manager: ScheduledPromptsManager):
    """Register handlers for scheduled prompts management."""
    handler = ScheduledPromptsHandler(prompts_manager)
    
    from telegram.ext import CommandHandler
    
    # Add command handlers
    application.add_handler(CommandHandler("prompts", handler.list_prompts_command))
    application.add_handler(CommandHandler("add_prompt", handler.add_prompt_command))
    application.add_handler(CommandHandler("toggle_prompts", handler.toggle_system_command))
    application.add_handler(CommandHandler("prompts_history", handler.prompts_history_command))
    
    # Add callback handler
    application.add_handler(CallbackQueryHandler(
        handler.callback_handler, 
        pattern="^(prompts_settings|prompts_history|prompt_toggle_|toggle_prompts_system).*"
    ))
    
    logger.info("✅ Scheduled prompts handlers registered")