#!/bin/bash
set -e

# Швидкий запуск для розробки з базовою ізоляцією

WORK_DIR="/home/vokov/projects/claude-notifer-and-bot"
VENV_PATH="/tmp/claude-bot-secure/claude-venv"

echo "🚀 Quick secure development start..."

# Перевірити чи існує secure venv
if [ ! -d "$VENV_PATH" ]; then
    echo "⚠️  Secure venv not found. Run ./setup-secure-venv.sh first"
    exit 1
fi

# Активувати venv
source "$VENV_PATH/bin/activate"

# Базові обмеження безпеки
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Обмежити ресурси для розробки
ulimit -f 524288     # 512MB файли
ulimit -v 524288     # 512MB RAM
ulimit -u 30         # 30 процесів

# Перевірити .env
if [ ! -f "$WORK_DIR/.env" ]; then
    echo "❌ .env file missing. Create it first:"
    echo "cp .env.example .env"
    exit 1
fi

cd "$WORK_DIR"

# Швидка перевірка Claude auth
if ! claude auth status >/dev/null 2>&1; then
    echo "⚠️  Claude not authenticated. Run: claude auth login"
fi

echo "✅ Starting bot in secure development mode..."
exec python -m src.main --debug "$@"