#!/usr/bin/env python3
"""
Real Context Callbacks Test - перевіряє справжню обробку callback'ів
"""
import asyncio
import sys
import os

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from unittest.mock import Mock, AsyncMock
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Update, User, Chat

async def test_real_callback_handling():
    """Тестує справжню обробку callback'ів через імпорт реального коду"""

    print("🔍 Тестуємо справжню обробку context callback'ів...\n")

    # Імпортуємо реальний обробник
    try:
        from src.bot.handlers.callback import handle_callback_query
        print("✅ Реальний handle_callback_query імпортовано")
    except ImportError as e:
        print(f"❌ Помилка імпорту handle_callback_query: {e}")
        return False

    # Імпортуємо context_commands
    try:
        from src.bot.features.context_commands import ContextCommands
        print("✅ ContextCommands імпортовано")
    except ImportError as e:
        print(f"❌ Помилка імпорту ContextCommands: {e}")
        return False

    # Створюємо mock об'єкти
    mock_user = Mock(spec=User)
    mock_user.id = 6412868393
    mock_user.first_name = "Test"
    mock_user.username = "testuser"

    mock_chat = Mock(spec=Chat)
    mock_chat.id = 6412868393

    # Створюємо реальний CallbackQuery
    mock_callback_query = Mock(spec=CallbackQuery)
    mock_callback_query.id = "test_callback"
    mock_callback_query.data = "context_export"  # Тестуємо експорт
    mock_callback_query.from_user = mock_user
    mock_callback_query.message = Mock()
    mock_callback_query.message.chat = mock_chat
    mock_callback_query.answer = AsyncMock()
    mock_callback_query.edit_message_text = AsyncMock()

    # Створюємо Update з CallbackQuery
    mock_update = Mock(spec=Update)
    mock_update.callback_query = mock_callback_query
    mock_update.effective_user = mock_user
    mock_update.effective_chat = mock_chat
    mock_update.message = None  # У callback update немає message

    # Створюємо context з bot_data
    mock_context = Mock()
    mock_context.bot_data = {}
    mock_context.user_data = {}

    # Тест 1: Перевіряємо обробку без context_commands
    print("\n📝 Тест 1: callback без context_commands в bot_data")
    try:
        await handle_callback_query(mock_update, mock_context)
        print("✅ Callback оброблено без помилок")

        # Перевіряємо чи було викликано answer()
        assert mock_callback_query.answer.called, "callback_query.answer() не було викликано"
        print("✅ callback_query.answer() було викликано")

        # Перевіряємо повідомлення про недоступність
        if mock_callback_query.edit_message_text.called:
            call_args = mock_callback_query.edit_message_text.call_args
            message_text = call_args[0][0]
            if "недоступна" in message_text.lower():
                print("✅ Показано повідомлення про недоступність context_commands")
            else:
                print(f"⚠️ Неочікуване повідомлення: {message_text}")

    except Exception as e:
        print(f"❌ Помилка в тесті 1: {e}")
        return False

    # Тест 2: Додаємо context_commands до bot_data
    print("\n📝 Тест 2: callback з context_commands в bot_data")

    # Створюємо mock для storage та context_memory
    mock_storage = Mock()
    mock_storage.context = Mock()
    mock_storage.context.get_context_stats = AsyncMock(return_value={
        'total_entries': 0,
        'sessions_count': 0,
        'first_entry': None,
        'last_entry': None,
        'high_importance': 0,
        'medium_importance': 0,
        'low_importance': 0
    })

    mock_context_memory = Mock()
    mock_context_memory.get_user_context = AsyncMock()
    mock_context_memory.get_user_context.return_value = Mock()
    mock_context_memory.get_user_context.return_value.last_updated = Mock()
    mock_context_memory.get_user_context.return_value.last_updated.strftime = Mock(return_value="2025-09-25 17:25")

    mock_context_memory.export_context = AsyncMock(return_value={
        "entries": [{"timestamp": "2025-09-25T17:25:00", "content": "test"}]
    })

    # Створюємо реальний ContextCommands
    context_commands = ContextCommands(mock_storage, mock_context_memory)

    # Додаємо до bot_data
    mock_context.bot_data["context_commands"] = context_commands
    mock_context.bot_data["approved_directory"] = "/tmp"

    # Скидаємо mock'и
    mock_callback_query.answer.reset_mock()
    mock_callback_query.edit_message_text.reset_mock()

    try:
        await handle_callback_query(mock_update, mock_context)
        print("✅ Callback з context_commands оброблено")

        # Перевіряємо чи було викликано answer()
        assert mock_callback_query.answer.called, "callback_query.answer() не було викликано"
        print("✅ callback_query.answer() було викликано")

        # Перевіряємо чи context_commands обробив запит
        if mock_update.message and hasattr(mock_update.message, 'reply_document'):
            print("✅ context_export спрацював (спроба надіслати документ)")
        else:
            print("ℹ️ context_export обробка завершена")

    except Exception as e:
        print(f"❌ Помилка в тесті 2: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n🎯 ВИСНОВОК:")
    print("Механізм обробки callback'ів працює на рівні коду.")
    print("Якщо кнопки не реагують в реальному боті - проблема в:")
    print("1. Ініціалізації context_commands в bot_data")
    print("2. Реєстрації CallbackQueryHandler")
    print("3. Конфліктах middleware")

    return True

if __name__ == "__main__":
    asyncio.run(test_real_callback_handling())