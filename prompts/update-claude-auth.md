# Промпт: Оновлення Claude авторизації та перезбірка контейнера

## Опис процесу
Цей промпт автоматизує процес оновлення Claude CLI авторизації в Docker контейнері шляхом створення архіву з робочими налаштуваннями авторизації з хостової системи та їх передачі в контейнер.

## Діалог з Claude Code

**Користувач:**
```
auth-update
```

**Claude Code відповідає:**
Я виконаю оновлення Claude авторизації в Docker контейнері. Це включає:

1. Перевірка поточного стану авторизації
2. Створення архіву з налаштуваннями Claude з хосту  
3. Копіювання архіву в контейнер
4. Розархівування налаштувань
5. Перезбірка та перезапуск контейнера

Почнемо:

*Виконує послідовність команд:*

```bash
# 1. Перевірка поточної авторизації Claude CLI на хості
claude auth status

# 2. Створення архіву з налаштуваннями Claude (.claude директорія)
tar -czf claude-auth-latest.tar.gz -C /home/vokov .claude

# 3. Копіювання архіву в Docker контейнер
docker cp claude-auth-latest.tar.gz claude-code-bot:/tmp/claude-auth.tar.gz

# 4. Розархівування налаштувань в контейнері
docker exec claude-code-bot bash -c "cd /home/claudebot && tar -xzf /tmp/claude-auth.tar.gz"

# 5. Перевірка авторизації в контейнері
docker exec claude-code-bot bash -c "claude auth status"

# 6. Очищення тимчасового архіву
rm claude-auth-latest.tar.gz
docker exec claude-code-bot rm /tmp/claude-auth.tar.gz

# 7. Перезбірка та перезапуск контейнера
docker-compose down
docker-compose up -d --build
```

**Підтвердження успіху:**
```bash
# Перевірка що контейнер працює
docker-compose logs --tail=20 claude_bot

# Перевірка авторизації після перезапуску  
docker exec claude-code-bot bash -c "claude auth status"
```

Авторизація Claude CLI в контейнері успішно оновлена та контейнер перезапущено.

## Коли використовувати
- Коли Claude CLI в контейнері повідомляє про проблеми з авторизацією
- При отриманні помилок типу "Authentication required" з контейнера
- Після оновлення Claude CLI на хостовій системі
- При переході на нову версію Claude або зміні API токенів

## Примітки
- **ВАЖЛИВО:** Завжди використовувати тільки архівування .claude налаштувань
- НЕ використовувати SDK режим (USE_SDK=false в .env)
- Переконайтесь що Claude CLI авторизований на хості перед початком процесу
- Процес безпечно перезаписує існуючі налаштування в контейнері