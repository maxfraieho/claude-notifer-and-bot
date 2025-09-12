# 🚀 Quick Start - Claude Telegram Bot

## 🎯 Варіант 1: Швидкий запуск з готовим образом (РЕКОМЕНДОВАНО)

### Одна команда:

```bash
curl -sSL https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/deploy.sh | bash
```

Або скачати та запустити:

```bash
wget https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/deploy.sh
chmod +x deploy.sh
./deploy.sh
```

**Готовий образ з Docker Hub:** `kroschu/claude-code-telegram:latest`

---

## 🔨 Варіант 2: Збірка з вихідного коду

### 1. Копіювання Claude CLI аутентифікації

**Важливо!** Спочатку скопіюйте вашу Claude CLI аутентифікацію:

```bash
# Копіювати вашу ~/.claude директорію в проект
cp -r ~/.claude ./.claude

# Перевірити що файли скопіювались
ls -la .claude/
```

### 2. Налаштування `.env` файлу

```bash
cp .env.example .env
```

Відредагуйте `.env` файл:

```bash
# ===== ОБОВ'ЯЗКОВО =====
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here     # Токен від @BotFather
TELEGRAM_BOT_USERNAME=your_bot_username           # Ім'я бота без @

# ===== CLAUDE CLI =====
USE_SDK=false                                     # Тільки Claude CLI!
CLAUDE_MODEL=claude-3-5-sonnet-20241022          # Модель Claude

# ===== БЕЗПЕКА =====
ALLOWED_USERS=123456789,987654321                # ID користувачів Telegram
APPROVED_DIRECTORY=/app/target_project            # Дозволена директорія
```

### 3. Запуск

```bash
docker-compose up -d --build
```

---

## 📋 Що потрібно:

1. **Налаштований Claude CLI** на хості (`claude auth status` має показувати успіх) - тільки для збірки з коду
2. **Telegram Bot Token** - отримати від [@BotFather](https://t.me/BotFather)
3. **Telegram User ID** - отримати від [@userinfobot](https://t.me/userinfobot)

## 🔄 Оновлення аутентифікації в готовому образі

**Готовий образ має вбудовану аутентифікацію і працює одразу!** 

Якщо потрібно оновити (через місяць), перезберіть образ локально:

```bash
# 1. Клонувати репозиторій
git clone https://github.com/maxfraieho/claude-notifer-and-bot.git
cd claude-notifer-and-bot

# 2. Скопіювати вашу аутентифікацію
cp -r ~/.claude ./.claude

# 3. Зібрати локально
docker-compose build --no-cache
```

## 📂 Цільова директорія

Бот працює з проектами в директорії `./target_project/` на хості.

## 🚨 Помилки?

```bash
# Перезапуск
docker-compose restart claude_bot

# Подивитися логи
docker-compose logs -f claude_bot

# Повна перезбірка (для локальних змін)
docker-compose down
docker-compose up -d --build --force-recreate
```

## ⚠️ Важливо

- **Ніяких API ключів не потрібно!**
- **Готовий образ:** містить всю аутентифікацію та працює одразу
- **Docker Hub:** `kroschu/claude-code-telegram:latest`