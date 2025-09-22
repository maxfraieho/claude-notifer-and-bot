#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

VENV_PATH="/tmp/claude-bot-simple"
PROJECT_DIR="/home/vokov/projects/claude-notifer-and-bot"

echo -e "${GREEN}🔥 Запуск бота з екстремальною оптимізацією пам'яті${NC}"

# Перевірити, чи не запущений вже бот
if pgrep -f "python -m src.main" > /dev/null; then
    PID=$(pgrep -f "python -m src.main")
    echo "❌ Bot already running with PID $PID"
    echo "Stop the existing instance first or wait for it to finish."
    exit 1
fi

# Звільнити максимум пам'яті
echo -e "${YELLOW}🧹 Агресивне звільнення пам'яті...${NC}"
sync
sudo sysctl -w vm.drop_caches=3 >/dev/null 2>&1 || true
sudo sysctl -w vm.swappiness=1 >/dev/null 2>&1 || true
sudo sysctl -w vm.vfs_cache_pressure=500 >/dev/null 2>&1 || true

# Активувати venv
source "$VENV_PATH/bin/activate"

# М'які обмеження пам'яті (без ulimit - дозволяємо Node.js запуститись)
# ulimit блокує Claude CLI навіть з мінімальними налаштуваннями
# Покладаємося тільки на NODE_OPTIONS для обмеження пам'яті

# Python мікро оптимізації
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONOPTIMIZE=2
export PYTHONHASHSEED=0
export MALLOC_TRIM_THRESHOLD_=10000

# Node.js мінімальні робочі налаштування для Claude CLI
export NODE_OPTIONS="--max-old-space-size=128 --max-semi-space-size=2"
export V8_HEAP_SPACE_STATS=0
export UV_THREADPOOL_SIZE=1

echo -e "${YELLOW}📊 Пам'ять перед запуском:${NC}"
free -m

cd "$PROJECT_DIR"

echo -e "${GREEN}✅ Запуск бота з екстремальними обмеженнями...${NC}"

# Запуск з timeout та catch OOM
timeout 3600 python -m src.main --debug "$@" || {
    echo -e "${RED}❌ Бот завершився (можливо через пам'ять)${NC}"
    echo "Спробуйте перезапустити або збільшити swap"
    exit 1
}