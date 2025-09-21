# Проблема з командою /actions - Промт для вирішення

## 🔍 Діагностика проблеми

**Поточна проблема:** Команда `/actions` не показує швидкі дії, а лише текст з локалізації без функціональних кнопок.

**Виявлені проблеми:**

1. **Неправильна реалізація хендлера `actions_handler`** (`src/bot/handlers/command.py:1677`):
   - Показує тільки текст `actions.title` без кнопок
   - Не викликає функціонал швидких дій

2. **Відсутнє з'єднання з QuickActionManager**:
   - Хендлер не використовує `context.bot_data.get("quick_actions")`
   - Не створює інлайн клавіатуру

3. **Розрив між функціоналом**:
   - Функціонал швидких дій реалізований у `_handle_quick_actions_action`
   - Але команда `/actions` не перенаправляє туди

## 🛠️ Рішення

### 1. Виправити хендлер команди `/actions`

**Файл:** `src/bot/handlers/command.py:1677-1689`

```python
async def actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available quick actions with functional buttons."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    try:
        # Use the same logic as the callback handler
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        # Get localized button texts
        keyboard = [
            [
                InlineKeyboardButton("📋 Показати файли", callback_data="quick_action:ls"),
                InlineKeyboardButton("🏠 Де я?", callback_data="quick_action:pwd"),
            ],
            [
                InlineKeyboardButton("💾 Git Status", callback_data="quick_action:git_status"),
                InlineKeyboardButton("🔍 Пошук TODO", callback_data="quick_action:grep"),
            ],
            [
                InlineKeyboardButton("📖 Читати файл", callback_data="file_edit:select_read"),
                InlineKeyboardButton("✏️ Редагувати файл", callback_data="file_edit:select_edit"),
            ],
            [
                InlineKeyboardButton("🔍 Знайти файли", callback_data="quick_action:find_files"),
                InlineKeyboardButton("🧪 Запустити тести", callback_data="quick:test"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        actions_text = await t(context, user_id, "quick_actions.title")
        await message.reply_text(
            actions_text,
            parse_mode=None,
            reply_markup=reply_markup
        )

    except Exception as e:
        await safe_user_error(update, context, "errors.actions_failed", e)
```

### 2. Альтернативне рішення - Перенаправлення

Або можна зробити простіше перенаправлення:

```python
async def actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available quick actions."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    try:
        # Create a fake query object to reuse existing logic
        from telegram import CallbackQuery

        # Send initial message with quick actions
        quick_actions_text = await t(context, user_id, "quick_actions.title")

        # Create dummy query-like object
        class DummyQuery:
            def __init__(self, msg):
                self.message = msg
                self.from_user = msg.from_user

            async def edit_message_text(self, text, **kwargs):
                await self.message.edit_text(text, **kwargs)

        # Send message first, then edit with buttons
        sent_message = await message.reply_text(quick_actions_text)

        # Create dummy query and call existing handler
        dummy_query = DummyQuery(sent_message)
        dummy_query.from_user = update.effective_user

        await _handle_quick_actions_action(dummy_query, context)

    except Exception as e:
        await safe_user_error(update, context, "errors.actions_failed", e)
```

### 3. Перевірити реєстрацію обробників

**Файл:** `src/bot/core.py`

Переконатися, що всі callback обробники зареєстровані:
- `handle_quick_action_execution_callback` для `quick_action:*`
- `handle_file_edit_callback` для `file_edit:*`
- `handle_quick_action_callback` для `quick:*`

## 🧪 Тестування

1. Запустити команду `/actions`
2. Перевірити, що з'являються функціональні кнопки
3. Натиснути кожну кнопку і перевірити виконання
4. Перевірити локалізацію українською

## 📝 Додаткові покращення

1. **Додати контекстні дії** - показувати різні кнопки залежно від поточної директорії
2. **Додати історію дій** - запам'ятовувати останні використані дії
3. **Покращити UX** - додати іконки та кращу навігацію

**Пріоритет:** ВИСОКИЙ - критична функціональність не працює