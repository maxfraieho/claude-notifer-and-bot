# Промпт: Налаштування середовища та конфігурації

## Опис процесу
Цей промпт автоматизує налаштування повного робочого середовища для проекту Claude Telegram Bot з нуля або відновлення після збою.

## Діалог з Claude Code

**Користувач:**
```
setup-environment
```

**Claude Code відповідає:**
Я виконаю повне налаштування робочого середовища. Процес включає:

1. Перевірка системних залежностей
2. Налаштування Python середовища з Poetry
3. Створення та налаштування .env файлу
4. Ініціалізація бази даних
5. Перевірка Docker налаштувань
6. Валідація Claude CLI авторизації
7. Тестування базової функціональності

Почнемо налаштування:

*Виконує послідовність команд:*

```bash
# 1. Перевірка системних залежностей
echo "=== System Requirements Check ==="
python --version
docker --version
docker-compose --version

# 2. Встановлення Poetry (якщо не встановлено)
curl -sSL https://install.python-poetry.org | python3 - || echo "Poetry already installed"

# 3. Встановлення залежностей проекту
poetry install

# 4. Створення базових директорій
mkdir -p data target_project logs backups

# 5. Перевірка .env файлу
ls -la .env || echo ".env файл не знайдено - потрібно створити"
```

**Інтерактивна конфігурація .env:**

Я створю .env файл з необхідними налаштуваннями. Будь ласка, надайте наступну інформацію:

1. `TELEGRAM_BOT_TOKEN` - токен Telegram бота
2. `TELEGRAM_BOT_USERNAME` - username бота  
3. `ALLOWED_USERS` - ID користувачів (через кому)
4. `ANTHROPIC_API_KEY` - API ключ Claude (опціонально)

**Користувач надає дані, Claude створює .env:**

```bash
# Створення .env файлу з наданими даними
cat > .env << 'EOF'
# Telegram Configuration
TELEGRAM_BOT_TOKEN=наданий_токен
TELEGRAM_BOT_USERNAME=наданий_username

# Security
ALLOWED_USERS=надані_user_ids
ENABLE_TOKEN_AUTH=false

# Claude Configuration  
USE_SDK=false
CLAUDE_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=наданий_api_key

# Paths
APPROVED_DIRECTORY=/app/target_project
TARGET_PROJECT_PATH=/app/target_project

# Features
CLAUDE_AVAILABILITY_MONITOR=true
CLAUDE_AVAILABILITY_CHECK_INTERVAL=60

# Development
DEBUG=false
LOG_LEVEL=INFO
EOF

echo "✅ .env файл створено"
```

**Продовження налаштування:**
```bash
# 6. Ініціалізація бази даних
poetry run python -c "
from src.storage.database import DatabaseManager
from src.config.settings import get_settings
db = DatabaseManager(get_settings().database_url)
db.create_tables()
print('✅ Database initialized')
"

# 7. Перевірка Claude CLI
claude --version && claude auth status

# 8. Тест Docker збірки
docker-compose build

# 9. Запуск контейнера для тестування
docker-compose up -d
sleep 10
docker-compose logs --tail=20 claude_bot

# 10. Базова валідація
docker exec claude-code-bot python -c "
from src.main import create_bot_application
print('✅ Application can be created')
"
```

## Варіанти налаштування

**Швидке налаштування для розробки:**
```
setup-dev
```

**Налаштування продакшен середовища:**
```
setup-production  
```

**Відновлення після збою:**
```
restore-environment
```

**Налаштування з backup:**
```
setup-from-backup
```

## Claude Code відповідає на варіанти:

### setup-dev:
```bash
echo "=== Development Setup ==="

# Встановлення з dev залежностями
poetry install --with dev

# Створення dev .env
cat > .env << 'EOF'
DEBUG=true
LOG_LEVEL=DEBUG  
USE_SDK=false
TELEGRAM_BOT_TOKEN=your_dev_bot_token
ALLOWED_USERS=your_user_id
APPROVED_DIRECTORY=$(pwd)/target_project
TARGET_PROJECT_PATH=$(pwd)/target_project
CLAUDE_AVAILABILITY_MONITOR=false
EOF

# Створення тестової директорії проекту
mkdir -p target_project
echo "# Test Project" > target_project/README.md

echo "✅ Development environment ready"
echo "Редагуйте .env файл з вашими токенами"
```

