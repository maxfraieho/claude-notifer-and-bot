#!/bin/bash

# 📊 Системний статус після оптимізації

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}📊 СТАТУС ОПТИМІЗОВАНОЇ СИСТЕМИ${NC}"
echo "════════════════════════════════════════"
echo "Час: $(date)"
echo ""

echo -e "${YELLOW}💾 Пам'ять та SWAP:${NC}"
free -h
echo ""

echo -e "${YELLOW}🗜️ ZSWAP (стиснення RAM):${NC}"
echo "Статус: $(cat /sys/module/zswap/parameters/enabled)"
echo "Компресор: $(cat /sys/module/zswap/parameters/compressor)"
echo "Макс. пул: $(cat /sys/module/zswap/parameters/max_pool_percent)%"
echo "Zpool: $(cat /sys/module/zswap/parameters/zpool)"

# Додаткові статистики ZSWAP якщо доступні
if [ -d "/sys/kernel/debug/zswap" ]; then
    echo "Збережено сторінок: $(cat /sys/kernel/debug/zswap/stored_pages 2>/dev/null || echo "N/A")"
    echo "Розмір пулу: $(cat /sys/kernel/debug/zswap/pool_total_size 2>/dev/null || echo "N/A") bytes"
fi
echo ""

echo -e "${YELLOW}⚡ CPU та енергія:${NC}"
echo "Load Average: $(cat /proc/loadavg | cut -d' ' -f1-3)"
echo "CPU Governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
echo "CPU Частота: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null | awk '{print $1/1000 " MHz"}' || echo "N/A")"
echo ""

echo -e "${YELLOW}🔧 VM параметри:${NC}"
echo "Swappiness: $(cat /proc/sys/vm/swappiness)"
echo "VFS cache pressure: $(cat /proc/sys/vm/vfs_cache_pressure)"
echo "Dirty ratio: $(cat /proc/sys/vm/dirty_ratio)"
echo ""

echo -e "${YELLOW}🤖 Bot та venv:${NC}"
if [ -d "/tmp/claude-bot-simple" ]; then
    echo "Venv: ✅ /tmp/claude-bot-simple"
else
    echo "Venv: ❌ не знайдено"
fi

if pgrep -f "src.main" >/dev/null; then
    bot_pid=$(pgrep -f "src.main")
    echo "Bot: ✅ Running (PID: $bot_pid)"
    echo "Bot RAM: $(ps -o rss= -p $bot_pid | awk '{print $1/1024 " MB"}' 2>/dev/null || echo "N/A")"
    echo "Bot CPU: $(ps -o %cpu= -p $bot_pid 2>/dev/null || echo "N/A")%"
else
    echo "Bot: ❌ Not running"
fi
echo ""

echo -e "${BLUE}💡 Статистика економії:${NC}"
total_ram=$(free -m | grep Mem | awk '{print $2}')
free_ram=$(free -m | grep Mem | awk '{print $7}')
ram_usage=$(( (total_ram - free_ram) * 100 / total_ram ))

echo "Використання RAM: ${ram_usage}%"
echo "ZSWAP активний: $([ "$(cat /sys/module/zswap/parameters/enabled)" = "Y" ] && echo "Так" || echo "Ні")"
echo "Режим CPU: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"

if [ "$ram_usage" -lt 60 ]; then
    echo -e "${GREEN}✅ Відмінне використання пам'яті${NC}"
elif [ "$ram_usage" -lt 80 ]; then
    echo -e "${YELLOW}⚠️ Помірне використання пам'яті${NC}"
else
    echo -e "${RED}🔥 Високе використання пам'яті${NC}"
fi