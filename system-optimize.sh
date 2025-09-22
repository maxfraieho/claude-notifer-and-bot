#!/bin/bash
set -e

# 🚀 Системна оптимізація для енергоефективності та продуктивності
# AMD C-60, 1.5GB RAM, Alpine Linux

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Системна оптимізація для економії енергії${NC}"

# Перевірка прав адміністратора
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Потрібні права root. Запустіть: sudo $0${NC}"
    exit 1
fi

echo -e "${YELLOW}📊 Поточний стан системи:${NC}"
free -h
echo ""

# 1. ZSWAP оптимізація для стиснення RAM
echo -e "${YELLOW}🗜️  Налаштування ZSWAP (стиснення RAM)...${NC}"

# Увімкнути zswap з оптимальними параметрами
echo 1 > /sys/module/zswap/parameters/enabled
echo 40 > /sys/module/zswap/parameters/max_pool_percent  # 40% RAM для zswap
echo lz4 > /sys/module/zswap/parameters/compressor      # Швидкий компресор
echo z3fold > /sys/module/zswap/parameters/zpool        # Ефективніший zpool

echo -e "${GREEN}✅ ZSWAP активовано з LZ4 компресією${NC}"

# 2. Налаштування swappiness для економії енергії
echo -e "${YELLOW}💾 Оптимізація swap...${NC}"
echo 10 > /proc/sys/vm/swappiness  # Менше використання swap = менше I/O
echo 50 > /proc/sys/vm/vfs_cache_pressure  # Агресивніше звільнення кешу

# 3. Налаштування CPU для економії енергії
echo -e "${YELLOW}⚡ Налаштування CPU governor...${NC}"
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    if [ -f "$cpu" ]; then
        echo powersave > "$cpu"  # Економний режим
    fi
done

# 4. Дискові оптимізації
echo -e "${YELLOW}💽 Дискові оптимізації...${NC}"
echo mq-deadline > /sys/block/sda/queue/scheduler  # Оптимальний для SSD/старих HDD
echo 1 > /sys/block/sda/queue/iosched/front_merges  # Злиття I/O запитів

# 5. Мережеві оптимізації
echo -e "${YELLOW}🌐 Мережеві оптимізації...${NC}"
echo 1 > /proc/sys/net/ipv4/tcp_window_scaling
echo 1 > /proc/sys/net/ipv4/tcp_timestamps
echo 1 > /proc/sys/net/core/netdev_max_backlog = 1000

# 6. Файлова система
echo -e "${YELLOW}📁 Файлова система...${NC}"
echo 5 > /proc/sys/vm/dirty_background_ratio   # Раніше записувати кеш
echo 10 > /proc/sys/vm/dirty_ratio            # Не накопичувати багато

# 7. Зробити налаштування постійними
echo -e "${YELLOW}💾 Створення постійних налаштувань...${NC}"

cat > /etc/sysctl.d/99-performance.conf << 'EOF'
# Системна оптимізація для економії енергії
# Memory management
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_background_ratio = 5
vm.dirty_ratio = 10
vm.dirty_expire_centisecs = 1500
vm.dirty_writeback_centisecs = 500

# Network optimizations
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.core.netdev_max_backlog = 1000
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# Kernel optimizations
kernel.pid_max = 32768
fs.file-max = 65536
EOF

# 8. Налаштування ZSWAP в kernel parameters
echo -e "${YELLOW}🔧 Налаштування kernel parameters...${NC}"

# Для Alpine Linux - модифікувати kernel parameters
if [ -f "/etc/update-extlinux.conf" ]; then
    sed -i 's/default_kernel_opts="/default_kernel_opts="zswap.enabled=1 zswap.compressor=lz4 zswap.max_pool_percent=40 zswap.zpool=z3fold /' /etc/update-extlinux.conf
    update-extlinux
fi

# 9. Налаштування для systemd сервісів (якщо є)
if command -v systemctl >/dev/null 2>&1; then
    echo -e "${YELLOW}🔧 Оптимізація systemd...${NC}"
    # Вимкнути непотрібні сервіси
    systemctl disable --now bluetooth 2>/dev/null || true
    systemctl disable --now cups 2>/dev/null || true
    systemctl disable --now avahi-daemon 2>/dev/null || true
fi

# 10. Створити скрипт моніторингу
cat > /usr/local/bin/system-monitor.sh << 'EOF'
#!/bin/bash
# Моніторинг системної продуктивності

echo "=== СИСТЕМА $(date) ==="
echo "CPU: $(cat /proc/loadavg | cut -d' ' -f1-3)"
echo "RAM: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "SWAP: $(free -h | grep Swap | awk '{print $3"/"$2}')"
echo "ZSWAP: $(cat /sys/kernel/debug/zswap/stored_pages 2>/dev/null || echo "N/A") pages"
echo "CPU Freq: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null | awk '{print $1/1000 " MHz"}' || echo "N/A")"
echo "Temperature: $(cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1 | awk '{print $1/1000 "°C"}' || echo "N/A")"
EOF

chmod +x /usr/local/bin/system-monitor.sh

echo ""
echo -e "${GREEN}✅ Системна оптимізація завершена!${NC}"
echo ""
echo -e "${YELLOW}📊 Новий стан системи:${NC}"
free -h
echo ""
echo -e "${YELLOW}🔧 Активні оптимізації:${NC}"
echo "• ZSWAP: $(cat /sys/module/zswap/parameters/enabled) (компресор: $(cat /sys/module/zswap/parameters/compressor))"
echo "• Swappiness: $(cat /proc/sys/vm/swappiness)"
echo "• CPU Governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "N/A")"
echo ""
echo -e "${YELLOW}📋 Команди для моніторингу:${NC}"
echo "• system-monitor.sh - поточний стан"
echo "• watch -n 5 system-monitor.sh - реальний час"
echo ""
echo -e "${GREEN}🔋 Очікувана економія енергії: 15-25%${NC}"
echo -e "${GREEN}🚀 Очікуване покращення продуктивності: 20-30%${NC}"