#!/usr/bin/env python3
"""
Real-time Callback Test - перехоплюємо callback'и в реальному часі
"""
import asyncio
import json
import signal
import sys
import os
from datetime import datetime

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Глобальна змінна для зупинки
stop_monitoring = False

def signal_handler(signum, frame):
    global stop_monitoring
    print(f"\n🛑 Зупиняємо моніторинг...")
    stop_monitoring = True

async def monitor_bot_activity():
    """Моніторимо активність бота в реальному часі"""

    print("🔍 Запускаємо реальний моніторинг callback'ів...")
    print("📝 Інструкції:")
    print("   1. Надішліть /context в Telegram боту")
    print("   2. Натисніть одну з кнопок")
    print("   3. Дивіться результати тут")
    print("   4. Ctrl+C для зупинки\n")

    # Патчимо callback handler для логування
    try:
        from src.bot.handlers.callback import handle_callback_query
        original_handler = handle_callback_query

        # Створюємо обгортку для логування
        async def logged_callback_handler(update, context):
            print(f"🎯 CALLBACK ПЕРЕХОПЛЕНО: {datetime.now()}")
            print(f"   📞 Data: {update.callback_query.data}")
            print(f"   👤 User: {update.callback_query.from_user.id}")
            print(f"   🔧 bot_data keys: {list(context.bot_data.keys())}")

            # Перевіряємо чи є context_commands
            if 'context_commands' in context.bot_data:
                print(f"   ✅ context_commands доступні: {type(context.bot_data['context_commands'])}")
            else:
                print(f"   ❌ context_commands відсутні")
                print(f"   📋 Доступні ключі: {list(context.bot_data.keys())}")

            # Викликаємо оригінальний handler
            try:
                result = await original_handler(update, context)
                print(f"   ✅ Handler виконаний успішно")
                return result
            except Exception as e:
                print(f"   ❌ Handler помилка: {e}")
                raise

        # Замінюємо handler
        import src.bot.handlers.callback
        src.bot.handlers.callback.handle_callback_query = logged_callback_handler
        print("✅ Callback handler патчено для логування")

    except Exception as e:
        print(f"❌ Помилка патчування handler: {e}")
        return

    # Моніторимо
    print("👁️ Моніторинг активний. Натискайте кнопки в Telegram...\n")

    try:
        while not stop_monitoring:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Зупинка моніторингу...")

    print("✅ Моніторинг завершено")

if __name__ == "__main__":
    # Встановлюємо обробник сигналу
    signal.signal(signal.SIGINT, signal_handler)

    # Запускаємо моніторинг
    try:
        asyncio.run(monitor_bot_activity())
    except KeyboardInterrupt:
        print("\n👋 Вихід")