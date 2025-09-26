#!/usr/bin/env python3
"""
Тест виправлення проблеми з callback'ами
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import Settings
from src.di.container import ApplicationContainer


class MockTelegramApp:
    """Mock для Telegram Application"""
    def __init__(self):
        self.handlers = []
        self.bot_data = {}

    def add_handler(self, handler, group=0):
        """Додає обробник"""
        self.handlers.append({
            'handler': handler,
            'group': group
        })

    def add_error_handler(self, handler):
        """Додає обробник помилок"""
        pass


async def test_callback_middleware():
    """Тестує чи застосовується middleware до callback'ів"""

    print("🔧 Тестування виправлення middleware для callback'ів...")

    # Створюємо налаштування
    settings = Settings(
        telegram_token="test_token",
        telegram_bot_username="test_bot",
        approved_directory="/tmp",
        database_url="sqlite:///tmp/test.db"
    )

    # Створюємо DI контейнер
    container = ApplicationContainer()
    await container.initialize(settings)

    # Отримуємо залежності
    dependencies = container.get("bot_dependencies")

    print(f"✅ Залежності створено: {len(dependencies)} компонентів")
    print(f"   context_commands: {'✅' if 'context_commands' in dependencies else '❌'}")

    # Створюємо mock для Telegram app
    mock_app = MockTelegramApp()

    # Імітуємо створення бота
    from src.bot.core import ClaudeCodeBot

    # Патчимо Application.builder для використання нашого mock
    with patch('telegram.ext.Application.builder') as mock_builder:
        mock_builder_instance = Mock()
        mock_builder_instance.token.return_value = mock_builder_instance
        mock_builder_instance.persistence.return_value = mock_builder_instance
        mock_builder_instance.connect_timeout.return_value = mock_builder_instance
        mock_builder_instance.read_timeout.return_value = mock_builder_instance
        mock_builder_instance.write_timeout.return_value = mock_builder_instance
        mock_builder_instance.pool_timeout.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_app
        mock_builder.return_value = mock_builder_instance

        # Створюємо бота
        bot = ClaudeCodeBot(settings, dependencies)

        try:
            await bot.initialize()
            print("✅ Бот ініціалізовано без помилок")

            # Аналізуємо зареєстровані обробники
            callback_handlers = [h for h in mock_app.handlers
                               if 'CallbackQueryHandler' in str(type(h['handler']))]

            print(f"\n📊 Зареєстровано CallbackQueryHandler'ів: {len(callback_handlers)}")

            # Групуємо по group
            groups = {}
            for h in callback_handlers:
                group = h['group']
                if group not in groups:
                    groups[group] = 0
                groups[group] += 1

            print("📋 Розподіл по групам:")
            for group in sorted(groups.keys()):
                print(f"   Group {group}: {groups[group]} обробників")

            # Перевіряємо middleware groups
            middleware_groups = [-4, -3, -2, -1]
            main_handler_group = 0

            middleware_coverage = all(group in groups for group in middleware_groups)
            main_handler_exists = main_handler_group in groups

            print(f"\n✅ Middleware coverage: {'✅' if middleware_coverage else '❌'}")
            print(f"✅ Main callback handler: {'✅' if main_handler_exists else '❌'}")

            if middleware_coverage and main_handler_exists:
                print("\n🎉 ВИПРАВЛЕННЯ УСПІШНЕ!")
                print("   Всі middleware тепер застосовуються до callback запитів")
                print("   context.bot_data буде правильно заповнюватися")
            else:
                print("\n❌ ПРОБЛЕМА НЕ ВИРІШЕНА")
                print("   Middleware не повністю застосовується до callback'ів")

        except Exception as e:
            print(f"❌ Помилка ініціалізації бота: {e}")
            import traceback
            traceback.print_exc()


async def main():
    await test_callback_middleware()


if __name__ == "__main__":
    asyncio.run(main())