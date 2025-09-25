#!/bin/bash

# Claude Bot Auto-Restart Script
# This script automatically restarts the bot when it exits

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Claude Bot with auto-restart capability..."

while true; do
    echo "$(date): Starting bot..."

    # Run the bot with poetry
    export PATH="$HOME/.local/bin:$PATH"
    poetry run python -m src.main --debug

    EXIT_CODE=$?
    echo "$(date): Bot exited with code $EXIT_CODE"

    # Check if it was a normal restart request (exit code 0 or 144)
    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 144 ]; then
        echo "$(date): Bot requested restart. Restarting in 2 seconds..."
        sleep 2
    else
        echo "$(date): Bot crashed (exit code $EXIT_CODE). Restarting in 5 seconds..."
        sleep 5
    fi
done