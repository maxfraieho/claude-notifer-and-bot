# 📄 **README: Розгортання Claude Code Telegram Bot з моніторингом доступності**

Ця інструкція допоможе вам розгорнути Telegram-бота, який автоматично сповіщає про доступність Claude CLI у Telegram-чати.

---

## 🐳 **1. Dockerfile**

Створіть файл `Dockerfile` у корені проєкту:

```dockerfile
# Dockerfile

FROM python:3.11-slim AS builder

# Встановлюємо залежності ОС, включаючи nodejs/npm для claude CLI
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    gcc \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Створюємо нерутового користувача
RUN useradd -m -u 1001 -s /bin/bash claudebot

# Перемикаємося на користувача
USER claudebot
WORKDIR /home/claudebot

# Встановлюємо змінну HOME — критично для пошуку ~/.claude
ENV HOME=/home/claudebot

# Копіюємо файли залежностей
COPY --chown=claudebot:claudebot pyproject.toml poetry.lock ./

# Встановлюємо Poetry та залежності
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/home/claudebot/.local/bin:${PATH}"
RUN poetry config virtualenvs.create false && poetry install --only=main

# Встановлюємо Claude CLI глобально через npm
# (Використовує токен з ~/.claude, який монтується з хосту)
RUN npm install -g @anthropic-ai/claude-code

# Копіюємо решту коду
COPY --chown=claudebot:claudebot . .

# Точка входу
ENTRYPOINT ["python", "-m", "src.main"]
```

> **Примітка**: Якщо `poetry` не використовується, замініть відповідні рядки на `COPY requirements.txt .` та `RUN pip install -r requirements.txt`.

---

## 🐋 **2. docker-compose.yml**

Створіть файл `docker-compose.yml`:

```yaml
# docker-compose.yml

version: '3.8'

services:
  claude_bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: claude-code-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      # Монтуємо директорію з токеном автентифікації Claude CLI з хосту у контейнер
      - ~/.claude:/home/claudebot/.claude
    working_dir: /app
    user: "1001:1001"
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0) if __import__('src.main') else sys.exit(1)"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  data:
```

> **Для Windows користувачів**:  
> Замість `~/.claude` використовуйте `${USERPROFILE}/.claude` у `docker-compose.yml`.

---

## 🔐 **Автентифікація Claude CLI**

Для роботи Claude CLI всередині контейнера **необхідно виконати автентифікацію на хості**, а потім **монтувати директорію з токеном** у контейнер.

### Кроки:

#### 1. Встановіть Claude CLI на хості (якщо ще не встановлено)

```bash
npm install -g @anthropic-ai/claude-code
```

#### 2. Виконайте автентифікацію на хості

```bash
claude auth login
```

Вам буде запропоновано відкрити посилання у браузері та увійти через обліковий запис Anthropic.

#### 3. Переконайтеся, що токен збережено

Після входу, токен зберігається у:

- **Linux/macOS**: `~/.claude`
- **Windows**: `%USERPROFILE%\.claude`

#### 4. Монтування у контейнер

Директорія `~/.claude` монтується у контейнер у `docker-compose.yml`:

```yaml
volumes:
  - ~/.claude:/home/claudebot/.claude
```

> **Для Windows**: Замініть `~/.claude` на `${USERPROFILE}/.claude` у `docker-compose.yml`.

#### 5. Перезапустіть контейнер

```bash
docker-compose up -d --build
```

Тепер Claude CLI всередині контейнера використовує токен, отриманий на хості.

---

### 🔄 Як це працює?

- `claude auth login` на хості зберігає токен доступу у `~/.claude`.
- При монтуванні цієї директорії у контейнер, `claude` CLI всередині контейнера **бачить той самий токен**.
- Це дозволяє уникнути необхідності виконувати `auth login` всередині контейнера (що складно через відсутність браузера).
- Контейнер і хост **ділять один токен**, що спрощує управління.

