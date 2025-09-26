#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

VENV_PATH="/tmp/claude-bot-simple"
# Get the directory where this script is located (project root)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}🔥 Запуск бота з екстремальною оптимізацією пам'яті${NC}"
echo -e "${YELLOW}📂 Робоча директорія: $PROJECT_DIR${NC}"

# Функція для очищення дублікатів процесів
cleanup_duplicates() {
    echo -e "${BLUE}🧹 Очищення дублікатів процесів...${NC}"

    # Знайти всі процеси бота та залишити тільки один
    PIDS=$(pgrep -f "python -m src.main" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "Знайдені процеси бота: $PIDS"
        # Вбити всі процеси
        for pid in $PIDS; do
            echo "Зупиняємо процес: $pid"
            kill -TERM "$pid" 2>/dev/null || true
        done
        sleep 2
        # Примусово вбити якщо ще живі
        for pid in $PIDS; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "Примусово зупиняємо процес: $pid"
                kill -KILL "$pid" 2>/dev/null || true
            fi
        done
    fi

    # Очистити зомбі процеси
    ps aux | grep '[Zz]ombie' | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true

    echo -e "${GREEN}✅ Дублікати очищені${NC}"
}

# Очистити дублікати перед запуском
cleanup_duplicates

# Функція для агресивного очищення пам'яті та кешу
memory_cleanup() {
    echo -e "${YELLOW}🧹 Агресивне звільнення пам'яті та кешу...${NC}"

    # Синхронізація файлової системи
    sync

    # Очищення Python кешу
    echo -e "${BLUE}📦 Очищення Python кешу...${NC}"
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true

    # Очищення tmp файлів
    echo -e "${BLUE}🗑️ Очищення тимчасових файлів...${NC}"
    rm -rf /tmp/claude* 2>/dev/null || true
    rm -rf /tmp/python* 2>/dev/null || true
    rm -rf "$PROJECT_DIR"/.pytest_cache 2>/dev/null || true
    rm -rf "$PROJECT_DIR"/data/telegram_persistence.pickle.* 2>/dev/null || true

    # Очищення логів (залишаємо останні)
    find "$PROJECT_DIR" -name "*.log" -mtime +1 -delete 2>/dev/null || true
    find "$PROJECT_DIR" -name "*.log.*" -delete 2>/dev/null || true

    # Системні кеші
    echo -e "${BLUE}💾 Очищення системних кешів...${NC}"
    sudo sysctl -w vm.drop_caches=3 >/dev/null 2>&1 || true
    sudo sysctl -w vm.swappiness=1 >/dev/null 2>&1 || true
    sudo sysctl -w vm.vfs_cache_pressure=500 >/dev/null 2>&1 || true

    # Очищення пам'яті Node.js/npm кешу
    npm cache clean --force 2>/dev/null || true

    echo -e "${GREEN}✅ Очищення завершене${NC}"
}

# Виконати очищення пам'яті
memory_cleanup

# Перевірити та активувати venv (якщо існує)
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo -e "${BLUE}🐍 Активація virtual environment...${NC}"
    source "$VENV_PATH/bin/activate"
else
    echo -e "${YELLOW}⚠️ Virtual environment не знайдено, використовуємо системний Python${NC}"
    # Перевірити чи є poetry
    if command -v poetry >/dev/null 2>&1; then
        echo -e "${BLUE}📦 Використовуємо Poetry environment...${NC}"
        export PYTHON_BIN="poetry run python"
    else
        echo -e "${BLUE}🐍 Використовуємо системний Python...${NC}"
        export PYTHON_BIN="python"
    fi
fi

# М'які обмеження пам'яті (без ulimit - дозволяємо Node.js запуститись)
# ulimit блокує Claude CLI навіть з мінімальними налаштуваннями
# Покладаємося тільки на NODE_OPTIONS для обмеження пам'яті

# Функція для оптимізації змінних середовища
setup_environment() {
    echo -e "${BLUE}⚙️ Налаштування середовища для економії пам'яті...${NC}"

    # Python мікро оптимізації
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONUNBUFFERED=1
    export PYTHONOPTIMIZE=2
    export PYTHONHASHSEED=0
    export MALLOC_TRIM_THRESHOLD_=10000
    export PYTHONMALLOC=malloc

    # Обмеження на SQLite
    export SQLITE_MAX_MEMORY=32768  # 32MB max

    # Node.js налаштування для Claude CLI (збільшуємо пам'ять)
    export NODE_OPTIONS="--max-old-space-size=256 --max-semi-space-size=4"
    export V8_HEAP_SPACE_STATS=0
    export UV_THREADPOOL_SIZE=1
    export NODE_ENV=production

    # Обмеження Telegram bot
    export TELEGRAM_MAX_CONNECTIONS=1

    echo -e "${GREEN}✅ Середовище налаштовано${NC}"
}

# Функція для показу статистики пам'яті
show_memory_stats() {
    echo -e "${YELLOW}📊 Поточний стан пам'яті:${NC}"
    echo -e "${BLUE}💾 Системна пам'ять:${NC}"
    free -h | head -2

    echo -e "${BLUE}🔄 Swap використання:${NC}"
    swapon --show=NAME,SIZE,USED,PRIO,TYPE 2>/dev/null || echo "Swap не налаштований"

    echo -e "${BLUE}📁 Розмір проекту:${NC}"
    du -sh "$PROJECT_DIR" 2>/dev/null || echo "Неможливо визначити розмір"

    echo -e "${BLUE}🏃‍♂️ Активні Python процеси:${NC}"
    ps aux | grep python | grep -v grep | wc -l || echo "0"
}

# Налаштувати середовище
setup_environment

echo -e "${YELLOW}📊 Стан системи перед запуском:${NC}"
show_memory_stats

cd "$PROJECT_DIR"

echo -e "${GREEN}✅ Запуск бота з екстремальними обмеженнями...${NC}"

# Функція для моніторингу та автоматичного перезапуску
monitor_and_run() {
    local restart_count=0
    local max_restarts=3

    while [ $restart_count -lt $max_restarts ]; do
        echo -e "${GREEN}✅ Запуск бота (спроба $((restart_count + 1))/$max_restarts)...${NC}"

        # Перевірка пам'яті перед запуском
        available_mem=$(free -m | awk 'NR==2{printf "%.0f", $7}')
        if [ "$available_mem" -lt 100 ]; then
            echo -e "${YELLOW}⚠️ Мало доступної пам'яті: ${available_mem}MB${NC}"
            memory_cleanup
        fi

        # Запуск бота з моніторингом
        ${PYTHON_BIN:-python} -m src.main --debug "$@" &
        BOT_PID=$!

        # Чекати на завершення процесу
        wait $BOT_PID
        exit_code=$?

        echo -e "${RED}❌ Бот завершився з кодом: $exit_code${NC}"

        # Аналіз причини завершення
        if [ $exit_code -eq 137 ]; then
            echo -e "${RED}🔥 Процес вбито через нестачу пам'яті (OOM Killer)${NC}"
        elif [ $exit_code -eq 1 ]; then
            echo -e "${YELLOW}⚠️ Помилка конфігурації або залежностей${NC}"
        fi

        # Показати стан пам'яті після краху
        echo -e "${BLUE}📊 Стан системи після завершення:${NC}"
        show_memory_stats

        restart_count=$((restart_count + 1))

        if [ $restart_count -lt $max_restarts ]; then
            echo -e "${YELLOW}🔄 Перезапуск через 5 секунд...${NC}"
            sleep 5

            # Очищення перед перезапуском
            cleanup_duplicates
            memory_cleanup
        fi
    done

    echo -e "${RED}❌ Досягнуто максимальну кількість перезапусків ($max_restarts)${NC}"
    echo -e "${YELLOW}💡 Рекомендації:${NC}"
    echo "  - Збільште swap файл"
    echo "  - Закрийте інші програми"
    echo "  - Перевірте налаштування пам'яті"
    exit 1
}

# Запуск з моніторингом
monitor_and_run "$@"