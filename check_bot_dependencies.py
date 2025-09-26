#!/usr/bin/env python3
"""
Перевірка ініціалізації залежностей бота
"""

import os
import sys
import asyncio

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def check_dependencies():
    """Перевіряє створення та ініціалізацію залежностей"""

    print("🔍 Перевіряємо ініціалізацію залежностей бота...")

    # Імпортуємо потрібні модулі
    from src.config.settings import Settings
    from src.di.container import ApplicationContainer

    # Створюємо тестові налаштування
    settings = Settings(
        telegram_token="test_token",
        telegram_bot_username="test_bot",
        approved_directory="/tmp",
        database_url="sqlite:///tmp/test.db"
    )

    print("\n📦 Створюємо DI контейнер...")
    container = ApplicationContainer()

    try:
        await container.initialize(settings)
        print("✅ DI контейнер ініціалізовано")

        # Перевіряємо наявність context_commands
        if container.has("context_commands"):
            context_commands = container.get("context_commands")
            print(f"✅ context_commands знайдено: {type(context_commands).__name__}")

            # Перевіряємо метод handle_callback_query
            if hasattr(context_commands, 'handle_callback_query'):
                print("✅ Метод handle_callback_query існує")
            else:
                print("❌ Метод handle_callback_query НЕ існує")

        else:
            print("❌ context_commands НЕ знайдено в контейнері")

        # Перевіряємо залежності бота
        if container.has("bot_dependencies"):
            bot_deps = container.get("bot_dependencies")
            print(f"\n📋 Залежності бота:")

            for key, value in bot_deps.items():
                print(f"  - {key}: {type(value).__name__}")

            if "context_commands" in bot_deps:
                print("✅ context_commands включено в залежності бота")
            else:
                print("❌ context_commands НЕ включено в залежності бота")

        else:
            print("❌ bot_dependencies НЕ знайдено")

        # Перевіряємо створення бота
        if container.has("bot"):
            bot = container.get("bot")
            print(f"\n🤖 Бот створено: {type(bot).__name__}")
        else:
            print("❌ Бот НЕ створено")

    except Exception as e:
        print(f"❌ Помилка ініціалізації: {e}")
        import traceback
        traceback.print_exc()

    print("\n🎯 РЕКОМЕНДАЦІЇ:")
    print("1. Перевірте що context_commands включено в bot_dependencies")
    print("2. Перевірте _inject_deps метод в ClaudeCodeBot")
    print("3. Перевірте реєстрацію CallbackQueryHandler")


async def main():
    await check_dependencies()


if __name__ == "__main__":
    asyncio.run(main())