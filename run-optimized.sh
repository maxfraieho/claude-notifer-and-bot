#!/bin/bash
set -e

# 🚀 Оптимізований запуск Claude Bot

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

VENV_PATH="/tmp/claude-bot-simple"
PROJECT_DIR="/home/vokov/projects/claude-notifer-and-bot"

echo -e "${GREEN}🚀 Запуск оптимізованого Claude Bot${NC}"

# Перевірити venv
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Virtual environment не знайдено в $VENV_PATH${NC}"
    echo "Запустіть спочатку встановлення залежностей."
    exit 1
fi

# Активувати venv
source "$VENV_PATH/bin/activate"

# Перевірити .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  .env файл не знайдено. Створюю з прикладу...${NC}"
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo -e "${YELLOW}📝 Відредагуйте .env файл перед запуском${NC}"
        exit 1
    fi
fi

# Застосувати ресурсні обмеження
echo -e "${YELLOW}🔒 Застосування ресурсних обмежень...${NC}"
ulimit -f 524288     # 512MB файли
ulimit -v 524288     # 512MB RAM
ulimit -u 30         # 30 процесів

# Встановити змінні середовища для оптимізації
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONOPTIMIZE=1
export NODE_OPTIONS="--max-old-space-size=256"

# Перевірити Claude CLI
if ! command -v claude >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Claude CLI не знайдено. Спробую встановити...${NC}"
    npm install -g @anthropic-ai/claude-code 2>/dev/null || {
        echo -e "${RED}❌ Не вдалося встановити Claude CLI${NC}"
        echo "Встановіть вручну: npm install -g @anthropic-ai/claude-code"
    }
fi

# Перевірити Claude auth
if ! claude auth status >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Claude CLI не авторизований${NC}"
    echo "Запустіть: claude auth login"
fi

# Показати статус системи
echo -e "${YELLOW}📊 Статус системи:${NC}"
echo "RAM: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "ZSWAP: $(cat /sys/module/zswap/parameters/enabled)"
echo "CPU Governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
echo "Load: $(cat /proc/loadavg | cut -d' ' -f1-3)"
echo ""

cd "$PROJECT_DIR"

echo -e "${GREEN}✅ Запуск бота...${NC}"

# Запустити з відловлюванням помилок
exec python -m src.main --debug "$@"