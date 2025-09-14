"""Centralized localization utilities with proper error handling."""

from typing import Any, Dict, Optional
from telegram import Update
from telegram.ext import ContextTypes

from .helpers import get_user_text
from .manager import LocalizationManager
from .storage import UserLanguageStorage


async def t(context: ContextTypes.DEFAULT_TYPE, user_id: int, key: str, **kwargs) -> str:
    """Get localized text with proper error handling and fallbacks.
    
    Args:
        context: Bot context containing localization services
        user_id: Telegram user ID
        key: Translation key
        **kwargs: Variables to format into the translation
        
    Returns:
        Localized text or fallback key in brackets if translation fails
    """
    localization: Optional[LocalizationManager] = context.bot_data.get("localization")
    user_language_storage: Optional[UserLanguageStorage] = context.bot_data.get("user_language_storage")
    
    if not localization or not user_language_storage:
        return f"[{key}]"
    
    try:
        return await get_user_text(localization, user_language_storage, user_id, key, **kwargs)
    except Exception:
        return f"[{key}]"


def t_sync(context: ContextTypes.DEFAULT_TYPE, key: str, language: Optional[str] = None, **kwargs) -> str:
    """Get localized text synchronously for bot startup/static strings.
    
    Args:
        context: Bot context containing localization services
        key: Translation key
        language: Language code, falls back to default if None
        **kwargs: Variables to format into the translation
        
    Returns:
        Localized text or fallback key in brackets if translation fails
    """
    localization: Optional[LocalizationManager] = context.bot_data.get("localization")
    
    if not localization:
        return f"[{key}]"
    
    try:
        return localization.get(key, language=language, **kwargs)
    except Exception:
        return f"[{key}]"


def get_user_id(update: Update) -> Optional[int]:
    """Safely get user ID from update.
    
    Args:
        update: Telegram update object
        
    Returns:
        User ID or None if not available
    """
    if update.effective_user:
        return update.effective_user.id
    return None


def get_effective_message(update: Update):
    """Safely get effective message from update.
    
    Args:
        update: Telegram update object
        
    Returns:
        Message object or None if not available
    """
    return update.effective_message