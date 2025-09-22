# Промпт: Комплексне перезавантаження Telegram бота

## Опис процесу
Цей промпт автоматизує повне перезавантаження Claude Code Telegram бота після виявлення проблем у роботі, включаючи помилки колбеків, проблеми локалізації, зависання процесів або інші критичні збої.

## Діалог з Claude Code

**Користувач:**
```
comprehensive-bot-restart
```

**Claude Code відповідає:**
Я виконаю комплексне перезавантаження Telegram бота. Це включає:

1. Аналіз та зупинка всіх запущених процесів бота
2. Діагностика проблем у конфігурації та логах
3. Перевірка цілісності коду та локалізації
4. Чистий перезапуск з повною валідацією
5. Моніторинг стабільності після запуску
6. Тестування критичних функцій

Почнемо комплексне перезавантаження:

*Виконує послідовність команд:*

```bash
echo "=== Comprehensive Bot Restart Analysis ==="
date
echo "Current directory: $(pwd)"

# 1. Аналіз запущених процесів
echo "=== Running Bot Processes ==="
ps aux | grep -E "(python.*src\.main|claude.*bot)" | grep -v grep || echo "No bot processes found"

# 2. Перевірка фонових процесів та портів
echo "=== Background Processes Check ==="
pgrep -f "src.main" | while read pid; do
    echo "Found bot process: $pid"
    ps -p $pid -o pid,ppid,cmd
done

# 3. Перевірка зайнятості портів
echo "=== Port Usage Check ==="
netstat -tulpn 2>/dev/null | grep -E ":(8080|8443|3000)" | head -5

# 4. Аналіз останніх логів на помилки
echo "=== Recent Error Analysis ==="
if [ -f /tmp/bot_debug.log ]; then
    tail -50 /tmp/bot_debug.log | grep -i -E "(error|exception|failed|git.*parse)" | tail -10
else
    echo "No debug log found"
fi
```

*Зупинка всіх процесів:*

```bash
echo "=== Stopping All Bot Processes ==="

# Знаходимо та зупиняємо всі процеси бота
pgrep -f "src.main" | while read pid; do
    echo "Stopping bot process: $pid"
    kill -TERM $pid
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        echo "Force killing process: $pid"
        kill -KILL $pid
    fi
done

# Зупиняємо фонові процеси
pgrep -f "run.*optimized" | while read pid; do
    echo "Stopping optimization process: $pid"
    kill -TERM $pid
done

# Очистка тимчасових файлів
rm -f /tmp/bot_debug.log
rm -f /tmp/bot_error.log

echo "✅ All processes stopped"
```

*Діагностика конфігурації:*

```bash
echo "=== Configuration Validation ==="

# Перевірка основних файлів
echo "1. Checking essential files:"
for file in .env src/main.py src/localization/translations/uk.json src/localization/translations/en.json; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

# Перевірка Python середовища
echo "2. Python environment check:"
if [ -d "venv" ]; then
    echo "✅ Virtual environment exists"
    source venv/bin/activate
    echo "Python version: $(python --version)"
    echo "Bot dependencies:"
    python -c "
import sys
try:
    import telegram
    print(f'✅ python-telegram-bot: {telegram.__version__}')
except ImportError:
    print('❌ python-telegram-bot not installed')

try:
    import structlog
    print('✅ structlog available')
except ImportError:
    print('❌ structlog not installed')
"
else
    echo "❌ Virtual environment not found"
fi

# Перевірка локалізації
echo "3. Localization validation:"
python -c "
import json
import sys
sys.path.insert(0, 'src')

try:
    with open('src/localization/translations/uk.json', 'r', encoding='utf-8') as f:
        uk_data = json.load(f)
    with open('src/localization/translations/en.json', 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Перевірка git секції
    if 'git' in uk_data and 'git' in en_data:
        git_keys = ['processing', 'success', 'error', 'diff_title']
        for key in git_keys:
            uk_key = f'git.{key}' in str(uk_data.get('git', {}))
            en_key = f'git.{key}' in str(en_data.get('git', {}))
            if uk_key and en_key:
                print(f'✅ git.{key} localized')
            else:
                print(f'❌ git.{key} missing in localizations')
    else:
        print('❌ Git localization missing')

except Exception as e:
    print(f'❌ Localization validation failed: {e}')
"
```

*Перевірка коду на синтаксичні помилки:*

```bash
echo "=== Code Syntax Validation ==="
python -m py_compile src/main.py && echo "✅ main.py syntax OK" || echo "❌ main.py syntax error"
python -m py_compile src/bot/handlers/callback.py && echo "✅ callback.py syntax OK" || echo "❌ callback.py syntax error"
python -m py_compile src/bot/handlers/command.py && echo "✅ command.py syntax OK" || echo "❌ command.py syntax error"
```