---

### 🚨 **Troubleshooting: Токен протермінувався**

Якщо Claude CLI всередині контейнера починає повертати помилки типу `unauthorized` або `authentication failed`:

1. **Виконайте на хості**:
   ```bash
   claude auth login
   ```
2. Увійдіть через браузер.
3. **Перезапустіть контейнер**:
   ```bash
   docker-compose restart claude_bot
   ```

Новий токен автоматично буде доступний у контейнері через монтування.

---

## ⚙️ **3. .env файл (приклад)**

Створіть файл `.env` у корені проєкту:

```
# .env

# Обов'язково: токен вашого Telegram-бота
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here

# Увімкнення моніторингу доступності Claude CLI
CLAUDE_AVAILABILITY_MONITOR=true

# Список Telegram chat_id для сповіщень (через кому)
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=-1001234567890,123456789

# Інтервал перевірки (секунди)
CLAUDE_AVAILABILITY_CHECK_INTERVAL=60

# Вікно DND (не надсилати сповіщення з 23:00 до 08:00 за Києвом)
CLAUDE_AVAILABILITY_DND_START=23:00
CLAUDE_AVAILABILITY_DND_END=08:00

# Кількість послідовних успішних перевірок для підтвердження доступності
CLAUDE_AVAILABILITY_DEBOUNCE_OK_COUNT=2

# Додаткові налаштування (опціонально)
DEBUG=false
LOG_LEVEL=INFO
```

