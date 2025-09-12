#!/bin/bash
# 🚀 Claude Telegram Bot - Quick Deploy Script
# Використовується готовий образ з Docker Hub: kroschu/claude-code-telegram:latest

set -e

echo "🚀 Claude Telegram Bot - Quick Deploy"
echo "======================================"

# Перевірка чи є Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не встановлений! Встановіть Docker та Docker Compose."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не встановлений! Встановіть Docker Compose."
    exit 1
fi

# Створити директорії
mkdir -p data target_project

# Створити docker-compose.yml з готовим образом
cat > docker-compose.yml << 'EOF'
services:
  claude_bot:
    image: kroschu/claude-code-telegram:latest
    container_name: claude-code-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./target_project:/app/target_project
    working_dir: /app
    user: "1000:1000"
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0) if __import__('src.main') else sys.exit(1)"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  data:
EOF

# Створити .env файл якщо не існує
if [ ! -f .env ]; then
    echo "📝 Створення .env файлу..."
    cat > .env << 'EOF'
# ===== ОБОВ'ЯЗКОВІ НАЛАШТУВАННЯ =====
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_BOT_USERNAME=YOUR_BOT_USERNAME

# ===== CLAUDE CLI НАЛАШТУВАННЯ =====
USE_SDK=false
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# ===== БЕЗПЕКА =====
ALLOWED_USERS=YOUR_TELEGRAM_USER_ID
APPROVED_DIRECTORY=/app/target_project

# ===== МОНІТОРИНГ ДОСТУПНОСТІ =====
CLAUDE_AVAILABILITY_MONITOR=true
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=YOUR_TELEGRAM_USER_ID
CLAUDE_AVAILABILITY_CHECK_INTERVAL=60
CLAUDE_AVAILABILITY_DND_START=23:00
CLAUDE_AVAILABILITY_DND_END=08:00
CLAUDE_AVAILABILITY_DEBOUNCE_OK_COUNT=2

# ===== ЛОГУВАННЯ =====
DEBUG=false
LOG_LEVEL=INFO
EOF
    
    echo "⚠️  ВАЖЛИВО: Відредагуйте файл .env з вашими налаштуваннями:"
    echo "   - TELEGRAM_BOT_TOKEN (від @BotFather)"
    echo "   - TELEGRAM_BOT_USERNAME (ім'я бота без @)"
    echo "   - ALLOWED_USERS (ваш Telegram User ID від @userinfobot)"
    echo ""
    echo "Після редагування .env запустіть скрипт знову."
    exit 0
fi

# Перевірка налаштувань
if grep -q "YOUR_BOT_TOKEN_HERE" .env; then
    echo "❌ Будь ласка, відредагуйте .env файл з вашими налаштуваннями!"
    exit 1
fi

echo "📦 Завантаження останнього образу..."
docker-compose pull

echo "🚀 Запуск бота..."
docker-compose up -d

echo "✅ Бот запущений!"
echo ""
echo "📋 Корисні команди:"
echo "   docker-compose logs -f claude_bot    # Дивитися логи"
echo "   docker-compose restart claude_bot    # Перезапустити"
echo "   docker-compose down                  # Зупинити"
echo "   docker-compose up -d --pull         # Оновити образ"
echo ""
echo "🎯 Бот готовий до роботи в Telegram!"