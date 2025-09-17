#!/bin/bash
set -e

echo "🚀 Starting Claude Code Telegram Bot (development mode)..."

# Activate virtual environment
source $(poetry env info --path)/bin/activate

# Run with debug logging
exec python -m src.main --debug "$@"