*Чистий запуск з моніторингом:*

```bash
echo "=== Clean Bot Startup ==="

# Створюємо новий лог файл
log_file="/tmp/bot_restart_$(date +%Y%m%d_%H%M%S).log"
echo "Starting bot with fresh logs: $log_file"

# Запуск з детальним логуванням
source venv/bin/activate
nohup python -m src.main --debug > "$log_file" 2>&1 &
bot_pid=$!

echo "Bot started with PID: $bot_pid"
echo "Log file: $log_file"

# Моніторинг запуску (перші 10 секунд)
echo "=== Startup Monitoring ==="
for i in {1..10}; do
    if kill -0 $bot_pid 2>/dev/null; then
        echo "[$i/10] Bot process running (PID: $bot_pid)"

        # Перевірка логів на помилки
        if [ -f "$log_file" ]; then
            errors=$(grep -i -E "(error|exception|failed)" "$log_file" | wc -l)
            if [ $errors -gt 0 ]; then
                echo "⚠️ Found $errors errors in startup logs"
            fi
        fi

        sleep 1
    else
        echo "❌ Bot process died during startup"
        echo "Last log entries:"
        tail -20 "$log_file" 2>/dev/null
        exit 1
    fi
done

echo "✅ Bot startup monitoring completed"
```

*Функціональне тестування:*

```bash
echo "=== Functional Testing ==="

# Тестування імпорту модулів
python -c "
import sys
sys.path.insert(0, 'src')

test_results = []

try:
    from src.bot.handlers.command import git_handler
    test_results.append('✅ Git command handler import OK')
except Exception as e:
    test_results.append(f'❌ Git command handler import failed: {e}')

try:
    from src.bot.handlers.callback import handle_git_callback
    test_results.append('✅ Git callback handler import OK')
except Exception as e:
    test_results.append(f'❌ Git callback handler import failed: {e}')

try:
    from src.localization.util import t
    test_results.append('✅ Localization utility import OK')
except Exception as e:
    test_results.append(f'❌ Localization utility import failed: {e}')

for result in test_results:
    print(result)
"

# Перевірка Telegram API connectivity (якщо є токен)
if [ -f ".env" ] && grep -q "TELEGRAM_BOT_TOKEN" .env; then
    echo "Testing Telegram API connectivity..."
    python -c "
import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

async def test_telegram():
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        try:
            bot = Bot(token)
            me = await bot.get_me()
            print(f'✅ Telegram API OK - Bot: {me.username}')
        except Exception as e:
            print(f'❌ Telegram API failed: {e}')
    else:
        print('⚠️ No Telegram token found')

asyncio.run(test_telegram())
"
fi
```

**Аналіз результатів та рекомендації:**

На основі аналізу я виявив:

**📊 Стан після перезапуску:**
- Процеси: [статус bot процесів]
- Логи: [кількість помилок у startup логах]
- Конфігурація: [статус валідації]
- Функціональність: [результати тестів]

**📋 Виявлені проблеми:**
- [Конкретні помилки з логів та тестування]
- [Проблеми конфігурації]
- [Проблеми залежностей]

**🔧 Рекомендовані дії:**
1. [Конкретні кроки для вирішення виявлених проблем]
2. [Потенційні покращення конфігурації]
3. [Рекомендації по моніторингу]

Чи потрібні додаткові дії або маєте питання щодо стану бота?

## Спеціалізовані варіанти перезапуску

**Швидке перезавантаження (якщо проблеми мінімальні):**
```
quick-bot-restart
```

**Перезавантаження з діагностикою Git проблем:**
```
git-focused-restart
```

**Екстрене перезавантаження (при критичних збоях):**
```
emergency-bot-restart
```

**Перезавантаження з повним оновленням залежностей:**
```
full-dependency-restart
```

## Claude Code відповідає на варіанти:

### quick-bot-restart:
```bash
echo "=== Quick Bot Restart ==="

# Швидка зупинка
pkill -f "src.main"
sleep 2

# Перевірка основних файлів
python -m py_compile src/main.py || exit 1

# Швидкий запуск
source venv/bin/activate
nohup python -m src.main --debug &>/tmp/quick_restart.log &
echo "Bot restarted quickly. PID: $!"

# Короткий моніторинг
sleep 5
if pgrep -f "src.main" >/dev/null; then
    echo "✅ Quick restart successful"
else
    echo "❌ Quick restart failed"
    tail -20 /tmp/quick_restart.log
fi
```

