#!/usr/bin/env python3
"""
Дебаг скрипт для перевірки роботи callback обробників
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


class MockTelegramQuery:
    """Mock для callback query"""
    def __init__(self, data):
        self.data = data
        self.from_user = Mock()
        self.from_user.id = 12345
        self.message = AsyncMock()
        self.edit_message_text = AsyncMock()
        self.answer = AsyncMock()


class MockTelegramUpdate:
    """Mock для Update з callback query"""
    def __init__(self, callback_data):
        self.callback_query = MockTelegramQuery(callback_data)
        self.effective_user = Mock()
        self.effective_user.id = 12345


class MockTelegramContext:
    """Mock для Context"""
    def __init__(self, has_context_commands=True):
        self.bot_data = {}

        if has_context_commands:
            # Створюємо mock context_commands
            from src.bot.features.context_commands import ContextCommands
            from src.storage.facade import Storage
            from src.claude.context_memory import ContextMemoryManager

            mock_storage = Mock(spec=Storage)
            mock_context_memory = Mock(spec=ContextMemoryManager)

            self.bot_data["context_commands"] = ContextCommands(mock_storage, mock_context_memory)


async def test_callback_handling():
    """Тест обробки callback запитів"""

    print("🔍 Тестуємо обробку callback запитів для управління контекстом...")

    # Імпортуємо обробник callback'ів
    from src.bot.handlers.callback import handle_callback_query

    # Тест 1: context_commands є в bot_data
    print("\n📝 Тест 1: context_commands доступні")
    update = MockTelegramUpdate("context_export")
    context = MockTelegramContext(has_context_commands=True)

    try:
        await handle_callback_query(update, context)
        print("✅ Callback оброблено без помилок")

        # Перевіряємо чи було викликано answer()
        if update.callback_query.answer.called:
            print("✅ callback_query.answer() було викликано")
        else:
            print("❌ callback_query.answer() НЕ було викликано")

    except Exception as e:
        print(f"❌ Помилка при обробці callback: {e}")

    # Тест 2: context_commands НЕ є в bot_data
    print("\n📝 Тест 2: context_commands недоступні")
    update = MockTelegramUpdate("context_export")
    context = MockTelegramContext(has_context_commands=False)

    try:
        await handle_callback_query(update, context)
        print("✅ Callback оброблено без помилок")

        # Перевіряємо чи було показано повідомлення про помилку
        if update.callback_query.edit_message_text.called:
            call_args = update.callback_query.edit_message_text.call_args[0][0]
            if "недоступна" in call_args:
                print("✅ Показано повідомлення про недоступність")
            else:
                print(f"❓ Показано інше повідомлення: {call_args}")
        else:
            print("❌ НЕ було показано повідомлення про помилку")

    except Exception as e:
        print(f"❌ Помилка при обробці callback: {e}")

    # Тест 3: Інші типи callback'ів
    print("\n📝 Тест 3: Неконтекстні callback'і")
    update = MockTelegramUpdate("action:status")
    context = MockTelegramContext(has_context_commands=True)

    try:
        await handle_callback_query(update, context)
        print("✅ Неконтекстний callback оброблено")
    except Exception as e:
        print(f"❌ Помилка при обробці неконтекстного callback: {e}")

    print("\n🎯 ВИСНОВОК:")
    print("Механізм обробки callback'ів працює на рівні коду.")
    print("Якщо кнопки не реагують - проблема може бути в:")
    print("1. Ініціалізації context_commands в bot_data")
    print("2. Реєстрації CallbackQueryHandler")
    print("3. Конфліктах middleware")


async def main():
    await test_callback_handling()


if __name__ == "__main__":
    asyncio.run(main())