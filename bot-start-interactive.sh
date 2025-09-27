#!/bin/bash

# Interactive Bot Start Script
# Starts bot in foreground for debugging and development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔄 Interactive Bot Start"
echo "======================="

# Verify required files exist
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found. Are you in the correct directory?"
    exit 1
fi

if [ ! -f "src/main.py" ]; then
    echo "❌ src/main.py not found. Bot source not available."
    exit 1
fi

# Set environment for memory optimization
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export PATH="$HOME/.local/bin:$PATH"

# Memory optimization flags
export PYTHONMALLOC=malloc
export MALLOC_TRIM_THRESHOLD_=100000

echo "🔧 Environment configured for memory optimization"
echo "🔄 Starting bot in interactive mode..."
echo "🛑 Press Ctrl+C to stop"
echo ""

# Run with poetry in optimized mode (foreground)
exec poetry run python -O -m src.main --debug