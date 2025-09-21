#!/usr/bin/env python3
"""
Швидка перевірка локалізації
Простий скрипт для перевірки критичних проблем локалізації
"""

import os
import re
import json
from pathlib import Path


def check_hardcoded_ui_elements():
    """Перевірка hardcoded UI елементів"""
    print("🔍 Перевірка hardcoded UI елементів...")

    project_root = Path(__file__).parent.parent
    critical_files = [
        project_root / "src" / "bot" / "handlers" / "dnd_prompts.py",
        project_root / "src" / "bot" / "handlers" / "command.py",
        project_root / "src" / "bot" / "handlers" / "callback.py"
    ]

    # Небезпечні patterns для кнопок
    dangerous_patterns = [
        r'InlineKeyboardButton\(\s*["\']([^"\']*[🔧📊🔄📝📋🔙➕⚙️🌙⚡📁🆕💾❓🏠🌐⬆️]+[^"\']*)["\']',
        r'InlineKeyboardButton\(\s*["\']([^"\']*(?:Налаштування|Settings|Створити|Create|Додати|Add|Редагувати|Edit)[^"\']*)["\']',
    ]

    violations = []

    for file_path in critical_files:
        if not file_path.exists():
            print(f"⚠️  Файл не існує: {file_path.name}")
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for line_num, line in enumerate(content.split('\n'), 1):
                # Skip якщо вже використовує локалізацію
                if 'await t(' in line or 'get_localized_text' in line:
                    continue

                for pattern in dangerous_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        violations.append({
                            'file': str(file_path.name),
                            'line': line_num,
                            'text': match.group(1),
                            'severity': 'CRITICAL'
                        })

        except Exception as e:
            print(f"❌ Помилка читання файлу {file_path.name}: {e}")
            continue

    if violations:
        print(f"❌ Знайдено {len(violations)} hardcoded UI елементів:")
        for v in violations:
            print(f"   {v['file']}:{v['line']} - '{v['text']}'")
        return False
    else:
        print("✅ Hardcoded UI елементи не знайдені в критичних файлах!")
        return True


def check_translation_files():
    """Перевірка файлів перекладів"""
    print("\n🌐 Перевірка файлів перекладів...")

    project_root = Path(__file__).parent.parent
    translations_dir = project_root / "src" / "localization" / "translations"

    if not translations_dir.exists():
        print("❌ Директорія перекладів не існує!")
        return False

    required_files = ["uk.json", "en.json"]
    all_good = True

    for file_name in required_files:
        file_path = translations_dir / file_name
        if not file_path.exists():
            print(f"❌ Файл перекладу {file_name} не існує!")
            all_good = False
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✅ {file_name} - корректний JSON")
            except Exception as e:
                print(f"❌ {file_name} - помилка JSON: {e}")
                all_good = False

    return all_good


def check_critical_localization_keys():
    """Перевірка критичних ключів локалізації"""
    print("\n🔑 Перевірка критичних ключів локалізації...")

    project_root = Path(__file__).parent.parent
    uk_file = project_root / "src" / "localization" / "translations" / "uk.json"

    if not uk_file.exists():
        print("❌ Файл UK перекладу не існує!")
        return False

    try:
        with open(uk_file, 'r', encoding='utf-8') as f:
            uk_data = json.load(f)
    except Exception as e:
        print(f"❌ Помилка читання UK файлу: {e}")
        return False

    # Критичні ключі які мають бути присутні після наших виправлень
    critical_keys = [
        ("buttons", "new_session"),
        ("buttons", "continue"),
        ("buttons", "settings"),
        ("buttons", "create_prompt"),
        ("buttons", "prompts_list"),
        ("buttons", "go_up"),
        ("buttons", "refresh"),
        ("buttons", "projects")
    ]

    missing_keys = []
    for section, key in critical_keys:
        if section not in uk_data:
            missing_keys.append(f"{section} (section)")
        elif key not in uk_data[section]:
            missing_keys.append(f"{section}.{key}")

    if missing_keys:
        print(f"❌ Відсутні критичні ключі: {missing_keys}")
        return False
    else:
        print("✅ Всі критичні ключі присутні!")
        return True


def check_localization_imports():
    """Перевірка локалізаційних imports"""
    print("\n📦 Перевірка локалізаційних imports...")

    project_root = Path(__file__).parent.parent
    handler_files = [
        project_root / "src" / "bot" / "handlers" / "dnd_prompts.py",
        project_root / "src" / "bot" / "handlers" / "command.py"
    ]

    missing_imports = []

    for file_path in handler_files:
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Перевірити чи є локалізаційні imports
            has_localization_import = (
                'from ...localization.util import' in content or
                'from ..localization.util import' in content
            )

            # Перевірити чи файл використовує InlineKeyboardButton
            uses_keyboard = 'InlineKeyboardButton(' in content

            if uses_keyboard and not has_localization_import:
                missing_imports.append(file_path.name)

        except Exception:
            continue

    if missing_imports:
        print(f"❌ Файли без локалізаційних imports: {missing_imports}")
        return False
    else:
        print("✅ Всі необхідні файли мають локалізаційні imports!")
        return True


def main():
    """Головна функція"""
    print("🚀 Швидка перевірка локалізації...\n")

    tests = [
        check_translation_files,
        check_critical_localization_keys,
        check_localization_imports,
        check_hardcoded_ui_elements
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "="*50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 Всі тести пройдено! ({passed}/{total})")
        print("✅ Локалізація в відмінному стані!")
        return 0
    else:
        print(f"⚠️  Пройдено {passed}/{total} тестів")
        print("❌ Потрібні додаткові виправлення!")
        return 1


if __name__ == "__main__":
    exit(main())