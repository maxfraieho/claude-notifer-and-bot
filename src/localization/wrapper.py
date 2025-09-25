"""
Localization wrapper helpers.
Provides async helpers to read user's locale from storage and render translations
consistently across handlers.
"""
import os
import asyncio
import structlog
from typing import Optional

logger = structlog.get_logger()

DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "uk")

# Simple in-memory TTL cache for user locales (10 min)
_locale_cache: dict = {}
_cache_ttl = 600  # seconds

async def _clear_cache_periodically():
    while True:
        await asyncio.sleep(_cache_ttl)
        _locale_cache.clear()

# Start cache clearing task only when there's a running event loop
def _start_cache_cleaner():
    try:
        loop = asyncio.get_running_loop()
        if loop:
            asyncio.create_task(_clear_cache_periodically())
    except RuntimeError:
        # No running event loop, will start when one is available
        pass

_start_cache_cleaner()

async def get_locale_for_user(context, user_id: int) -> str:
    # Check cache first
    if user_id in _locale_cache:
        cached_locale, timestamp = _locale_cache[user_id]
        if asyncio.get_event_loop().time() - timestamp < _cache_ttl:
            logger.debug("Locale from cache", user_id=user_id, locale=cached_locale)
            return cached_locale

    # Try user language storage (DB/Redis)
    user_language_storage = context.bot_data.get("user_language_storage")
    if user_language_storage:
        try:
            locale = await user_language_storage.get_user_language(user_id)
            if locale:
                _locale_cache[user_id] = (locale, asyncio.get_event_loop().time())
                logger.info("Locale from storage", user_id=user_id, locale=locale, source="db")
                return locale
        except Exception as e:
            logger.warning("Failed to get locale from storage", user_id=user_id, error=str(e))

    # Fallback to Telegram language code
    try:
        tg_lang = context.user_data.get("_telegram_language_code")
        if tg_lang:
            _locale_cache[user_id] = (tg_lang, asyncio.get_event_loop().time())
            logger.info("Locale from Telegram", user_id=user_id, locale=tg_lang, source="telegram")
            return tg_lang
    except Exception:
        pass

    logger.info("Locale fallback", user_id=user_id, locale=DEFAULT_LOCALE, source="default")
    return DEFAULT_LOCALE

from .i18n import i18n

async def t(context, user_id: int, key: str, **kwargs) -> str:
    locale = await get_locale_for_user(context, user_id)
    text = i18n.get(key, locale=locale)
    try:
        return text.format(**kwargs) if kwargs else text
    except Exception:
        return text

async def send_t(bot, chat_id: int, user_id: int, key: str, **kwargs):
    text = await t(bot, user_id, key, **kwargs)
    await bot.send_message(chat_id, text)