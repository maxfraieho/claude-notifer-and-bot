# Server Deployment Fix Commands

## Вирішення проблем на сервері

### 1. Очистка конфліктуючих Docker мереж:

```bash
# Зупинити всі контейнери
docker stop $(docker ps -aq) 2>/dev/null || true

# Видалити конфліктуючі мережі
docker network rm claude-notifer-and-bot_default 2>/dev/null || true
docker network rm claude-bot_default 2>/dev/null || true

# Очистити невикористовувані мережі
docker network prune -f
```

### 2. Скопіювати оновлений docker-compose.remote.yml на сервер:

```bash
# На локальній машині - скопіювати файл на сервер
scp docker-compose.remote.yml vokov@x86-64-srv:~/claude-bot/
```

### 3. Запустити бот з новою конфігурацією:

```bash
# На сервері
cd ~/claude-bot

# Переконатися що .env файл існує
ls -la .env

# Створити потрібні директорії
mkdir -p data target_project
chmod 755 data target_project

# Запустити з оновленим файлом
docker compose -f docker-compose.remote.yml up -d

# Перевірити статус
docker compose -f docker-compose.remote.yml ps
docker compose -f docker-compose.remote.yml logs -f
```

### 4. Альтернативний спосіб - використати просту конфігурацію:

Якщо проблема з мережею продовжується, можна використати спрощений docker-compose без custom network:

```yaml
services:
  claude_bot:
    image: kroschu/claude-notifer-chat-amd64:latest
    container_name: claude-code-bot-prod
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./target_project:/app/target_project
      - ~/.claude:/home/claudebot/.claude:ro
    user: "1001:1001"
    environment:
      - PYTHONUNBUFFERED=1
      - TZ=Europe/Kiev
```