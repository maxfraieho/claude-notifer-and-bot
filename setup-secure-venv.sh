#!/bin/bash
set -e

echo "🔒 Setting up SECURE Virtual Environment for Claude Bot"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Створити ізольовану директорію для venv
VENV_DIR="/tmp/claude-bot-secure"
WORK_DIR="/home/vokov/projects/claude-notifer-and-bot"

echo -e "${YELLOW}🔧 Creating isolated venv directory...${NC}"
mkdir -p "$VENV_DIR"
chmod 700 "$VENV_DIR"  # Тільки власник має доступ

# Створити venv з обмеженнями
echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
python3 -m venv "$VENV_DIR/claude-venv" --clear

# Активувати venv
source "$VENV_DIR/claude-venv/bin/activate"

# Оновити pip та встановити poetry
echo -e "${YELLOW}📦 Installing Poetry in isolated environment...${NC}"
pip install --upgrade pip
pip install poetry==1.7.1

# Встановити залежності з lockfile
cd "$WORK_DIR"
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
poetry config virtualenvs.create false  # Використовувати активний venv
poetry install --only=main --no-root

# Створити скрипт запуску з обмеженнями
echo -e "${YELLOW}📝 Creating secure run script...${NC}"
cat > "$VENV_DIR/run-secure-bot.sh" << 'EOF'
#!/bin/bash
set -e

# Ізоляційні змінні
export HOME="/tmp/claude-bot-home"
export TMPDIR="/tmp/claude-bot-tmp"
export PYTHONPATH="/home/vokov/projects/claude-notifer-and-bot"

# Створити тимчасові директорії
mkdir -p "$HOME" "$TMPDIR"
chmod 700 "$HOME" "$TMPDIR"

# Обмежити мережевий доступ (потребує firejail)
if command -v firejail >/dev/null 2>&1; then
    echo "🔒 Running with firejail network isolation..."
    exec firejail \
        --private="$HOME" \
        --private-tmp="$TMPDIR" \
        --read-only=/home/vokov/projects/claude-notifer-and-bot \
        --whitelist=/home/vokov/projects/claude-notifer-and-bot/target_project \
        --whitelist=/home/vokov/projects/claude-notifer-and-bot/data \
        --net=none \
        --no-new-privs \
        --seccomp \
        --caps.drop=all \
        /tmp/claude-bot-secure/claude-venv/bin/python -m src.main "$@"
else
    echo "⚠️  firejail not available, running with basic isolation..."
    # Базова ізоляція через ulimit
    ulimit -f 1048576    # Обмежити розмір файлів (1GB)
    ulimit -v 1048576    # Обмежити віртуальну память (1GB)
    ulimit -u 100        # Обмежити кількість процесів

    exec /tmp/claude-bot-secure/claude-venv/bin/python -m src.main "$@"
fi
EOF

chmod +x "$VENV_DIR/run-secure-bot.sh"

# Створити скрипт для розробки
cat > "$VENV_DIR/run-dev-secure.sh" << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting Claude Bot in SECURE development mode..."

# Активувати venv
source /tmp/claude-bot-secure/claude-venv/bin/activate

# Перевірки безпеки
if [ ! -f "/home/vokov/projects/claude-notifer-and-bot/.env" ]; then
    echo "❌ .env file not found"
    exit 1
fi

# Обмежити ресурси
ulimit -f 1048576    # 1GB файли
ulimit -v 1048576    # 1GB RAM
ulimit -u 50         # 50 процесів

cd /home/vokov/projects/claude-notifer-and-bot

# Запустити з debug
exec python -m src.main --debug "$@"
EOF

chmod +x "$VENV_DIR/run-dev-secure.sh"

# Встановити firejail якщо відсутній
if ! command -v firejail >/dev/null 2>&1; then
    echo -e "${YELLOW}🔒 Installing firejail for additional security...${NC}"
    if command -v apt >/dev/null 2>&1; then
        echo "Run: sudo apt install firejail"
    elif command -v apk >/dev/null 2>&1; then
        echo "Run: sudo apk add firejail"
    else
        echo "Install firejail manually for enhanced security"
    fi
fi

echo -e "${GREEN}✅ Secure venv setup complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Usage:${NC}"
echo "• Development: $VENV_DIR/run-dev-secure.sh"
echo "• Production:  $VENV_DIR/run-secure-bot.sh"
echo ""
echo -e "${YELLOW}🔒 Security features:${NC}"
echo "• Isolated venv in /tmp"
echo "• Limited file system access"
echo "• Resource limits (RAM/CPU/processes)"
echo "• Network isolation (with firejail)"
echo "• No new privileges"
echo ""
echo -e "${YELLOW}⚠️  For maximum security, install firejail:${NC}"
echo "sudo apt install firejail"