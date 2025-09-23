"""
Модуль локалізації для Claude Bot
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class I18n:
    """Клас для роботи з локалізацією"""

    def __init__(self, default_locale: str = "uk"):
        self.default_locale = default_locale
        self.current_locale = default_locale
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.load_translations()

    def load_translations(self):
        """Завантажити всі переклади"""
        locales_dir = Path(__file__).parent.parent / "locales"

        if not locales_dir.exists():
            logger.warning("Папка локалізації не знайдена")
            return

        for locale_file in locales_dir.glob("*.json"):
            locale_code = locale_file.stem
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self.translations[locale_code] = json.load(f)
                logger.info(f"Завантажено переклади для {locale_code}")
            except Exception as e:
                logger.error(f"Помилка завантаження {locale_file}: {e}")

    def set_locale(self, locale: str):
        """Встановити поточну локаль"""
        if locale in self.translations:
            self.current_locale = locale
            logger.info(f"Локаль змінено на {locale}")
        else:
            logger.warning(f"Локаль {locale} не знайдено")

    def get(self, key: str, locale: Optional[str] = None) -> str:
        """Отримати переклад за ключем"""
        target_locale = locale or self.current_locale

        if target_locale not in self.translations:
            target_locale = self.default_locale

        if target_locale not in self.translations:
            return key

        # Розбираємо ключ типу "commands.start"
        keys = key.split(".")
        result = self.translations[target_locale]

        try:
            for k in keys:
                result = result[k]
            return result
        except (KeyError, TypeError):
            logger.warning(f"Переклад не знайдено для ключа {key}")
            return key

    def t(self, key: str, locale: Optional[str] = None) -> str:
        """Короткий псевдонім для get()"""
        return self.get(key, locale)

# Глобальний екземпляр
i18n = I18n()

def _(key: str) -> str:
    """Функція для швидкого доступу до перекладів"""
    return i18n.get(key)
