"""Helper functions for localization."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import LocalizationManager
    from .storage import UserLanguageStorage


async def get_user_text(
    localization: "LocalizationManager",
    user_lang_storage: "UserLanguageStorage", 
    user_id: int,
    key: str,
    **kwargs
) -> str:
    """Get localized text for a specific user.
    
    Args:
        localization: Localization manager instance
        user_lang_storage: User language storage instance
        user_id: Telegram user ID
        key: Translation key
        **kwargs: Variables to format into the translation
        
    Returns:
        Localized text
    """
    # Get user's preferred language
    user_language = await user_lang_storage.get_user_language(user_id)
    
    # Use the user's language or fall back to default
    return localization.get(key, language=user_language, **kwargs)