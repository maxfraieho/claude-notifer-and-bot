#!/usr/bin/env python3

"""
Тест локалізації для перевірки роботи системи після перезапуску
"""

import asyncio
import sys
import os

# Додаємо шлях до проекту
sys.path.insert(0, '/home/vokov/projects/claude-notifer-and-bot/src')

from localization.wrapper import t, get_locale_for_user
from localization.i18n import i18n

class MockContext:
    def __init__(self):
        self.bot_data = {}
        self.user_data = {"_telegram_language_code": "uk"}

async def test_restart_localization():
    print("🧪 Тестуємо локалізацію після перезапуску...")

    context = MockContext()
    user_id = 6412868393

    try:
        # Тест ключів, які використовуються в коді перезапуску
        welcome_text = await t(context, user_id, "commands.start.welcome", name="Володимир")
        restarted_text = await t(context, user_id, "commands.restart.completed")

        new_session_btn = await t(context, user_id, "buttons.new_session")
        continue_btn = await t(context, user_id, "buttons.continue_session")
        status_btn = await t(context, user_id, "buttons.check_status")
        context_btn = await t(context, user_id, "buttons.context")
        settings_btn = await t(context, user_id, "buttons.settings")
        help_btn = await t(context, user_id, "buttons.get_help")
        lang_btn = await t(context, user_id, "buttons.language_settings")

        print("\n✅ Результати локалізації:")
        print(f"Привітання: {welcome_text}")
        print(f"Перезапуск: {restarted_text}")
        print("\n📱 Кнопки:")
        print(f"• Нова сесія: {new_session_btn}")
        print(f"• Продовжити: {continue_btn}")
        print(f"• Статус: {status_btn}")
        print(f"• Контекст: {context_btn}")
        print(f"• Налаштування: {settings_btn}")
        print(f"• Допомога: {help_btn}")
        print(f"• Мова: {lang_btn}")

        # Перевіряємо чи не повертаються ключі замість тексту
        issues = []
        if "commands.start.welcome" in welcome_text:
            issues.append("❌ welcome_text містить ключ")
        if "commands.restart.completed" in restarted_text:
            issues.append("❌ restarted_text містить ключ")
        if "buttons." in new_session_btn:
            issues.append("❌ buttons містять ключі")

        if issues:
            print(f"\n🚨 Знайдені проблеми:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print(f"\n🎉 Всі тексти локалізовані правильно!")

        return len(issues) == 0

    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_restart_localization())
    sys.exit(0 if success else 1)