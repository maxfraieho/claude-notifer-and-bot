#!/bin/bash

# Universal Bot Restart Script
# Kills all existing instances, cleans up sessions, and starts fresh
# Can be used from console or Telegram restart command

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔄 Universal Bot Restart Script"
echo "==============================="

# Function to kill processes safely
kill_processes() {
    local pattern="$1"
    local description="$2"

    echo "🔍 Looking for $description..."

    # Find processes matching pattern
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)

    if [ -n "$pids" ]; then
        echo "📋 Found PIDs: $pids"

        # Try graceful shutdown first
        echo "⏹️  Attempting graceful shutdown..."
        echo "$pids" | xargs -r kill -TERM 2>/dev/null || true

        # Wait longer for graceful shutdown
        echo "⏳ Waiting for graceful shutdown..."
        sleep 5

        # Check if any processes are still running
        local remaining=$(pgrep -f "$pattern" 2>/dev/null || true)
        if [ -n "$remaining" ]; then
            echo "💀 Force killing remaining processes: $remaining"
            echo "$remaining" | xargs -r kill -9 2>/dev/null || true
            sleep 1
        fi

        echo "✅ Cleaned up $description"
    else
        echo "✅ No $description processes found"
    fi
}

# Function to cleanup background bash sessions (except current)
cleanup_background_sessions() {
    echo "🧹 Cleaning up background bash sessions..."

    # Get current session info
    local current_session="${BASH_SUBSHELL:-$$}"

    # Kill background Python processes
    kill_processes "python.*src\.main" "Python bot processes"

    # Kill poetry processes that might be hanging
    kill_processes "poetry run python" "Poetry Python processes"

    # Kill any hanging bash processes from previous bot runs
    # Be careful not to kill our current session
    local bash_pids=$(pgrep -f "bash.*poetry\|bash.*src\.main" 2>/dev/null | grep -v "^$$\$" || true)
    if [ -n "$bash_pids" ]; then
        echo "🔄 Cleaning up hanging bash processes: $bash_pids"
        echo "$bash_pids" | xargs -r kill -9 2>/dev/null || true
    fi

    echo "✅ Background sessions cleaned"
}

# Function to verify no bot processes are running
verify_cleanup() {
    echo "🔍 Verifying cleanup..."

    local remaining=$(pgrep -f "python.*src\.main" 2>/dev/null || true)
    if [ -n "$remaining" ]; then
        echo "❌ Warning: Some processes still running: $remaining"
        echo "🔨 Force killing..."
        echo "$remaining" | xargs -r kill -9 2>/dev/null || true
        sleep 1
    fi

    remaining=$(pgrep -f "python.*src\.main" 2>/dev/null || true)
    if [ -n "$remaining" ]; then
        echo "❌ Failed to clean up all processes. Manual intervention required."
        echo "Run: sudo kill -9 $remaining"
        exit 1
    fi

    echo "✅ All bot processes stopped"
}

# Function to clear temporary files
cleanup_temp_files() {
    echo "🗑️  Cleaning temporary files..."

    # Remove any existing restart info files
    rm -f /tmp/claude_bot_restart_info.json || true

    # Clean up any other bot-related temp files
    rm -f /tmp/claude_bot_*.tmp || true
    rm -f /tmp/bot_*.log || true

    echo "✅ Temporary files cleaned"
}

# Function to start bot with memory optimization
start_bot() {
    echo "🚀 Starting bot with memory optimization..."
    echo "📁 Working directory: $PWD"

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
    echo "🔄 Starting bot..."

    # Run with poetry in optimized mode in background
    nohup poetry run python -O -m src.main --debug > /tmp/claude_bot.log 2>&1 &
    local bot_pid=$!

    echo "🤖 Bot started with PID: $bot_pid"
    echo "📋 Log file: /tmp/claude_bot.log"

    # Wait a moment to check if bot started successfully
    sleep 3
    if kill -0 "$bot_pid" 2>/dev/null; then
        echo "✅ Bot is running successfully"
        echo "📝 Use 'tail -f /tmp/claude_bot.log' to see logs"
        echo "🛑 Use 'kill $bot_pid' to stop the bot"
    else
        echo "❌ Bot failed to start"
        return 1
    fi
}

# Main execution flow
main() {
    echo "$(date): Starting bot restart procedure..."

    # Step 1: Kill all existing bot processes
    kill_processes "python.*src\.main" "bot processes"

    # Step 2: Clean up background sessions
    cleanup_background_sessions

    # Step 3: Verify cleanup
    verify_cleanup

    # Step 4: Clean temporary files
    cleanup_temp_files

    # Step 5: Wait a moment for system cleanup
    echo "⏳ Waiting for system cleanup..."
    sleep 3

    # Step 6: Final verification before starting
    echo "🔍 Final verification before starting..."
    local final_check=$(pgrep -f "python.*src\.main" 2>/dev/null || true)
    if [ -n "$final_check" ]; then
        echo "❌ Critical: Bot processes still running: $final_check"
        echo "🔨 Emergency cleanup..."
        echo "$final_check" | xargs -r kill -9 2>/dev/null || true
        sleep 2
    fi

    # Step 7: Start the bot
    start_bot

    # If we get here, the bot has exited
    echo ""
    echo "🏁 Bot process completed"
    echo "$(date): Bot restart script finished"
}

# Handle script termination
cleanup_on_exit() {
    echo ""
    echo "🛑 Script interrupted"
    kill_processes "python.*src\.main" "bot processes" >/dev/null 2>&1 || true
    exit 1
}

trap cleanup_on_exit SIGINT SIGTERM

# Check if running as root (in container)
if [ "$(id -u)" = "0" ]; then
    echo "⚠️  Running as root - this is normal in containers"
fi

# Run main function
main