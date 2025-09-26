#!/usr/bin/env python3
"""
Debug Bot Data - перевіряємо що знаходиться в bot_data запущеного бота
"""
import asyncio
import sys
import os
from pathlib import Path

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def debug_bot_data():
    """Дебагуємо ініціалізацію bot_data"""

    print("🔍 Перевіряємо ініціалізацію bot_data...\n")

    # Перевіряємо DI container
    try:
        from src.di.container import get_di_container
        container = get_di_container()
        print("✅ DI container доступний")

        # Перевіряємо наявність context_commands
        if container.has("context_commands"):
            context_commands = container.get("context_commands")
            print(f"✅ context_commands знайдено в DI: {type(context_commands)}")
        else:
            print("❌ context_commands відсутні в DI container")

        # Перевіряємо bot_dependencies
        if container.has("bot_dependencies"):
            deps = container.get("bot_dependencies")
            print(f"✅ bot_dependencies знайдено: {list(deps.keys())}")

            if "context_commands" in deps:
                print("✅ context_commands є в bot_dependencies")
            else:
                print("❌ context_commands відсутні в bot_dependencies")
        else:
            print("❌ bot_dependencies відсутні в DI container")

    except Exception as e:
        print(f"❌ Помилка DI container: {e}")

    # Перевіряємо головний Bot
    try:
        from src.bot.core import ClaudeCodeBot
        from src.config.settings import Settings

        settings = Settings()
        print(f"✅ Settings завантажено")

        # Перевіряємо наявність файлу persistence
        persistence_file = Path("data/telegram_persistence.pickle")
        if persistence_file.exists():
            print(f"✅ Persistence файл існує: {persistence_file}")
        else:
            print(f"❌ Persistence файл відсутній: {persistence_file}")

    except Exception as e:
        print(f"❌ Помилка перевірки Bot: {e}")

    # Додатковий тест - чи може DI створити всі залежності
    try:
        from src.di.container import ApplicationContainer
        from src.config.settings import Settings

        settings = Settings()
        test_container = ApplicationContainer()
        await test_container.initialize(settings)

        # Перевіряємо всі компоненти
        components_to_check = [
            "storage", "auth_manager", "claude_integration",
            "context_commands", "unified_menu"
        ]

        print(f"\n📋 Перевірка компонентів DI:")
        for component in components_to_check:
            try:
                if test_container.has(component):
                    obj = test_container.get(component)
                    print(f"  ✅ {component}: {type(obj).__name__}")
                else:
                    print(f"  ❌ {component}: відсутній")
            except Exception as e:
                print(f"  ❌ {component}: помилка - {e}")

        await test_container.shutdown()

    except Exception as e:
        print(f"❌ Помилка тестування DI: {e}")

if __name__ == "__main__":
    asyncio.run(debug_bot_data())