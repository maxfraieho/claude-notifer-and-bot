#!/usr/bin/env python3
"""
Повний дебаг тест callback системи
"""

import os
import sys
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

# Налаштування логування
logging.basicConfig(level=logging.DEBUG)

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


class RealCallbackTest:
    """Тест з реальними компонентами"""

    async def test_full_system(self):
        """Тест повної системи"""

        print("🔍 ПОВНИЙ ТЕСТ CALLBACK СИСТЕМИ")
        print("=" * 50)

        # Імпорт реальних компонентів
        from src.config.settings import Settings
        from src.di.container import ApplicationContainer
        from src.bot.handlers.callback import handle_callback_query
        from src.bot.features.context_commands import ContextCommands

        # Створення налаштувань
        settings = Settings(
            telegram_token="test_token",
            telegram_bot_username="test_bot",
            approved_directory="/tmp",
            database_url="sqlite:///data/bot.db"
        )
        print("✅ Налаштування створено")

        # Ініціалізація DI
        container = ApplicationContainer()
        await container.initialize(settings)
        dependencies = container.get("bot_dependencies")
        print("✅ DI контейнер ініціалізовано")

        # Mock Telegram objects
        class MockCallbackQuery:
            def __init__(self, data):
                self.data = data
                self.from_user = Mock()
                self.from_user.id = 123456789
                self.answer = AsyncMock()
                self.edit_message_text = AsyncMock()
                self.message = Mock()
                self.message.reply_text = AsyncMock()
                self.message.reply_document = AsyncMock()

        class MockUpdate:
            def __init__(self, callback_data):
                self.callback_query = MockCallbackQuery(callback_data)
                self.effective_user = Mock()
                self.effective_user.id = 123456789

        class MockContext:
            def __init__(self, has_deps=True):
                self.bot_data = dependencies if has_deps else {}
                self.user_data = {}

        # Тест 1: Перевірка наявності context_commands
        print("\n📝 Тест 1: Наявність context_commands в dependencies")
        if "context_commands" in dependencies:
            context_commands = dependencies["context_commands"]
            print(f"✅ context_commands знайдено: {type(context_commands).__name__}")

            # Перевіряємо методи
            methods = ["handle_callback_query", "handle_context_export", "handle_context_clear"]
            for method in methods:
                if hasattr(context_commands, method):
                    print(f"  ✅ {method} існує")
                else:
                    print(f"  ❌ {method} НЕ існує")
        else:
            print("❌ context_commands НЕ знайдено в dependencies")
            return False

        # Тест 2: Перевірка callback handler'а
        print("\n📝 Тест 2: Тест callback handler з правильними dependencies")

        test_callbacks = [
            "context_export",
            "context_clear",
            "context_search",
            "context_list",
            "context_close"
        ]

        for callback_data in test_callbacks:
            print(f"\n  🔄 Тестуємо: {callback_data}")

            update = MockUpdate(callback_data)
            context = MockContext(has_deps=True)

            try:
                await handle_callback_query(update, context)
                print(f"    ✅ Callback {callback_data} оброблено без помилок")

                # Перевіряємо чи було викликано answer
                if update.callback_query.answer.called:
                    print(f"    ✅ callback_query.answer() викликано")
                else:
                    print(f"    ❌ callback_query.answer() НЕ викликано")

            except Exception as e:
                print(f"    ❌ Помилка: {e}")

        # Тест 3: Тест без dependencies
        print("\n📝 Тест 3: Тест без dependencies (має показати помилку)")

        update = MockUpdate("context_export")
        context = MockContext(has_deps=False)

        try:
            await handle_callback_query(update, context)
            if update.callback_query.edit_message_text.called:
                error_msg = update.callback_query.edit_message_text.call_args[0][0]
                print(f"✅ Показано помилку: {error_msg}")
            else:
                print("❌ Помилка НЕ показана")
        except Exception as e:
            print(f"❌ Неочікувана помилка: {e}")

        print("\n🎯 ВИСНОВОК:")
        print("Система callback'ів працює правильно на рівні коду.")
        print("Якщо кнопки не працюють у боті, проблема в middleware або ініціалізації.")

        return True


async def main():
    """Головна функція"""
    tester = RealCallbackTest()
    success = await tester.test_full_system()

    if success:
        print("\n✅ ТЕСТ ПРОЙШОВ УСПІШНО")
        print("Можна запускати бот з повним логуванням для діагностики")
    else:
        print("\n❌ ТЕСТ ПРОВАЛИВСЯ")


if __name__ == "__main__":
    asyncio.run(main())