#!/usr/bin/env python3
"""Fix Ukrainian JSON localization file by adding missing start section."""

import json
from pathlib import Path

def fix_uk_json():
    """Fix the Ukrainian JSON file by adding missing commands."""
    
    # File paths
    uk_file = Path("/home/vokov/claude-notifer-and-bot/src/localization/translations/uk.json")
    en_file = Path("/home/vokov/claude-notifer-and-bot/src/localization/translations/en.json")
    
    # Load English file to get structure
    with open(en_file, 'r', encoding='utf-8') as f:
        en_data = json.load(f)
    
    # Load Ukrainian file (currently broken with duplicate commands)
    with open(uk_file, 'r', encoding='utf-8') as f:
        uk_data = json.load(f)
    
    print("Current UK commands keys:", list(uk_data.get('commands', {}).keys()))
    print("EN commands keys:", list(en_data.get('commands', {}).keys()))
    
    # Get the start section from English as template
    en_start = en_data.get('commands', {}).get('start', {})
    en_help = en_data.get('commands', {}).get('help', {})
    
    print("EN start keys:", list(en_start.keys()))
    print("EN help keys:", list(en_help.keys()))
    
    # The Ukrainian translations for start section
    uk_start = {
        "welcome": "👋 Вітаю у Claude Code Telegram боті, {name}!",
        "description": "🤖 Я допомагаю отримати віддалений доступ до Claude Code через Telegram.",
        "available_commands": "**Доступні команди:**",
        "help_cmd": "Показати детальну довідку",
        "new_cmd": "Почати нову сесію з Claude",
        "ls_cmd": "Показати файли в поточній директорії",
        "cd_cmd": "Змінити директорію",
        "projects_cmd": "Показати доступні проекти",
        "status_cmd": "Показати статус сесії",
        "actions_cmd": "Показати швидкі дії",
        "git_cmd": "Команди Git репозиторію",
        "quick_start": "**Швидкий старт:**",
        "quick_start_1": "Використайте `/projects` щоб побачити доступні проекти",
        "quick_start_2": "Використайте `/cd <проект>` щоб перейти до проекту",
        "quick_start_3": "Надішліть будь-яке повідомлення щоб почати кодити з Claude!",
        "security_note": "🔒 Ваш доступ захищений і всі дії логуються.",
        "usage_note": "📊 Використовуйте `/status` щоб перевірити ліміти використання."
    }
    
    # Ukrainian translations for help section  
    uk_help = {
        "title": "🤖 **Довідка Claude Code Telegram Bot**",
        "navigation_title": "**Команди навігації:**",
        "ls_desc": "Показати файли і директорії", 
        "cd_desc": "Змінити директорію",
        "pwd_desc": "Показати поточну директорію",
        "projects_desc": "Показати доступні проекти",
        "session_title": "**Команди сесії:**",
        "new_desc": "Почати нову сесію Claude",
        "continue_desc": "Продовжити останню сесію (з опціональним повідомленням)",
        "end_desc": "Завершити поточну сесію",
        "status_desc": "Показати статус сесії та використання",
        "export_desc": "Експортувати історію сесії",
        "actions_desc": "Показати контекстні швидкі дії",
        "git_desc": "Інформація про Git репозиторій",
        "usage_title": "**Приклади використання:**",
        "usage_cd": "Увійти в директорію проекту",
        "usage_ls": "Подивитися що є в поточній директорії", 
        "usage_code": "Попросити Claude написати код",
        "usage_file": "Надіслати файл для перегляду Claude",
        "file_ops_title": "**Операції з файлами:**",
        "file_ops_send": "Надсилайте текстові файли (.py, .js, .md, тощо) для перегляду",
        "file_ops_modify": "Claude може читати, змінювати та створювати файли",
        "file_ops_security": "Всі операції з файлами в межах дозволеної директорії",
        "security_title": "**Функції безпеки:**",
        "security_path": "🔒 Захист від обходу шляхів",
        "security_rate": "⏱️ Обмеження швидкості для запобігання зловживанням",
        "security_usage": "📊 Відстеження використання та ліміти",
        "security_validation": "🛡️ Валідація та санітаризація вводу",
        "tips_title": "**Поради:**",
        "tips_specific": "Використовуйте конкретні, зрозумілі запити для кращих результатів",
        "tips_status": "Перевіряйте `/status` щоб відстежувати ваше використання",
        "tips_buttons": "Використовуйте кнопки швидких дій коли доступно"
    }
    
    # Add missing sections to the current commands
    if 'commands' not in uk_data:
        uk_data['commands'] = {}
    
    # Add the missing start and help sections
    uk_data['commands']['start'] = uk_start
    uk_data['commands']['help'] = uk_help
    
    # Also check if we have buttons section
    if 'buttons' not in uk_data:
        uk_data['buttons'] = {}
        
    # Add missing button translations if they don't exist
    button_translations = {
        "show_projects": "📁 Показати проекти",
        "get_help": "❓ Отримати допомогу", 
        "new_session": "🆕 Нова сесія",
        "check_status": "📊 Перевірити статус",
        "language_settings": "🌐 Мова"
    }
    
    for key, value in button_translations.items():
        if key not in uk_data['buttons']:
            uk_data['buttons'][key] = value
    
    print("After fix - commands keys:", list(uk_data.get('commands', {}).keys()))
    
    # Save the fixed file
    with open(uk_file, 'w', encoding='utf-8') as f:
        json.dump(uk_data, f, indent=2, ensure_ascii=False)
    
    print(f"Fixed Ukrainian JSON file: {uk_file}")
    
    # Verify the fix
    with open(uk_file, 'r', encoding='utf-8') as f:
        fixed_data = json.load(f)
    
    print("Verification - commands keys:", list(fixed_data.get('commands', {}).keys()))
    print("Start section exists:", 'start' in fixed_data.get('commands', {}))
    if 'start' in fixed_data.get('commands', {}):
        print("Start welcome text:", fixed_data['commands']['start'].get('welcome', 'NOT FOUND'))

if __name__ == "__main__":
    fix_uk_json()