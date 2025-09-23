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

# Start bot
echo "🚀 Starting bot..."

# Get the directory where this script is located (bot root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📂 Bot directory: $SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "/tmp/claude-bot-simple" ]; then
    echo "❌ Virtual environment not found at /tmp/claude-bot-simple! Run setup first."
    exit 1
fi

# Check if launch script exists
if [ ! -f "./run-ultra-low-memory.sh" ]; then
    echo "❌ Launch script not found! Expected: $SCRIPT_DIR/run-ultra-low-memory.sh"
    exit 1
fi

# Activate virtual environment and start bot using optimal script
echo "🔥 Using ultra-low-memory configuration..."
nohup ./run-ultra-low-memory.sh > /tmp/bot.log 2>&1 &

# Wait a moment and check if bot started successfully
sleep 3
NEW_PID=$(ps aux | grep -v grep | grep "python.*src\.main" | awk '{print $2}' | head -1)

if [ -n "$NEW_PID" ]; then
    echo "✅ Bot started successfully with PID: $NEW_PID"
    echo "📝 Logs available at: /tmp/bot.log"
    echo "📊 Check status with: ps aux | grep 'python.*src\.main'"
else
    echo "❌ Failed to start bot. Check logs:"
    tail -20 /tmp/bot.log
    exit 1
fi