> 🔑 **Як отримати `TELEGRAM_BOT_TOKEN`?**  
> Створіть бота через [@BotFather](https://t.me/BotFather) у Telegram.

> 📌 **Як отримати `chat_id`?**  
> Надішліть повідомлення у чат → використайте бота [@userinfobot](https://t.me/userinfobot) або зробіть запит до `https://api.telegram.org/bot<TOKEN>/getUpdates`.

---

## 🚀 **4. Інструкція по розгортанню**

Виконайте наступні кроки у терміналі:

### Крок 1: Клонувати репозиторій (якщо ще не клоновано)

```
git clone https://github.com/your-username/claude-code-telegram-main.git
cd claude-code-telegram-main
```

### Крок 2: Створити `.env` файл

Скопіюйте вміст прикладу вище у файл `.env` та підставте свої значення, особливо `TELEGRAM_BOT_TOKEN` та `CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS`.

### Крок 3: Створити директорію для даних

```
mkdir -p data
```

Ця директорія буде містити файли стану:
- `./data/.claude_last_cmd.json` — поточний стан (available/unavailable)
- `./data/transitions.jsonl` — історія переходів станів

### Крок 4: Запустити контейнер

```
docker-compose up -d --build
```

### Крок 5: Перевірити логи

```
docker-compose logs -f claude_bot
```

Очікувані повідомлення у логах:
```
✅ Claude CLI monitoring enabled. Interval: 60s. Notification chats: [-1001234567890, 123456789]
✅ Моніторинг Claude CLI увімкнено.
🟢 Claude Code CLI Available
📅 `2025-04-05 09:15:33`
🖥️ `Linux x86_64`
⏱️  (перерва: 2год 45хв)
```

### Крок 6: Перевірити сповіщення у Telegram

Переконайтеся, що вказаний чат отримав повідомлення у форматі:

```
🟢 **Claude Code CLI Available**
📅 `2025-04-05 09:15:33`
🖥️ `Linux x86_64`
⏱️  (перерва: 2год 45хв)
```

---

## 🔄 **5. Оновлення бота**

Для оновлення коду бота:

```
git pull origin main
docker-compose up -d --build
```

Контейнер перезбереся та перезапуститься з новим кодом. Стан зберігається у `./data`, тому історія не втрачається.

---

## 🛠️ **6. Налаштування**

### Зміна чатів для сповіщень

Відредагуйте `.env`:

```
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=111111111,-1002222222222,333333333
```

Потім перезапустіть:

```
docker-compose up -d
```

### Зміна DND вікна

Відредагуйте `.env`:

```
CLAUDE_AVAILABILITY_DND_START=00:00
CLAUDE_AVAILABILITY_DND_END=07:00
```

Перезапустіть сервіс.

---

## 🚨 **7. Troubleshooting**

### ❌ Проблема: `Claude CLI not found` у логах

**Симптоми:**
```
Claude CLI недоступний: [Errno 2] No such file or directory: 'claude'
```

**Рішення:**

1. Переконайтеся, що `claude` встановлено у контейнері. Перевірте `Dockerfile` — має бути рядок:
   ```dockerfile
   RUN npm install -g @anthropic-ai/claude-code
   ```

2. Увійдіть у контейнер і перевірте вручну:
   ```bash
   docker-compose exec claude_bot bash
   which claude
   claude --version
   ```

3. Якщо `claude` не знайдено, оновіть `Dockerfile`, додавши встановлення `nodejs` та `npm`:

   ```dockerfile
   RUN apt-get update && apt-get install -y \
       curl \
       git \
       jq \
       gcc \
       nodejs \
       npm \
       && rm -rf /var/lib/apt/lists/*
   ```

### ❌ Проблема: Сповіщення не надходять

**Перевірте:**

1. Правильність `TELEGRAM_BOT_TOKEN`.
2. Чи додано бота до чатів, які вказані в `CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS`.
3. Чи має бот права на надсилання повідомлень у групах (для супергруп — додати як адміністратора).
4. Логи: `docker-compose logs -f claude_bot` — шукайте помилки надсилання.

### ❌ Проблема: Файли стану не створюються

**Перевірте права:**

```
ls -la ./data
```

Якщо директорія порожня або немає прав — виправте:

```
sudo chown -R 1001:1001 ./data
sudo chmod -R 755 ./data
```

---

## 📂 **8. Де шукати файли стану?**

Після запуску файли з'являться у:

- `./data/.claude_last_cmd.json` — останній стан та час перевірки.
- `./data/transitions.jsonl` — журнал усіх переходів (кожен рядок — окремий JSON).

Приклад запису в `transitions.jsonl`:
```
{"timestamp": "2025-04-05T09:15:33+03:00", "from": "unavailable", "to": "available", "duration_unavailable": 10000.5, "platform": "Linux x86_64"}
```

---

✅ **Готово!**  
Ваш бот розгорнуто, налаштовано та готовий до роботи. Він автоматично стежитиме за доступністю Claude CLI та надсилатиме сповіщення у Telegram з урахуванням DND.
```

```

## 🐳 **Розгортання (Linux/macOS)**

```bash
# 1. Клонувати репозиторій
git clone https://github.com/your-username/claude-code-telegram-main.git
cd claude-code-telegram-main

# 2. Встановити Claude CLI на хості
npm install -g @anthropic-ai/claude-code

# 3. Авторизуватися на хості
claude auth login
# → Відкрийте посилання у браузері та увійдіть

# 4. Створити .env та data
cp .env.example .env
mkdir -p data

# 5. Запустити
docker-compose up -d --build
```

---

## 🪟 **Розгортання (Windows PowerShell)**

```powershell
# 1. Клонувати репозиторій
git clone https://github.com/your-username/claude-code-telegram-main.git
cd claude-code-telegram-main

# 2. Встановити Claude CLI (через npm)
npm install -g @anthropic-ai/claude-code

# 3. Авторизуватися
claude auth login
# → Відкрийте посилання у браузері та увійдіть

# 4. Створити .env та data
Copy-Item .env.example .env
mkdir data

# 5. ВІДРЕДАГУЙТЕ docker-compose.yml: замініть ~/.claude на ${USERPROFILE}/.claude

# 6. Запустити
docker-compose up -d --build