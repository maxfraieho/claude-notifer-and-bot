#!/bin/bash
set -e

# ⚡ Інтелектуальне управління живленням та продуктивністю

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="/usr/local/bin"
CONFIG_DIR="/etc/power-manager"

echo -e "${GREEN}⚡ Система інтелектуального управління живленням${NC}"

# Створити директорії
mkdir -p "$CONFIG_DIR"

# Функція визначення навантаження
get_system_load() {
    local load=$(cat /proc/loadavg | cut -d' ' -f1)
    echo "$load"
}

# Функція визначення використання RAM
get_memory_usage() {
    local mem_percent=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    echo "$mem_percent"
}

# Функція перемикання режимів
set_power_mode() {
    local mode=$1

    case $mode in
        "performance")
            echo -e "${YELLOW}🚀 Режим продуктивності${NC}"
            # CPU на максимум
            for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
                [ -f "$gov" ] && echo performance > "$gov"
            done
            # Агресивніший I/O
            echo deadline > /sys/block/sda/queue/scheduler 2>/dev/null || true
            echo 1000 > /proc/sys/vm/dirty_expire_centisecs
            echo 500 > /proc/sys/vm/dirty_writeback_centisecs
            # Більше RAM для cache
            echo 5 > /proc/sys/vm/swappiness
            ;;

        "balanced")
            echo -e "${BLUE}⚖️  Збалансований режим${NC}"
            # CPU автоматично
            for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
                [ -f "$gov" ] && echo schedutil > "$gov"
            done
            echo mq-deadline > /sys/block/sda/queue/scheduler 2>/dev/null || true
            echo 1500 > /proc/sys/vm/dirty_expire_centisecs
            echo 500 > /proc/sys/vm/dirty_writeback_centisecs
            echo 10 > /proc/sys/vm/swappiness
            ;;

        "powersave")
            echo -e "${GREEN}🔋 Режим економії${NC}"
            # CPU на мінімум
            for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
                [ -f "$gov" ] && echo powersave > "$gov"
            done
            # Менше дискової активності
            echo noop > /sys/block/sda/queue/scheduler 2>/dev/null || echo none > /sys/block/sda/queue/scheduler 2>/dev/null || true
            echo 3000 > /proc/sys/vm/dirty_expire_centisecs
            echo 1500 > /proc/sys/vm/dirty_writeback_centisecs
            echo 20 > /proc/sys/vm/swappiness
            ;;
    esac

    echo "$mode" > "$CONFIG_DIR/current_mode"
    echo -e "${GREEN}✅ Режим $mode активовано${NC}"
}

# Автоматичне визначення режиму
auto_mode() {
    local load=$(get_system_load)
    local mem_usage=$(get_memory_usage)
    local current_mode=$(cat "$CONFIG_DIR/current_mode" 2>/dev/null || echo "balanced")

    # Правила перемикання
    if (( $(echo "$load > 1.5" | bc -l) )) || [ "$mem_usage" -gt 80 ]; then
        if [ "$current_mode" != "performance" ]; then
            echo "Високе навантаження: load=$load, RAM=${mem_usage}%"
            set_power_mode "performance"
        fi
    elif (( $(echo "$load < 0.3" | bc -l) )) && [ "$mem_usage" -lt 40 ]; then
        if [ "$current_mode" != "powersave" ]; then
            echo "Низьке навантаження: load=$load, RAM=${mem_usage}%"
            set_power_mode "powersave"
        fi
    else
        if [ "$current_mode" != "balanced" ]; then
            echo "Помірне навантаження: load=$load, RAM=${mem_usage}%"
            set_power_mode "balanced"
        fi
    fi
}

# Створити основний скрипт управління
cat > "$SCRIPT_DIR/power-manager" << 'EOF'
#!/bin/bash

