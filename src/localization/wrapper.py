"""
Localization wrapper helpers.
Provides async helpers to read user's locale from storage and render translations
consistently across handlers.
"""
import os
import asyncio
import structlog
from typing import Optional
from collections import OrderedDict
import time

logger = structlog.get_logger()

DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "uk")

# Thread/async-safe TTL cache for user locales (10 min)
class TTLCache:
    def __init__(self, ttl_seconds: int = 600):
        self._cache = OrderedDict()
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()

    async def get(self, key):
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    # Move to end (LRU behavior)
                    self._cache.move_to_end(key)
                    return value
                else:
                    # Expired - remove
                    del self._cache[key]
            return None

    async def set(self, key, value):
        async with self._lock:
            self._cache[key] = (value, time.time())
            # Keep cache size reasonable
            if len(self._cache) > 1000:
                # Remove oldest 10% when cache is full
                for _ in range(100):
                    if self._cache:
                        self._cache.popitem(last=False)

    async def clear(self):
        async with self._lock:
            self._cache.clear()

# Global cache instance
_locale_cache = TTLCache(ttl_seconds=600)

async def _clear_cache_periodically():
    """Periodic cache cleanup task"""
    while True:
        await asyncio.sleep(600)  # 10 minutes
        await _locale_cache.clear()

# Start cache clearing task only when there's a running event loop
def _start_cache_cleaner():
    try:
        loop = asyncio.get_running_loop()
        if loop:
            # Check if task is already running
            if not hasattr(_start_cache_cleaner, '_task_started'):
                asyncio.create_task(_clear_cache_periodically())
                _start_cache_cleaner._task_started = True
    except RuntimeError:
        # No running event loop, will start when one is available
        pass

_start_cache_cleaner()

async def get_locale_for_user(context, user_id: int) -> str:
    """Get locale for user with proper fallback chain and caching"""

    # Check cache first
    cached_locale = await _locale_cache.get(user_id)
    if cached_locale:
        logger.debug("Locale from cache", user_id=user_id, locale=cached_locale, source="cache")
        return cached_locale

    # Try user language storage (DB/Redis)
    user_language_storage = context.bot_data.get("user_language_storage")
    if user_language_storage:
        try:
            locale = await user_language_storage.get_user_language(user_id)
            if locale:
                await _locale_cache.set(user_id, locale)
                logger.info("Locale from storage", user_id=user_id, locale=locale, source="db")
                return locale
        except Exception as e:
            logger.warning("Failed to get locale from storage", user_id=user_id, error=str(e), source="db_error")

    # Fallback to Telegram language code
    try:
        tg_lang = context.user_data.get("_telegram_language_code")
        if tg_lang and tg_lang in ["uk", "en"]:  # Only supported languages
            await _locale_cache.set(user_id, tg_lang)
            logger.info("Locale from Telegram", user_id=user_id, locale=tg_lang, source="telegram")
            return tg_lang
    except Exception:
        pass

    # Final fallback to DEFAULT_LOCALE
    logger.info("Locale fallback", user_id=user_id, locale=DEFAULT_LOCALE, source="default")
    return DEFAULT_LOCALE

from .i18n import i18n

async def t(context, user_id: int, key: str, **kwargs) -> str:
    """Get localized text for user with formatting support"""
    locale = await get_locale_for_user(context, user_id)
    # Use the improved i18n.get() method that handles kwargs and fallbacks
    return i18n.get(key, locale=locale, **kwargs)

async def send_t(bot, chat_id: int, user_id: int, key: str, **kwargs):
    text = await t(bot, user_id, key, **kwargs)
    await bot.send_message(chat_id, text)