### setup-production:
```bash
echo "=== Production Setup ==="

# Використання production конфігурації
cat > .env << 'EOF'
DEBUG=false
LOG_LEVEL=INFO
USE_SDK=false
TELEGRAM_BOT_TOKEN=your_production_token
ALLOWED_USERS=production_user_ids
APPROVED_DIRECTORY=/app/target_project
TARGET_PROJECT_PATH=/app/target_project
CLAUDE_AVAILABILITY_MONITOR=true
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=notification_chat_ids
CLAUDE_AVAILABILITY_CHECK_INTERVAL=300
EOF

# Налаштування логування
mkdir -p logs
chmod 755 logs

# Налаштування systemd сервісу (опціонально)
echo "Створити systemd service? (y/n)"
```

### restore-environment:
```bash
echo "=== Environment Restoration ==="

# Перевірка що можна відновити
ls -la backups/ 2>/dev/null || echo "Backup directory not found"

# Очищення поточного стану
docker-compose down -v
rm -rf data/*

# Відновлення залежностей
poetry install

# Пересоздання бази даних
poetry run python -c "
from src.storage.database import DatabaseManager
from src.config.settings import get_settings
db = DatabaseManager(get_settings().database_url)
db.drop_all_tables()
db.create_tables()
print('✅ Database recreated')
"

# Перезапуск системи
docker-compose up -d --build
```

### setup-from-backup:
```bash
echo "=== Setup from Backup ==="

# Показати доступні backup
echo "Available backups:"
ls -la backups/

echo "Введіть назву backup файлу для відновлення:"
read backup_file

if [ -f "backups/$backup_file" ]; then
    tar -xzf "backups/$backup_file" -C ./
    echo "✅ Backup відновлено"
    
    # Перезапуск з відновленими даними
    docker-compose up -d --build
else
    echo "❌ Backup файл не знайдено"
fi
```

## Перевірка конфігурації

**Користувач:**
```
validate-config
```

**Claude Code:**
```bash
echo "=== Configuration Validation ==="

# Перевірка .env файлу
echo "1. Environment variables:"
if [ -f .env ]; then
    echo "✅ .env exists"
    
    # Перевірка критичних змінних
    source .env
    [ -n "$TELEGRAM_BOT_TOKEN" ] && echo "✅ TELEGRAM_BOT_TOKEN set" || echo "❌ TELEGRAM_BOT_TOKEN missing"
    [ -n "$ALLOWED_USERS" ] && echo "✅ ALLOWED_USERS set" || echo "❌ ALLOWED_USERS missing"
else
    echo "❌ .env file missing"
fi

# Перевірка директорій
echo "2. Directories:"
for dir in data target_project logs; do
    [ -d "$dir" ] && echo "✅ $dir exists" || echo "❌ $dir missing"
done

# Перевірка Poetry
echo "3. Python environment:"
poetry check && echo "✅ Poetry config valid" || echo "❌ Poetry config invalid"

# Перевірка Docker
echo "4. Docker setup:"
docker-compose config && echo "✅ Docker compose valid" || echo "❌ Docker compose invalid"

# Перевірка Claude CLI
echo "5. Claude CLI:"
claude auth status && echo "✅ Claude authenticated" || echo "❌ Claude not authenticated"
```

## Автоматичне налаштування

**Користувач:**
```
auto-setup
```

**Claude Code виконує повністю автоматичне налаштування з мінімальним втручанням користувача:**

```bash
#!/bin/bash
echo "=== Automatic Environment Setup ==="

# Перевірка що все необхідне встановлено
command -v python3 >/dev/null || { echo "Python 3 required"; exit 1; }
command -v docker >/dev/null || { echo "Docker required"; exit 1; }

# Встановлення Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Встановлення залежностей
poetry install

# Створення базових директорій
mkdir -p {data,target_project,logs,backups}

# Створення шаблону .env
cat > .env.template << 'EOF'
# Скопіюйте цей файл в .env та заповніть значення
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
ALLOWED_USERS=your_telegram_user_id
DEBUG=false
LOG_LEVEL=INFO
USE_SDK=false
APPROVED_DIRECTORY=/app/target_project
TARGET_PROJECT_PATH=/app/target_project
CLAUDE_AVAILABILITY_MONITOR=true
EOF

echo "✅ Automatic setup completed"
echo "Скопіюйте .env.template в .env та заповніть токени"
echo "Потім запустіть: docker-compose up -d --build"
```

## Коли використовувати
- При первинному розгортанні проекту
- На новому сервері або локальній машині
- Після критичного збою системи
- При оновленні середовища розробки
- Для стандартизації налаштувань в команді
- При міграції на новий хост

## Перевірка готовності
- ✅ Poetry встановлено та налаштовано
- ✅ Всі залежності встановлені
- ✅ .env файл створено та валідний
- ✅ База даних ініціалізована
- ✅ Docker контейнер запускається
- ✅ Telegram Bot підключається
- ✅ Claude CLI авторизований