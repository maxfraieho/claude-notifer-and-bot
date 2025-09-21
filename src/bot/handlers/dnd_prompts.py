"""
DND Prompts Command Handlers - Обробники команд для управління DND промптами
"""

import structlog
from typing import cast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from pathlib import Path

from ...localization.util import t, get_user_id, get_effective_message
from ..features.dnd_prompt_manager import DNDPromptManager, DNDPrompt
from datetime import datetime

logger = structlog.get_logger()

async def dnd_prompts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /dnd_prompts command - manage DND prompts."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    try:
        # Отримати менеджер промптів
        settings = context.bot_data.get("settings")
        if not settings:
            await message.reply_text("❌ Налаштування системи недоступні")
            return
            
        data_dir = Path("./data")
        prompt_manager = DNDPromptManager(data_dir)
        await prompt_manager.load_prompts()
        
        prompts = await prompt_manager.list_prompts()
        
        if not prompts:
            # Створити зразкові промпти
            await prompt_manager.create_sample_prompts()
            prompts = await prompt_manager.list_prompts()
        
        # Створити меню управління
        keyboard = [
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.create_prompt"), callback_data="dnd:create"),
                InlineKeyboardButton(await t(context, user_id, "buttons.prompts_list"), callback_data="dnd:list")
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.settings"), callback_data="dnd:settings"),
                InlineKeyboardButton(await t(context, user_id, "buttons.statistics"), callback_data="dnd:stats")
            ],
            [
                InlineKeyboardButton("📤 Експорт", callback_data="dnd:export"),
                InlineKeyboardButton("📥 Імпорт", callback_data="dnd:import")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = f"""🌙 **DND Prompts Manager**

📊 **Статистика:**
• Всього промптів: {len(prompts)}
• Активних: {len([p for p in prompts if p.enabled])}
• Категорій: {len(set(p.category for p in prompts))}

🕒 **DND період:** 23:00 - 08:00
Промпти виконуються автоматично коли Claude CLI доступна та користувачі не активні.

**Оберіть дію:**"""
        
        await message.reply_text(message_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error("Error in dnd_prompts command", error=str(e), user_id=user_id)
        await message.reply_text("❌ Помилка завантаження DND промптів")

async def create_dnd_prompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create_dnd_prompt command - create new DND prompt."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    try:
        # Інструкції для створення промпту
        instructions = """📝 **Створення DND промпту**

Для створення нового промпту, надішліть повідомлення у форматі:

```
TITLE: Назва промпту
DESCRIPTION: Опис що робить промпт
CATEGORY: код-якость|безпека|документація|оптимізація
PRIORITY: 1-10
DURATION: хвилини
TAGS: тег1,тег2,тег3

--- PROMPT ---
Тут іде сам текст промпту у markdown форматі.

Можете використовувати команди Claude CLI:
- Read для читання файлів
- Write для створення файлів  
- Bash для виконання команд
- Grep для пошуку

Приклад промпту:
Проаналізуй код проекту та створи звіт з рекомендаціями...
```

**Приклад:**"""
        
        example = """```
TITLE: Щоденний код-ревю
DESCRIPTION: Автоматичний аналіз змін за день
CATEGORY: код-якость
PRIORITY: 8
DURATION: 30
TAGS: git,code-review,analysis

--- PROMPT ---
Виконай аналіз змін у git репозиторії за останній день:

1. `git log --oneline --since="1 day ago"`
2. `git diff HEAD~1..HEAD`
3. Прочитай змінені файли через Read
4. Створи звіт з рекомендаціями

Зосередься на:
- Якості коду
- Потенційних багах
- Покращеннях архітектури
```"""

        keyboard = [
            [InlineKeyboardButton(await t(context, user_id, "buttons.prompt_templates"), callback_data="dnd:templates")],
            [InlineKeyboardButton(await t(context, user_id, "buttons.back_to_menu"), callback_data="dnd:menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(f"{instructions}\n\n{example}", reply_markup=reply_markup)
        
        # Зберегти стан для наступного повідомлення
        context.user_data['creating_dnd_prompt'] = True
        
    except Exception as e:
        logger.error("Error in create_dnd_prompt command", error=str(e), user_id=user_id)
        await message.reply_text("❌ Помилка створення промпту")

async def handle_dnd_prompt_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle DND prompt creation from user message."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message or not message.text:
        return False
        
    # Перевірити чи користувач створює промпт
    if not context.user_data.get('creating_dnd_prompt'):
        return False
    
    try:
        text = message.text.strip()
        
        # Парсинг промпту
        lines = text.split('\n')
        metadata = {}
        prompt_content = ""
        
        parsing_prompt = False
        
        for line in lines:
            line = line.strip()
            
            if line == "--- PROMPT ---":
                parsing_prompt = True
                continue
                
            if parsing_prompt:
                prompt_content += line + "\n"
            elif ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'title':
                    metadata['title'] = value
                elif key == 'description':
                    metadata['description'] = value
                elif key == 'category':
                    metadata['category'] = value
                elif key == 'priority':
                    metadata['priority'] = int(value)
                elif key == 'duration':
                    metadata['estimated_duration'] = int(value)
                elif key == 'tags':
                    metadata['tags'] = [t.strip() for t in value.split(',')]
        
        # Валідація
        if not metadata.get('title'):
            await message.reply_text("❌ Не вказано TITLE промпту")
            return True
            
        if not prompt_content.strip():
            await message.reply_text("❌ Не вказано текст промпту після --- PROMPT ---")
            return True
        
        # Створити промпт
        prompt_id = metadata['title'].lower().replace(' ', '_').replace('-', '_')
        prompt_id = ''.join(c for c in prompt_id if c.isalnum() or c == '_')
        
        dnd_prompt = DNDPrompt(
            id=prompt_id,
            title=metadata.get('title', 'Новий промпт'),
            description=metadata.get('description', ''),
            prompt_content=prompt_content.strip(),
            tags=metadata.get('tags', []),
            priority=metadata.get('priority', 5),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            category=metadata.get('category', 'general'),
            estimated_duration=metadata.get('estimated_duration', 30)
        )
        
        # Зберегти промпт
        data_dir = Path("./data")
        prompt_manager = DNDPromptManager(data_dir)
        
        success = await prompt_manager.add_prompt(dnd_prompt)
        
        if success:
            await message.reply_text(f"""✅ **Промпт створено успішно!**

**ID:** `{prompt_id}`
**Назва:** {dnd_prompt.title}
**Категорія:** {dnd_prompt.category}
**Пріоритет:** {dnd_prompt.priority}/10
**Тривалість:** {dnd_prompt.estimated_duration} хв

Промпт збережено у файл `data/dnd_prompts/{prompt_id}.md`

Він буде автоматично виконуватися під час DND періоду.""")
        else:
            await message.reply_text("❌ Помилка збереження промпту. Можливо промпт з таким ID вже існує.")
        
        # Очистити стан
        context.user_data['creating_dnd_prompt'] = False
        return True
        
    except Exception as e:
        logger.error("Error handling DND prompt creation", error=str(e), user_id=user_id)
        await message.reply_text("❌ Помилка обробки промпту. Перевірте формат.")
        context.user_data['creating_dnd_prompt'] = False
        return True

async def list_dnd_prompts(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str = None) -> None:
    """Show list of DND prompts."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    try:
        data_dir = Path("./data")
        prompt_manager = DNDPromptManager(data_dir)
        await prompt_manager.load_prompts()
        
        prompts = await prompt_manager.list_prompts(category=category)
        
        if not prompts:
            await message.reply_text(f"📋 Промптів не знайдено{f' в категорії {category}' if category else ''}")
            return
        
        # Групувати за категоріями
        by_category = {}
        for prompt in prompts:
            if prompt.category not in by_category:
                by_category[prompt.category] = []
            by_category[prompt.category].append(prompt)
        
        message_text = f"📋 **DND Промпти** ({len(prompts)})\n\n"
        
        for cat, cat_prompts in by_category.items():
            message_text += f"**📂 {cat.upper()}** ({len(cat_prompts)})\n"
            
            for prompt in cat_prompts[:5]:  # Показати перші 5
                status = "✅" if prompt.enabled else "❌"
                message_text += f"{status} **{prompt.title}** (P:{prompt.priority}, {prompt.estimated_duration}м)\n"
                message_text += f"   _{prompt.description[:60]}..._\n"
            
            if len(cat_prompts) > 5:
                message_text += f"   ... та ще {len(cat_prompts) - 5} промптів\n"
            
            message_text += "\n"
        
        keyboard = [
            [InlineKeyboardButton(await t(context, user_id, "buttons.create_new"), callback_data="dnd:create")],
            [InlineKeyboardButton(await t(context, user_id, "buttons.back_simple"), callback_data="dnd:menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(message_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error("Error listing DND prompts", error=str(e), user_id=user_id)
        await message.reply_text("❌ Помилка завантаження списку промптів")