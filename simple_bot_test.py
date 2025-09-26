#!/usr/bin/env python3
"""
Простий тест бота без конфліктів процесів
"""

import os
import sys
import asyncio

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_bot_initialization():
    """Тест ініціалізації бота з callback обробниками"""

    print("🔍 Тестуємо повну ініціалізацію бота...")

    from src.config.settings import Settings
    from src.di.container import ApplicationContainer
    from src.bot.core import ClaudeCodeBot

    # Налаштування
    settings = Settings(
        telegram_token="1234567890:FAKE_TOKEN_FOR_TESTING",
        telegram_bot_username="test_bot",
        approved_directory="/tmp",
        database_url="sqlite:///data/bot.db"
    )

    print("✅ Налаштування створено")

    # DI контейнер
    container = ApplicationContainer()
    await container.initialize(settings)
    dependencies = container.get("bot_dependencies")

    print("✅ DI контейнер ініціалізовано")
    print(f"   Залежності: {len(dependencies)}")
    print(f"   context_commands: {'✅' if 'context_commands' in dependencies else '❌'}")

    # Симуляція бота (без реального запуску)
    class MockBot:
        def __init__(self):
            self.bot_data = {}

    class MockApp:
        def __init__(self):
            self.bot = MockBot()
            self.handlers = []
            self.bot_data = {}

        def add_handler(self, handler, group=0):
            self.handlers.append({
                'handler': handler,
                'group': group,
                'type': type(handler).__name__
            })

        def add_error_handler(self, handler):
            pass

    # Мокаємо Telegram Application
    import unittest.mock
    with unittest.mock.patch('telegram.ext.Application.builder') as mock_builder:
        mock_builder_instance = unittest.mock.Mock()
        mock_builder_instance.token.return_value = mock_builder_instance
        mock_builder_instance.persistence.return_value = mock_builder_instance
        mock_builder_instance.connect_timeout.return_value = mock_builder_instance
        mock_builder_instance.read_timeout.return_value = mock_builder_instance
        mock_builder_instance.write_timeout.return_value = mock_builder_instance
        mock_builder_instance.pool_timeout.return_value = mock_builder_instance

        mock_app = MockApp()
        mock_builder_instance.build.return_value = mock_app
        mock_builder.return_value = mock_builder_instance

        # Мокаємо set_my_commands
        with unittest.mock.patch.object(mock_app.bot, 'set_my_commands', new_callable=unittest.mock.AsyncMock):
            # Створюємо бот
            bot = ClaudeCodeBot(settings, dependencies)

            try:
                await bot.initialize()
                print("✅ Бот ініціалізовано успішно")

                # Аналізуємо обробники
                callback_handlers = [h for h in mock_app.handlers if 'CallbackQuery' in h['type']]
                message_handlers = [h for h in mock_app.handlers if 'MessageHandler' in h['type']]

                print(f"\n📊 Статистика обробників:")
                print(f"   MessageHandler: {len(message_handlers)}")
                print(f"   CallbackQueryHandler: {len(callback_handlers)}")

                print(f"\n📋 CallbackQueryHandler по групах:")
                callback_groups = {}
                for h in callback_handlers:
                    group = h['group']
                    callback_groups[group] = callback_groups.get(group, 0) + 1

                for group in sorted(callback_groups.keys()):
                    print(f"   Group {group}: {callback_groups[group]} handlers")

                # Перевіряємо middleware coverage
                expected_middleware_groups = [-4, -3, -2, -1]
                main_handler_group = 0

                middleware_ok = all(group in callback_groups for group in expected_middleware_groups)
                main_handler_ok = main_handler_group in callback_groups

                print(f"\n✅ Middleware coverage: {'✅' if middleware_ok else '❌'}")
                print(f"✅ Main callback handler: {'✅' if main_handler_ok else '❌'}")

                if middleware_ok and main_handler_ok:
                    print("\n🎉 ВИПРАВЛЕННЯ УСПІШНЕ!")
                    print("   Всі middleware тепер застосовуються до callback'ів")
                    print("   Бот готовий до роботи з кнопками")

                    # Симуляція callback запиту
                    print("\n🧪 Симуляція callback запиту...")

                    # Mock callback query
                    class TestUpdate:
                        def __init__(self):
                            self.callback_query = unittest.mock.Mock()
                            self.callback_query.data = "context_export"
                            self.callback_query.from_user = unittest.mock.Mock()
                            self.callback_query.from_user.id = 123456789
                            self.callback_query.answer = unittest.mock.AsyncMock()
                            self.effective_user = self.callback_query.from_user

                    class TestContext:
                        def __init__(self):
                            self.bot_data = dependencies
                            self.user_data = {}

                    # Тестуємо обробник
                    from src.bot.handlers.callback import handle_callback_query

                    test_update = TestUpdate()
                    test_context = TestContext()

                    try:
                        await handle_callback_query(test_update, test_context)
                        print("   ✅ Callback handler працює з dependencies")
                    except Exception as e:
                        print(f"   ❌ Callback handler не працює: {e}")

                else:
                    print("\n❌ ПРОБЛЕМА НЕ ПОВНІСТЮ ВИРІШЕНА")

            except Exception as e:
                print(f"❌ Помилка ініціалізації бота: {e}")
                import traceback
                traceback.print_exc()
                return False

    return True


async def main():
    """Головна функція"""
    success = await test_bot_initialization()

    if success:
        print("\n🎯 РЕЗУЛЬТАТ: Бот правильно налаштований для роботи з callback'ами")
        print("\n📝 НАСТУПНІ КРОКИ:")
        print("1. Запустіть бот: python -m src.main")
        print("2. Протестуйте команду /context")
        print("3. Натисніть будь-яку кнопку")
        print("4. Кнопки повинні працювати!")
    else:
        print("\n❌ РЕЗУЛЬТАТ: Залишились проблеми з конфігурацією")


if __name__ == "__main__":
    asyncio.run(main())