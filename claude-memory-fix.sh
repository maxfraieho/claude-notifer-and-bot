#!/bin/bash
set -e

# 🧠 Фікс пам'яті для Claude CLI на слабких системах

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🧠 Claude CLI Memory Fix для 1.5GB RAM системи${NC}"

# 1. Звільнити максимум пам'яті
echo -e "${YELLOW}🧹 Звільнення пам'яті...${NC}"

# Очистити кеші
sudo sysctl -w vm.drop_caches=3
sync

# Зменшити swap використання до мінімуму
sudo sysctl -w vm.swappiness=5

# Агресивніше звільнення пам'яті
sudo sysctl -w vm.vfs_cache_pressure=200

# 2. Оптимізувати Node.js для малої пам'яті
echo -e "${YELLOW}⚙️ Налаштування Node.js...${NC}"

# Експорт змінних для Node.js
export NODE_OPTIONS="--max-old-space-size=128 --max-semi-space-size=2"
export V8_HEAP_SPACE_STATS=0
export UV_THREADPOOL_SIZE=2

# 3. Налаштувати Claude CLI
echo -e "${YELLOW}🔧 Налаштування Claude CLI...${NC}"

# Створити wrapper для claude
cat > /usr/local/bin/claude-low-memory << 'EOF'
#!/bin/bash

# Налаштування для малої пам'яті
export NODE_OPTIONS="--max-old-space-size=128 --max-semi-space-size=2"
export V8_HEAP_SPACE_STATS=0
export UV_THREADPOOL_SIZE=2

# Запуск claude з обмеженнями
exec timeout 300 claude "$@"
EOF

chmod +x /usr/local/bin/claude-low-memory

# 4. Створити оптимізований скрипт запуску бота
cat > run-memory-optimized.sh << 'EOF'
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
EOF

chmod +x run-memory-optimized.sh

# 5. Додатковий swap якщо потрібно
if [ $(free -m | grep Swap | awk '{print $2}') -lt 2048 ]; then
    echo -e "${YELLOW}💾 Створення додаткового swap файлу...${NC}"

    # Створити 1GB swap файл
    sudo fallocate -l 1G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile

    # Додати до fstab
    if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
    fi

    echo -e "${GREEN}✅ Додано 1GB swap${NC}"
fi

# 6. Показати результат
echo ""
echo -e "${GREEN}🎉 Memory Fix завершено!${NC}"
echo ""
echo -e "${YELLOW}📋 Нові команди:${NC}"
echo "• ./run-memory-optimized.sh - запуск з оптимізацією пам'яті"
echo "• claude-low-memory - Claude CLI з обмеженнями"
echo ""
echo -e "${YELLOW}📊 Поточний стан пам'яті:${NC}"
free -h
echo ""
echo -e "${YELLOW}💾 Swap:${NC}"
cat /proc/swaps

echo ""
echo -e "${GREEN}🚀 Тепер спробуйте: ./run-memory-optimized.sh${NC}"