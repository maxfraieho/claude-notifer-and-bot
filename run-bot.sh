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
