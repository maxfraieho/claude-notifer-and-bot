#!/usr/bin/env python3
"""
Тест для перевірки роботи кнопок управління контекстом Claude CLI
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.bot.features.context_commands import ContextCommands
from src.claude.context_memory import ContextMemoryManager
from src.storage.facade import Storage
from src.config.settings import Settings


class MockTelegramUpdate:
    """Mock об'єкт для Telegram Update"""

    def __init__(self, user_id=12345):
        self.effective_user = Mock()
        self.effective_user.id = user_id

        self.message = AsyncMock()
        self.message.reply_text = AsyncMock()
        self.message.reply_document = AsyncMock()

        self.callback_query = AsyncMock()
        self.callback_query.data = ""
        self.callback_query.edit_message_text = AsyncMock()
        self.callback_query.answer = AsyncMock()
        self.callback_query.message = self.message


class MockTelegramContext:
    """Mock об'єкт для Telegram Context"""

    def __init__(self):
        self.bot_data = {
            "approved_directory": "/tmp/test_project"
        }
        self.user_data = {}


async def test_context_buttons():
    """Тест функцій кнопок управління контекстом"""

    print("🧪 Початок тестування кнопок управління контекстом...")

    # Створюємо mock об'єкти
    mock_storage = Mock(spec=Storage)
    mock_storage.context = Mock()

    # Налаштовуємо mock для статистики
    mock_storage.context.get_context_stats = AsyncMock(return_value={
        'total_entries': 15,
        'sessions_count': 3,
        'first_entry': '2024-09-20T10:00:00',
        'last_entry': '2024-09-25T15:30:00',
        'high_importance': 5,
        'medium_importance': 8,
        'low_importance': 2
    })

    # Налаштовуємо mock для пошуку
    mock_storage.context.search_context_entries = AsyncMock(return_value=[])
    mock_storage.context.get_recent_context_entries = AsyncMock(return_value=[])

    mock_context_memory = Mock(spec=ContextMemoryManager)
    mock_context_memory.get_user_context = AsyncMock()
    mock_context_memory.get_user_context.return_value = Mock()
    mock_context_memory.get_user_context.return_value.last_updated = datetime.now()

    mock_context_memory.export_context = AsyncMock(return_value={
        "entries": [
            {"timestamp": "2024-09-25T15:30:00", "content": "test message", "type": "user"},
        ]
    })
    mock_context_memory.clear_context = AsyncMock(return_value=True)

    # Створюємо ContextCommands
    context_commands = ContextCommands(mock_storage, mock_context_memory)

    # Створюємо mock об'єкти для Telegram
    update = MockTelegramUpdate()
    context = MockTelegramContext()

    print("✅ Mock об'єкти створено")

    # Тест 1: Статус контексту
    print("\n📊 Тест 1: Перевірка статусу контексту...")
    try:
        await context_commands.handle_context_status(update, context)

        # Перевіряємо, що було викликано reply_text
        assert update.message.reply_text.called, "reply_text не було викликано"

        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]  # Перший аргумент

        # Перевіряємо наявність ключових слів в повідомленні
        assert "Статус контекстної пам'яті" in message_text, "Заголовок не знайдено"
        assert "15" in message_text, "Кількість записів не знайдена"
        assert "📤 Експорт" in str(call_args), "Кнопка 'Експорт' не знайдена"
        assert "🔍 Пошук" in str(call_args), "Кнопка 'Пошук' не знайдена"
        assert "🗑️ Очистити" in str(call_args), "Кнопка 'Очистити' не знайдена"

        print("✅ Статус контексту працює коректно")

    except Exception as e:
        print(f"❌ Помилка в тесті статусу: {e}")
        return False

    # Тест 2: Експорт контексту
    print("\n📤 Тест 2: Перевірка експорту контексту...")
    try:
        await context_commands.handle_context_export(update, context)

        # Перевіряємо, що було викликано reply_document
        assert update.message.reply_document.called, "reply_document не було викликано"

        print("✅ Експорт контексту працює коректно")

    except Exception as e:
        print(f"❌ Помилка в тесті експорту: {e}")
        return False

    # Тест 3: Очищення контексту (запит підтвердження)
    print("\n🗑️ Тест 3: Перевірка запиту очищення контексту...")
    try:
        await context_commands.handle_context_clear(update, context)

        # Перевіряємо, що було викликано reply_text з підтвердженням
        assert update.message.reply_text.called, "reply_text не було викликано"

        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]

        assert "Підтвердження очищення" in message_text, "Запит підтвердження не знайдено"
        assert "✅ Так, очистити" in str(call_args), "Кнопка підтвердження не знайдена"

        print("✅ Запит очищення працює коректно")

    except Exception as e:
        print(f"❌ Помилка в тесті очищення: {e}")
        return False

    # Тест 4: Підтвердження очищення
    print("\n✅ Тест 4: Перевірка підтвердження очищення...")
    try:
        await context_commands.handle_context_clear_confirm(update, context)

        # Перевіряємо, що було викликано edit_message_text
        assert update.callback_query.edit_message_text.called, "edit_message_text не було викликано"

        call_args = update.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]

        assert "успішно очищено" in message_text, "Повідомлення про успіх не знайдено"

        print("✅ Підтвердження очищення працює коректно")

    except Exception as e:
        print(f"❌ Помилка в тесті підтвердження очищення: {e}")
        return False

    # Тест 5: Пошук в контексті
    print("\n🔍 Тест 5: Перевірка пошуку в контексті...")
    try:
        await context_commands.handle_context_search(update, context)

        # Перевіряємо, що було викликано reply_text з інструкцією
        assert update.message.reply_text.called, "reply_text не було викликано"

        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]

        assert "Пошук в контексті" in message_text, "Заголовок пошуку не знайдено"
        assert "awaiting_context_search" in context.user_data, "Стан пошуку не встановлено"

        print("✅ Пошук в контексті працює коректно")

    except Exception as e:
        print(f"❌ Помилка в тесті пошуку: {e}")
        return False

    # Тест 6: Список контексту
    print("\n📋 Тест 6: Перевірка списку контексту...")
    try:
        await context_commands.handle_context_list(update, context)

        # Перевіряємо, що було викликано reply_text
        assert update.message.reply_text.called, "reply_text не було викликано"

        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]

        assert "Список контексту" in message_text, "Заголовок списку не знайдено"

        print("✅ Список контексту працює коректно")

    except Exception as e:
        print(f"❌ Помилка в тесті списку: {e}")
        return False

    # Тест 7: Callback handlers
    print("\n🔄 Тест 7: Перевірка обробників callback...")
    callback_tests = [
        ("context_export", "handle_context_export"),
        ("context_clear", "handle_context_clear"),
        ("context_search", "handle_context_search"),
        ("context_list", "handle_context_list"),
        ("context_close", "закрити"),
    ]

    for callback_data, expected_behavior in callback_tests:
        try:
            update.callback_query.data = callback_data
            await context_commands.handle_callback_query(update, context)
            print(f"  ✅ Callback '{callback_data}' обробляється коректно")
        except Exception as e:
            print(f"  ❌ Помилка в callback '{callback_data}': {e}")
            return False

    print("\n🎉 Всі тести пройдено успішно!")
    print("\n📋 Результати тестування:")
    print("  ✅ Статус контексту - працює")
    print("  ✅ Експорт контексту - працює")
    print("  ✅ Очищення контексту - працює")
    print("  ✅ Пошук в контексті - працює")
    print("  ✅ Список контексту - працює")
    print("  ✅ Callback обробники - працюють")

    return True


async def main():
    """Головна функція тестування"""

    print("🤖 Тест кнопок управління контекстом Claude CLI")
    print("=" * 50)

    success = await test_context_buttons()

    if success:
        print("\n🎯 ВИСНОВОК: Всі кнопки управління контекстом працюють коректно!")
        print("📝 Функціонал готовий до використання.")
    else:
        print("\n❌ ВИСНОВОК: Виявлено проблеми з кнопками управління контекстом!")
        print("🔧 Потрібні додаткові виправлення.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())