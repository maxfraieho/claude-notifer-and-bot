import pytest
from unittest.mock import Mock, AsyncMock
from src.localization.wrapper import get_locale_for_user, t, _locale_cache

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear locale cache before each test"""
    _locale_cache.clear()
    yield
    _locale_cache.clear()

@pytest.mark.asyncio
async def test_get_locale_for_user_from_storage():
    context = Mock()
    storage_mock = AsyncMock()
    storage_mock.get_user_language = AsyncMock(return_value="en")
    context.bot_data = {"user_language_storage": storage_mock}

    locale = await get_locale_for_user(context, 123)
    assert locale == "en"

@pytest.mark.asyncio
async def test_get_locale_for_user_fallback_to_telegram():
    context = Mock()
    context.bot_data = {}
    context.user_data = {"_telegram_language_code": "uk"}

    locale = await get_locale_for_user(context, 123)
    assert locale == "uk"

@pytest.mark.asyncio
async def test_t_function():
    # Mock the i18n.get method
    from src.localization.i18n import i18n
    i18n.get = Mock(return_value="Hello {name}")

    context = Mock()
    context.bot_data = {}
    context.user_data = {"_telegram_language_code": "en"}

    text = await t(context, 123, "greeting", name="World")
    assert text == "Hello World"