#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get the directory where this script is located (project root)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}🚀 Запуск бота з додатковою пам'яттю для Claude CLI${NC}"
echo -e "${YELLOW}📂 Робоча директорія: $PROJECT_DIR${NC}"

# Очистити дублікати процесів
if pgrep -f "python -m src.main" > /dev/null; then
    echo -e "${YELLOW}⚠️ Зупиняємо існуючі процеси бота...${NC}"
    pkill -f "python -m src.main" || true
    sleep 2
fi

# Налаштування змінних середовища для більшої кількості пам'яті
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Node.js з додатковою пам'яттю для Claude CLI
export NODE_OPTIONS="--max-old-space-size=512 --max-semi-space-size=8"
export UV_THREADPOOL_SIZE=2
export NODE_ENV=production

# Обмеження Telegram bot
export TELEGRAM_MAX_CONNECTIONS=2

echo -e "${BLUE}💾 NODE_OPTIONS: $NODE_OPTIONS${NC}"
echo -e "${BLUE}📊 Показати статистику пам'яті:${NC}"
free -h

cd "$PROJECT_DIR"

echo -e "${GREEN}✅ Запуск бота з додатковою пам'яттю...${NC}"

# Перевірити чи є poetry
if command -v poetry >/dev/null 2>&1; then
    echo -e "${BLUE}📦 Використовуємо Poetry...${NC}"
    poetry run python -m src.main --debug "$@"
else
    echo -e "${BLUE}🐍 Використовуємо системний Python...${NC}"
    python -m src.main --debug "$@"
fi