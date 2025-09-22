#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

VENV_PATH="/tmp/claude-bot-simple"
PROJECT_DIR="/home/vokov/projects/claude-notifer-and-bot"

echo -e "${GREEN}🧠 Запуск бота з оптимізацією пам'яті${NC}"

# Звільнити пам'ять
echo -e "${YELLOW}🧹 Звільнення пам'яті...${NC}"
sync
sudo sysctl -w vm.drop_caches=1 >/dev/null 2>&1 || true

# Активувати venv
source "$VENV_PATH/bin/activate"

# Максимальні обмеження пам'яті
ulimit -v 262144      # 256MB віртуальної пам'яті
ulimit -m 262144      # 256MB фізичної пам'яті
ulimit -u 15          # 15 процесів
ulimit -f 131072      # 128MB файли

# Python оптимізації
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONOPTIMIZE=2
export PYTHONHASHSEED=0

# Node.js оптимізації для Claude CLI
export NODE_OPTIONS="--max-old-space-size=96 --max-semi-space-size=1"
export V8_HEAP_SPACE_STATS=0
export UV_THREADPOOL_SIZE=1

echo -e "${YELLOW}📊 Пам'ять перед запуском:${NC}"
free -m

cd "$PROJECT_DIR"

echo -e "${GREEN}✅ Запуск бота з жорсткими обмеженнями...${NC}"

# Запуск з timeout та catch OOM
timeout 3600 python -m src.main --debug "$@" || {
    echo -e "${RED}❌ Бот завершився (можливо через пам'ять)${NC}"
    echo "Спробуйте перезапустити або збільшити swap"
    exit 1
}
