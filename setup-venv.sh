#!/bin/bash
set -e

echo "🚀 Setting up Virtual Environment for Claude Code Telegram Bot"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on the correct directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: pyproject.toml not found. Run this script from the project root directory.${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Checking system requirements...${NC}"

# Check Python version
python_version=$(python3 --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}❌ Python 3.11+ required. Found: $python_version${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python $python_version found${NC}"

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}📦 Installing Poetry...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

echo -e "${GREEN}✅ Poetry available${NC}"

# Check Node.js for Claude CLI
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js required for Claude CLI. Please install Node.js 18+${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Node.js $(node --version) found${NC}"

# Create virtual environment and install dependencies
echo -e "${YELLOW}🔧 Creating virtual environment...${NC}"
poetry install --with dev

# Install Claude CLI if not present
if ! command -v claude &> /dev/null; then
    echo -e "${YELLOW}📥 Installing Claude CLI...${NC}"
    npm install -g @anthropic-ai/claude-code
fi

echo -e "${GREEN}✅ Claude CLI available${NC}"

# Check Claude authentication
echo -e "${YELLOW}🔐 Checking Claude CLI authentication...${NC}"
if claude auth status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Claude CLI authentication found${NC}"
else
    echo -e "${YELLOW}⚠️  Claude CLI authentication required. Run: claude auth login${NC}"
fi

# Create necessary directories
mkdir -p data
mkdir -p target_project

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}📋 Created .env from .env.example. Please configure it.${NC}"
    else
        echo -e "${YELLOW}📋 Creating sample .env file...${NC}"
        cat > .env << 'EOF'
# Required settings
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
APPROVED_DIRECTORY=/home/vokov/claude-notifer-and-bot/target_project

# Security (choose one or both)
ALLOWED_USERS=123456789,987654321  # Telegram user IDs
ENABLE_TOKEN_AUTH=false
AUTH_TOKEN_SECRET=your_secret_here

# Claude settings (prefer CLI over SDK)
USE_SDK=false
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Monitoring
CLAUDE_AVAILABILITY_MONITOR=true
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=your_chat_id
CLAUDE_AVAILABILITY_CHECK_INTERVAL=60

# Target project
TARGET_PROJECT_PATH=/home/vokov/claude-notifer-and-bot/target_project
EOF
        echo -e "${YELLOW}📋 Created sample .env file. Please configure it before running.${NC}"
    fi
fi

# Create run script
echo -e "${YELLOW}📝 Creating run scripts...${NC}"

cat > run-bot.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting Claude Code Telegram Bot (venv mode)..."

# Activate virtual environment
source $(poetry env info --path)/bin/activate

# Check environment
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it first."
    exit 1
fi

# Check Claude authentication
if ! claude auth status > /dev/null 2>&1; then
    echo "⚠️  Claude CLI authentication required. Run: claude auth login"
    exit 1
fi

echo "✅ Environment ready. Starting bot..."

# Run the bot
exec python -m src.main "$@"
EOF

cat > run-dev.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting Claude Code Telegram Bot (development mode)..."

# Activate virtual environment
source $(poetry env info --path)/bin/activate

# Run with debug logging
exec python -m src.main --debug "$@"
EOF

cat > run-tests.sh << 'EOF'
#!/bin/bash
set -e

echo "🧪 Running tests..."

# Activate virtual environment
source $(poetry env info --path)/bin/activate

# Run tests
poetry run pytest "$@"
EOF

cat > run-lint.sh << 'EOF'
#!/bin/bash
set -e

echo "🔍 Running code quality checks..."

# Activate virtual environment
source $(poetry env info --path)/bin/activate

echo "📝 Formatting code with black..."
poetry run black src/

echo "📝 Sorting imports with isort..."
poetry run isort src/

echo "🔍 Linting with flake8..."
poetry run flake8 src/

echo "🔍 Type checking with mypy..."
poetry run mypy src/

echo "✅ All checks passed!"
EOF

# Make scripts executable
chmod +x run-bot.sh run-dev.sh run-tests.sh run-lint.sh

echo -e "${GREEN}✅ Virtual environment setup complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Configure .env file with your bot token and settings"
echo "2. Ensure Claude CLI is authenticated: claude auth login"
echo "3. Run the bot: ./run-bot.sh"
echo ""
echo -e "${YELLOW}📋 Available scripts:${NC}"
echo "• ./run-bot.sh      - Start the bot"
echo "• ./run-dev.sh      - Start with debug logging"
echo "• ./run-tests.sh    - Run tests"
echo "• ./run-lint.sh     - Run code quality checks"
echo ""
echo -e "${YELLOW}📋 Development workflow:${NC}"
echo "• poetry shell      - Activate virtual environment"
echo "• poetry add <pkg>  - Add dependencies"
echo "• poetry install    - Install dependencies"
echo ""
echo -e "${GREEN}🎉 Ready for faster development without Docker rebuilds!${NC}"