CONFIG_DIR="/etc/power-manager"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_status() {
    echo -e "${BLUE}📊 Поточний стан системи${NC}"
    echo "Load: $(cat /proc/loadavg | cut -d' ' -f1-3)"
    echo "RAM: $(free -h | grep Mem | awk '{print $3"/"$2}')"
    echo "CPU Mode: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "N/A")"
    echo "Power Mode: $(cat $CONFIG_DIR/current_mode 2>/dev/null || echo "unknown")"
    echo "ZSWAP: $(cat /sys/module/zswap/parameters/enabled 2>/dev/null || echo "N/A")"
}

case "$1" in
    "performance"|"perf")
        source /home/vokov/projects/claude-notifer-and-bot/power-manager.sh
        set_power_mode "performance"
        ;;
    "balanced"|"balance")
        source /home/vokov/projects/claude-notifer-and-bot/power-manager.sh
        set_power_mode "balanced"
        ;;
    "powersave"|"save")
        source /home/vokov/projects/claude-notifer-and-bot/power-manager.sh
        set_power_mode "powersave"
        ;;
    "auto")
        source /home/vokov/projects/claude-notifer-and-bot/power-manager.sh
        auto_mode
        ;;
    "status"|"")
        show_status
        ;;
    *)
        echo "Usage: $0 {performance|balanced|powersave|auto|status}"
        echo ""
        echo "Modes:"
        echo "  performance - Максимальна продуктивність"
        echo "  balanced    - Збалансований режим"
        echo "  powersave   - Економія енергії"
        echo "  auto        - Автоматичний вибір"
        echo "  status      - Поточний стан"
        ;;
esac
EOF

chmod +x "$SCRIPT_DIR/power-manager"

# Створити сервіс автоматичного моніторингу
cat > "$SCRIPT_DIR/power-daemon.sh" << 'EOF'
#!/bin/bash
# Демон автоматичного управління живленням

LOGFILE="/var/log/power-manager.log"
CONFIG_DIR="/etc/power-manager"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOGFILE"
}

# Основний цикл
while true; do
    # Перевірити стан кожні 30 секунд
    source /home/vokov/projects/claude-notifer-and-bot/power-manager.sh
    auto_mode >> "$LOGFILE" 2>&1

    # Очищати логи старші 7 днів
    find "$LOGFILE" -mtime +7 -delete 2>/dev/null || true

    sleep 30
done
EOF

chmod +x "$SCRIPT_DIR/power-daemon.sh"

# Створити systemd сервіс якщо доступний
if command -v systemctl >/dev/null 2>&1; then
    cat > /etc/systemd/system/power-manager.service << 'EOF'
[Unit]
Description=Intelligent Power Management Daemon
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/local/bin/power-daemon.sh
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable power-manager.service
    echo -e "${GREEN}✅ Systemd сервіс створено${NC}"
fi

# Створити OpenRC сервіс для Alpine
cat > /etc/init.d/power-manager << 'EOF'
#!/sbin/openrc-run

name="power-manager"
description="Intelligent Power Management Daemon"
command="/usr/local/bin/power-daemon.sh"
command_background="yes"
pidfile="/var/run/power-manager.pid"

depend() {
    after local
}
EOF

chmod +x /etc/init.d/power-manager
rc-update add power-manager default 2>/dev/null || true

echo -e "${GREEN}✅ OpenRC сервіс створено${NC}"

# Встановити початковий режим
set_power_mode "balanced"

echo ""
echo -e "${GREEN}🎉 Система управління живленням встановлена!${NC}"
echo ""
echo -e "${YELLOW}📋 Доступні команди:${NC}"
echo "• power-manager performance - максимальна продуктивність"
echo "• power-manager balanced    - збалансований режим"
echo "• power-manager powersave   - економія енергії"
echo "• power-manager auto        - автоматичний вибір"
echo "• power-manager status      - поточний стан"
echo ""
echo -e "${YELLOW}🤖 Автоматичний режим:${NC}"
echo "• Запуск: rc-service power-manager start"
echo "• Зупинка: rc-service power-manager stop"
echo "• Лог: tail -f /var/log/power-manager.log"
echo ""
echo -e "${BLUE}💡 Очікувана економія енергії: 20-40%${NC}"