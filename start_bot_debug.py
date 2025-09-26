#!/usr/bin/env python3
"""
Запуск бота з спеціальним debug режимом для callback'ів
"""

import os
import sys
import asyncio
import logging
import structlog

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Налаштування детального логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('callback_debug.log', mode='w')
    ]
)

# Налаштування structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


async def main():
    """Запуск бота з debug логуванням"""

    print("🚀 Запускаю бот з debug логуванням для callback'ів...")
    print("📁 Логи зберігаються в callback_debug.log")
    print("🔍 Слідкуйте за callback'ами в режимі реального часу")
    print("=" * 60)

    from src.main import main as bot_main

    # Патч для додаткового логування callback'ів
    original_handle_callback_query = None

    try:
        from src.bot.handlers import callback
        original_handle_callback_query = callback.handle_callback_query

        async def debug_handle_callback_query(update, context):
            """Обгортка для детального логування"""
            logger = structlog.get_logger("CALLBACK_DEBUG")

            callback_data = update.callback_query.data if update.callback_query else "No data"
            user_id = update.effective_user.id if update.effective_user else "Unknown"

            logger.info("🔔 CALLBACK RECEIVED",
                       callback_data=callback_data,
                       user_id=user_id)

            # Перевіряємо наявність залежностей
            has_context_commands = "context_commands" in context.bot_data
            logger.info("🧩 DEPENDENCIES CHECK",
                       has_context_commands=has_context_commands,
                       available_deps=list(context.bot_data.keys()))

            try:
                result = await original_handle_callback_query(update, context)
                logger.info("✅ CALLBACK PROCESSED SUCCESSFULLY", callback_data=callback_data)
                return result
            except Exception as e:
                logger.error("❌ CALLBACK PROCESSING FAILED",
                           callback_data=callback_data,
                           error=str(e),
                           exc_info=True)
                raise

        # Замінюємо обробник
        callback.handle_callback_query = debug_handle_callback_query
        print("✅ Увімкнено детальне логування callback'ів")

    except Exception as e:
        print(f"⚠️ Не вдалося увімкнути debug callback: {e}")

    # Запускаємо бот
    try:
        await bot_main()
    except KeyboardInterrupt:
        print("\n🛑 Зупинка бота...")
    except Exception as e:
        print(f"❌ Помилка запуску бота: {e}")
        raise
    finally:
        # Відновлюємо оригінальний обробник
        if original_handle_callback_query:
            callback.handle_callback_query = original_handle_callback_query


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До побачення!")
    except Exception as e:
        print(f"💥 Критична помилка: {e}")
        sys.exit(1)