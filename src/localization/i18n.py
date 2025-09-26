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
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.load_translations()

    def load_translations(self):
        """Завантажити всі переклади"""
        locales_dir = Path(__file__).parent / "../locales"

        if not locales_dir.exists():
            logger.warning(f"Папка локалізації не знайдена: {locales_dir.absolute()}")
            return

        loaded_count = 0
        for locale_file in locales_dir.glob("*.json"):
            locale_code = locale_file.stem
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.translations[locale_code] = data
                    key_count = self._count_keys(data)
                    logger.info(f"✅ Завантажено переклади для '{locale_code}' ({key_count} ключів)")
                    loaded_count += 1
            except json.JSONDecodeError as e:
                logger.error(f"❌ Помилка JSON в {locale_file}: рядок {e.lineno}, позиція {e.colno}")
            except Exception as e:
                logger.error(f"❌ Помилка завантаження {locale_file}: {e}")

        logger.info(f"📊 Завантажено {loaded_count} файлів локалізації з {len(list(locales_dir.glob('*.json')))} доступних")

    def set_locale(self, locale: str):
        """Deprecated: do not set global current locale in multi-worker environments.
        Locale should be passed explicitly to `get()` or managed per-user in storage.
        This method will only log an informational message for backward compatibility.
        """
        if locale in self.translations:
            logger.info(f"(deprecated) requested to set locale to {locale}; use per-request locale storage instead")
        else:
            logger.warning(f"Локаль {locale} не знайдено")

    def _count_keys(self, data: dict, path: str = "") -> int:
        """Рекурсивно підраховує кількість ключів перекладу"""
        count = 0
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, dict):
                count += self._count_keys(value, current_path)
            else:
                count += 1
        return count

    def get_debug_info(self) -> dict:
        """Повертає детальну інформацію для відлагодження"""
        info = {
            "default_locale": self.default_locale,
            "loaded_locales": list(self.translations.keys()),
            "key_counts": {},
            "sample_keys": {}
        }

        for locale, data in self.translations.items():
            info["key_counts"][locale] = self._count_keys(data)
            # Зібрати перші 3 ключі як зразок
            sample = []
            for key in self._get_all_keys(data):
                sample.append(key)
                if len(sample) >= 3:
                    break
            info["sample_keys"][locale] = sample

        return info

    def _get_all_keys(self, data: dict, path: str = "") -> list:
        """Повертає всі ключі у вигляді dot-notation списку"""
        keys = []
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, dict):
                keys.extend(self._get_all_keys(value, current_path))
            else:
                keys.append(current_path)
        return keys

    def _get_plural_form_uk(self, count: int) -> str:
        """Визначає форму множини для української мови"""
        if count % 10 == 1 and count % 100 != 11:
            return "one"
        elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
            return "few"
        else:
            return "many"

    def get(self, key: str, locale: Optional[str] = None, **kwargs) -> str:
        """Отримати переклад за ключем з підтримкою форматування.

        НІКОЛИ не повертає сирий ключ як «успішний переклад».
        При відсутності перекладу повертає зрозуміле fallback повідомлення.

        Args:
            key: Ключ перекладу (підтримує dot notation)
            locale: Код локалі (None = використати default_locale)
            **kwargs: Змінні для форматування рядка

        Returns:
            Переклад з форматуванням або fallback повідомлення
        """
        target_locale = locale or self.default_locale

        # Спробувати запрошену локаль
        if target_locale not in self.translations:
            # Fallback до default_locale
            target_locale = self.default_locale

        # Якщо навіть default_locale відсутня - повернути fallback
        if target_locale not in self.translations:
            logger.error(f"Локаль {target_locale} не завантажена")
            return f"[missing translation: {key} | locale={locale or 'default'}]"

        # Розбираємо ключ типу "commands.start"
        keys = key.split(".")
        result = self.translations[target_locale]

        try:
            for k in keys:
                result = result[k]

            # Якщо знайшли переклад
            if isinstance(result, str):
                # Спробувати форматування з kwargs
                if kwargs:
                    try:
                        return result.format(**kwargs)
                    except KeyError as e:
                        logger.error(f"Відсутня змінна '{e}' для форматування ключа '{key}'")
                        # Повертаємо неформатований текст як fallback
                        return result
                    except Exception as e:
                        logger.error(f"Помилка форматування ключа '{key}': {e}")
                        return result
                else:
                    return result
            elif isinstance(result, dict):
                # Підтримка плюралізації
                if 'count' in kwargs and target_locale == 'uk':
                    count = kwargs['count']
                    plural_form = self._get_plural_form_uk(count)
                    if plural_form in result:
                        text = result[plural_form]
                        try:
                            return text.format(**kwargs)
                        except Exception as e:
                            logger.error(f"Помилка форматування плюральної форми '{key}': {e}")
                            return text
                    else:
                        logger.warning(f"Плюральна форма '{plural_form}' не знайдена для '{key}'")
                        # Fallback до першої доступної форми
                        first_form = next(iter(result.values()), str(result))
                        try:
                            return first_form.format(**kwargs)
                        except:
                            return first_form
                return str(result)
            else:
                return str(result)

        except (KeyError, TypeError):
            # Ключ не знайдено - НЕ повертаємо сирий ключ!
            logger.warning(f"Переклад не знайдено для ключа '{key}' в локалі '{target_locale}'")
            return f"[missing translation: {key} | locale={target_locale}]"

    def t(self, key: str, locale: Optional[str] = None, **kwargs) -> str:
        """Короткий псевдонім для get()"""
        return self.get(key, locale, **kwargs)

# Глобальний екземпляр
i18n = I18n()

def _(key: str, **kwargs) -> str:
    """Функція для швидкого доступу до перекладів"""
    return i18n.get(key, **kwargs)
