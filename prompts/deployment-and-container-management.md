# Промпт: Деплой та управління контейнерами

## Опис процесу
Цей промпт автоматизує процес деплою, перезапуску, моніторингу та управління Docker контейнерами проекту Claude Telegram Bot.

## Діалог з Claude Code

**Користувач:**
```
deploy
```

**Claude Code відповідає:**
Я виконаю повний цикл деплою проекту. Процес включає:

1. Перевірка готовності до деплою
2. Збірка та запуск контейнера
3. Перевірка здоров'я системи
4. Моніторинг логів
5. Валідація функціональності

Почнемо деплой:

*Виконує послідовність команд:*

```bash
# 1. Перевірка конфігурації та .env файлу
ls -la .env docker-compose.yml

# 2. Перевірка наявності критичних директорій
mkdir -p data target_project

# 3. Зупинка старих контейнерів
docker-compose down

# 4. Очищення старих образів (опціонально)
docker system prune -f --volumes

# 5. Збірка та запуск
docker-compose up -d --build

# 6. Перевірка статусу контейнера
docker-compose ps

# 7. Перевірка логів запуску
docker-compose logs --tail=50 claude_bot

# 8. Перевірка здоров'я
docker inspect claude-code-bot --format='{{.State.Health.Status}}'
```

**Результат деплою:**
- ✅ Контейнер успішно запущено
- ✅ Health check пройдено
- ✅ Telegram Bot підключений
- ⚠️ [При наявності проблем] Потребує втручання

Чи хочете переглянути поточні логи або провести тестування функціональності?

## Варіанти управління контейнером

**Швидкий перезапуск без перезбірки:**
```
restart-bot
```

**Перегляд логів в режимі реального часу:**
```
logs-live
```

**Повна діагностика системи:**
```
health-check
```

**Очищення та повна перезбірка:**
```
rebuild-clean
```

**Backup даних перед деплоєм:**
```
backup-before-deploy
```

## Claude Code відповідає на варіанти:

### restart-bot:
```bash
# Швидкий перезапуск
docker-compose restart claude_bot

# Перевірка статусу
docker-compose ps claude_bot
docker-compose logs --tail=20 claude_bot
```

### logs-live:
```bash
# Логи в режимі реального часу з кольорами
docker-compose logs -f --tail=100 claude_bot

# Користувач може натиснути Ctrl+C для виходу
```

### health-check:
```bash
# Детальна діагностика
echo "=== Container Status ==="
docker-compose ps

echo "=== Health Status ==="  
docker inspect claude-code-bot --format='{{.State.Health}}'

echo "=== Resource Usage ==="
docker stats claude-code-bot --no-stream

echo "=== Network Connectivity ==="
docker exec claude-code-bot ping -c 3 google.com

echo "=== Bot Authentication ==="
docker exec claude-code-bot claude auth status
```

### rebuild-clean:
```bash
# Повне очищення та перезбірка
docker-compose down -v --remove-orphans
docker system prune -a -f --volumes
docker-compose up -d --build --force-recreate
```

### backup-before-deploy:
```bash
# Backup даних та конфігурації
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cp -r data backups/$(date +%Y%m%d_%H%M%S)/
cp .env backups/$(date +%Y%m%d_%H%M%S)/
tar -czf backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz backups/$(date +%Y%m%d_%H%M%S)/

echo "Backup створено: backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
```

## Діагностика проблем

**Користувач:**
```
diagnose-bot
```

**Claude Code виконує повну діагностику:**
```bash
echo "=== Telegram Bot Status ==="
docker exec claude-code-bot python -c "
import requests
import os
token = os.getenv('TELEGRAM_BOT_TOKEN')
if token:
    resp = requests.get(f'https://api.telegram.org/bot{token}/getMe')
    print(f'Bot API Response: {resp.status_code}')
    if resp.status_code == 200:
        print(f'Bot Info: {resp.json()}')
    else:
        print(f'Error: {resp.text}')
else:
    print('TELEGRAM_BOT_TOKEN not found')
"

echo "=== Claude CLI Status ==="
docker exec claude-code-bot claude --version
docker exec claude-code-bot claude auth status

echo "=== Application Logs ==="
docker-compose logs --tail=50 claude_bot | grep -E "(ERROR|CRITICAL|Exception)"

echo "=== System Resources ==="
docker exec claude-code-bot df -h
docker exec claude-code-bot free -m
```

## Моніторинг продуктивності

**Користувач:**
```
monitor-performance
```

**Claude Code:**
```bash
# Моніторинг в режимі реального часу
echo "Моніторинг продуктивності (Ctrl+C для виходу):"

while true; do
    clear
    echo "=== $(date) ==="
    echo
    
    echo "Container Stats:"
    docker stats claude-code-bot --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    
    echo
    echo "Active Connections:"
    docker exec claude-code-bot netstat -tn 2>/dev/null | wc -l
    
    echo
    echo "Recent Errors:"
    docker-compose logs --since=1m claude_bot 2>/dev/null | grep -i error | tail -3
    
    sleep 5
done
```

## Коли використовувати
- При первинному деплої проекту
- Після внесення змін в код
- При проблемах з роботою бота
- Для регулярного оновлення в продакшені
- При зміні конфігурації або змінних середовища
- Для профілактичного перезапуску системи

## Безпечні практики
- Завжди створює backup перед важливими операціями
- Перевіряє конфігурацію перед деплоєм
- Моніторить логи після запуску
- Валідує доступність всіх сервісів
- Зберігає історію деплоїв в логах Docker