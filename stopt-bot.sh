#!/bin/bash

# Bot restart script with duplicate cleanup
echo "🔄 Restarting Claude Code Telegram Bot..."

# Kill all bot processes
echo "🛑 Stopping all bot processes..."
pkill -f "python.*src\.main" 2>/dev/null || true

# Remove lock files
echo "🗑️ Cleaning up lock files..."
rm -f /tmp/claude_bot.lock

# Wait for processes to fully stop
echo "⏳ Waiting for processes to stop..."
sleep 3

# Verify no processes are running
RUNNING_PROCS=$(ps aux | grep -v grep | grep "python.*src\.main" | wc -l)
if [ $RUNNING_PROCS -gt 0 ]; then
    echo "⚠️ Force killing remaining processes..."
    pkill -9 -f "python.*src\.main" 2>/dev/null || true
    sleep 2
fi

