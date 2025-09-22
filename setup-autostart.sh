#!/bin/bash
set -e

# 🔄 Налаштування автозапуску оптимізацій

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔄 Налаштування автозапуску оптимізацій${NC}"

# Перевірка прав
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Потрібні права root${NC}"
    exit 1
fi

# 1. Створити скрипт автозапуску оптимізацій
echo -e "${YELLOW}📝 Створення /etc/local.d/optimize.start...${NC}"

cat > /etc/local.d/optimize.start << 'EOF'
#!/bin/bash
# Автозапуск системних оптимізацій

# Логування
exec >> /var/log/boot-optimization.log 2>&1

echo "$(date): Starting system optimizations..."

# Дати системі час завантажитися
sleep 5

# ZSWAP налаштування
echo 1 > /sys/module/zswap/parameters/enabled
echo lz4 > /sys/module/zswap/parameters/compressor
echo 40 > /sys/module/zswap/parameters/max_pool_percent
echo z3fold > /sys/module/zswap/parameters/zpool 2>/dev/null || echo zbud > /sys/module/zswap/parameters/zpool

# VM параметри
sysctl -w vm.swappiness=10
sysctl -w vm.vfs_cache_pressure=50
sysctl -w vm.dirty_background_ratio=5
sysctl -w vm.dirty_ratio=10

# CPU governor
echo powersave > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || true
echo powersave > /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor 2>/dev/null || true

# Створити tmpfs для bot
mkdir -p /tmp/claude-bot
mount -t tmpfs -o size=100M,nodev,nosuid,noexec tmpfs /tmp/claude-bot 2>/dev/null || true

echo "$(date): System optimizations applied successfully"
EOF

chmod +x /etc/local.d/optimize.start

# 2. Створити постійні sysctl налаштування
echo -e "${YELLOW}📝 Створення /etc/sysctl.d/99-optimize.conf...${NC}"

cat > /etc/sysctl.d/99-optimize.conf << 'EOF'
# Системні оптимізації для економії енергії
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_background_ratio = 5
vm.dirty_ratio = 10
vm.dirty_expire_centisecs = 1500
vm.dirty_writeback_centisecs = 500

# Мережеві оптимізації
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.core.netdev_max_backlog = 1000
EOF

# 3. Налаштувати kernel boot параметри для ZSWAP
echo -e "${YELLOW}⚙️ Налаштування kernel parameters...${NC}"

if [ -f "/etc/update-extlinux.conf" ]; then
    # Резервна копія
    cp /etc/update-extlinux.conf /etc/update-extlinux.conf.backup

    # Додати ZSWAP параметри якщо їх ще немає
    if ! grep -q "zswap.enabled=1" /etc/update-extlinux.conf; then
        sed -i 's/default_kernel_opts="/&zswap.enabled=1 zswap.compressor=lz4 zswap.max_pool_percent=40 zswap.zpool=z3fold /' /etc/update-extlinux.conf
        update-extlinux
        echo -e "${GREEN}✅ Kernel parameters оновлено${NC}"
    else
        echo -e "${YELLOW}⚠️ Kernel parameters вже налаштовані${NC}"
    fi
fi

# 4. Створити сервіс моніторингу (якщо потрібно)
echo -e "${YELLOW}🔍 Створення сервісу моніторингу...${NC}"

cat > /etc/init.d/system-monitor << 'EOF'
#!/sbin/openrc-run

name="system-monitor"
description="System optimization monitor"
command="/usr/local/bin/system-monitor-daemon"
command_background="yes"
pidfile="/var/run/system-monitor.pid"

depend() {
    after local
}
EOF

# Створити daemon скрипт
cat > /usr/local/bin/system-monitor-daemon << 'EOF'
#!/bin/bash
# Daemon для моніторингу системи

while true; do
    # Логувати стан кожні 5 хвилин
    echo "$(date): $(free -h | grep Mem | awk '{print "RAM: "$3"/"$2}')" >> /var/log/system-monitor.log

    # Очищати старі логи (старші 7 днів)
    find /var/log/system-monitor.log -mtime +7 -delete 2>/dev/null || true

    sleep 300  # 5 хвилин
done
EOF

chmod +x /etc/init.d/system-monitor
chmod +x /usr/local/bin/system-monitor-daemon

# 5. Створити швидкі команди
echo -e "${YELLOW}📋 Створення швидких команд...${NC}"

cat > /usr/local/bin/opt-status << 'EOF'
#!/bin/bash
# Швидка перевірка статусу оптимізацій
/home/vokov/projects/claude-notifer-and-bot/system-status.sh
EOF

cat > /usr/local/bin/opt-restart << 'EOF'
#!/bin/bash
# Повторне застосування оптимізацій
echo "🔄 Застосування оптимізацій..."
/etc/local.d/optimize.start
echo "✅ Готово!"
EOF

chmod +x /usr/local/bin/opt-status
chmod +x /usr/local/bin/opt-restart

# 6. Налаштувати логування
echo -e "${YELLOW}📝 Налаштування логування...${NC}"
touch /var/log/boot-optimization.log
touch /var/log/system-monitor.log
chmod 644 /var/log/boot-optimization.log
chmod 644 /var/log/system-monitor.log

echo ""
echo -e "${GREEN}🎉 Автозапуск налаштовано!${NC}"
echo ""
echo -e "${YELLOW}📋 Створені файли:${NC}"
echo "• /etc/local.d/optimize.start - автозапуск оптимізацій"
echo "• /etc/sysctl.d/99-optimize.conf - постійні параметри"
echo "• /usr/local/bin/opt-status - швидка перевірка"
echo "• /usr/local/bin/opt-restart - повторне застосування"
echo ""
echo -e "${YELLOW}📋 Команди:${NC}"
echo "• opt-status - статус оптимізацій"
echo "• opt-restart - застосувати оптимізації"
echo "• tail -f /var/log/boot-optimization.log - лог автозапуску"
echo ""
echo -e "${GREEN}🔄 Оптимізації будуть застосовуватися автоматично при завантаженні${NC}"

# Застосувати оптимізації зараз
echo -e "${YELLOW}🚀 Застосування оптимізацій зараз...${NC}"
/etc/local.d/optimize.start

echo -e "${GREEN}✅ Все готово!${NC}"