### git-focused-restart:
```bash
echo "=== Git-Focused Bot Restart ==="

# Зупинка з акцентом на Git проблеми
pkill -f "src.main"

# Спеціальна перевірка Git компонентів
echo "Validating Git components:"
python -c "
import sys, json
sys.path.insert(0, 'src')

# Перевірка Git локалізації
with open('src/localization/translations/uk.json', 'r', encoding='utf-8') as f:
    uk = json.load(f)
with open('src/localization/translations/en.json', 'r', encoding='utf-8') as f:
    en = json.load(f)

git_keys = ['processing', 'success', 'error', 'diff_title', 'unknown_git_action']
for key in git_keys:
    if key in str(uk.get('git', {})) and key in str(en.get('git', {})):
        print(f'✅ git.{key}')
    else:
        print(f'❌ git.{key} missing')

# Тестування Git callback handler
try:
    from src.bot.handlers.callback import handle_git_callback
    print('✅ Git callback handler loaded')
except Exception as e:
    print(f'❌ Git callback handler error: {e}')
"

# Запуск з фокусом на Git логування
source venv/bin/activate
python -m src.main --debug 2>&1 | tee /tmp/git_restart.log | grep -i git &

echo "Git-focused restart completed"
```

### emergency-bot-restart:
```bash
echo "=== Emergency Bot Restart ==="

# Створюємо backup поточного стану
backup_dir="emergency_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "backups/$backup_dir"
cp -f /tmp/bot_debug.log "backups/$backup_dir/" 2>/dev/null

# Агресивна зупинка всіх процесів
pkill -9 -f "src.main"
pkill -9 -f "python.*claude"
pkill -9 -f "run.*optimized"

# Очистка всіх логів та временних файлів
rm -f /tmp/bot_*.log
rm -f /tmp/claude_*.log

# Перевірка системних ресурсів
echo "System resources:"
free -h
df -h . | tail -1

# Екстрений запуск з мінімальними логами
source venv/bin/activate
python -m src.main > /tmp/emergency_restart.log 2>&1 &
emergency_pid=$!

echo "Emergency restart initiated with PID: $emergency_pid"

# Інтенсивний моніторинг
for i in {1..15}; do
    if kill -0 $emergency_pid 2>/dev/null; then
        echo "[$i/15] Emergency process stable"
        sleep 1
    else
        echo "❌ Emergency restart failed"
        cat /tmp/emergency_restart.log
        exit 1
    fi
done

echo "🚨 Emergency restart completed successfully"
```

### full-dependency-restart:
```bash
echo "=== Full Dependency Restart ==="

# Зупинка бота
pkill -f "src.main"

# Оновлення Python залежностей
source venv/bin/activate
echo "Updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Перевірка версій критичних бібліотек
echo "Checking library versions:"
python -c "
import telegram, structlog, asyncio
print(f'telegram: {telegram.__version__}')
print(f'structlog: {structlog.__version__}')
print(f'python: {__import__('sys').version}')
"

# Повна валідація після оновлення
python -m py_compile src/main.py
python -c "from src.main import create_bot_application; print('✅ Application validation passed')"

# Запуск після оновлення
python -m src.main --debug &>/tmp/dependency_restart.log &
echo "Full dependency restart completed with PID: $!"
```

## Автоматична діагностика проблем

```python
# Автоматичний аналіз поширених проблем
common_issues = {
    'git_parse_error': 'Git callback parse entities error',
    'import_error': 'Module import failures',
    'telegram_api_error': 'Telegram API connectivity issues',
    'localization_error': 'Missing or corrupted translation files',
    'process_zombie': 'Zombie bot processes',
    'port_conflict': 'Port already in use conflicts'
}

def diagnose_and_recommend():
    issues_found = []
    recommendations = []

    # Аналіз логів
    if check_logs_for_pattern('parse entities'):
        issues_found.append('git_parse_error')
        recommendations.append('Fix Git message formatting in localization')

    if check_process_count() > 1:
        issues_found.append('process_zombie')
        recommendations.append('Kill all bot processes before restart')

    if not validate_localization_files():
        issues_found.append('localization_error')
        recommendations.append('Restore or fix translation files')

    return generate_action_plan(issues_found, recommendations)
```

## Коли використовувати
- ✅ При помилках Git callback ("Can't parse entities")
- ✅ При зависанні або дублюванні процесів бота
- ✅ При проблемах локалізації або перекладів
- ✅ При критичних помилках Telegram API
- ✅ Після оновлення коду або конфігурації
- ✅ При підозрі на корупцію стану бота

## Безпечні практики
- 🔒 Завжди створює backup логів перед рестартом
- 📊 Валідує конфігурацію перед запуском
- 🔍 Моніторить стабільність після перезапуску
- 📝 Документує всі виявлені проблеми
- ⚡ Надає конкретні рекомендації для усунення проблем
- 🚨 Має аварійні процедури для критичних ситуацій