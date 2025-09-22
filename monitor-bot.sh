#!/bin/bash

# Моніторинг роботи бота в реальному часі

echo "🔍 Monitoring Claude Bot Security..."

# Показати активні процеси Python
echo "=== Python Processes ==="
ps aux | grep python | grep -v grep

echo ""
echo "=== Network Connections ==="
ss -tuln | grep python || echo "No python network connections"

echo ""
echo "=== File Descriptors ==="
lsof -c python 2>/dev/null | head -20 || echo "lsof not available"

echo ""
echo "=== Memory Usage ==="
ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem | grep python | head -5

echo ""
echo "=== Resource Limits ==="
if pgrep -f "src.main" >/dev/null; then
    BOT_PID=$(pgrep -f "src.main")
    echo "Bot PID: $BOT_PID"
    cat /proc/$BOT_PID/limits 2>/dev/null || echo "Cannot read limits"
fi

# Continuous monitoring
if [ "$1" = "--watch" ]; then
    echo ""
    echo "🔄 Watching (Ctrl+C to stop)..."
    while true; do
        clear
        bash "$0"
        sleep 5
    done
fi