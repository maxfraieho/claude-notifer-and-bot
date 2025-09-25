#!/usr/bin/env python3

"""
Простий тест локалізації перезапуску
"""

import asyncio
from localization.i18n import i18n

def test_translation_keys():
    """Перевіряємо чи існують потрібні ключі в переклади"""

    print("🧪 Тестуємо ключі локалізації...")

    # Ключі які використовуються в restart коді
    test_keys = [
        "commands.start.welcome",
        "commands.restart.completed",
        "buttons.new_session",
        "buttons.continue_session",
        "buttons.check_status",
        "buttons.context",
        "buttons.settings",
        "buttons.get_help",
        "buttons.language_settings"
    ]

    results = {}
    for key in test_keys:
        try:
            # Перевіряємо чи повертається переклад
            uk_text = i18n.get(key, locale="uk")
            en_text = i18n.get(key, locale="en")

            # Якщо переклад містить сам ключ - це проблема
            uk_good = key not in uk_text
            en_good = key not in en_text

            results[key] = {
                "uk": uk_text,
                "en": en_text,
                "uk_ok": uk_good,
                "en_ok": en_good
            }

            print(f"{'✅' if uk_good and en_good else '❌'} {key}")
            print(f"  UK: {uk_text}")
            print(f"  EN: {en_text}")

        except Exception as e:
            print(f"❌ {key}: ERROR - {e}")
            results[key] = {"error": str(e)}

    # Підрахунок результатів
    good_keys = sum(1 for r in results.values() if isinstance(r, dict) and r.get("uk_ok") and r.get("en_ok"))
    total_keys = len(test_keys)

    print(f"\n📊 Результат: {good_keys}/{total_keys} ключів працюють правильно")

    if good_keys == total_keys:
        print("🎉 Всі ключі локалізації працюють!")
        return True
    else:
        print("⚠️ Є проблеми з локалізацією")
        return False

if __name__ == "__main__":
    success = test_translation_keys()
    exit(0 if success else 1)