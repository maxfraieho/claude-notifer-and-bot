# Код проєкту: claude-notifer-and-bot

**Згенеровано:** 2025-09-08 21:12:57
**Директорія:** `C:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot`

---

## Структура проєкту

```
├── data/
├── src/
│   ├── bot/
│   │   ├── features/
│   │   ├── handlers/
│   │   ├── middleware/
│   │   ├── utils/
│   │   ├── __init__.py
│   │   └── core.py
│   ├── claude/
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   ├── facade.py
│   │   ├── integration.py
│   │   ├── monitor.py
│   │   ├── parser.py
│   │   ├── sdk_integration.py
│   │   └── session.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── environments.py
│   │   ├── features.py
│   │   ├── loader.py
│   │   └── settings.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── audit.py
│   │   ├── auth.py
│   │   ├── rate_limiter.py
│   │   └── validators.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── facade.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── session_storage.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── constants.py
│   ├── __init__.py
│   ├── exceptions.py
│   └── main.py
├── Dockerfile
├── README.md
├── claude-notifer-and-bot.md
├── docker-compose.yml
├── poetry.lock
└── pyproject.toml
```

---

## Файли проєкту

### docker-compose.yml

**Розмір:** 894 байт

```yaml
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
      # Mount the Claude CLI authentication directory from the host
      # For Linux/macOS: ~/.claude
      # For Windows: ${USERPROFILE}/.claude
      - ~/.claude:/home/claudebot/.claude
      - ./target_project:/app/target_project  # ✅ New volume for target project
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

### README.md

**Розмір:** 23,630 байт

```text
# 📄 **README: Розгортання Claude Code Telegram Bot з моніторингом доступності**

Ця інструкція допоможе вам розгорнути Telegram-бота, який автоматично сповіщає про доступність Claude CLI у Telegram-чати.

---

## 🐳 **1. Dockerfile**

Створіть файл [Dockerfile](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\Dockerfile) у корені проєкту:

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

# ✅ Створюємо директорію для цільового проєкту та встановлюємо права
RUN mkdir -p /app/target_project && chown claudebot:claudebot /app/target_project

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

Створіть файл [docker-compose.yml](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\docker-compose.yml):

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
      - ./target_project:/app/target_project  # ✅ Новий том для цільового проєкту
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
> Замість `~/.claude` використовуйте `${USERPROFILE}/.claude` у [docker-compose.yml](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\docker-compose.yml).

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

Директорія `~/.claude` монтується у контейнер у [docker-compose.yml](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\docker-compose.yml):

```yaml
volumes:
  - ~/.claude:/home/claudebot/.claude
```

> **Для Windows**: Замініть `~/.claude` на `${USERPROFILE}/.claude` у [docker-compose.yml](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\docker-compose.yml).

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

Створіть файл [.env](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\.env) у корені проєкту:

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

# Шлях до цільового проєкту всередині контейнера
TARGET_PROJECT_PATH=/app/target_project

# Додаткові налаштування (опціонально)
DEBUG=false
LOG_LEVEL=INFO
```

> 🔑 **Як отримати `TELEGRAM_BOT_TOKEN`?**  
> Створіть бота через [@BotFather](https://t.me/BotFather) у Telegram.

> 📌 **Як отримати `chat_id`?**  
> Надішліть повідомлення у чат → використайте бота [@userinfobot](https://t.me/userinfobot) або зробіть запит до `https://api.telegram.org/bot<TOKEN>/getUpdates`.

---

## 📁 **Робота з цільовим проєктом**

Ви можете монтувати будь-який локальний проєкт у контейнер, щоб Claude CLI міг з ним працювати.

### Кроки:

#### 1. Клонуйте або скопіюйте ваш проєкт у директорію `target_project`

```bash
# Приклад: клонування репозиторію
git clone https://github.com/your-username/your-project.git target_project

# Або просто скопіюйте існуючу директорію
cp -r /path/to/your/project ./target_project
```

#### 2. Переконайтеся, що [docker-compose.yml](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\docker-compose.yml) монтує `./target_project:/app/target_project`

#### 3. Запустіть або перезапустіть контейнер

```bash
docker-compose up -d --build
```

---

### 🔄 Як це працює?

- Директорія `./target_project` на хості синхронізується з `/app/target_project` у контейнері.
- **Будь-які зміни на хості** (редагування, додавання файлів) **миттєво відображаються** у контейнері.
- Claude CLI може виконувати команди безпосередньо над цією директорією.

---

### 🛠️ Приклади команд Claude CLI

Після монтування ви можете виконувати такі команди (вручну або через бота):

```bash
# Перегляд та аналіз репозиторію
claude repo review /app/target_project

# Аудит безпеки
claude audit /app/target_project

# Рефакторинг конкретного файлу
claude refactor /app/target_project/src/main.py --goal "Improve readability"

# Генерація документації
claude document /app/target_project --output /app/target_project/README.md

# Запуск тестів (якщо підтримується)
claude test /app/target_project
```

> 💡 **Інтеграція з ботом**: У майбутніх версіях бота ви зможете відправляти команди типу `/review`, `/audit`, `/refactor` — вони будуть виконуватися над `TARGET_PROJECT_PATH`.

---

### 🚨 **Troubleshooting**

**Проблема**: Claude CLI не має доступу до файлів у `/app/target_project`.

**Рішення**:

- Переконайтеся, що директорія існує на хості: `ls -la ./target_project`
- Перевірте права: `sudo chown -R 1001:1001 ./target_project` (Linux/macOS)
- Увійдіть у контейнер і перевірте вручну:

  ```bash
  docker-compose exec claude_bot bash
  ls -la /app/target_project
  whoami  # має бути claudebot
  ```

---

## 🚀 **4. Інструкція по розгортанню**

Виконайте наступні кроки у терміналі:

### Крок 1: Клонувати репозиторій (якщо ще не клоновано)

```
git clone https://github.com/your-username/claude-code-telegram-main.git
cd claude-code-telegram-main
```

### Крок 2: Створити [.env](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\.env) файл

Скопіюйте вміст прикладу вище у файл [.env](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\.env) та підставте свої значення, особливо `TELEGRAM_BOT_TOKEN` та `CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS`.

### Крок 3: Створити директорію для даних

```
mkdir -p data
```

Ця директорія буде містити файли стану:
- `./data/.claude_last_cmd.json` — поточний стан (available/unavailable/limited) з деталями
- `./data/transitions.jsonl` — історія переходів станів з інформацією про ліміти

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

Відредагуйте [.env](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\.env):

```
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=111111111,-1002222222222,333333333
```

Потім перезапустіть:

```
docker-compose up -d
```

### Зміна DND вікна

Відредагуйте [.env](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\.env):

```
CLAUDE_AVAILABILITY_DND_START=00:00
CLAUDE_AVAILABILITY_DND_END=07:00
```

Перезапустіть сервіс.

---

## 📊 **7. Моніторинг лімітів використання Claude CLI**

Бот автоматично розпізнає та відслідковуватиме ліміти використання Claude CLI.

### 🔍 **Розпізнавання лімітів**

Бот аналізує вивід Claude CLI на наявність повідомлень про ліміти:
- `"5-hour limit reached ∙ resets 2pm"`
- `"limit reached ∙ resets 11:30am"`
- `"Rate limit exceeded. resets 14:00"`

### 📱 **Повідомлення у Telegram**

**При досягненні ліміту:**
```
🔴 Claude CLI недоступний (ліміт використання)
📅 2025-09-08 11:30:00
⏳ Очікуваний час відновлення: 14:00 (за даними CLI)
```

**При відновленні доступу:**
```
🟢 Claude CLI знову доступний
📅 2025-09-08 16:30:00
🖥️ Linux x86_64
⏱️ (перерва: 5год 0хв)
📅 Фактичний час відновлення: 16:30
⏳ Очікуваний був: 14:00
```

### 📄 **Формат файлів стану**

**`.claude_last_cmd.json` з лімітом:**
```json
{
  "available": false,
  "reason": "limit",
  "reset_expected": "2025-09-08T14:00:00Z",
  "last_check": "2025-09-08T11:30:00+03:00"
}
```

**`transitions.jsonl` запис:**
```json
{
  "timestamp": "2025-09-08T11:30:00Z",
  "from": "available",
  "to": "limited",
  "reset_expected": "2025-09-08T14:00:00Z",
  "platform": "Linux x86_64"
}
```

**При відновленні:**
```json
{
  "timestamp": "2025-09-08T16:30:00Z",
  "from": "limited", 
  "to": "available",
  "reset_expected": "2025-09-08T14:00:00Z",
  "reset_actual": "2025-09-08T16:30:00Z",
  "duration_unavailable": 18000,
  "platform": "Linux x86_64"
}
```

### 🌙 **DND та ліміти**

- **Повідомлення про ліміт** надсилаються негайно (навіть під час DND)
- **Повідомлення про відновлення** відкладаються до ранку, якщо відновлення сталося під час DND
- У відкладених повідомленнях показується як очікуваний, так і фактичний час відновлення

---

## 🚨 **8. Troubleshooting**

### ❌ Проблема: `Claude CLI not found` у логах

**Симптоми:**
```
Claude CLI недоступний: [Errno 2] No such file or directory: 'claude'
```

**Рішення:**

1. Переконайтеся, що `claude` встановлено у контейнері. Перевірте [Dockerfile](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\Dockerfile) — має бути рядок:
   ```dockerfile
   RUN npm install -g @anthropic-ai/claude-code
   ```

2. Увійдіть у контейнер і перевірте вручну:
   ```bash
   docker-compose exec claude_bot bash
   which claude
   claude --version
   ```

3. Якщо `claude` не знайдено, оновіть [Dockerfile](file://c:\Users\tukro\OneDrive\Документы\GitHub\claude-notifer-and-bot\Dockerfile), додавши встановлення `nodejs` та `npm`:

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

### ❌ Проблема: Ліміти не розпізнаються

**Симптоми:**
- Claude CLI повертає помилки про ліміт, але бот показує стан як "unavailable" замість "limited"
- Немає інформації про `reset_expected` у файлах стану

**Рішення:**

1. Перевірте логи бота на наявність повідомлень про парсинг:
   ```bash
   docker-compose logs claude_bot | grep -i "limit\|reset"
   ```

2. Перевірте формат повідомлення Claude CLI:
   ```bash
   docker-compose exec claude_bot bash
   claude --version
   # Якщо є ліміт, подивіться точний текст помилки
   ```

3. Якщо формат відрізняється від очікуваного, повідомте про це розробникам.

### ❌ Проблема: Неточні часи відновлення

**Симптоми:**
- `reset_expected` не збігається з реальним часом відновлення
- Claude CLI показує час в іншому форматі

**Примітка:** 
Час відновлення парситься з повідомлень Claude CLI та конвертується в часову зону Europe/Kyiv. Якщо ваша система використовує іншу часову зону, це може спричинити розбіжності.

---

## 📂 **9. Де шукати файли стану?**

Після запуску файли з'являться у:

- `./data/.claude_last_cmd.json` — останній стан та час перевірки з деталями про ліміти.
- `./data/transitions.jsonl` — журнал усіх переходів з інформацією про ліміти (кожен рядок — окремий JSON).

Приклади записів в `transitions.jsonl`:

**Звичайний перехід:**
```json
{"timestamp": "2025-09-08T09:15:33Z", "from": "unavailable", "to": "available", "duration_unavailable": 10000.5, "platform": "Linux x86_64"}
```

**Перехід через ліміт:**
```json
{"timestamp": "2025-09-08T11:30:00Z", "from": "available", "to": "limited", "reset_expected": "2025-09-08T14:00:00Z", "platform": "Linux x86_64"}
```

**Відновлення після ліміту:**
```json
{"timestamp": "2025-09-08T16:30:00Z", "from": "limited", "to": "available", "reset_expected": "2025-09-08T14:00:00Z", "reset_actual": "2025-09-08T16:30:00Z", "duration_unavailable": 18000, "platform": "Linux x86_64"}
```

---

✅ **Готово!**  
Ваш бот розгорнуто, налаштовано та готовий до роботи. Він автоматично стежитиме за доступністю Claude CLI та надсилатиме сповіщення у Telegram з урахуванням DND.

---

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
```

```

### src\exceptions.py

**Розмір:** 1,887 байт

```python
"""Custom exceptions for Claude Code Telegram Bot."""


class ClaudeCodeTelegramError(Exception):
    """Base exception for Claude Code Telegram Bot."""

    pass


class ConfigurationError(ClaudeCodeTelegramError):
    """Configuration-related errors."""

    pass


class MissingConfigError(ConfigurationError):
    """Required configuration is missing."""

    pass


class InvalidConfigError(ConfigurationError):
    """Configuration is invalid."""

    pass


class SecurityError(ClaudeCodeTelegramError):
    """Security-related errors."""

    pass


class AuthenticationError(SecurityError):
    """Authentication failed."""

    pass


class AuthorizationError(SecurityError):
    """Authorization failed."""

    pass


class DirectoryTraversalError(SecurityError):
    """Directory traversal attempt detected."""

    pass


class ClaudeError(ClaudeCodeTelegramError):
    """Claude Code-related errors."""

    pass


class ClaudeTimeoutError(ClaudeError):
    """Claude Code operation timed out."""

    pass


class ClaudeProcessError(ClaudeError):
    """Claude Code process execution failed."""

    pass


class ClaudeParsingError(ClaudeError):
    """Failed to parse Claude Code output."""

    pass


class StorageError(ClaudeCodeTelegramError):
    """Storage-related errors."""

    pass


class DatabaseConnectionError(StorageError):
    """Database connection failed."""

    pass


class DataIntegrityError(StorageError):
    """Data integrity check failed."""

    pass


class TelegramError(ClaudeCodeTelegramError):
    """Telegram API-related errors."""

    pass


class MessageTooLongError(TelegramError):
    """Message exceeds Telegram's length limit."""

    pass


class RateLimitError(TelegramError):
    """Rate limit exceeded."""

    pass


class RateLimitExceeded(RateLimitError):
    """Rate limit exceeded (alias for compatibility)."""

    pass

```

### src\main.py

**Розмір:** 8,642 байт

```python
"""Main entry point for Claude Code Telegram Bot."""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Any, Dict

import structlog

from src import __version__
from src.bot.core import ClaudeCodeBot
from src.claude import (
    ClaudeIntegration,
    ClaudeProcessManager,
    SessionManager,
    ToolMonitor,
)
from src.claude.sdk_integration import ClaudeSDKManager
from src.config.features import FeatureFlags
from src.config.loader import load_config
from src.config.settings import Settings
from src.exceptions import ConfigurationError
from src.security.audit import AuditLogger, InMemoryAuditStorage
from src.security.auth import (
    AuthenticationManager,
    InMemoryTokenStorage,
    TokenAuthProvider,
    WhitelistAuthProvider,
)
from src.security.rate_limiter import RateLimiter
from src.security.validators import SecurityValidator
from src.storage.facade import Storage
from src.storage.session_storage import SQLiteSessionStorage


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging."""
    level = logging.DEBUG if debug else logging.INFO

    # Configure standard logging
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if not debug
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Claude Code Telegram Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", action="version", version=f"Claude Code Telegram Bot {__version__}"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument("--config-file", type=Path, help="Path to configuration file")

    return parser.parse_args()


async def create_application(config: Settings) -> Dict[str, Any]:
    """Create and configure the application components."""
    logger = structlog.get_logger()
    logger.info("Creating application components")

    # Initialize storage system
    storage = Storage(config.database_url)
    await storage.initialize()

    # Create security components
    providers = []

    # Add whitelist provider if users are configured
    if config.allowed_users:
        providers.append(WhitelistAuthProvider(config.allowed_users))

    # Add token provider if enabled
    if config.enable_token_auth:
        token_storage = InMemoryTokenStorage()  # TODO: Use database storage
        providers.append(TokenAuthProvider(config.auth_token_secret, token_storage))

    # Fall back to allowing all users in development mode
    if not providers and config.development_mode:
        logger.warning(
            "No auth providers configured - creating development-only allow-all provider"
        )
        providers.append(WhitelistAuthProvider([], allow_all_dev=True))
    elif not providers:
        raise ConfigurationError("No authentication providers configured")

    auth_manager = AuthenticationManager(providers)
    security_validator = SecurityValidator(config.approved_directory)
    rate_limiter = RateLimiter(config)

    # Create audit storage and logger
    audit_storage = InMemoryAuditStorage()  # TODO: Use database storage in production
    audit_logger = AuditLogger(audit_storage)

    # Create Claude integration components with persistent storage
    session_storage = SQLiteSessionStorage(storage.db_manager)
    session_manager = SessionManager(config, session_storage)
    tool_monitor = ToolMonitor(config, security_validator)

    # Create Claude manager based on configuration
    if config.use_sdk:
        logger.info("Using Claude Python SDK integration")
        sdk_manager = ClaudeSDKManager(config)
        process_manager = None
    else:
        logger.info("Using Claude CLI subprocess integration")
        process_manager = ClaudeProcessManager(config)
        sdk_manager = None

    # Create main Claude integration facade
    claude_integration = ClaudeIntegration(
        config=config,
        process_manager=process_manager,
        sdk_manager=sdk_manager,
        session_manager=session_manager,
        tool_monitor=tool_monitor,
    )

    # Create bot with all dependencies
    dependencies = {
        "auth_manager": auth_manager,
        "security_validator": security_validator,
        "rate_limiter": rate_limiter,
        "audit_logger": audit_logger,
        "claude_integration": claude_integration,
        "storage": storage,
    }

    bot = ClaudeCodeBot(config, dependencies)

    logger.info("Application components created successfully")

    return {
        "bot": bot,
        "claude_integration": claude_integration,
        "storage": storage,
        "config": config,
    }


async def run_application(app: Dict[str, Any]) -> None:
    """Run the application with graceful shutdown handling."""
    logger = structlog.get_logger()
    bot: ClaudeCodeBot = app["bot"]
    claude_integration: ClaudeIntegration = app["claude_integration"]
    storage: Storage = app["storage"]

    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info("Shutdown signal received", signal=signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start the bot
        logger.info("Starting Claude Code Telegram Bot")

        # Run bot in background task
        bot_task = asyncio.create_task(bot.start())
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        # Wait for either bot completion or shutdown signal
        done, pending = await asyncio.wait(
            [bot_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error("Application error", error=str(e))
        raise
    finally:
        # Graceful shutdown
        logger.info("Shutting down application")

        try:
            await bot.stop()
            await claude_integration.shutdown()
            await storage.close()
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))

        logger.info("Application shutdown complete")


async def main() -> None:
    """Main application entry point."""
    args = parse_args()
    setup_logging(debug=args.debug)

    logger = structlog.get_logger()
    logger.info("Starting Claude Code Telegram Bot", version=__version__)

    try:
        # Load configuration
        from src.config import FeatureFlags, load_config

        config = load_config(config_file=args.config_file)
        features = FeatureFlags(config)

        logger.info(
            "Configuration loaded",
            environment="production" if config.is_production else "development",
            enabled_features=features.get_enabled_features(),
            debug=config.debug,
        )

        # Initialize bot and Claude integration
        app = await create_application(config)
        await run_application(app)

    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error", error=str(e))
        sys.exit(1)


def run() -> None:
    """Synchronous entry point for setuptools."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)


if __name__ == "__main__":
    run()

```

### src\__init__.py

**Розмір:** 1,234 байт

```python
"""Claude Code Telegram Bot.

A Telegram bot that provides remote access to Claude Code CLI, allowing developers
to interact with their projects from anywhere through a secure, terminal-like
interface within Telegram.

Features:
- Environment-based configuration with Pydantic validation
- Feature flags for dynamic functionality control
- Comprehensive security framework (planned)
- Session persistence and state management (planned)
- Real-time Claude Code integration (planned)

Current Implementation Status:
- ✅ Project Structure & Configuration System (Complete)
- 🚧 Authentication & Security Framework (TODO-3)
- 🚧 Telegram Bot Core (TODO-4)
- 🚧 Claude Code Integration (TODO-5)
- 🚧 Storage Layer (TODO-6)
"""

__version__ = "0.1.0"
__author__ = "Richard Atkinson"
__email__ = "richardatk01@gmail.com"
__license__ = "MIT"
__homepage__ = "https://github.com/richardatkinson/claude-code-telegram"

# Development status indicators
__status__ = "Alpha"
__implementation_phase__ = "TODO-3 Complete"

# Completed components
__completed_todos__ = [
    "TODO-1: Project Structure",
    "TODO-2: Configuration Management",
    "TODO-3: Authentication & Security Framework",
]
__next_todo__ = "TODO-4: Telegram Bot Core"

```

### src\bot\core.py

**Розмір:** 13,654 байт

```python
"""Main Telegram bot class.

Features:
- Command registration
- Handler management
- Context injection
- Graceful shutdown
"""

import asyncio
from typing import Any, Callable, Dict, Optional

import structlog
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..config.features import FeatureFlags
from ..config.settings import Settings
from ..exceptions import ClaudeCodeTelegramError
from .features.registry import FeatureRegistry

logger = structlog.get_logger()


class ClaudeCodeBot:
    """Main bot orchestrator."""

    def __init__(self, settings: Settings, dependencies: Dict[str, Any]):
        """Initialize bot with settings and dependencies."""
        self.settings = settings
        self.deps = dependencies
        self.app: Optional[Application] = None
        self.is_running = False
        self.feature_registry: Optional[FeatureRegistry] = None

    async def initialize(self) -> None:
        """Initialize bot application."""
        logger.info("Initializing Telegram bot")

        # Create application
        builder = Application.builder()
        builder.token(self.settings.telegram_token_str)

        # Configure connection settings
        builder.connect_timeout(30)
        builder.read_timeout(30)
        builder.write_timeout(30)
        builder.pool_timeout(30)

        self.app = builder.build()

        # Initialize feature registry
        self.feature_registry = FeatureRegistry(
            config=self.settings,
            storage=self.deps.get("storage"),
            security=self.deps.get("security"),
        )

        # Add feature registry to dependencies
        self.deps["features"] = self.feature_registry

        # Set bot commands for menu
        await self._set_bot_commands()

        # Register handlers
        self._register_handlers()

        # Add middleware
        self._add_middleware()

        # Set error handler
        self.app.add_error_handler(self._error_handler)

        # Set up Claude availability monitoring if enabled
        features = FeatureFlags(self.settings)
        if features.claude_availability_monitor:
            from .features.availability_monitor import setup_availability_monitor
            await setup_availability_monitor(self.app, self.settings)

        logger.info("Bot initialization complete")

    async def _set_bot_commands(self) -> None:
        """Set bot command menu."""
        commands = [
            BotCommand("start", "Start bot and show help"),
            BotCommand("help", "Show available commands"),
            BotCommand("new", "Start new Claude session"),
            BotCommand("continue", "Continue last session"),
            BotCommand("ls", "List files in current directory"),
            BotCommand("cd", "Change directory"),
            BotCommand("pwd", "Show current directory"),
            BotCommand("projects", "Show all projects"),
            BotCommand("status", "Show session status"),
            BotCommand("export", "Export current session"),
            BotCommand("actions", "Show quick actions"),
            BotCommand("git", "Git repository commands"),
        ]

        await self.app.bot.set_my_commands(commands)
        logger.info("Bot commands set", commands=[cmd.command for cmd in commands])

    def _register_handlers(self) -> None:
        """Register all command and message handlers."""
        from .handlers import callback, command, message

        # Command handlers
        handlers = [
            ("start", command.start_command),
            ("help", command.help_command),
            ("new", command.new_session),
            ("continue", command.continue_session),
            ("end", command.end_session),
            ("ls", command.list_files),
            ("cd", command.change_directory),
            ("pwd", command.print_working_directory),
            ("projects", command.show_projects),
            ("status", command.session_status),
            ("export", command.export_session),
            ("actions", command.quick_actions),
            ("git", command.git_command),
        ]

        for cmd, handler in handlers:
            self.app.add_handler(CommandHandler(cmd, self._inject_deps(handler)))

        # Message handlers with priority groups
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._inject_deps(message.handle_text_message),
            ),
            group=10,
        )

        self.app.add_handler(
            MessageHandler(
                filters.Document.ALL, self._inject_deps(message.handle_document)
            ),
            group=10,
        )

        self.app.add_handler(
            MessageHandler(filters.PHOTO, self._inject_deps(message.handle_photo)),
            group=10,
        )

        # Callback query handler
        self.app.add_handler(
            CallbackQueryHandler(self._inject_deps(callback.handle_callback_query))
        )

        logger.info("Bot handlers registered")

    def _inject_deps(self, handler: Callable) -> Callable:
        """Inject dependencies into handlers."""

        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Add dependencies to context
            for key, value in self.deps.items():
                context.bot_data[key] = value

            # Add settings
            context.bot_data["settings"] = self.settings

            return await handler(update, context)

        return wrapped

    def _add_middleware(self) -> None:
        """Add middleware to application."""
        from .middleware.auth import auth_middleware
        from .middleware.rate_limit import rate_limit_middleware
        from .middleware.security import security_middleware

        # Middleware runs in order of group numbers (lower = earlier)
        # Security middleware first (validate inputs)
        self.app.add_handler(
            MessageHandler(
                filters.ALL, self._create_middleware_handler(security_middleware)
            ),
            group=-3,
        )

        # Authentication second
        self.app.add_handler(
            MessageHandler(
                filters.ALL, self._create_middleware_handler(auth_middleware)
            ),
            group=-2,
        )

        # Rate limiting third
        self.app.add_handler(
            MessageHandler(
                filters.ALL, self._create_middleware_handler(rate_limit_middleware)
            ),
            group=-1,
        )

        logger.info("Middleware added to bot")

    def _create_middleware_handler(self, middleware_func: Callable) -> Callable:
        """Create middleware handler that injects dependencies."""

        async def middleware_wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE
        ):
            # Inject dependencies into context
            for key, value in self.deps.items():
                context.bot_data[key] = value
            context.bot_data["settings"] = self.settings

            # Create a dummy handler that does nothing (middleware will handle everything)
            async def dummy_handler(event, data):
                return None

            # Call middleware with Telegram-style parameters
            return await middleware_func(dummy_handler, update, context.bot_data)

        return middleware_wrapper

    async def start(self) -> None:
        """Start the bot."""
        if self.is_running:
            logger.warning("Bot is already running")
            return

        await self.initialize()

        logger.info(
            "Starting bot", mode="webhook" if self.settings.webhook_url else "polling"
        )

        try:
            self.is_running = True

            if self.settings.webhook_url:
                # Webhook mode
                await self.app.run_webhook(
                    listen="0.0.0.0",
                    port=self.settings.webhook_port,
                    url_path=self.settings.webhook_path,
                    webhook_url=self.settings.webhook_url,
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES,
                )
            else:
                # Polling mode - initialize and start polling manually
                await self.app.initialize()
                await self.app.start()
                await self.app.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                )

                # Keep running until manually stopped
                while self.is_running:
                    await asyncio.sleep(1)
        except Exception as e:
            logger.error("Error running bot", error=str(e))
            raise ClaudeCodeTelegramError(f"Failed to start bot: {str(e)}") from e
        finally:
            self.is_running = False

    async def stop(self) -> None:
        """Gracefully stop the bot."""
        if not self.is_running:
            logger.warning("Bot is not running")
            return

        logger.info("Stopping bot")

        try:
            self.is_running = False  # Stop the main loop first

            # Shutdown feature registry
            if self.feature_registry:
                self.feature_registry.shutdown()

            if self.app:
                # Stop the updater if it's running
                if self.app.updater.running:
                    await self.app.updater.stop()

                # Stop the application
                await self.app.stop()
                await self.app.shutdown()

            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error("Error stopping bot", error=str(e))
            raise ClaudeCodeTelegramError(f"Failed to stop bot: {str(e)}") from e

    async def _error_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle errors globally."""
        error = context.error
        logger.error(
            "Global error handler triggered",
            error=str(error),
            update_type=type(update).__name__ if update else None,
            user_id=(
                update.effective_user.id if update and update.effective_user else None
            ),
        )

        # Determine error message for user
        from ..exceptions import (
            AuthenticationError,
            ConfigurationError,
            RateLimitExceeded,
            SecurityError,
        )

        error_messages = {
            AuthenticationError: "🔒 Authentication required. Please contact the administrator.",
            SecurityError: "🛡️ Security violation detected. This incident has been logged.",
            RateLimitExceeded: "⏱️ Rate limit exceeded. Please wait before sending more messages.",
            ConfigurationError: "⚙️ Configuration error. Please contact the administrator.",
            asyncio.TimeoutError: "⏰ Operation timed out. Please try again with a simpler request.",
        }

        error_type = type(error)
        user_message = error_messages.get(
            error_type, "❌ An unexpected error occurred. Please try again."
        )

        # Try to notify user
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(user_message)
            except Exception:
                logger.exception("Failed to send error message to user")

        # Log to audit system if available
        from ..security.audit import AuditLogger

        audit_logger: Optional[AuditLogger] = context.bot_data.get("audit_logger")
        if audit_logger and update and update.effective_user:
            try:
                await audit_logger.log_security_violation(
                    user_id=update.effective_user.id,
                    violation_type="system_error",
                    details=f"Error type: {error_type.__name__}, Message: {str(error)}",
                    severity="medium",
                )
            except Exception:
                logger.exception("Failed to log error to audit system")

    async def get_bot_info(self) -> Dict[str, Any]:
        """Get bot information."""
        if not self.app:
            return {"status": "not_initialized"}

        try:
            me = await self.app.bot.get_me()
            return {
                "status": "running" if self.is_running else "initialized",
                "username": me.username,
                "first_name": me.first_name,
                "id": me.id,
                "can_join_groups": me.can_join_groups,
                "can_read_all_group_messages": me.can_read_all_group_messages,
                "supports_inline_queries": me.supports_inline_queries,
                "webhook_url": self.settings.webhook_url,
                "webhook_port": (
                    self.settings.webhook_port if self.settings.webhook_url else None
                ),
            }
        except Exception as e:
            logger.error("Failed to get bot info", error=str(e))
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            if not self.app:
                return False

            # Try to get bot info
            await self.app.bot.get_me()
            return True
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False

```

### src\bot\__init__.py

**Розмір:** 55 байт

```python
"""Telegram bot module for Claude Code integration."""

```

### src\bot\features\availability_monitor.py

**Розмір:** 18,931 байт

```python
"""Claude CLI availability monitoring feature."""

import asyncio
import json
import re
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from zoneinfo import ZoneInfo

import structlog
from telegram import Bot
from telegram.error import RetryAfter, TimedOut, NetworkError
from telegram.ext import Application

from src.config.settings import Settings

# Add retry support
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)


class ClaudeAvailabilityMonitor:
    """Monitors Claude CLI availability and sends notifications."""

    def __init__(self, application: Application, settings: Settings):
        """Initialize the availability monitor."""
        self.application = application
        self.settings = settings
        self.bot: Bot = application.bot
        self.last_state: Optional[bool] = None
        self.ok_counter = 0
        self.pending_notification: Optional[Dict[str, Any]] = None

        # Ensure state files exist
        self._init_state_files()

    def _init_state_files(self):
        """Initialize state files if they don't exist."""
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)
        
        self.state_file = data_dir / ".claude_last_cmd.json"
        self.transitions_log = data_dir / "transitions.jsonl"
        
        if not self.state_file.exists():
            self.state_file.write_text(json.dumps({"available": False, "last_check": None}))
        if not self.transitions_log.exists():
            self.transitions_log.touch()

    def parse_limit_message(self, output: str) -> Optional[datetime]:
        """Parse limit message from Claude CLI output and extract reset time.
        
        Args:
            output: Combined stdout/stderr output from Claude CLI
            
        Returns:
            datetime in UTC if reset time found, None otherwise
            
        Examples:
            "5-hour limit reached ∙ resets 2pm" -> datetime for 2pm today in Europe/Kyiv -> UTC
            "limit reached ∙ resets 11:30am" -> datetime for 11:30am today in Europe/Kyiv -> UTC
            "limit reached ∙ resets 14:00" -> datetime for 14:00 today in Europe/Kyiv -> UTC
        """
        # Regex pattern to match various time formats after "resets"
        pattern = r"resets\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)"
        
        match = re.search(pattern, output, re.IGNORECASE)
        if not match:
            return None
            
        time_str = match.group(1).strip().lower()
        
        try:
            # Parse different time formats
            if 'am' in time_str or 'pm' in time_str:
                # Handle 12-hour format: "2pm", "11:30am", "2:00 pm"
                time_str = time_str.replace(' ', '')  # Remove spaces
                if ':' in time_str:
                    # "11:30am" format
                    time_obj = datetime.strptime(time_str, "%I:%M%p").time()
                else:
                    # "2pm" format  
                    time_obj = datetime.strptime(time_str, "%I%p").time()
            else:
                # Handle 24-hour format: "14:00", "2" (assume 24-hour if no am/pm)
                if ':' in time_str:
                    # "14:00" format
                    time_obj = datetime.strptime(time_str, "%H:%M").time()
                else:
                    # Single digit like "2" - assume 24-hour format
                    time_obj = datetime.strptime(time_str, "%H").time()
            
            # Create datetime for today in Europe/Kyiv timezone
            kyiv_tz = ZoneInfo("Europe/Kyiv")
            today = datetime.now(kyiv_tz).date()
            reset_time_kyiv = datetime.combine(today, time_obj, tzinfo=kyiv_tz)
            
            # If the time is in the past today, assume it means tomorrow
            if reset_time_kyiv <= datetime.now(kyiv_tz):
                reset_time_kyiv = reset_time_kyiv.replace(day=reset_time_kyiv.day + 1)
            
            # Convert to UTC
            reset_time_utc = reset_time_kyiv.astimezone(ZoneInfo("UTC"))
            
            logger.debug(f"Parsed reset time: {time_str} -> {reset_time_utc.isoformat()}")
            return reset_time_utc
            
        except ValueError as e:
            logger.warning(f"Failed to parse time '{time_str}': {e}")
            return None

    async def health_check(self) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """Perform health check by running `claude --version`.
        
        Returns:
            Tuple of (is_available, reason, reset_time):
            - is_available: True if Claude CLI is working
            - reason: None if available, "limit" if rate limited, "error" for other issues
            - reset_time: UTC datetime when limit resets, None if not applicable
        
        ⚠️ For Claude CLI to work inside the container:
        - Authentication must be done on the host and the ~/.claude directory must be mounted
          to /home/claudebot/.claude in the container.
        - The target project directory must be mounted to /app/target_project.
        - See README.md for instructions.
        """
        try:
            # Replace subprocess.run with async call
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Use async timeout
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            
            if proc.returncode == 0:
                logger.debug("Claude CLI check: available")
                return True, None, None
            
            # Decode output for analysis
            stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
            combined_output = f"{stdout_text}\n{stderr_text}"
            
            # Check if this is a limit-related error
            reset_time = self.parse_limit_message(combined_output)
            if reset_time:
                logger.debug(f"Claude CLI rate limited, resets at: {reset_time.isoformat()}")
                return False, "limit", reset_time
            
            # Other error
            logger.debug(f"Claude CLI check: unavailable (exit_code={proc.returncode})")
            return False, "error", None
            
        except (asyncio.TimeoutError, FileNotFoundError, Exception) as e:
            logger.warning(f"Claude CLI unavailable: {e}")
            return False, "error", None

    async def _save_state(self, available: bool, reason: Optional[str] = None, reset_expected: Optional[datetime] = None):
        """Save current state to file asynchronously."""
        state = {
            "available": available,
            "last_check": datetime.now(ZoneInfo("Europe/Kyiv")).isoformat()
        }
        
        # Add reason and reset_expected for limited state
        if not available and reason:
            state["reason"] = reason
            if reset_expected and reason == "limit":
                state["reset_expected"] = reset_expected.isoformat()
        
        # Use aiofiles for async file writing
        import aiofiles
        async with aiofiles.open(self.state_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(state, ensure_ascii=False, indent=2))

    async def _log_transition(self, from_state: str, to_state: str, 
                            duration: Optional[float] = None, 
                            reset_expected: Optional[datetime] = None,
                            reset_actual: Optional[datetime] = None):
        """Log state transition to transitions.jsonl asynchronously."""
        record = {
            "timestamp": datetime.now(ZoneInfo("UTC")).isoformat(),
            "from": from_state,
            "to": to_state,
            "duration_unavailable": duration,
            "platform": self._get_platform()
        }
        
        # Add reset times for limit-related transitions
        if reset_expected:
            record["reset_expected"] = reset_expected.isoformat()
        if reset_actual:
            record["reset_actual"] = reset_actual.isoformat()
        
        # Use aiofiles for async file writing
        import aiofiles
        async with aiofiles.open(self.transitions_log, "a", encoding="utf-8") as f:
            await f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _get_platform(self) -> str:
        """Get platform information."""
        import platform
        return f"{platform.system()} {platform.machine()}"

    def _is_dnd_time(self) -> bool:
        """Check if current time is within DND window (23:00–08:00 Europe/Kyiv)."""
        now = datetime.now(ZoneInfo("Europe/Kyiv")).time()
        dnd_start = self.settings.claude_availability.dnd_start
        dnd_end = self.settings.claude_availability.dnd_end

        if dnd_start > dnd_end:  # e.g., 23:00–08:00
            return now >= dnd_start or now < dnd_end
        else:
            return dnd_start <= now < dnd_end

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RetryAfter, TimedOut, NetworkError)),
        reraise=True
    )
    async def _send_notification(self, message: str):
        """Send notification to all subscribed chats with retry logic."""
        chat_ids = self.settings.claude_availability.notify_chat_ids
        if not chat_ids:
            logger.warning("No chats configured for Claude CLI availability notifications")
            return

        for chat_id in chat_ids:
            try:
                await self.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                logger.info(f"Availability notification sent to chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {chat_id}: {e}")
                raise  # Retry only for specific error types

    async def _build_availability_message(self, downtime_duration: Optional[float] = None, 
                                        reset_expected: Optional[datetime] = None, 
                                        reset_actual: Optional[datetime] = None) -> str:
        """Build availability message in the specified format."""
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        platform = self._get_platform()
        duration_str = ""
        if downtime_duration:
            hours, remainder = divmod(downtime_duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f" (перерва: {int(hours)}год {int(minutes)}хв)"

        message = (
            f"🟢 **Claude CLI знову доступний**\n"
            f"📅 `{now.strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"🖥️ `{platform}`\n"
            f"⏱️ {duration_str}"
        )
        
        # Add reset time information if available
        if reset_expected and reset_actual:
            kyiv_tz = ZoneInfo("Europe/Kyiv")
            expected_local = reset_expected.astimezone(kyiv_tz)
            actual_local = reset_actual.astimezone(kyiv_tz)
            
            message += (
                f"\n📅 Фактичний час відновлення: {actual_local.strftime('%H:%M')}"
                f"\n⏳ Очікуваний був: {expected_local.strftime('%H:%M')}"
            )
        
        return message

    async def _build_limit_message(self, reset_expected: Optional[datetime] = None) -> str:
        """Build limit reached message for Telegram."""
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        
        message = (
            f"🔴 **Claude CLI недоступний (ліміт використання)**\n"
            f"📅 `{now.strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        
        if reset_expected:
            kyiv_tz = ZoneInfo("Europe/Kyiv")
            reset_local = reset_expected.astimezone(kyiv_tz)
            message += f"\n⏳ Очікуваний час відновлення: {reset_local.strftime('%H:%M')} (за даними CLI)"
        
        return message

    async def monitor_task(self, context):
        """Main monitoring task that runs periodically."""
        if not self.settings.claude_availability.enabled:
            return  # Feature disabled

        # Get current health status
        current_available, current_reason, current_reset_time = await self.health_check()
        current_time = time.time()

        # Load previous state
        try:
            # Use aiofiles for async file reading
            import aiofiles
            async with aiofiles.open(self.state_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                last_state_data = json.loads(content)
                
            last_available = last_state_data.get("available", False)
            last_reason = last_state_data.get("reason")
            last_reset_expected_str = last_state_data.get("reset_expected")
            last_reset_expected = datetime.fromisoformat(last_reset_expected_str) if last_reset_expected_str else None
            last_check_str = last_state_data.get("last_check")
            last_check = datetime.fromisoformat(last_check_str) if last_check_str else None
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            logger.error(f"Error reading state: {e}")
            last_available = False
            last_reason = None
            last_reset_expected = None
            last_check = None

        # Debounce logic: need N consecutive OK checks for availability
        if current_available:
            self.ok_counter += 1
        else:
            self.ok_counter = 0

        debounce_threshold = self.settings.claude_availability.debounce_ok_count
        confirmed_available = self.ok_counter >= debounce_threshold

        # Determine current state string for logging
        if confirmed_available:
            current_state = "available"
        elif current_reason == "limit":
            current_state = "limited"
        else:
            current_state = "unavailable"

        # Determine previous state string for logging
        if last_available:
            last_state = "available"
        elif last_reason == "limit":
            last_state = "limited"
        else:
            last_state = "unavailable"

        # Check if state changed
        state_changed = (confirmed_available != last_available) or (current_reason != last_reason)

        if state_changed:
            downtime_duration = None
            reset_actual = None
            
            # Calculate downtime duration if recovering from unavailable/limited
            if last_check and not last_available and confirmed_available:
                downtime_duration = (datetime.now(ZoneInfo("Europe/Kyiv")) - last_check).total_seconds()
                if last_state == "limited":
                    reset_actual = datetime.now(ZoneInfo("UTC"))

            # Log the transition
            await self._log_transition(
                from_state=last_state,
                to_state=current_state,
                duration=downtime_duration,
                reset_expected=last_reset_expected if last_state == "limited" and current_state == "available" else current_reset_time,
                reset_actual=reset_actual
            )

            # Save new state
            await self._save_state(confirmed_available, current_reason, current_reset_time)

            # Handle notifications
            if confirmed_available and not last_available:
                # Became available from limited/unavailable
                message = await self._build_availability_message(
                    downtime_duration=downtime_duration,
                    reset_expected=last_reset_expected,
                    reset_actual=reset_actual
                )
                
                if self._is_dnd_time():
                    # Save for sending in the morning
                    self.pending_notification = {
                        "message": message,
                        "prepared_at": current_time
                    }
                    logger.info(f"Transition from {last_state} to available during DND - notification deferred.")
                else:
                    await self._send_notification(message)
                    self.pending_notification = None

            elif not confirmed_available and last_available and current_reason == "limit":
                # Became limited from available
                message = await self._build_limit_message(current_reset_time)
                
                if not self._is_dnd_time():
                    await self._send_notification(message)
                # Note: We don't defer limit notifications during DND as they are important

            self.last_state = confirmed_available

        # If there's a pending notification and we're no longer in DND - send it
        if self.pending_notification and not self._is_dnd_time():
            await self._send_notification(self.pending_notification["message"])
            logger.info("Deferred availability notification sent.")
            self.pending_notification = None

        # Always update the last check time
        await self._save_state(confirmed_available, current_reason, current_reset_time)


async def setup_availability_monitor(application: Application, settings: Settings):
    """Set up Claude CLI availability monitoring."""
    if not settings.claude_availability.enabled:
        logger.info("Claude CLI availability monitoring disabled in settings.")
        return

    monitor = ClaudeAvailabilityMonitor(application, settings)

    # Add periodic task
    application.job_queue.run_repeating(
        monitor.monitor_task,
        interval=settings.claude_availability.check_interval_seconds,
        first=10,  # First check after 10 seconds
        name="claude_availability_monitor"
    )

    logger.info(
        f"✅ Claude CLI monitoring enabled. Interval: {settings.claude_availability.check_interval_seconds}s. "
        f"Notification chats: {settings.claude_availability.notify_chat_ids}"
    )

```

### src\bot\features\conversation_mode.py

**Розмір:** 13,397 байт

```python
"""Enhanced conversation features.

This module implements the Conversation Enhancement feature from TODO-7, providing:

Features:
- Context preservation across conversation turns
- Intelligent follow-up suggestions based on tools used and content
- Code execution tracking and analysis
- Interactive conversation controls with inline keyboards
- Smart suggestion prioritization

Core Components:
- ConversationContext: Tracks conversation state and metadata
- ConversationEnhancer: Main class for generating suggestions and formatting responses

The implementation analyzes Claude's responses to generate contextually relevant
follow-up suggestions, making it easier for users to continue productive conversations
with actionable next steps.

Usage:
    enhancer = ConversationEnhancer()
    enhancer.update_context(user_id, claude_response)
    suggestions = enhancer.generate_follow_up_suggestions(response, context)
    keyboard = enhancer.create_follow_up_keyboard(suggestions)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ...claude.integration import ClaudeResponse

logger = structlog.get_logger()


@dataclass
class ConversationContext:
    """Context information for a conversation."""

    user_id: int
    session_id: Optional[str] = None
    project_path: Optional[str] = None
    last_tools_used: List[str] = field(default_factory=list)
    last_response_content: str = ""
    conversation_turn: int = 0
    has_errors: bool = False
    active_files: List[str] = field(default_factory=list)
    todo_count: int = 0

    def update_from_response(self, response: ClaudeResponse) -> None:
        """Update context from Claude response."""
        self.session_id = response.session_id
        self.last_response_content = response.content.lower()
        self.conversation_turn += 1
        self.has_errors = response.is_error or "error" in self.last_response_content

        # Extract tools used
        self.last_tools_used = [tool.get("name", "") for tool in response.tools_used]

        # Update active files if file tools were used
        if any(tool in self.last_tools_used for tool in ["Edit", "Write", "Read"]):
            # In a real implementation, we'd parse the tool outputs to get file names
            # For now, we'll track that file operations occurred
            pass

        # Count TODOs/FIXMEs in response
        todo_keywords = ["todo", "fixme", "note", "hack", "bug"]
        self.todo_count = sum(
            1 for keyword in todo_keywords if keyword in self.last_response_content
        )


class ConversationEnhancer:
    """Enhance conversation experience."""

    def __init__(self) -> None:
        """Initialize conversation enhancer."""
        self.conversation_contexts: Dict[int, ConversationContext] = {}

    def get_or_create_context(self, user_id: int) -> ConversationContext:
        """Get or create conversation context for user."""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = ConversationContext(user_id=user_id)

        return self.conversation_contexts[user_id]

    def update_context(self, user_id: int, response: ClaudeResponse) -> None:
        """Update conversation context with response."""
        context = self.get_or_create_context(user_id)
        context.update_from_response(response)

        logger.debug(
            "Updated conversation context",
            user_id=user_id,
            session_id=context.session_id,
            turn=context.conversation_turn,
            tools_used=context.last_tools_used,
        )

    def generate_follow_up_suggestions(
        self, response: ClaudeResponse, context: ConversationContext
    ) -> List[str]:
        """Generate relevant follow-up suggestions."""
        suggestions = []

        # Based on tools used
        tools_used = [tool.get("name", "") for tool in response.tools_used]

        if "Write" in tools_used or "MultiEdit" in tools_used:
            suggestions.extend(
                [
                    "Add tests for the new code",
                    "Create documentation for this",
                    "Review the implementation",
                ]
            )

        if "Edit" in tools_used:
            suggestions.extend(
                [
                    "Review the changes made",
                    "Run tests to verify changes",
                    "Check for any side effects",
                ]
            )

        if "Read" in tools_used:
            suggestions.extend(
                [
                    "Explain how this code works",
                    "Suggest improvements",
                    "Add error handling",
                ]
            )

        if "Bash" in tools_used:
            suggestions.extend(
                [
                    "Explain the command output",
                    "Run additional related commands",
                    "Check for any issues",
                ]
            )

        if "Glob" in tools_used or "Grep" in tools_used:
            suggestions.extend(
                [
                    "Analyze the search results",
                    "Look into specific files found",
                    "Create a summary of findings",
                ]
            )

        # Based on response content analysis
        content_lower = response.content.lower()

        if "error" in content_lower or "failed" in content_lower:
            suggestions.extend(
                [
                    "Help me debug this error",
                    "Suggest alternative approaches",
                    "Check the logs for more details",
                ]
            )

        if "todo" in content_lower or "fixme" in content_lower:
            suggestions.extend(
                [
                    "Complete the TODO items",
                    "Prioritize the tasks",
                    "Create an action plan",
                ]
            )

        if "test" in content_lower and (
            "fail" in content_lower or "error" in content_lower
        ):
            suggestions.extend(
                [
                    "Fix the failing tests",
                    "Update test expectations",
                    "Add more test coverage",
                ]
            )

        if "install" in content_lower or "dependency" in content_lower:
            suggestions.extend(
                [
                    "Verify the installation",
                    "Check for version conflicts",
                    "Update package documentation",
                ]
            )

        if "git" in content_lower:
            suggestions.extend(
                [
                    "Review the git status",
                    "Check commit history",
                    "Create a commit with changes",
                ]
            )

        # Based on conversation context
        if context.conversation_turn > 1:
            suggestions.append("Continue with the next step")

        if context.has_errors:
            suggestions.extend(
                ["Investigate the error further", "Try a different approach"]
            )

        if context.todo_count > 0:
            suggestions.append("Address the TODO items")

        # General suggestions based on development patterns
        if any(keyword in content_lower for keyword in ["function", "class", "method"]):
            suggestions.extend(
                ["Add unit tests", "Improve documentation", "Add type hints"]
            )

        if "performance" in content_lower or "optimize" in content_lower:
            suggestions.extend(
                [
                    "Profile the performance",
                    "Benchmark the changes",
                    "Monitor resource usage",
                ]
            )

        # Remove duplicates and limit to most relevant
        unique_suggestions = list(dict.fromkeys(suggestions))

        # Prioritize based on tools used and content
        prioritized = []

        # High priority: error handling and fixes
        for suggestion in unique_suggestions:
            if any(
                keyword in suggestion.lower() for keyword in ["error", "debug", "fix"]
            ):
                prioritized.append(suggestion)

        # Medium priority: development workflow
        for suggestion in unique_suggestions:
            if suggestion not in prioritized and any(
                keyword in suggestion.lower()
                for keyword in ["test", "review", "verify"]
            ):
                prioritized.append(suggestion)

        # Lower priority: enhancements
        for suggestion in unique_suggestions:
            if suggestion not in prioritized:
                prioritized.append(suggestion)

        # Return top 3-4 most relevant suggestions
        return prioritized[:4]

    def create_follow_up_keyboard(self, suggestions: List[str]) -> InlineKeyboardMarkup:
        """Create keyboard with follow-up suggestions."""
        if not suggestions:
            return InlineKeyboardMarkup([])

        keyboard = []

        # Add suggestion buttons (max 4, in rows of 1 for better mobile experience)
        for suggestion in suggestions[:4]:
            # Create a shorter hash for callback data
            suggestion_hash = str(hash(suggestion) % 1000000)
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"💡 {suggestion}", callback_data=f"followup:{suggestion_hash}"
                    )
                ]
            )

        # Add control buttons
        keyboard.append(
            [
                InlineKeyboardButton(
                    "✅ Continue Coding", callback_data="conversation:continue"
                ),
                InlineKeyboardButton(
                    "🛑 End Session", callback_data="conversation:end"
                ),
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    def should_show_suggestions(self, response: ClaudeResponse) -> bool:
        """Determine if follow-up suggestions should be shown."""
        # Don't show suggestions for errors
        if response.is_error:
            return False

        # Show suggestions if tools were used
        if response.tools_used:
            return True

        # Show suggestions for longer responses (likely more substantial)
        if len(response.content) > 200:
            return True

        # Show suggestions if response contains actionable content
        actionable_keywords = [
            "todo",
            "fixme",
            "next",
            "consider",
            "you can",
            "you could",
            "try",
            "test",
            "check",
            "verify",
            "review",
        ]

        content_lower = response.content.lower()
        return any(keyword in content_lower for keyword in actionable_keywords)

    def format_response_with_suggestions(
        self,
        response: ClaudeResponse,
        context: ConversationContext,
        max_content_length: int = 3000,
    ) -> tuple[str, Optional[InlineKeyboardMarkup]]:
        """Format response with follow-up suggestions."""
        # Truncate content if too long for Telegram
        content = response.content
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n\n... _(response truncated)_"

        # Add session info if this is a new session
        if context.conversation_turn == 1 and response.session_id:
            session_info = f"\n\n🆔 **Session:** `{response.session_id[:8]}...`"
            content += session_info

        # Add cost info if significant
        if response.cost > 0.01:
            cost_info = f"\n\n💰 **Cost:** ${response.cost:.4f}"
            content += cost_info

        # Generate follow-up suggestions
        keyboard = None
        if self.should_show_suggestions(response):
            suggestions = self.generate_follow_up_suggestions(response, context)
            if suggestions:
                keyboard = self.create_follow_up_keyboard(suggestions)
                logger.debug(
                    "Generated follow-up suggestions",
                    user_id=context.user_id,
                    suggestions=suggestions,
                )

        return content, keyboard

    def clear_context(self, user_id: int) -> None:
        """Clear conversation context for user."""
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]
            logger.debug("Cleared conversation context", user_id=user_id)

    def get_context_summary(self, user_id: int) -> Optional[Dict]:
        """Get summary of conversation context."""
        context = self.conversation_contexts.get(user_id)
        if not context:
            return None

        return {
            "session_id": context.session_id,
            "project_path": context.project_path,
            "conversation_turn": context.conversation_turn,
            "last_tools_used": context.last_tools_used,
            "has_errors": context.has_errors,
            "todo_count": context.todo_count,
            "active_files_count": len(context.active_files),
        }

```

### src\bot\features\file_handler.py

**Розмір:** 16,716 байт

```python
"""
Advanced file handling

Features:
- Multiple file processing
- Zip archive extraction
- Code analysis
- Diff generation
"""

import shutil
import tarfile
import uuid
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from telegram import Document

from src.config import Settings
from src.security.validators import SecurityValidator


@dataclass
class ProcessedFile:
    """Processed file result"""

    type: str
    prompt: str
    metadata: Dict[str, any]


@dataclass
class CodebaseAnalysis:
    """Codebase analysis result"""

    languages: Dict[str, int]
    frameworks: List[str]
    entry_points: List[str]
    todo_count: int
    test_coverage: bool
    file_stats: Dict[str, int]


class FileHandler:
    """Handle various file operations"""

    def __init__(self, config: Settings, security: SecurityValidator):
        self.config = config
        self.security = security
        self.temp_dir = Path("/tmp/claude_bot_files")
        self.temp_dir.mkdir(exist_ok=True)

        # Supported code extensions
        self.code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".scala",
            ".r",
            ".jl",
            ".lua",
            ".pl",
            ".sh",
            ".bash",
            ".zsh",
            ".fish",
            ".ps1",
            ".sql",
            ".html",
            ".css",
            ".scss",
            ".sass",
            ".less",
            ".vue",
            ".yaml",
            ".yml",
            ".json",
            ".xml",
            ".toml",
            ".ini",
            ".cfg",
            ".dockerfile",
            ".makefile",
            ".cmake",
            ".gradle",
            ".maven",
        }

        # Language mapping
        self.language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
            ".r": "R",
            ".jl": "Julia",
            ".lua": "Lua",
            ".pl": "Perl",
            ".sh": "Shell",
            ".sql": "SQL",
            ".html": "HTML",
            ".css": "CSS",
            ".vue": "Vue",
            ".yaml": "YAML",
            ".json": "JSON",
            ".xml": "XML",
        }

    async def handle_document_upload(
        self, document: Document, user_id: int, context: str = ""
    ) -> ProcessedFile:
        """Process uploaded document"""

        # Download file
        file_path = await self._download_file(document)

        try:
            # Detect file type
            file_type = self._detect_file_type(file_path)

            # Process based on type
            if file_type == "archive":
                return await self._process_archive(file_path, context)
            elif file_type == "code":
                return await self._process_code_file(file_path, context)
            elif file_type == "text":
                return await self._process_text_file(file_path, context)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

        finally:
            # Cleanup
            file_path.unlink(missing_ok=True)

    async def _download_file(self, document: Document) -> Path:
        """Download file from Telegram"""
        # Get file
        file = await document.get_file()

        # Create temp file path
        file_name = document.file_name or f"file_{uuid.uuid4()}"
        file_path = self.temp_dir / file_name

        # Download to path
        await file.download_to_drive(str(file_path))

        return file_path

    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type based on extension and content"""
        ext = file_path.suffix.lower()

        # Check if archive
        if ext in {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z"}:
            return "archive"

        # Check if code
        if ext in self.code_extensions:
            return "code"

        # Check if text
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                f.read(1024)  # Try reading first 1KB
            return "text"
        except (UnicodeDecodeError, IOError):
            return "binary"

    async def _process_archive(self, archive_path: Path, context: str) -> ProcessedFile:
        """Extract and analyze archive contents"""

        # Create extraction directory
        extract_dir = self.temp_dir / f"extract_{uuid.uuid4()}"
        extract_dir.mkdir()

        try:
            # Extract based on type
            if archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path) as zf:
                    # Security check - prevent zip bombs
                    total_size = sum(f.file_size for f in zf.filelist)
                    if total_size > 100 * 1024 * 1024:  # 100MB limit
                        raise ValueError("Archive too large")

                    # Extract with security checks
                    for file_info in zf.filelist:
                        # Prevent path traversal
                        file_path = Path(file_info.filename)
                        if file_path.is_absolute() or ".." in file_path.parts:
                            continue

                        # Extract file
                        target_path = extract_dir / file_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        with (
                            zf.open(file_info) as source,
                            open(target_path, "wb") as target,
                        ):
                            shutil.copyfileobj(source, target)

            elif archive_path.suffix in {".tar", ".gz", ".bz2", ".xz"}:
                with tarfile.open(archive_path) as tf:
                    # Security checks
                    total_size = sum(member.size for member in tf.getmembers())
                    if total_size > 100 * 1024 * 1024:  # 100MB limit
                        raise ValueError("Archive too large")

                    # Extract with security checks
                    for member in tf.getmembers():
                        # Prevent path traversal
                        if member.name.startswith("/") or ".." in member.name:
                            continue

                        tf.extract(member, extract_dir)

            # Analyze contents
            file_tree = self._build_file_tree(extract_dir)
            code_files = self._find_code_files(extract_dir)

            # Create analysis prompt
            prompt = f"{context}\n\nProject structure:\n{file_tree}\n\n"

            # Add key files
            for file_path in code_files[:5]:  # Limit to 5 files
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                prompt += f"\nFile: {file_path.relative_to(extract_dir)}\n```\n{content[:1000]}...\n```\n"

            return ProcessedFile(
                type="archive",
                prompt=prompt,
                metadata={
                    "file_count": len(list(extract_dir.rglob("*"))),
                    "code_files": len(code_files),
                },
            )

        finally:
            # Cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)

    async def _process_code_file(self, file_path: Path, context: str) -> ProcessedFile:
        """Process single code file"""
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        # Detect language
        language = self._detect_language(file_path.suffix)

        # Create prompt
        prompt = f"{context}\n\nFile: {file_path.name}\nLanguage: {language}\n\n```{language.lower()}\n{content}\n```"

        return ProcessedFile(
            type="code",
            prompt=prompt,
            metadata={
                "language": language,
                "lines": len(content.splitlines()),
                "size": file_path.stat().st_size,
            },
        )

    async def _process_text_file(self, file_path: Path, context: str) -> ProcessedFile:
        """Process text file"""
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        # Create prompt
        prompt = f"{context}\n\nFile: {file_path.name}\n\n{content}"

        return ProcessedFile(
            type="text",
            prompt=prompt,
            metadata={
                "lines": len(content.splitlines()),
                "size": file_path.stat().st_size,
            },
        )

    def _build_file_tree(self, directory: Path, prefix: str = "") -> str:
        """Build visual file tree"""
        items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name))
        tree_lines = []

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "

            if item.is_dir():
                tree_lines.append(f"{prefix}{current_prefix}{item.name}/")
                # Recursive call with updated prefix
                sub_prefix = prefix + ("    " if is_last else "│   ")
                tree_lines.append(self._build_file_tree(item, sub_prefix))
            else:
                size = item.stat().st_size
                tree_lines.append(
                    f"{prefix}{current_prefix}{item.name} ({self._format_size(size)})"
                )

        return "\n".join(filter(None, tree_lines))

    def _format_size(self, size: int) -> str:
        """Format file size for display"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"

    def _find_code_files(self, directory: Path) -> List[Path]:
        """Find all code files in directory"""
        code_files = []

        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.code_extensions:
                # Skip common non-code directories
                if any(
                    part in file_path.parts
                    for part in ["node_modules", "__pycache__", ".git", "dist", "build"]
                ):
                    continue
                code_files.append(file_path)

        # Sort by importance (main files first, then by name)
        def sort_key(path: Path) -> tuple:
            name = path.name.lower()
            # Prioritize main/index files
            if name in [
                "main.py",
                "index.js",
                "app.py",
                "server.py",
                "main.go",
                "main.rs",
            ]:
                return (0, name)
            elif name.startswith("index."):
                return (1, name)
            elif name.startswith("main."):
                return (2, name)
            else:
                return (3, name)

        code_files.sort(key=sort_key)
        return code_files

    def _detect_language(self, extension: str) -> str:
        """Detect programming language from extension"""
        return self.language_map.get(extension.lower(), "text")

    async def analyze_codebase(self, directory: Path) -> CodebaseAnalysis:
        """Analyze entire codebase"""

        analysis = CodebaseAnalysis(
            languages={},
            frameworks=[],
            entry_points=[],
            todo_count=0,
            test_coverage=False,
            file_stats={},
        )

        # Language detection
        language_stats = defaultdict(int)
        file_extensions = defaultdict(int)

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                file_extensions[ext] += 1

                language = self._detect_language(ext)
                if language and language != "text":
                    language_stats[language] += 1

        analysis.languages = dict(language_stats)
        analysis.file_stats = dict(file_extensions)

        # Find entry points
        analysis.entry_points = self._find_entry_points(directory)

        # Detect frameworks
        analysis.frameworks = self._detect_frameworks(directory)

        # Find TODOs and FIXMEs
        analysis.todo_count = await self._find_todos(directory)

        # Check for tests
        test_files = self._find_test_files(directory)
        analysis.test_coverage = len(test_files) > 0

        return analysis

    def _find_entry_points(self, directory: Path) -> List[str]:
        """Find likely entry points in the codebase"""
        entry_points = []

        # Common entry point patterns
        patterns = [
            "main.py",
            "app.py",
            "server.py",
            "__main__.py",
            "index.js",
            "app.js",
            "server.js",
            "main.js",
            "main.go",
            "main.rs",
            "main.cpp",
            "main.c",
            "Main.java",
            "App.java",
            "index.php",
            "index.html",
        ]

        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    entry_points.append(str(file_path.relative_to(directory)))

        return entry_points

    def _detect_frameworks(self, directory: Path) -> List[str]:
        """Detect frameworks and libraries used"""
        frameworks = []

        # Framework indicators
        indicators = {
            "package.json": ["React", "Vue", "Angular", "Express", "Next.js"],
            "requirements.txt": ["Django", "Flask", "FastAPI", "PyTorch", "TensorFlow"],
            "Cargo.toml": ["Tokio", "Actix", "Rocket"],
            "go.mod": ["Gin", "Echo", "Fiber"],
            "pom.xml": ["Spring", "Maven"],
            "build.gradle": ["Spring", "Gradle"],
            "composer.json": ["Laravel", "Symfony"],
            "Gemfile": ["Rails", "Sinatra"],
        }

        for indicator_file, possible_frameworks in indicators.items():
            file_path = directory / indicator_file
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
                for framework in possible_frameworks:
                    if framework.lower() in content:
                        frameworks.append(framework)

        # Check for specific framework files
        if (directory / "manage.py").exists():
            frameworks.append("Django")
        if (directory / "artisan").exists():
            frameworks.append("Laravel")
        if (directory / "next.config.js").exists():
            frameworks.append("Next.js")

        return list(set(frameworks))  # Remove duplicates

    async def _find_todos(self, directory: Path) -> int:
        """Count TODO and FIXME comments"""
        todo_count = 0

        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.code_extensions:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    # Count TODOs and FIXMEs
                    todo_count += content.upper().count("TODO")
                    todo_count += content.upper().count("FIXME")
                except Exception:
                    continue

        return todo_count

    def _find_test_files(self, directory: Path) -> List[Path]:
        """Find test files in the codebase"""
        test_files = []

        # Common test patterns
        test_patterns = [
            "test_*.py",
            "*_test.py",
            "*_test.go",
            "*.test.js",
            "*.spec.js",
            "*.test.ts",
            "*.spec.ts",
        ]

        for pattern in test_patterns:
            test_files.extend(directory.rglob(pattern))

        # Check test directories
        for test_dir_name in ["test", "tests", "__tests__", "spec"]:
            test_dir = directory / test_dir_name
            if test_dir.exists() and test_dir.is_dir():
                test_files.extend(test_dir.rglob("*"))

        return [f for f in test_files if f.is_file()]

```

### src\bot\features\git_integration.py

**Розмір:** 12,632 байт

```python
"""Git integration for safe repository operations."""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

from src.config.settings import Settings
from src.exceptions import SecurityError

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Git operation error."""

    pass


@dataclass
class GitStatus:
    """Git repository status."""

    branch: str
    modified: List[str]
    added: List[str]
    deleted: List[str]
    untracked: List[str]
    ahead: int
    behind: int

    @property
    def is_clean(self) -> bool:
        """Check if working directory is clean."""
        return not any([self.modified, self.added, self.deleted, self.untracked])


@dataclass
class CommitInfo:
    """Git commit information."""

    hash: str
    author: str
    date: datetime
    message: str
    files_changed: int
    insertions: int
    deletions: int


class GitIntegration:
    """Safe git integration for repositories."""

    # Safe git commands allowed
    SAFE_COMMANDS: Set[str] = {
        "status",
        "log",
        "diff",
        "branch",
        "remote",
        "show",
        "ls-files",
        "ls-tree",
        "rev-parse",
        "rev-list",
        "describe",
    }

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r"--exec",
        r"--upload-pack",
        r"--receive-pack",
        r"-c\s*core\.gitProxy",
        r"-c\s*core\.sshCommand",
    ]

    def __init__(self, settings: Settings):
        """Initialize git integration.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.approved_dir = Path(settings.approved_directory)

    async def execute_git_command(
        self, command: List[str], cwd: Path
    ) -> Tuple[str, str]:
        """Execute safe git command.

        Args:
            command: Git command parts
            cwd: Working directory

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            SecurityError: If command is unsafe
            GitError: If git command fails
        """
        # Validate command safety
        if not command or command[0] != "git":
            raise SecurityError("Only git commands allowed")

        if len(command) < 2 or command[1] not in self.SAFE_COMMANDS:
            raise SecurityError(f"Unsafe git command: {command[1]}")

        # Check for dangerous patterns
        cmd_str = " ".join(command)
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_str, re.IGNORECASE):
                raise SecurityError(f"Dangerous pattern detected: {pattern}")

        # Validate working directory
        try:
            cwd = cwd.resolve()
            if not cwd.is_relative_to(self.approved_dir):
                raise SecurityError("Repository outside approved directory")
        except Exception:
            raise SecurityError("Invalid repository path")

        # Execute command
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise GitError(f"Git command failed: {stderr.decode()}")

            return stdout.decode(), stderr.decode()

        except asyncio.TimeoutError:
            raise GitError("Git command timed out")
        except Exception as e:
            logger.error(f"Git command error: {e}")
            raise GitError(f"Failed to execute git command: {e}")

    async def get_status(self, repo_path: Path) -> GitStatus:
        """Get repository status.

        Args:
            repo_path: Repository path

        Returns:
            Git status information
        """
        # Get branch and tracking info
        branch_out, _ = await self.execute_git_command(
            ["git", "branch", "--show-current"], repo_path
        )
        branch = branch_out.strip() or "HEAD"

        # Get file status
        status_out, _ = await self.execute_git_command(
            ["git", "status", "--porcelain=v1"], repo_path
        )

        modified = []
        added = []
        deleted = []
        untracked = []

        for line in status_out.strip().split("\n"):
            if not line:
                continue

            status = line[:2]
            filename = line[3:]

            if status == "??":
                untracked.append(filename)
            elif "M" in status:
                modified.append(filename)
            elif "A" in status:
                added.append(filename)
            elif "D" in status:
                deleted.append(filename)

        # Get ahead/behind counts
        ahead = behind = 0
        try:
            # Try to get upstream tracking info
            rev_out, _ = await self.execute_git_command(
                ["git", "rev-list", "--count", "--left-right", "HEAD...@{upstream}"],
                repo_path,
            )
            if rev_out.strip():
                parts = rev_out.strip().split("\t")
                if len(parts) == 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
        except GitError:
            # No upstream configured
            pass

        return GitStatus(
            branch=branch,
            modified=modified,
            added=added,
            deleted=deleted,
            untracked=untracked,
            ahead=ahead,
            behind=behind,
        )

    async def get_diff(
        self, repo_path: Path, staged: bool = False, file_path: Optional[str] = None
    ) -> str:
        """Get repository diff.

        Args:
            repo_path: Repository path
            staged: Show staged changes
            file_path: Specific file to diff

        Returns:
            Formatted diff output
        """
        command = ["git", "diff"]

        if staged:
            command.append("--staged")

        # Add formatting options
        command.extend(["--no-color", "--minimal"])

        if file_path:
            # Validate file path
            file_path_obj = (repo_path / file_path).resolve()
            if not file_path_obj.is_relative_to(repo_path):
                raise SecurityError("File path outside repository")
            command.append(file_path)

        diff_out, _ = await self.execute_git_command(command, repo_path)

        if not diff_out.strip():
            return "No changes to show"

        # Format diff with indicators
        lines = []
        for line in diff_out.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(f"➕ {line[1:]}")
            elif line.startswith("-") and not line.startswith("---"):
                lines.append(f"➖ {line[1:]}")
            elif line.startswith("@@"):
                lines.append(f"📍 {line}")
            else:
                lines.append(line)

        return "\n".join(lines)

    async def get_file_history(
        self, repo_path: Path, file_path: str, limit: int = 10
    ) -> List[CommitInfo]:
        """Get file commit history.

        Args:
            repo_path: Repository path
            file_path: File to get history for
            limit: Maximum commits to return

        Returns:
            List of commit information
        """
        # Validate file path
        file_path_obj = (repo_path / file_path).resolve()
        if not file_path_obj.is_relative_to(repo_path):
            raise SecurityError("File path outside repository")

        # Get commit log with stats
        log_out, _ = await self.execute_git_command(
            [
                "git",
                "log",
                f"--max-count={limit}",
                "--pretty=format:%H|%an|%aI|%s",
                "--numstat",
                "--",
                file_path,
            ],
            repo_path,
        )

        commits = []
        current_commit = None

        for line in log_out.strip().split("\n"):
            if not line:
                continue

            if "|" in line and len(line.split("|")) == 4:
                # Commit info line
                parts = line.split("|")

                if current_commit:
                    commits.append(current_commit)

                current_commit = CommitInfo(
                    hash=parts[0][:8],  # Short hash
                    author=parts[1],
                    date=datetime.fromisoformat(parts[2].replace("Z", "+00:00")),
                    message=parts[3],
                    files_changed=0,
                    insertions=0,
                    deletions=0,
                )
            elif current_commit and "\t" in line:
                # Numstat line
                parts = line.split("\t")
                if len(parts) == 3:
                    try:
                        insertions = int(parts[0]) if parts[0] != "-" else 0
                        deletions = int(parts[1]) if parts[1] != "-" else 0
                        current_commit.insertions += insertions
                        current_commit.deletions += deletions
                        current_commit.files_changed += 1
                    except ValueError:
                        pass

        if current_commit:
            commits.append(current_commit)

        return commits

    def format_status(self, status: GitStatus) -> str:
        """Format git status for display.

        Args:
            status: Git status object

        Returns:
            Formatted status string
        """
        lines = [f"🌿 Branch: {status.branch}"]

        # Add tracking info
        if status.ahead or status.behind:
            tracking = []
            if status.ahead:
                tracking.append(f"↑{status.ahead}")
            if status.behind:
                tracking.append(f"↓{status.behind}")
            lines.append(f"📊 Tracking: {' '.join(tracking)}")

        if status.is_clean:
            lines.append("✅ Working tree clean")
        else:
            if status.modified:
                lines.append(f"📝 Modified: {len(status.modified)} files")
                for f in status.modified[:5]:  # Show first 5
                    lines.append(f"  • {f}")
                if len(status.modified) > 5:
                    lines.append(f"  ... and {len(status.modified) - 5} more")

            if status.added:
                lines.append(f"➕ Added: {len(status.added)} files")
                for f in status.added[:5]:
                    lines.append(f"  • {f}")
                if len(status.added) > 5:
                    lines.append(f"  ... and {len(status.added) - 5} more")

            if status.deleted:
                lines.append(f"➖ Deleted: {len(status.deleted)} files")
                for f in status.deleted[:5]:
                    lines.append(f"  • {f}")
                if len(status.deleted) > 5:
                    lines.append(f"  ... and {len(status.deleted) - 5} more")

            if status.untracked:
                lines.append(f"❓ Untracked: {len(status.untracked)} files")
                for f in status.untracked[:5]:
                    lines.append(f"  • {f}")
                if len(status.untracked) > 5:
                    lines.append(f"  ... and {len(status.untracked) - 5} more")

        return "\n".join(lines)

    def format_history(self, commits: List[CommitInfo]) -> str:
        """Format commit history for display.

        Args:
            commits: List of commits

        Returns:
            Formatted history string
        """
        if not commits:
            return "No commit history found"

        lines = ["📜 Commit History:"]

        for commit in commits:
            lines.append(
                f"\n🔹 {commit.hash} - {commit.date.strftime('%Y-%m-%d %H:%M')}"
            )
            lines.append(f"   👤 {commit.author}")
            lines.append(f"   💬 {commit.message}")

            if commit.files_changed:
                stats = []
                if commit.insertions:
                    stats.append(f"+{commit.insertions}")
                if commit.deletions:
                    stats.append(f"-{commit.deletions}")
                lines.append(
                    f"   📊 {commit.files_changed} files changed, {' '.join(stats)}"
                )

        return "\n".join(lines)

```

### src\bot\features\image_handler.py

**Розмір:** 5,555 байт

```python
"""
Handle image uploads for UI/screenshot analysis

Features:
- OCR for text extraction
- UI element detection
- Image description
- Diagram analysis
"""

import base64
from dataclasses import dataclass
from typing import Dict, Optional

from telegram import PhotoSize

from src.config import Settings


@dataclass
class ProcessedImage:
    """Processed image result"""

    prompt: str
    image_type: str
    base64_data: str
    size: int
    metadata: Dict[str, any] = None


class ImageHandler:
    """Process image uploads"""

    def __init__(self, config: Settings):
        self.config = config
        self.supported_formats = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    async def process_image(
        self, photo: PhotoSize, caption: Optional[str] = None
    ) -> ProcessedImage:
        """Process uploaded image"""

        # Download image
        file = await photo.get_file()
        image_bytes = await file.download_as_bytearray()

        # Detect image type
        image_type = self._detect_image_type(image_bytes)

        # Create appropriate prompt
        if image_type == "screenshot":
            prompt = self._create_screenshot_prompt(caption)
        elif image_type == "diagram":
            prompt = self._create_diagram_prompt(caption)
        elif image_type == "ui_mockup":
            prompt = self._create_ui_prompt(caption)
        else:
            prompt = self._create_generic_prompt(caption)

        # Convert to base64 for Claude (if supported in future)
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        return ProcessedImage(
            prompt=prompt,
            image_type=image_type,
            base64_data=base64_image,
            size=len(image_bytes),
            metadata={
                "format": self._detect_format(image_bytes),
                "has_caption": caption is not None,
            },
        )

    def _detect_image_type(self, image_bytes: bytes) -> str:
        """Detect type of image"""
        # Simple heuristic based on image characteristics
        # In practice, could use ML model for better detection

        # For now, return generic type
        return "screenshot"

    def _detect_format(self, image_bytes: bytes) -> str:
        """Detect image format from magic bytes"""
        # Check magic bytes for common formats
        if image_bytes.startswith(b"\x89PNG"):
            return "png"
        elif image_bytes.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        elif image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
            return "gif"
        elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:12]:
            return "webp"
        else:
            return "unknown"

    def _create_screenshot_prompt(self, caption: Optional[str]) -> str:
        """Create prompt for screenshot analysis"""
        base_prompt = """I'm sharing a screenshot with you. Please analyze it and help me with:

1. Identifying what application or website this is from
2. Understanding the UI elements and their purpose
3. Any issues or improvements you notice
4. Answering any specific questions I have

"""
        if caption:
            base_prompt += f"Specific request: {caption}"

        return base_prompt

    def _create_diagram_prompt(self, caption: Optional[str]) -> str:
        """Create prompt for diagram analysis"""
        base_prompt = """I'm sharing a diagram with you. Please help me:

1. Understand the components and their relationships
2. Identify the type of diagram (flowchart, architecture, etc.)
3. Explain any technical concepts shown
4. Suggest improvements or clarifications

"""
        if caption:
            base_prompt += f"Specific request: {caption}"

        return base_prompt

    def _create_ui_prompt(self, caption: Optional[str]) -> str:
        """Create prompt for UI mockup analysis"""
        base_prompt = """I'm sharing a UI mockup with you. Please analyze:

1. The layout and visual hierarchy
2. User experience considerations
3. Accessibility aspects
4. Implementation suggestions
5. Any potential improvements

"""
        if caption:
            base_prompt += f"Specific request: {caption}"

        return base_prompt

    def _create_generic_prompt(self, caption: Optional[str]) -> str:
        """Create generic image analysis prompt"""
        base_prompt = """I'm sharing an image with you. Please analyze it and provide relevant insights.

"""
        if caption:
            base_prompt += f"Context: {caption}"

        return base_prompt

    def supports_format(self, filename: str) -> bool:
        """Check if image format is supported"""
        if not filename:
            return False

        # Extract extension
        parts = filename.lower().split(".")
        if len(parts) < 2:
            return False

        extension = f".{parts[-1]}"
        return extension in self.supported_formats

    async def validate_image(self, image_bytes: bytes) -> tuple[bool, Optional[str]]:
        """Validate image data"""
        # Check size
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > max_size:
            return False, "Image too large (max 10MB)"

        # Check format
        format_type = self._detect_format(image_bytes)
        if format_type == "unknown":
            return False, "Unsupported image format"

        # Basic validity check
        if len(image_bytes) < 100:  # Too small to be a real image
            return False, "Invalid image data"

        return True, None

```

### src\bot\features\quick_actions.py

**Розмір:** 8,782 байт

```python
"""Quick Actions feature implementation.

Provides context-aware quick action suggestions for common development tasks.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.storage.models import SessionModel

logger = logging.getLogger(__name__)


@dataclass
class QuickAction:
    """Represents a quick action suggestion."""

    id: str
    name: str
    description: str
    command: str
    icon: str
    category: str
    context_required: List[str]  # Required context keys
    priority: int = 0  # Higher = more important


class QuickActionManager:
    """Manages quick action suggestions based on context."""

    def __init__(self) -> None:
        """Initialize the quick action manager."""
        self.actions = self._create_default_actions()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _create_default_actions(self) -> Dict[str, QuickAction]:
        """Create default quick actions."""
        return {
            "test": QuickAction(
                id="test",
                name="Run Tests",
                description="Run project tests",
                command="test",
                icon="🧪",
                category="testing",
                context_required=["has_tests"],
                priority=10,
            ),
            "install": QuickAction(
                id="install",
                name="Install Dependencies",
                description="Install project dependencies",
                command="install",
                icon="📦",
                category="setup",
                context_required=["has_package_manager"],
                priority=9,
            ),
            "format": QuickAction(
                id="format",
                name="Format Code",
                description="Format code with project formatter",
                command="format",
                icon="🎨",
                category="quality",
                context_required=["has_formatter"],
                priority=7,
            ),
            "lint": QuickAction(
                id="lint",
                name="Lint Code",
                description="Check code quality",
                command="lint",
                icon="🔍",
                category="quality",
                context_required=["has_linter"],
                priority=8,
            ),
            "security": QuickAction(
                id="security",
                name="Security Scan",
                description="Run security vulnerability scan",
                command="security",
                icon="🔒",
                category="security",
                context_required=["has_dependencies"],
                priority=6,
            ),
            "optimize": QuickAction(
                id="optimize",
                name="Optimize",
                description="Optimize code performance",
                command="optimize",
                icon="⚡",
                category="performance",
                context_required=["has_code"],
                priority=5,
            ),
            "document": QuickAction(
                id="document",
                name="Generate Docs",
                description="Generate documentation",
                command="document",
                icon="📝",
                category="documentation",
                context_required=["has_code"],
                priority=4,
            ),
            "refactor": QuickAction(
                id="refactor",
                name="Refactor",
                description="Suggest code improvements",
                command="refactor",
                icon="🔧",
                category="quality",
                context_required=["has_code"],
                priority=3,
            ),
        }

    async def get_suggestions(
        self, session: SessionModel, limit: int = 6
    ) -> List[QuickAction]:
        """Get quick action suggestions based on session context.

        Args:
            session: Current session
            limit: Maximum number of suggestions

        Returns:
            List of suggested actions
        """
        try:
            # Analyze context
            context = await self._analyze_context(session)

            # Filter actions based on context
            available_actions = []
            for action in self.actions.values():
                if self._is_action_available(action, context):
                    available_actions.append(action)

            # Sort by priority and return top N
            available_actions.sort(key=lambda x: x.priority, reverse=True)
            return available_actions[:limit]

        except Exception as e:
            self.logger.error(f"Error getting suggestions: {e}")
            return []

    async def _analyze_context(self, session: SessionModel) -> Dict[str, Any]:
        """Analyze session context to determine available actions.

        Args:
            session: Current session

        Returns:
            Context dictionary
        """
        context = {
            "has_code": True,  # Default assumption
            "has_tests": False,
            "has_package_manager": False,
            "has_formatter": False,
            "has_linter": False,
            "has_dependencies": False,
        }

        # Analyze recent messages for context clues
        if session.context:
            recent_messages = session.context.get("recent_messages", [])
            for msg in recent_messages:
                content = msg.get("content", "").lower()

                # Check for test indicators
                if any(word in content for word in ["test", "pytest", "unittest"]):
                    context["has_tests"] = True

                # Check for package manager indicators
                if any(word in content for word in ["pip", "poetry", "npm", "yarn"]):
                    context["has_package_manager"] = True
                    context["has_dependencies"] = True

                # Check for formatter indicators
                if any(word in content for word in ["black", "prettier", "format"]):
                    context["has_formatter"] = True

                # Check for linter indicators
                if any(
                    word in content for word in ["flake8", "pylint", "eslint", "mypy"]
                ):
                    context["has_linter"] = True

        # File-based context analysis could be added here
        # For now, we'll use heuristics based on session history

        return context

    def _is_action_available(
        self, action: QuickAction, context: Dict[str, Any]
    ) -> bool:
        """Check if an action is available in the given context.

        Args:
            action: The action to check
            context: Current context

        Returns:
            True if action is available
        """
        # Check all required context keys
        for key in action.context_required:
            if not context.get(key, False):
                return False
        return True

    def create_inline_keyboard(
        self, actions: List[QuickAction], columns: int = 2
    ) -> InlineKeyboardMarkup:
        """Create inline keyboard for quick actions.

        Args:
            actions: List of actions to display
            columns: Number of columns in keyboard

        Returns:
            Inline keyboard markup
        """
        keyboard = []
        row = []

        for i, action in enumerate(actions):
            button = InlineKeyboardButton(
                text=f"{action.icon} {action.name}",
                callback_data=f"quick_action:{action.id}",
            )
            row.append(button)

            # Add row when full or last item
            if len(row) >= columns or i == len(actions) - 1:
                keyboard.append(row)
                row = []

        return InlineKeyboardMarkup(keyboard)

    async def execute_action(
        self, action_id: str, session: SessionModel, callback: Optional[Callable] = None
    ) -> str:
        """Execute a quick action.

        Args:
            action_id: ID of action to execute
            session: Current session
            callback: Optional callback for command execution

        Returns:
            Command to execute
        """
        action = self.actions.get(action_id)
        if not action:
            raise ValueError(f"Unknown action: {action_id}")

        self.logger.info(
            f"Executing quick action: {action.name} for session {session.id}"
        )

        # Return the command - actual execution is handled by the bot
        return action.command

```

### src\bot\features\registry.py

**Розмір:** 4,981 байт

```python
"""
Central feature registry and management
"""

from typing import Any, Dict, Optional

import structlog

from src.config.settings import Settings
from src.security.validators import SecurityValidator
from src.storage.facade import Storage

from .conversation_mode import ConversationEnhancer
from .file_handler import FileHandler
from .git_integration import GitIntegration
from .image_handler import ImageHandler
from .quick_actions import QuickActionManager
from .session_export import SessionExporter

logger = structlog.get_logger(__name__)


class FeatureRegistry:
    """Manage all bot features"""

    def __init__(self, config: Settings, storage: Storage, security: SecurityValidator):
        self.config = config
        self.storage = storage
        self.security = security
        self.features: Dict[str, Any] = {}

        # Initialize features based on config
        self._initialize_features()

    def _initialize_features(self):
        """Initialize enabled features"""
        logger.info("Initializing bot features")

        # File upload handling - conditionally enabled
        if self.config.enable_file_uploads:
            try:
                self.features["file_handler"] = FileHandler(
                    config=self.config, security=self.security
                )
                logger.info("File handler feature enabled")
            except Exception as e:
                logger.error("Failed to initialize file handler", error=str(e))

        # Git integration - conditionally enabled
        if self.config.enable_git_integration:
            try:
                self.features["git"] = GitIntegration(settings=self.config)
                logger.info("Git integration feature enabled")
            except Exception as e:
                logger.error("Failed to initialize git integration", error=str(e))

        # Quick actions - conditionally enabled
        if self.config.enable_quick_actions:
            try:
                self.features["quick_actions"] = QuickActionManager()
                logger.info("Quick actions feature enabled")
            except Exception as e:
                logger.error("Failed to initialize quick actions", error=str(e))

        # Session export - always enabled
        try:
            self.features["session_export"] = SessionExporter(storage=self.storage)
            logger.info("Session export feature enabled")
        except Exception as e:
            logger.error("Failed to initialize session export", error=str(e))

        # Image handling - always enabled
        try:
            self.features["image_handler"] = ImageHandler(config=self.config)
            logger.info("Image handler feature enabled")
        except Exception as e:
            logger.error("Failed to initialize image handler", error=str(e))

        # Conversation enhancements - always enabled
        try:
            self.features["conversation"] = ConversationEnhancer()
            logger.info("Conversation enhancer feature enabled")
        except Exception as e:
            logger.error("Failed to initialize conversation enhancer", error=str(e))

        logger.info(
            "Feature initialization complete",
            enabled_features=list(self.features.keys()),
        )

    def get_feature(self, name: str) -> Optional[Any]:
        """Get feature by name"""
        return self.features.get(name)

    def is_enabled(self, feature_name: str) -> bool:
        """Check if feature is enabled"""
        return feature_name in self.features

    def get_file_handler(self) -> Optional[FileHandler]:
        """Get file handler feature"""
        return self.get_feature("file_handler")

    def get_git_integration(self) -> Optional[GitIntegration]:
        """Get git integration feature"""
        return self.get_feature("git")

    def get_quick_actions(self) -> Optional[QuickActionManager]:
        """Get quick actions feature"""
        return self.get_feature("quick_actions")

    def get_session_export(self) -> Optional[SessionExporter]:
        """Get session export feature"""
        return self.get_feature("session_export")

    def get_image_handler(self) -> Optional[ImageHandler]:
        """Get image handler feature"""
        return self.get_feature("image_handler")

    def get_conversation_enhancer(self) -> Optional[ConversationEnhancer]:
        """Get conversation enhancer feature"""
        return self.get_feature("conversation")

    def get_enabled_features(self) -> Dict[str, Any]:
        """Get all enabled features"""
        return self.features.copy()

    def shutdown(self):
        """Shutdown all features"""
        logger.info("Shutting down features")

        # Clear conversation contexts
        conversation = self.get_conversation_enhancer()
        if conversation:
            conversation.conversation_contexts.clear()

        # Clear feature registry
        self.features.clear()

        logger.info("Feature shutdown complete")

```

### src\bot\features\session_export.py

**Розмір:** 8,641 байт

```python
"""Session export functionality for exporting chat history in various formats."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from src.storage.facade import Storage
from src.utils.constants import MAX_SESSION_LENGTH


class ExportFormat(Enum):
    """Supported export formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


@dataclass
class ExportedSession:
    """Exported session data."""

    format: ExportFormat
    content: str
    filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class SessionExporter:
    """Handles exporting chat sessions in various formats."""

    def __init__(self, storage: Storage):
        """Initialize exporter with storage dependency.

        Args:
            storage: Storage facade for session data access
        """
        self.storage = storage

    async def export_session(
        self,
        user_id: int,
        session_id: str,
        format: ExportFormat = ExportFormat.MARKDOWN,
    ) -> ExportedSession:
        """Export a session in the specified format.

        Args:
            user_id: User ID
            session_id: Session ID to export
            format: Export format (markdown, json, html)

        Returns:
            ExportedSession with exported content

        Raises:
            ValueError: If session not found or invalid format
        """
        # Get session data
        session = await self.storage.get_session(user_id, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get session messages
        messages = await self.storage.get_session_messages(
            session_id, limit=MAX_SESSION_LENGTH
        )

        # Export based on format
        if format == ExportFormat.MARKDOWN:
            content = await self._export_markdown(session, messages)
            mime_type = "text/markdown"
            extension = "md"
        elif format == ExportFormat.JSON:
            content = await self._export_json(session, messages)
            mime_type = "application/json"
            extension = "json"
        elif format == ExportFormat.HTML:
            content = await self._export_html(session, messages)
            mime_type = "text/html"
            extension = "html"
        else:
            raise ValueError(f"Unsupported export format: {format}")

        # Create filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{session_id[:8]}_{timestamp}.{extension}"

        return ExportedSession(
            format=format,
            content=content,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(content.encode()),
            created_at=datetime.utcnow(),
        )

    async def _export_markdown(self, session: dict, messages: list) -> str:
        """Export session as Markdown.

        Args:
            session: Session metadata
            messages: List of messages

        Returns:
            Markdown formatted content
        """
        lines = []

        # Header
        lines.append(f"# Claude Code Session Export")
        lines.append(f"\n**Session ID:** `{session['id']}`")
        lines.append(f"**Created:** {session['created_at']}")
        if session.get("updated_at"):
            lines.append(f"**Last Updated:** {session['updated_at']}")
        lines.append(f"**Message Count:** {len(messages)}")
        lines.append("\n---\n")

        # Messages
        for msg in messages:
            timestamp = msg["created_at"]
            role = "You" if msg["role"] == "user" else "Claude"
            content = msg["content"]

            lines.append(f"### {role} - {timestamp}")
            lines.append(f"\n{content}\n")
            lines.append("---\n")

        return "\n".join(lines)

    async def _export_json(self, session: dict, messages: list) -> str:
        """Export session as JSON.

        Args:
            session: Session metadata
            messages: List of messages

        Returns:
            JSON formatted content
        """
        export_data = {
            "session": {
                "id": session["id"],
                "user_id": session["user_id"],
                "created_at": session["created_at"].isoformat(),
                "updated_at": (
                    session.get("updated_at", "").isoformat()
                    if session.get("updated_at")
                    else None
                ),
                "message_count": len(messages),
            },
            "messages": [
                {
                    "id": msg["id"],
                    "role": msg["role"],
                    "content": msg["content"],
                    "created_at": msg["created_at"].isoformat(),
                }
                for msg in messages
            ],
        }

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    async def _export_html(self, session: dict, messages: list) -> str:
        """Export session as HTML.

        Args:
            session: Session metadata
            messages: List of messages

        Returns:
            HTML formatted content
        """
        # Convert markdown content to HTML-safe format
        markdown_content = await self._export_markdown(session, messages)
        html_content = self._markdown_to_html(markdown_content)

        # HTML template
        template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Session - {session['id'][:8]}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #34495e;
            margin-top: 20px;
        }}
        code {{
            background-color: #f8f8f8;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #e1e4e8;
        }}
        .metadata {{
            background-color: #f0f7ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .message {{
            margin: 20px 0;
            padding: 15px;
            border-left: 4px solid #3498db;
            background-color: #f9f9f9;
        }}
        .message.claude {{
            border-left-color: #2ecc71;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e1e4e8;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>"""

        return template

    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML.

        Simple conversion for basic markdown elements.

        Args:
            markdown: Markdown content

        Returns:
            HTML content
        """
        html = markdown

        # Headers
        html = html.replace("# ", "<h1>").replace("\n\n", "</h1>\n\n", 1)
        html = html.replace("### ", "<h3>").replace("\n", "</h3>\n", 3)

        # Bold
        import re

        html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)

        # Code blocks
        html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

        # Line breaks and paragraphs
        html = html.replace("\n\n", "</p>\n<p>")
        html = f"<p>{html}</p>"

        # Clean up empty paragraphs
        html = html.replace("<p></p>", "")
        html = html.replace("<p><h", "<h")
        html = html.replace("</h1></p>", "</h1>")
        html = html.replace("</h3></p>", "</h3>")

        # Horizontal rules
        html = html.replace("<p>---</p>", "<hr>")

        return html

```

### src\bot\features\__init__.py

**Розмір:** 306 байт

```python
"""Bot features package"""

from .conversation_mode import ConversationContext, ConversationEnhancer
from .file_handler import CodebaseAnalysis, FileHandler, ProcessedFile

__all__ = [
    "FileHandler",
    "ProcessedFile",
    "CodebaseAnalysis",
    "ConversationEnhancer",
    "ConversationContext",
]

```

### src\bot\handlers\callback.py

**Розмір:** 41,191 байт

```python
"""Handle inline keyboard callbacks."""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ...claude.facade import ClaudeIntegration
from ...config.settings import Settings
from ...security.audit import AuditLogger
from ...security.validators import SecurityValidator

logger = structlog.get_logger()


async def handle_callback_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Route callback queries to appropriate handlers."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    user_id = query.from_user.id
    data = query.data

    logger.info("Processing callback query", user_id=user_id, callback_data=data)

    try:
        # Parse callback data
        if ":" in data:
            action, param = data.split(":", 1)
        else:
            action, param = data, None

        # Route to appropriate handler
        handlers = {
            "cd": handle_cd_callback,
            "action": handle_action_callback,
            "confirm": handle_confirm_callback,
            "quick": handle_quick_action_callback,
            "followup": handle_followup_callback,
            "conversation": handle_conversation_callback,
            "git": handle_git_callback,
            "export": handle_export_callback,
        }

        handler = handlers.get(action)
        if handler:
            await handler(query, param, context)
        else:
            await query.edit_message_text(
                "❌ **Unknown Action**\n\n"
                "This button action is not recognized. "
                "The bot may have been updated since this message was sent."
            )

    except Exception as e:
        logger.error(
            "Error handling callback query",
            error=str(e),
            user_id=user_id,
            callback_data=data,
        )

        try:
            await query.edit_message_text(
                "❌ **Error Processing Action**\n\n"
                "An error occurred while processing your request.\n"
                "Please try again or use text commands."
            )
        except Exception:
            # If we can't edit the message, send a new one
            await query.message.reply_text(
                "❌ **Error Processing Action**\n\n"
                "An error occurred while processing your request."
            )


async def handle_cd_callback(
    query, project_name: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle directory change from inline keyboard."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]
    security_validator: SecurityValidator = context.bot_data.get("security_validator")
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    try:
        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )

        # Handle special paths
        if project_name == "/":
            new_path = settings.approved_directory
        elif project_name == "..":
            new_path = current_dir.parent
            # Ensure we don't go above approved directory
            if not str(new_path).startswith(str(settings.approved_directory)):
                new_path = settings.approved_directory
        else:
            new_path = settings.approved_directory / project_name

        # Validate path if security validator is available
        if security_validator:
            # Pass the absolute path for validation
            valid, resolved_path, error = security_validator.validate_path(
                str(new_path), settings.approved_directory
            )
            if not valid:
                await query.edit_message_text(f"❌ **Access Denied**\n\n{error}")
                return
            # Use the validated path
            new_path = resolved_path

        # Check if directory exists
        if not new_path.exists() or not new_path.is_dir():
            await query.edit_message_text(
                f"❌ **Directory Not Found**\n\n"
                f"The directory `{project_name}` no longer exists or is not accessible."
            )
            return

        # Update directory and clear session
        context.user_data["current_directory"] = new_path
        context.user_data["claude_session_id"] = None

        # Send confirmation with new directory info
        relative_path = new_path.relative_to(settings.approved_directory)

        # Add navigation buttons
        keyboard = [
            [
                InlineKeyboardButton("📁 List Files", callback_data="action:ls"),
                InlineKeyboardButton(
                    "🆕 New Session", callback_data="action:new_session"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📋 Projects", callback_data="action:show_projects"
                ),
                InlineKeyboardButton("📊 Status", callback_data="action:status"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ **Directory Changed**\n\n"
            f"📂 Current directory: `{relative_path}/`\n\n"
            f"🔄 Claude session cleared. You can now start coding in this directory!",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        # Log successful directory change
        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id, command="cd", args=[project_name], success=True
            )

    except Exception as e:
        await query.edit_message_text(f"❌ **Error changing directory**\n\n{str(e)}")

        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id, command="cd", args=[project_name], success=False
            )


async def handle_action_callback(
    query, action_type: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle general action callbacks."""
    actions = {
        "help": _handle_help_action,
        "show_projects": _handle_show_projects_action,
        "new_session": _handle_new_session_action,
        "continue": _handle_continue_action,
        "end_session": _handle_end_session_action,
        "status": _handle_status_action,
        "ls": _handle_ls_action,
        "start_coding": _handle_start_coding_action,
        "quick_actions": _handle_quick_actions_action,
        "refresh_status": _handle_refresh_status_action,
        "refresh_ls": _handle_refresh_ls_action,
        "export": _handle_export_action,
    }

    handler = actions.get(action_type)
    if handler:
        await handler(query, context)
    else:
        await query.edit_message_text(
            f"❌ **Unknown Action: {action_type}**\n\n"
            "This action is not implemented yet."
        )


async def handle_confirm_callback(
    query, confirmation_type: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle confirmation dialogs."""
    if confirmation_type == "yes":
        await query.edit_message_text("✅ **Confirmed**\n\nAction will be processed.")
    elif confirmation_type == "no":
        await query.edit_message_text("❌ **Cancelled**\n\nAction was cancelled.")
    else:
        await query.edit_message_text("❓ **Unknown confirmation response**")


# Action handlers


async def _handle_help_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help action."""
    help_text = (
        "🤖 **Quick Help**\n\n"
        "**Navigation:**\n"
        "• `/ls` - List files\n"
        "• `/cd <dir>` - Change directory\n"
        "• `/projects` - Show projects\n\n"
        "**Sessions:**\n"
        "• `/new` - New Claude session\n"
        "• `/status` - Session status\n\n"
        "**Tips:**\n"
        "• Send any text to interact with Claude\n"
        "• Upload files for code review\n"
        "• Use buttons for quick actions\n\n"
        "Use `/help` for detailed help."
    )

    keyboard = [
        [
            InlineKeyboardButton("📖 Full Help", callback_data="action:full_help"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="action:main_menu"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        help_text, parse_mode="Markdown", reply_markup=reply_markup
    )


async def _handle_show_projects_action(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle show projects action."""
    settings: Settings = context.bot_data["settings"]

    try:
        # Get directories in approved directory
        projects = []
        for item in sorted(settings.approved_directory.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                projects.append(item.name)

        if not projects:
            await query.edit_message_text(
                "📁 **No Projects Found**\n\n"
                "No subdirectories found in your approved directory.\n"
                "Create some directories to organize your projects!"
            )
            return

        # Create project buttons
        keyboard = []
        for i in range(0, len(projects), 2):
            row = []
            for j in range(2):
                if i + j < len(projects):
                    project = projects[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"📁 {project}", callback_data=f"cd:{project}"
                        )
                    )
            keyboard.append(row)

        # Add navigation buttons
        keyboard.append(
            [
                InlineKeyboardButton("🏠 Root", callback_data="cd:/"),
                InlineKeyboardButton(
                    "🔄 Refresh", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        project_list = "\n".join([f"• `{project}/`" for project in projects])

        await query.edit_message_text(
            f"📁 **Available Projects**\n\n"
            f"{project_list}\n\n"
            f"Click a project to navigate to it:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

    except Exception as e:
        await query.edit_message_text(f"❌ Error loading projects: {str(e)}")


async def _handle_new_session_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle new session action."""
    settings: Settings = context.bot_data["settings"]

    # Clear session
    context.user_data["claude_session_id"] = None
    context.user_data["session_started"] = True

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 Start Coding", callback_data="action:start_coding"
            ),
            InlineKeyboardButton(
                "📁 Change Project", callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 Quick Actions", callback_data="action:quick_actions"
            ),
            InlineKeyboardButton("❓ Help", callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🆕 **New Claude Code Session**\n\n"
        f"📂 Working directory: `{relative_path}/`\n\n"
        f"Ready to help you code! Send me a message to get started:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def _handle_end_session_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle end session action."""
    settings: Settings = context.bot_data["settings"]

    # Check if there's an active session
    claude_session_id = context.user_data.get("claude_session_id")

    if not claude_session_id:
        await query.edit_message_text(
            "ℹ️ **No Active Session**\n\n"
            "There's no active Claude session to end.\n\n"
            "**What you can do:**\n"
            "• Use the button below to start a new session\n"
            "• Check your session status\n"
            "• Send any message to start a conversation",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🆕 New Session", callback_data="action:new_session"
                        )
                    ],
                    [InlineKeyboardButton("📊 Status", callback_data="action:status")],
                ]
            ),
        )
        return

    # Get current directory for display
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Clear session data
    context.user_data["claude_session_id"] = None
    context.user_data["session_started"] = False
    context.user_data["last_message"] = None

    # Create quick action buttons
    keyboard = [
        [
            InlineKeyboardButton("🆕 New Session", callback_data="action:new_session"),
            InlineKeyboardButton(
                "📁 Change Project", callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="action:status"),
            InlineKeyboardButton("❓ Help", callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✅ **Session Ended**\n\n"
        f"Your Claude session has been terminated.\n\n"
        f"**Current Status:**\n"
        f"• Directory: `{relative_path}/`\n"
        f"• Session: None\n"
        f"• Ready for new commands\n\n"
        f"**Next Steps:**\n"
        f"• Start a new session\n"
        f"• Check status\n"
        f"• Send any message to begin a new conversation",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def _handle_continue_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle continue session action."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]
    claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        if not claude_integration:
            await query.edit_message_text(
                "❌ **Claude Integration Not Available**\n\n"
                "Claude integration is not properly configured."
            )
            return

        # Check if there's an existing session in user context
        claude_session_id = context.user_data.get("claude_session_id")

        if claude_session_id:
            # Continue with the existing session (no prompt = use --continue)
            await query.edit_message_text(
                f"🔄 **Continuing Session**\n\n"
                f"Session ID: `{claude_session_id[:8]}...`\n"
                f"Directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
                f"Continuing where you left off...",
                parse_mode="Markdown",
            )

            claude_response = await claude_integration.run_command(
                prompt="",  # Empty prompt triggers --continue
                working_directory=current_dir,
                user_id=user_id,
                session_id=claude_session_id,
            )
        else:
            # No session in context, try to find the most recent session
            await query.edit_message_text(
                "🔍 **Looking for Recent Session**\n\n"
                "Searching for your most recent session in this directory...",
                parse_mode="Markdown",
            )

            claude_response = await claude_integration.continue_session(
                user_id=user_id,
                working_directory=current_dir,
                prompt=None,  # No prompt = use --continue
            )

        if claude_response:
            # Update session ID in context
            context.user_data["claude_session_id"] = claude_response.session_id

            # Send Claude's response
            await query.message.reply_text(
                f"✅ **Session Continued**\n\n"
                f"{claude_response.content[:500]}{'...' if len(claude_response.content) > 500 else ''}",
                parse_mode="Markdown",
            )
        else:
            # No session found to continue
            await query.edit_message_text(
                "❌ **No Session Found**\n\n"
                f"No recent Claude session found in this directory.\n"
                f"Directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
                f"**What you can do:**\n"
                f"• Use the button below to start a fresh session\n"
                f"• Check your session status\n"
                f"• Navigate to a different directory",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🆕 New Session", callback_data="action:new_session"
                            ),
                            InlineKeyboardButton(
                                "📊 Status", callback_data="action:status"
                            ),
                        ]
                    ]
                ),
            )

    except Exception as e:
        logger.error("Error in continue action", error=str(e), user_id=user_id)
        await query.edit_message_text(
            f"❌ **Error Continuing Session**\n\n"
            f"An error occurred: `{str(e)}`\n\n"
            f"Try starting a new session instead.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🆕 New Session", callback_data="action:new_session"
                        )
                    ]
                ]
            ),
        )


async def _handle_status_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle status action."""
    # This essentially duplicates the /status command functionality
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]

    claude_session_id = context.user_data.get("claude_session_id")
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Get usage info if rate limiter is available
    rate_limiter = context.bot_data.get("rate_limiter")
    usage_info = ""
    if rate_limiter:
        try:
            user_status = rate_limiter.get_user_status(user_id)
            cost_usage = user_status.get("cost_usage", {})
            current_cost = cost_usage.get("current", 0.0)
            cost_limit = cost_usage.get("limit", settings.claude_max_cost_per_user)
            cost_percentage = (current_cost / cost_limit) * 100 if cost_limit > 0 else 0

            usage_info = f"💰 Usage: ${current_cost:.2f} / ${cost_limit:.2f} ({cost_percentage:.0f}%)\n"
        except Exception:
            usage_info = "💰 Usage: _Unable to retrieve_\n"

    status_lines = [
        "📊 **Session Status**",
        "",
        f"📂 Directory: `{relative_path}/`",
        f"🤖 Claude Session: {'✅ Active' if claude_session_id else '❌ None'}",
        usage_info.rstrip(),
    ]

    if claude_session_id:
        status_lines.append(f"🆔 Session ID: `{claude_session_id[:8]}...`")

    # Add action buttons
    keyboard = []
    if claude_session_id:
        keyboard.append(
            [
                InlineKeyboardButton("🔄 Continue", callback_data="action:continue"),
                InlineKeyboardButton(
                    "🛑 End Session", callback_data="action:end_session"
                ),
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🆕 New Session", callback_data="action:new_session"
                ),
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🆕 Start Session", callback_data="action:new_session"
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_status"),
            InlineKeyboardButton("📁 Projects", callback_data="action:show_projects"),
        ]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "\n".join(status_lines), parse_mode="Markdown", reply_markup=reply_markup
    )


async def _handle_ls_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ls action."""
    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # List directory contents (similar to /ls command)
        items = []
        directories = []
        files = []

        for item in sorted(current_dir.iterdir()):
            if item.name.startswith("."):
                continue

            if item.is_dir():
                directories.append(f"📁 {item.name}/")
            else:
                try:
                    size = item.stat().st_size
                    size_str = _format_file_size(size)
                    files.append(f"📄 {item.name} ({size_str})")
                except OSError:
                    files.append(f"📄 {item.name}")

        items = directories + files
        relative_path = current_dir.relative_to(settings.approved_directory)

        if not items:
            message = f"📂 `{relative_path}/`\n\n_(empty directory)_"
        else:
            message = f"📂 `{relative_path}/`\n\n"
            max_items = 30  # Limit for inline display
            if len(items) > max_items:
                shown_items = items[:max_items]
                message += "\n".join(shown_items)
                message += f"\n\n_... and {len(items) - max_items} more items_"
            else:
                message += "\n".join(items)

        # Add buttons
        keyboard = []
        if current_dir != settings.approved_directory:
            keyboard.append(
                [
                    InlineKeyboardButton("⬆️ Go Up", callback_data="cd:.."),
                    InlineKeyboardButton("🏠 Root", callback_data="cd:/"),
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_ls"),
                InlineKeyboardButton(
                    "📋 Projects", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message, parse_mode="Markdown", reply_markup=reply_markup
        )

    except Exception as e:
        await query.edit_message_text(f"❌ Error listing directory: {str(e)}")


async def _handle_start_coding_action(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle start coding action."""
    await query.edit_message_text(
        "🚀 **Ready to Code!**\n\n"
        "Send me any message to start coding with Claude:\n\n"
        "**Examples:**\n"
        '• _"Create a Python script that..."_\n'
        '• _"Help me debug this code..."_\n'
        '• _"Explain how this file works..."_\n'
        "• Upload a file for review\n\n"
        "I'm here to help with all your coding needs!"
    )


async def _handle_quick_actions_action(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quick actions menu."""
    keyboard = [
        [
            InlineKeyboardButton("🧪 Run Tests", callback_data="quick:test"),
            InlineKeyboardButton("📦 Install Deps", callback_data="quick:install"),
        ],
        [
            InlineKeyboardButton("🎨 Format Code", callback_data="quick:format"),
            InlineKeyboardButton("🔍 Find TODOs", callback_data="quick:find_todos"),
        ],
        [
            InlineKeyboardButton("🔨 Build", callback_data="quick:build"),
            InlineKeyboardButton("🚀 Start Server", callback_data="quick:start"),
        ],
        [
            InlineKeyboardButton("📊 Git Status", callback_data="quick:git_status"),
            InlineKeyboardButton("🔧 Lint Code", callback_data="quick:lint"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="action:new_session")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🛠️ **Quick Actions**\n\n"
        "Choose a common development task:\n\n"
        "_Note: These will be fully functional once Claude Code integration is complete._",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def _handle_refresh_status_action(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle refresh status action."""
    await _handle_status_action(query, context)


async def _handle_refresh_ls_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle refresh ls action."""
    await _handle_ls_action(query, context)


async def _handle_export_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export action."""
    await query.edit_message_text(
        "📤 **Export Session**\n\n"
        "Session export functionality will be available once the storage layer is implemented.\n\n"
        "**Planned features:**\n"
        "• Export conversation history\n"
        "• Save session state\n"
        "• Share conversations\n"
        "• Create session backups\n\n"
        "_Coming in the next development phase!_"
    )


async def handle_quick_action_callback(
    query, action_id: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quick action callbacks."""
    user_id = query.from_user.id

    # Get quick actions manager from bot data if available
    quick_actions = context.bot_data.get("quick_actions")

    if not quick_actions:
        await query.edit_message_text(
            "❌ **Quick Actions Not Available**\n\n"
            "Quick actions feature is not available."
        )
        return

    # Get Claude integration
    claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")
    if not claude_integration:
        await query.edit_message_text(
            "❌ **Claude Integration Not Available**\n\n"
            "Claude integration is not properly configured."
        )
        return

    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # Get the action from the manager
        action = quick_actions.actions.get(action_id)
        if not action:
            await query.edit_message_text(
                f"❌ **Action Not Found**\n\n"
                f"Quick action '{action_id}' is not available."
            )
            return

        # Execute the action
        await query.edit_message_text(
            f"🚀 **Executing {action.icon} {action.name}**\n\n"
            f"Running quick action in directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
            f"Please wait...",
            parse_mode="Markdown",
        )

        # Run the action through Claude
        claude_response = await claude_integration.run_command(
            prompt=action.prompt, working_directory=current_dir, user_id=user_id
        )

        if claude_response:
            # Format and send the response
            response_text = claude_response.content
            if len(response_text) > 4000:
                response_text = response_text[:4000] + "...\n\n_(Response truncated)_"

            await query.message.reply_text(
                f"✅ **{action.icon} {action.name} Complete**\n\n{response_text}",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                f"❌ **Action Failed**\n\n"
                f"Failed to execute {action.name}. Please try again."
            )

    except Exception as e:
        logger.error("Quick action execution failed", error=str(e), user_id=user_id)
        await query.edit_message_text(
            f"❌ **Action Error**\n\n"
            f"An error occurred while executing {action_id}: {str(e)}"
        )


async def handle_followup_callback(
    query, suggestion_hash: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle follow-up suggestion callbacks."""
    user_id = query.from_user.id

    # Get conversation enhancer from bot data if available
    conversation_enhancer = context.bot_data.get("conversation_enhancer")

    if not conversation_enhancer:
        await query.edit_message_text(
            "❌ **Follow-up Not Available**\n\n"
            "Conversation enhancement features are not available."
        )
        return

    try:
        # Get stored suggestions (this would need to be implemented in the enhancer)
        # For now, we'll provide a generic response
        await query.edit_message_text(
            "💡 **Follow-up Suggestion Selected**\n\n"
            "This follow-up suggestion will be implemented once the conversation "
            "enhancement system is fully integrated with the message handler.\n\n"
            "**Current Status:**\n"
            "• Suggestion received ✅\n"
            "• Integration pending 🔄\n\n"
            "_You can continue the conversation by sending a new message._"
        )

        logger.info(
            "Follow-up suggestion selected",
            user_id=user_id,
            suggestion_hash=suggestion_hash,
        )

    except Exception as e:
        logger.error(
            "Error handling follow-up callback",
            error=str(e),
            user_id=user_id,
            suggestion_hash=suggestion_hash,
        )

        await query.edit_message_text(
            "❌ **Error Processing Follow-up**\n\n"
            "An error occurred while processing your follow-up suggestion."
        )


async def handle_conversation_callback(
    query, action_type: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle conversation control callbacks."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]

    if action_type == "continue":
        # Remove suggestion buttons and show continue message
        await query.edit_message_text(
            "✅ **Continuing Conversation**\n\n"
            "Send me your next message to continue coding!\n\n"
            "I'm ready to help with:\n"
            "• Code review and debugging\n"
            "• Feature implementation\n"
            "• Architecture decisions\n"
            "• Testing and optimization\n"
            "• Documentation\n\n"
            "_Just type your request or upload files._"
        )

    elif action_type == "end":
        # End the current session
        conversation_enhancer = context.bot_data.get("conversation_enhancer")
        if conversation_enhancer:
            conversation_enhancer.clear_context(user_id)

        # Clear session data
        context.user_data["claude_session_id"] = None
        context.user_data["session_started"] = False

        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )
        relative_path = current_dir.relative_to(settings.approved_directory)

        # Create quick action buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    "🆕 New Session", callback_data="action:new_session"
                ),
                InlineKeyboardButton(
                    "📁 Change Project", callback_data="action:show_projects"
                ),
            ],
            [
                InlineKeyboardButton("📊 Status", callback_data="action:status"),
                InlineKeyboardButton("❓ Help", callback_data="action:help"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "✅ **Conversation Ended**\n\n"
            f"Your Claude session has been terminated.\n\n"
            f"**Current Status:**\n"
            f"• Directory: `{relative_path}/`\n"
            f"• Session: None\n"
            f"• Ready for new commands\n\n"
            f"**Next Steps:**\n"
            f"• Start a new session\n"
            f"• Check status\n"
            f"• Send any message to begin a new conversation",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        logger.info("Conversation ended via callback", user_id=user_id)

    else:
        await query.edit_message_text(
            f"❌ **Unknown Conversation Action: {action_type}**\n\n"
            "This conversation action is not recognized."
        )


async def handle_git_callback(
    query, git_action: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle git-related callbacks."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("git"):
        await query.edit_message_text(
            "❌ **Git Integration Disabled**\n\n"
            "Git integration feature is not enabled."
        )
        return

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        git_integration = features.get_git_integration()
        if not git_integration:
            await query.edit_message_text(
                "❌ **Git Integration Unavailable**\n\n"
                "Git integration service is not available."
            )
            return

        if git_action == "status":
            # Refresh git status
            git_status = await git_integration.get_status(current_dir)
            status_message = git_integration.format_status(git_status)

            keyboard = [
                [
                    InlineKeyboardButton("📊 Show Diff", callback_data="git:diff"),
                    InlineKeyboardButton("📜 Show Log", callback_data="git:log"),
                ],
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="git:status"),
                    InlineKeyboardButton("📁 Files", callback_data="action:ls"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                status_message, parse_mode="Markdown", reply_markup=reply_markup
            )

        elif git_action == "diff":
            # Show git diff
            diff_output = await git_integration.get_diff(current_dir)

            if not diff_output.strip():
                diff_message = "📊 **Git Diff**\n\n_No changes to show._"
            else:
                # Clean up diff output for Telegram
                # Remove emoji symbols that interfere with markdown parsing
                clean_diff = diff_output.replace("➕", "+").replace("➖", "-").replace("📍", "@")
                
                # Limit diff output
                max_length = 2000
                if len(clean_diff) > max_length:
                    clean_diff = (
                        clean_diff[:max_length] + "\n\n_... output truncated ..._"
                    )

                diff_message = f"📊 **Git Diff**\n\n```\n{clean_diff}\n```"

            keyboard = [
                [
                    InlineKeyboardButton("📜 Show Log", callback_data="git:log"),
                    InlineKeyboardButton("📊 Status", callback_data="git:status"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                diff_message, parse_mode="Markdown", reply_markup=reply_markup
            )

        elif git_action == "log":
            # Show git log
            commits = await git_integration.get_file_history(current_dir, ".")

            if not commits:
                log_message = "📜 **Git Log**\n\n_No commits found._"
            else:
                log_message = "📜 **Git Log**\n\n"
                for commit in commits[:10]:  # Show last 10 commits
                    short_hash = commit.hash[:7]
                    short_message = commit.message[:60]
                    if len(commit.message) > 60:
                        short_message += "..."
                    log_message += f"• `{short_hash}` {short_message}\n"

            keyboard = [
                [
                    InlineKeyboardButton("📊 Show Diff", callback_data="git:diff"),
                    InlineKeyboardButton("📊 Status", callback_data="git:status"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                log_message, parse_mode="Markdown", reply_markup=reply_markup
            )

        else:
            await query.edit_message_text(
                f"❌ **Unknown Git Action: {git_action}**\n\n"
                "This git action is not recognized."
            )

    except Exception as e:
        logger.error(
            "Error in git callback",
            error=str(e),
            git_action=git_action,
            user_id=user_id,
        )
        await query.edit_message_text(f"❌ **Git Error**\n\n{str(e)}")


async def handle_export_callback(
    query, export_format: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle export format selection callbacks."""
    user_id = query.from_user.id
    features = context.bot_data.get("features")

    if export_format == "cancel":
        await query.edit_message_text(
            "📤 **Export Cancelled**\n\n" "Session export has been cancelled."
        )
        return

    session_exporter = features.get_session_export() if features else None
    if not session_exporter:
        await query.edit_message_text(
            "❌ **Export Unavailable**\n\n" "Session export service is not available."
        )
        return

    # Get current session
    claude_session_id = context.user_data.get("claude_session_id")
    if not claude_session_id:
        await query.edit_message_text(
            "❌ **No Active Session**\n\n" "There's no active session to export."
        )
        return

    try:
        # Show processing message
        await query.edit_message_text(
            f"📤 **Exporting Session**\n\n"
            f"Generating {export_format.upper()} export...",
            parse_mode="Markdown",
        )

        # Export session
        exported_session = await session_exporter.export_session(
            claude_session_id, export_format
        )

        # Send the exported file
        from io import BytesIO

        file_bytes = BytesIO(exported_session.content.encode("utf-8"))
        file_bytes.name = exported_session.filename

        await query.message.reply_document(
            document=file_bytes,
            filename=exported_session.filename,
            caption=(
                f"📤 **Session Export Complete**\n\n"
                f"Format: {exported_session.format.upper()}\n"
                f"Size: {exported_session.size_bytes:,} bytes\n"
                f"Created: {exported_session.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            parse_mode="Markdown",
        )

        # Update the original message
        await query.edit_message_text(
            f"✅ **Export Complete**\n\n"
            f"Your session has been exported as {exported_session.filename}.\n"
            f"Check the file above for your complete conversation history.",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(
            "Export failed", error=str(e), user_id=user_id, format=export_format
        )
        await query.edit_message_text(f"❌ **Export Failed**\n\n{str(e)}")


def _format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}B"
        size /= 1024
    return f"{size:.1f}TB"

```

### src\bot\handlers\command.py

**Розмір:** 34,764 байт

```python
"""Command handlers for bot operations."""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ...claude.facade import ClaudeIntegration
from ...config.settings import Settings
from ...security.audit import AuditLogger
from ...security.validators import SecurityValidator

logger = structlog.get_logger()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user

    welcome_message = (
        f"👋 Welcome to Claude Code Telegram Bot, {user.first_name}!\n\n"
        f"🤖 I help you access Claude Code remotely through Telegram.\n\n"
        f"**Available Commands:**\n"
        f"• `/help` - Show detailed help\n"
        f"• `/new` - Start a new Claude session\n"
        f"• `/ls` - List files in current directory\n"
        f"• `/cd <dir>` - Change directory\n"
        f"• `/projects` - Show available projects\n"
        f"• `/status` - Show session status\n"
        f"• `/actions` - Show quick actions\n"
        f"• `/git` - Git repository commands\n\n"
        f"**Quick Start:**\n"
        f"1. Use `/projects` to see available projects\n"
        f"2. Use `/cd <project>` to navigate to a project\n"
        f"3. Send any message to start coding with Claude!\n\n"
        f"🔒 Your access is secured and all actions are logged.\n"
        f"📊 Use `/status` to check your usage limits."
    )

    # Add quick action buttons
    keyboard = [
        [
            InlineKeyboardButton(
                "📁 Show Projects", callback_data="action:show_projects"
            ),
            InlineKeyboardButton("❓ Get Help", callback_data="action:help"),
        ],
        [
            InlineKeyboardButton("🆕 New Session", callback_data="action:new_session"),
            InlineKeyboardButton("📊 Check Status", callback_data="action:status"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_message, parse_mode="Markdown", reply_markup=reply_markup
    )

    # Log command
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")
    if audit_logger:
        await audit_logger.log_command(
            user_id=user.id, command="start", args=[], success=True
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "🤖 **Claude Code Telegram Bot Help**\n\n"
        "**Navigation Commands:**\n"
        "• `/ls` - List files and directories\n"
        "• `/cd <directory>` - Change to directory\n"
        "• `/pwd` - Show current directory\n"
        "• `/projects` - Show available projects\n\n"
        "**Session Commands:**\n"
        "• `/new` - Start new Claude session\n"
        "• `/continue [message]` - Continue last session (optionally with message)\n"
        "• `/end` - End current session\n"
        "• `/status` - Show session and usage status\n"
        "• `/export` - Export session history\n"
        "• `/actions` - Show context-aware quick actions\n"
        "• `/git` - Git repository information\n\n"
        "**Usage Examples:**\n"
        "• `cd myproject` - Enter project directory\n"
        "• `ls` - See what's in current directory\n"
        "• `Create a simple Python script` - Ask Claude to code\n"
        "• Send a file to have Claude review it\n\n"
        "**File Operations:**\n"
        "• Send text files (.py, .js, .md, etc.) for review\n"
        "• Claude can read, modify, and create files\n"
        "• All file operations are within your approved directory\n\n"
        "**Security Features:**\n"
        "• 🔒 Path traversal protection\n"
        "• ⏱️ Rate limiting to prevent abuse\n"
        "• 📊 Usage tracking and limits\n"
        "• 🛡️ Input validation and sanitization\n\n"
        "**Tips:**\n"
        "• Use specific, clear requests for best results\n"
        "• Check `/status` to monitor your usage\n"
        "• Use quick action buttons when available\n"
        "• File uploads are automatically processed by Claude\n\n"
        "Need more help? Contact your administrator."
    )

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command."""
    settings: Settings = context.bot_data["settings"]

    # For now, we'll use a simple session concept
    # This will be enhanced when we implement proper session management

    # Get current directory (default to approved directory)
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Clear any existing session data
    context.user_data["claude_session_id"] = None
    context.user_data["session_started"] = True

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 Start Coding", callback_data="action:start_coding"
            ),
            InlineKeyboardButton(
                "📁 Change Project", callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 Quick Actions", callback_data="action:quick_actions"
            ),
            InlineKeyboardButton("❓ Help", callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🆕 **New Claude Code Session**\n\n"
        f"📂 Working directory: `{relative_path}/`\n\n"
        f"Ready to help you code! Send me a message to get started, or use the buttons below:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def continue_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /continue command with optional prompt."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Parse optional prompt from command arguments
    prompt = " ".join(context.args) if context.args else None

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        if not claude_integration:
            await update.message.reply_text(
                "❌ **Claude Integration Not Available**\n\n"
                "Claude integration is not properly configured."
            )
            return

        # Check if there's an existing session in user context
        claude_session_id = context.user_data.get("claude_session_id")

        if claude_session_id:
            # We have a session in context, continue it directly
            status_msg = await update.message.reply_text(
                f"🔄 **Continuing Session**\n\n"
                f"Session ID: `{claude_session_id[:8]}...`\n"
                f"Directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
                f"{'Processing your message...' if prompt else 'Continuing where you left off...'}",
                parse_mode="Markdown",
            )

            # Continue with the existing session
            claude_response = await claude_integration.run_command(
                prompt=prompt or "",
                working_directory=current_dir,
                user_id=user_id,
                session_id=claude_session_id,
            )
        else:
            # No session in context, try to find the most recent session
            status_msg = await update.message.reply_text(
                "🔍 **Looking for Recent Session**\n\n"
                "Searching for your most recent session in this directory...",
                parse_mode="Markdown",
            )

            claude_response = await claude_integration.continue_session(
                user_id=user_id,
                working_directory=current_dir,
                prompt=prompt,
            )

        if claude_response:
            # Update session ID in context
            context.user_data["claude_session_id"] = claude_response.session_id

            # Delete status message and send response
            await status_msg.delete()

            # Format and send Claude's response
            from ..utils.formatting import ResponseFormatter

            formatter = ResponseFormatter()
            formatted_messages = formatter.format_claude_response(claude_response)

            for msg in formatted_messages:
                await update.message.reply_text(
                    msg.content,
                    parse_mode="Markdown",
                    reply_markup=msg.reply_markup,
                )

            # Log successful continue
            if audit_logger:
                await audit_logger.log_command(
                    user_id=user_id,
                    command="continue",
                    args=context.args or [],
                    success=True,
                )

        else:
            # No session found to continue
            await status_msg.edit_text(
                "❌ **No Session Found**\n\n"
                f"No recent Claude session found in this directory.\n"
                f"Directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
                f"**What you can do:**\n"
                f"• Use `/new` to start a fresh session\n"
                f"• Use `/status` to check your sessions\n"
                f"• Navigate to a different directory with `/cd`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🆕 New Session", callback_data="action:new_session"
                            ),
                            InlineKeyboardButton(
                                "📊 Status", callback_data="action:status"
                            ),
                        ]
                    ]
                ),
            )

    except Exception as e:
        error_msg = str(e)
        logger.error("Error in continue command", error=error_msg, user_id=user_id)

        # Delete status message if it exists
        try:
            if "status_msg" in locals():
                await status_msg.delete()
        except Exception:
            pass

        # Send error response
        await update.message.reply_text(
            f"❌ **Error Continuing Session**\n\n"
            f"An error occurred while trying to continue your session:\n\n"
            f"`{error_msg}`\n\n"
            f"**Suggestions:**\n"
            f"• Try starting a new session with `/new`\n"
            f"• Check your session status with `/status`\n"
            f"• Contact support if the issue persists",
            parse_mode="Markdown",
        )

        # Log failed continue
        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id,
                command="continue",
                args=context.args or [],
                success=False,
            )


async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ls command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # List directory contents
        items = []
        directories = []
        files = []

        for item in sorted(current_dir.iterdir()):
            # Skip hidden files (starting with .)
            if item.name.startswith("."):
                continue

            if item.is_dir():
                directories.append(f"📁 {item.name}/")
            else:
                # Get file size
                try:
                    size = item.stat().st_size
                    size_str = _format_file_size(size)
                    files.append(f"📄 {item.name} ({size_str})")
                except OSError:
                    files.append(f"📄 {item.name}")

        # Combine directories first, then files
        items = directories + files

        # Format response
        relative_path = current_dir.relative_to(settings.approved_directory)
        if not items:
            message = f"📂 `{relative_path}/`\n\n_(empty directory)_"
        else:
            message = f"📂 `{relative_path}/`\n\n"

            # Limit items shown to prevent message being too long
            max_items = 50
            if len(items) > max_items:
                shown_items = items[:max_items]
                message += "\n".join(shown_items)
                message += f"\n\n_... and {len(items) - max_items} more items_"
            else:
                message += "\n".join(items)

        # Add navigation buttons if not at root
        keyboard = []
        if current_dir != settings.approved_directory:
            keyboard.append(
                [
                    InlineKeyboardButton("⬆️ Go Up", callback_data="cd:.."),
                    InlineKeyboardButton("🏠 Go to Root", callback_data="cd:/"),
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_ls"),
                InlineKeyboardButton(
                    "📁 Projects", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await update.message.reply_text(
            message, parse_mode="Markdown", reply_markup=reply_markup
        )

        # Log successful command
        if audit_logger:
            await audit_logger.log_command(user_id, "ls", [], True)

    except Exception as e:
        error_msg = f"❌ Error listing directory: {str(e)}"
        await update.message.reply_text(error_msg)

        # Log failed command
        if audit_logger:
            await audit_logger.log_command(user_id, "ls", [], False)

        logger.error("Error in list_files command", error=str(e), user_id=user_id)


async def change_directory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cd command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    security_validator: SecurityValidator = context.bot_data.get("security_validator")
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Parse arguments
    if not context.args:
        await update.message.reply_text(
            "**Usage:** `/cd <directory>`\n\n"
            "**Examples:**\n"
            "• `/cd myproject` - Enter subdirectory\n"
            "• `/cd ..` - Go up one level\n"
            "• `/cd /` - Go to root of approved directory\n\n"
            "**Tips:**\n"
            "• Use `/ls` to see available directories\n"
            "• Use `/projects` to see all projects",
            parse_mode="Markdown",
        )
        return

    target_path = " ".join(context.args)
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # Validate path using security validator
        if security_validator:
            valid, resolved_path, error = security_validator.validate_path(
                target_path, current_dir
            )

            if not valid:
                await update.message.reply_text(f"❌ **Access Denied**\n\n{error}")

                # Log security violation
                if audit_logger:
                    await audit_logger.log_security_violation(
                        user_id=user_id,
                        violation_type="path_traversal_attempt",
                        details=f"Attempted path: {target_path}",
                        severity="medium",
                    )
                return
        else:
            # Fallback validation without security validator
            if target_path == "/":
                resolved_path = settings.approved_directory
            elif target_path == "..":
                resolved_path = current_dir.parent
                if not str(resolved_path).startswith(str(settings.approved_directory)):
                    resolved_path = settings.approved_directory
            else:
                resolved_path = current_dir / target_path
                resolved_path = resolved_path.resolve()

        # Check if directory exists and is actually a directory
        if not resolved_path.exists():
            await update.message.reply_text(
                f"❌ **Directory Not Found**\n\n`{target_path}` does not exist."
            )
            return

        if not resolved_path.is_dir():
            await update.message.reply_text(
                f"❌ **Not a Directory**\n\n`{target_path}` is not a directory."
            )
            return

        # Update current directory in user data
        context.user_data["current_directory"] = resolved_path

        # Clear Claude session on directory change
        context.user_data["claude_session_id"] = None

        # Send confirmation
        relative_path = resolved_path.relative_to(settings.approved_directory)
        await update.message.reply_text(
            f"✅ **Directory Changed**\n\n"
            f"📂 Current directory: `{relative_path}/`\n\n"
            f"🔄 Claude session cleared. Send a message to start coding in this directory.",
            parse_mode="Markdown",
        )

        # Log successful command
        if audit_logger:
            await audit_logger.log_command(user_id, "cd", [target_path], True)

    except Exception as e:
        error_msg = f"❌ **Error changing directory**\n\n{str(e)}"
        await update.message.reply_text(error_msg, parse_mode="Markdown")

        # Log failed command
        if audit_logger:
            await audit_logger.log_command(user_id, "cd", [target_path], False)

        logger.error("Error in change_directory command", error=str(e), user_id=user_id)


async def print_working_directory(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /pwd command."""
    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    relative_path = current_dir.relative_to(settings.approved_directory)
    absolute_path = str(current_dir)

    # Add quick navigation buttons
    keyboard = [
        [
            InlineKeyboardButton("📁 List Files", callback_data="action:ls"),
            InlineKeyboardButton("📋 Projects", callback_data="action:show_projects"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📍 **Current Directory**\n\n"
        f"Relative: `{relative_path}/`\n"
        f"Absolute: `{absolute_path}`",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /projects command."""
    settings: Settings = context.bot_data["settings"]

    try:
        # Get directories in approved directory (these are "projects")
        projects = []
        for item in sorted(settings.approved_directory.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                projects.append(item.name)

        if not projects:
            await update.message.reply_text(
                "📁 **No Projects Found**\n\n"
                "No subdirectories found in your approved directory.\n"
                "Create some directories to organize your projects!"
            )
            return

        # Create inline keyboard with project buttons
        keyboard = []
        for i in range(0, len(projects), 2):
            row = []
            for j in range(2):
                if i + j < len(projects):
                    project = projects[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"📁 {project}", callback_data=f"cd:{project}"
                        )
                    )
            keyboard.append(row)

        # Add navigation buttons
        keyboard.append(
            [
                InlineKeyboardButton("🏠 Go to Root", callback_data="cd:/"),
                InlineKeyboardButton(
                    "🔄 Refresh", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        project_list = "\n".join([f"• `{project}/`" for project in projects])

        await update.message.reply_text(
            f"📁 **Available Projects**\n\n"
            f"{project_list}\n\n"
            f"Click a project below to navigate to it:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error loading projects: {str(e)}")
        logger.error("Error in show_projects command", error=str(e))


async def session_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    # Get session info
    claude_session_id = context.user_data.get("claude_session_id")
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Get rate limiter info if available
    rate_limiter = context.bot_data.get("rate_limiter")
    usage_info = ""
    if rate_limiter:
        try:
            user_status = rate_limiter.get_user_status(user_id)
            cost_usage = user_status.get("cost_usage", {})
            current_cost = cost_usage.get("current", 0.0)
            cost_limit = cost_usage.get("limit", settings.claude_max_cost_per_user)
            cost_percentage = (current_cost / cost_limit) * 100 if cost_limit > 0 else 0

            usage_info = f"💰 Usage: ${current_cost:.2f} / ${cost_limit:.2f} ({cost_percentage:.0f}%)\n"
        except Exception:
            usage_info = "💰 Usage: _Unable to retrieve_\n"

    # Format status message
    status_lines = [
        "📊 **Session Status**",
        "",
        f"📂 Directory: `{relative_path}/`",
        f"🤖 Claude Session: {'✅ Active' if claude_session_id else '❌ None'}",
        usage_info.rstrip(),
        f"🕐 Last Update: {update.message.date.strftime('%H:%M:%S UTC')}",
    ]

    if claude_session_id:
        status_lines.append(f"🆔 Session ID: `{claude_session_id[:8]}...`")

    # Add action buttons
    keyboard = []
    if claude_session_id:
        keyboard.append(
            [
                InlineKeyboardButton("🔄 Continue", callback_data="action:continue"),
                InlineKeyboardButton(
                    "🆕 New Session", callback_data="action:new_session"
                ),
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🆕 Start Session", callback_data="action:new_session"
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton("📤 Export", callback_data="action:export"),
            InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_status"),
        ]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "\n".join(status_lines), parse_mode="Markdown", reply_markup=reply_markup
    )


async def export_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command."""
    user_id = update.effective_user.id
    features = context.bot_data.get("features")

    # Check if session export is available
    session_exporter = features.get_session_export() if features else None

    if not session_exporter:
        await update.message.reply_text(
            "📤 **Export Session**\n\n"
            "Session export functionality is not available.\n\n"
            "**Planned features:**\n"
            "• Export conversation history\n"
            "• Save session state\n"
            "• Share conversations\n"
            "• Create session backups"
        )
        return

    # Get current session
    claude_session_id = context.user_data.get("claude_session_id")

    if not claude_session_id:
        await update.message.reply_text(
            "❌ **No Active Session**\n\n"
            "There's no active Claude session to export.\n\n"
            "**What you can do:**\n"
            "• Start a new session with `/new`\n"
            "• Continue an existing session with `/continue`\n"
            "• Check your status with `/status`"
        )
        return

    # Create export format selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("📝 Markdown", callback_data="export:markdown"),
            InlineKeyboardButton("🌐 HTML", callback_data="export:html"),
        ],
        [
            InlineKeyboardButton("📋 JSON", callback_data="export:json"),
            InlineKeyboardButton("❌ Cancel", callback_data="export:cancel"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📤 **Export Session**\n\n"
        f"Ready to export session: `{claude_session_id[:8]}...`\n\n"
        "**Choose export format:**",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def end_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /end command to terminate the current session."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    # Check if there's an active session
    claude_session_id = context.user_data.get("claude_session_id")

    if not claude_session_id:
        await update.message.reply_text(
            "ℹ️ **No Active Session**\n\n"
            "There's no active Claude session to end.\n\n"
            "**What you can do:**\n"
            "• Use `/new` to start a new session\n"
            "• Use `/status` to check your session status\n"
            "• Send any message to start a conversation"
        )
        return

    # Get current directory for display
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Clear session data
    context.user_data["claude_session_id"] = None
    context.user_data["session_started"] = False
    context.user_data["last_message"] = None

    # Create quick action buttons
    keyboard = [
        [
            InlineKeyboardButton("🆕 New Session", callback_data="action:new_session"),
            InlineKeyboardButton(
                "📁 Change Project", callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="action:status"),
            InlineKeyboardButton("❓ Help", callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ **Session Ended**\n\n"
        f"Your Claude session has been terminated.\n\n"
        f"**Current Status:**\n"
        f"• Directory: `{relative_path}/`\n"
        f"• Session: None\n"
        f"• Ready for new commands\n\n"
        f"**Next Steps:**\n"
        f"• Start a new session with `/new`\n"
        f"• Check status with `/status`\n"
        f"• Send any message to begin a new conversation",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )

    logger.info("Session ended by user", user_id=user_id, session_id=claude_session_id)


async def quick_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /actions command to show quick actions."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("quick_actions"):
        await update.message.reply_text(
            "❌ **Quick Actions Disabled**\n\n"
            "Quick actions feature is not enabled.\n"
            "Contact your administrator to enable this feature."
        )
        return

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        quick_action_manager = features.get_quick_actions()
        if not quick_action_manager:
            await update.message.reply_text(
                "❌ **Quick Actions Unavailable**\n\n"
                "Quick actions service is not available."
            )
            return

        # Get context-aware actions
        actions = await quick_action_manager.get_suggestions(
            session_data={"working_directory": str(current_dir), "user_id": user_id}
        )

        if not actions:
            await update.message.reply_text(
                "🤖 **No Actions Available**\n\n"
                "No quick actions are available for the current context.\n\n"
                "**Try:**\n"
                "• Navigating to a project directory with `/cd`\n"
                "• Creating some code files\n"
                "• Starting a Claude session with `/new`"
            )
            return

        # Create inline keyboard
        keyboard = quick_action_manager.create_inline_keyboard(actions, max_columns=2)

        relative_path = current_dir.relative_to(settings.approved_directory)
        await update.message.reply_text(
            f"⚡ **Quick Actions**\n\n"
            f"📂 Context: `{relative_path}/`\n\n"
            f"Select an action to execute:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    except Exception as e:
        await update.message.reply_text(f"❌ **Error Loading Actions**\n\n{str(e)}")
        logger.error("Error in quick_actions command", error=str(e), user_id=user_id)


async def git_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /git command to show git repository information."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("git"):
        await update.message.reply_text(
            "❌ **Git Integration Disabled**\n\n"
            "Git integration feature is not enabled.\n"
            "Contact your administrator to enable this feature."
        )
        return

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        git_integration = features.get_git_integration()
        if not git_integration:
            await update.message.reply_text(
                "❌ **Git Integration Unavailable**\n\n"
                "Git integration service is not available."
            )
            return

        # Check if current directory is a git repository
        if not (current_dir / ".git").exists():
            await update.message.reply_text(
                f"📂 **Not a Git Repository**\n\n"
                f"Current directory `{current_dir.relative_to(settings.approved_directory)}/` is not a git repository.\n\n"
                f"**Options:**\n"
                f"• Navigate to a git repository with `/cd`\n"
                f"• Initialize a new repository (ask Claude to help)\n"
                f"• Clone an existing repository (ask Claude to help)"
            )
            return

        # Get git status
        git_status = await git_integration.get_status(current_dir)

        # Format status message
        relative_path = current_dir.relative_to(settings.approved_directory)
        status_message = f"🔗 **Git Repository Status**\n\n"
        status_message += f"📂 Directory: `{relative_path}/`\n"
        status_message += f"🌿 Branch: `{git_status.branch}`\n"

        if git_status.ahead > 0:
            status_message += f"⬆️ Ahead: {git_status.ahead} commits\n"
        if git_status.behind > 0:
            status_message += f"⬇️ Behind: {git_status.behind} commits\n"

        # Show file changes
        if not git_status.is_clean:
            status_message += f"\n**Changes:**\n"
            if git_status.modified:
                status_message += f"📝 Modified: {len(git_status.modified)} files\n"
            if git_status.added:
                status_message += f"➕ Added: {len(git_status.added)} files\n"
            if git_status.deleted:
                status_message += f"➖ Deleted: {len(git_status.deleted)} files\n"
            if git_status.untracked:
                status_message += f"❓ Untracked: {len(git_status.untracked)} files\n"
        else:
            status_message += "\n✅ Working directory clean\n"

        # Create action buttons
        keyboard = [
            [
                InlineKeyboardButton("📊 Show Diff", callback_data="git:diff"),
                InlineKeyboardButton("📜 Show Log", callback_data="git:log"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="git:status"),
                InlineKeyboardButton("📁 Files", callback_data="action:ls"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            status_message, parse_mode="Markdown", reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(f"❌ **Git Error**\n\n{str(e)}")
        logger.error("Error in git_command", error=str(e), user_id=user_id)


def _format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}B"
        size /= 1024
    return f"{size:.1f}TB"

```

### src\bot\handlers\message.py

**Розмір:** 33,755 байт

```python
"""Message handlers for non-command inputs."""

import asyncio
from typing import Optional

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from ...claude.exceptions import ClaudeToolValidationError
from ...config.settings import Settings
from ...security.audit import AuditLogger
from ...security.rate_limiter import RateLimiter
from ...security.validators import SecurityValidator

logger = structlog.get_logger()


async def _format_progress_update(update_obj) -> Optional[str]:
    """Format progress updates with enhanced context and visual indicators."""
    if update_obj.type == "tool_result":
        # Show tool completion status
        tool_name = "Unknown"
        if update_obj.metadata and update_obj.metadata.get("tool_use_id"):
            # Try to extract tool name from context if available
            tool_name = update_obj.metadata.get("tool_name", "Tool")

        if update_obj.is_error():
            return f"❌ **{tool_name} failed**\n\n_{update_obj.get_error_message()}_"
        else:
            execution_time = ""
            if update_obj.metadata and update_obj.metadata.get("execution_time_ms"):
                time_ms = update_obj.metadata["execution_time_ms"]
                execution_time = f" ({time_ms}ms)"
            return f"✅ **{tool_name} completed**{execution_time}"

    elif update_obj.type == "progress":
        # Handle progress updates
        progress_text = f"🔄 **{update_obj.content or 'Working...'}**"

        percentage = update_obj.get_progress_percentage()
        if percentage is not None:
            # Create a simple progress bar
            filled = int(percentage / 10)  # 0-10 scale
            bar = "█" * filled + "░" * (10 - filled)
            progress_text += f"\n\n`{bar}` {percentage}%"

        if update_obj.progress:
            step = update_obj.progress.get("step")
            total_steps = update_obj.progress.get("total_steps")
            if step and total_steps:
                progress_text += f"\n\nStep {step} of {total_steps}"

        return progress_text

    elif update_obj.type == "error":
        # Handle error messages
        return f"❌ **Error**\n\n_{update_obj.get_error_message()}_"

    elif update_obj.type == "assistant" and update_obj.tool_calls:
        # Show when tools are being called
        tool_names = update_obj.get_tool_names()
        if tool_names:
            tools_text = ", ".join(tool_names)
            return f"🔧 **Using tools:** {tools_text}"

    elif update_obj.type == "assistant" and update_obj.content:
        # Regular content updates with preview
        content_preview = (
            update_obj.content[:150] + "..."
            if len(update_obj.content) > 150
            else update_obj.content
        )
        return f"🤖 **Claude is working...**\n\n_{content_preview}_"

    elif update_obj.type == "system":
        # System initialization or other system messages
        if update_obj.metadata and update_obj.metadata.get("subtype") == "init":
            tools_count = len(update_obj.metadata.get("tools", []))
            model = update_obj.metadata.get("model", "Claude")
            return f"🚀 **Starting {model}** with {tools_count} tools available"

    return None


def _format_error_message(error_str: str) -> str:
    """Format error messages for user-friendly display."""
    if "usage limit reached" in error_str.lower():
        # Usage limit error - already user-friendly from integration.py
        return error_str
    elif "tool not allowed" in error_str.lower():
        # Tool validation error - already handled in facade.py
        return error_str
    elif "no conversation found" in error_str.lower():
        return (
            f"🔄 **Session Not Found**\n\n"
            f"The Claude session could not be found or has expired.\n\n"
            f"**What you can do:**\n"
            f"• Use `/new` to start a fresh session\n"
            f"• Try your request again\n"
            f"• Use `/status` to check your current session"
        )
    elif "rate limit" in error_str.lower():
        return (
            f"⏱️ **Rate Limit Reached**\n\n"
            f"Too many requests in a short time period.\n\n"
            f"**What you can do:**\n"
            f"• Wait a moment before trying again\n"
            f"• Use simpler requests\n"
            f"• Check your current usage with `/status`"
        )
    elif "timeout" in error_str.lower():
        return (
            f"⏰ **Request Timeout**\n\n"
            f"Your request took too long to process and timed out.\n\n"
            f"**What you can do:**\n"
            f"• Try breaking down your request into smaller parts\n"
            f"• Use simpler commands\n"
            f"• Try again in a moment"
        )
    else:
        # Generic error handling
        return (
            f"❌ **Claude Code Error**\n\n"
            f"Failed to process your request: {error_str}\n\n"
            f"Please try again or contact the administrator if the problem persists."
        )


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle regular text messages as Claude prompts."""
    user_id = update.effective_user.id
    message_text = update.message.text
    settings: Settings = context.bot_data["settings"]

    # Get services
    rate_limiter: Optional[RateLimiter] = context.bot_data.get("rate_limiter")
    audit_logger: Optional[AuditLogger] = context.bot_data.get("audit_logger")

    logger.info(
        "Processing text message", user_id=user_id, message_length=len(message_text)
    )

    try:
        # Check rate limit with estimated cost for text processing
        estimated_cost = _estimate_text_processing_cost(message_text)

        if rate_limiter:
            allowed, limit_message = await rate_limiter.check_rate_limit(
                user_id, estimated_cost
            )
            if not allowed:
                await update.message.reply_text(f"⏱️ {limit_message}")
                return

        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Create progress message
        progress_msg = await update.message.reply_text(
            "🤔 Processing your request...",
            reply_to_message_id=update.message.message_id,
        )

        # Get Claude integration and storage from context
        claude_integration = context.bot_data.get("claude_integration")
        storage = context.bot_data.get("storage")

        if not claude_integration:
            await update.message.reply_text(
                "❌ **Claude integration not available**\n\n"
                "The Claude Code integration is not properly configured. "
                "Please contact the administrator.",
                parse_mode="Markdown",
            )
            return

        # Get current directory
        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )

        # Get existing session ID
        session_id = context.user_data.get("claude_session_id")

        # Enhanced stream updates handler with progress tracking
        async def stream_handler(update_obj):
            try:
                progress_text = await _format_progress_update(update_obj)
                if progress_text:
                    await progress_msg.edit_text(progress_text, parse_mode="Markdown")
            except Exception as e:
                logger.warning("Failed to update progress message", error=str(e))

        # Run Claude command
        try:
            claude_response = await claude_integration.run_command(
                prompt=message_text,
                working_directory=current_dir,
                user_id=user_id,
                session_id=session_id,
                on_stream=stream_handler,
            )

            # Update session ID
            context.user_data["claude_session_id"] = claude_response.session_id

            # Check if Claude changed the working directory and update our tracking
            _update_working_directory_from_claude_response(
                claude_response, context, settings, user_id
            )

            # Log interaction to storage
            if storage:
                try:
                    await storage.save_claude_interaction(
                        user_id=user_id,
                        session_id=claude_response.session_id,
                        prompt=message_text,
                        response=claude_response,
                        ip_address=None,  # Telegram doesn't provide IP
                    )
                except Exception as e:
                    logger.warning("Failed to log interaction to storage", error=str(e))

            # Format response
            from ..utils.formatting import ResponseFormatter

            formatter = ResponseFormatter(settings)
            formatted_messages = formatter.format_claude_response(
                claude_response.content
            )

        except ClaudeToolValidationError as e:
            # Tool validation error with detailed instructions
            logger.error(
                "Tool validation error",
                error=str(e),
                user_id=user_id,
                blocked_tools=e.blocked_tools,
            )
            # Error message already formatted, create FormattedMessage
            from ..utils.formatting import FormattedMessage

            formatted_messages = [FormattedMessage(str(e), parse_mode="Markdown")]
        except Exception as e:
            logger.error("Claude integration failed", error=str(e), user_id=user_id)
            # Format error and create FormattedMessage
            from ..utils.formatting import FormattedMessage

            formatted_messages = [
                FormattedMessage(_format_error_message(str(e)), parse_mode="Markdown")
            ]

        # Delete progress message
        await progress_msg.delete()

        # Send formatted responses (may be multiple messages)
        for i, message in enumerate(formatted_messages):
            try:
                await update.message.reply_text(
                    message.text,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup,
                    reply_to_message_id=update.message.message_id if i == 0 else None,
                )

                # Small delay between messages to avoid rate limits
                if i < len(formatted_messages) - 1:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(
                    "Failed to send response message", error=str(e), message_index=i
                )
                # Try to send error message
                await update.message.reply_text(
                    "❌ Failed to send response. Please try again.",
                    reply_to_message_id=update.message.message_id if i == 0 else None,
                )

        # Update session info
        context.user_data["last_message"] = update.message.text

        # Add conversation enhancements if available
        features = context.bot_data.get("features")
        conversation_enhancer = (
            features.get_conversation_enhancer() if features else None
        )

        if conversation_enhancer and claude_response:
            try:
                # Update conversation context
                conversation_context = conversation_enhancer.update_context(
                    session_id=claude_response.session_id,
                    user_id=user_id,
                    working_directory=str(current_dir),
                    tools_used=claude_response.tools_used or [],
                    response_content=claude_response.content,
                )

                # Check if we should show follow-up suggestions
                if conversation_enhancer.should_show_suggestions(
                    claude_response.tools_used or [], claude_response.content
                ):
                    # Generate follow-up suggestions
                    suggestions = conversation_enhancer.generate_follow_up_suggestions(
                        claude_response.content,
                        claude_response.tools_used or [],
                        conversation_context,
                    )

                    if suggestions:
                        # Create keyboard with suggestions
                        suggestion_keyboard = (
                            conversation_enhancer.create_follow_up_keyboard(suggestions)
                        )

                        # Send follow-up suggestions
                        await update.message.reply_text(
                            "💡 **What would you like to do next?**",
                            parse_mode="Markdown",
                            reply_markup=suggestion_keyboard,
                        )

            except Exception as e:
                logger.warning(
                    "Conversation enhancement failed", error=str(e), user_id=user_id
                )

        # Log successful message processing
        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id,
                command="text_message",
                args=[update.message.text[:100]],  # First 100 chars
                success=True,
            )

        logger.info("Text message processed successfully", user_id=user_id)

    except Exception as e:
        # Clean up progress message if it exists
        try:
            await progress_msg.delete()
        except:
            pass

        error_msg = f"❌ **Error processing message**\n\n{str(e)}"
        await update.message.reply_text(error_msg, parse_mode="Markdown")

        # Log failed processing
        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id,
                command="text_message",
                args=[update.message.text[:100]],
                success=False,
            )

        logger.error("Error processing text message", error=str(e), user_id=user_id)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle file uploads."""
    user_id = update.effective_user.id
    document = update.message.document
    settings: Settings = context.bot_data["settings"]

    # Get services
    security_validator: Optional[SecurityValidator] = context.bot_data.get(
        "security_validator"
    )
    audit_logger: Optional[AuditLogger] = context.bot_data.get("audit_logger")
    rate_limiter: Optional[RateLimiter] = context.bot_data.get("rate_limiter")

    logger.info(
        "Processing document upload",
        user_id=user_id,
        filename=document.file_name,
        file_size=document.file_size,
    )

    try:
        # Validate filename using security validator
        if security_validator:
            valid, error = security_validator.validate_filename(document.file_name)
            if not valid:
                await update.message.reply_text(
                    f"❌ **File Upload Rejected**\n\n{error}"
                )

                # Log security violation
                if audit_logger:
                    await audit_logger.log_security_violation(
                        user_id=user_id,
                        violation_type="invalid_file_upload",
                        details=f"Filename: {document.file_name}, Error: {error}",
                        severity="medium",
                    )
                return

        # Check file size limits
        max_size = 10 * 1024 * 1024  # 10MB
        if document.file_size > max_size:
            await update.message.reply_text(
                f"❌ **File Too Large**\n\n"
                f"Maximum file size: {max_size // 1024 // 1024}MB\n"
                f"Your file: {document.file_size / 1024 / 1024:.1f}MB"
            )
            return

        # Check rate limit for file processing
        file_cost = _estimate_file_processing_cost(document.file_size)
        if rate_limiter:
            allowed, limit_message = await rate_limiter.check_rate_limit(
                user_id, file_cost
            )
            if not allowed:
                await update.message.reply_text(f"⏱️ {limit_message}")
                return

        # Send processing indicator
        await update.message.chat.send_action("upload_document")

        progress_msg = await update.message.reply_text(
            f"📄 Processing file: `{document.file_name}`...", parse_mode="Markdown"
        )

        # Check if enhanced file handler is available
        features = context.bot_data.get("features")
        file_handler = features.get_file_handler() if features else None

        if file_handler:
            # Use enhanced file handler
            try:
                processed_file = await file_handler.handle_document_upload(
                    document,
                    user_id,
                    update.message.caption or "Please review this file:",
                )
                prompt = processed_file.prompt

                # Update progress message with file type info
                await progress_msg.edit_text(
                    f"📄 Processing {processed_file.type} file: `{document.file_name}`...",
                    parse_mode="Markdown",
                )

            except Exception as e:
                logger.warning(
                    "Enhanced file handler failed, falling back to basic handler",
                    error=str(e),
                )
                file_handler = None  # Fall back to basic handling

        if not file_handler:
            # Fall back to basic file handling
            file = await document.get_file()
            file_bytes = await file.download_as_bytearray()

            # Try to decode as text
            try:
                content = file_bytes.decode("utf-8")

                # Check content length
                max_content_length = 50000  # 50KB of text
                if len(content) > max_content_length:
                    content = (
                        content[:max_content_length]
                        + "\n... (file truncated for processing)"
                    )

                # Create prompt with file content
                caption = update.message.caption or "Please review this file:"
                prompt = f"{caption}\n\n**File:** `{document.file_name}`\n\n```\n{content}\n```"

            except UnicodeDecodeError:
                await progress_msg.edit_text(
                    "❌ **File Format Not Supported**\n\n"
                    "File must be text-based and UTF-8 encoded.\n\n"
                    "**Supported formats:**\n"
                    "• Source code files (.py, .js, .ts, etc.)\n"
                    "• Text files (.txt, .md)\n"
                    "• Configuration files (.json, .yaml, .toml)\n"
                    "• Documentation files"
                )
                return

        # Delete progress message
        await progress_msg.delete()

        # Create a new progress message for Claude processing
        claude_progress_msg = await update.message.reply_text(
            "🤖 Processing file with Claude...", parse_mode="Markdown"
        )

        # Get Claude integration from context
        claude_integration = context.bot_data.get("claude_integration")

        if not claude_integration:
            await claude_progress_msg.edit_text(
                "❌ **Claude integration not available**\n\n"
                "The Claude Code integration is not properly configured.",
                parse_mode="Markdown",
            )
            return

        # Get current directory and session
        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )
        session_id = context.user_data.get("claude_session_id")

        # Process with Claude
        try:
            claude_response = await claude_integration.run_command(
                prompt=prompt,
                working_directory=current_dir,
                user_id=user_id,
                session_id=session_id,
            )

            # Update session ID
            context.user_data["claude_session_id"] = claude_response.session_id

            # Check if Claude changed the working directory and update our tracking
            _update_working_directory_from_claude_response(
                claude_response, context, settings, user_id
            )

            # Format and send response
            from ..utils.formatting import ResponseFormatter

            formatter = ResponseFormatter(settings)
            formatted_messages = formatter.format_claude_response(
                claude_response.content
            )

            # Delete progress message
            await claude_progress_msg.delete()

            # Send responses
            for i, message in enumerate(formatted_messages):
                await update.message.reply_text(
                    message.text,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup,
                    reply_to_message_id=(update.message.message_id if i == 0 else None),
                )

                if i < len(formatted_messages) - 1:
                    await asyncio.sleep(0.5)

        except Exception as e:
            await claude_progress_msg.edit_text(
                _format_error_message(str(e)), parse_mode="Markdown"
            )
            logger.error("Claude file processing failed", error=str(e), user_id=user_id)

        # Log successful file processing
        if audit_logger:
            await audit_logger.log_file_access(
                user_id=user_id,
                file_path=document.file_name,
                action="upload_processed",
                success=True,
                file_size=document.file_size,
            )

    except Exception as e:
        try:
            await progress_msg.delete()
        except:
            pass

        error_msg = f"❌ **Error processing file**\n\n{str(e)}"
        await update.message.reply_text(error_msg, parse_mode="Markdown")

        # Log failed file processing
        if audit_logger:
            await audit_logger.log_file_access(
                user_id=user_id,
                file_path=document.file_name,
                action="upload_failed",
                success=False,
                file_size=document.file_size,
            )

        logger.error("Error processing document", error=str(e), user_id=user_id)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    # Check if enhanced image handler is available
    features = context.bot_data.get("features")
    image_handler = features.get_image_handler() if features else None

    if image_handler:
        try:
            # Send processing indicator
            progress_msg = await update.message.reply_text(
                "📸 Processing image...", parse_mode="Markdown"
            )

            # Get the largest photo size
            photo = update.message.photo[-1]

            # Process image with enhanced handler
            processed_image = await image_handler.process_image(
                photo, update.message.caption
            )

            # Delete progress message
            await progress_msg.delete()

            # Create Claude progress message
            claude_progress_msg = await update.message.reply_text(
                "🤖 Analyzing image with Claude...", parse_mode="Markdown"
            )

            # Get Claude integration
            claude_integration = context.bot_data.get("claude_integration")

            if not claude_integration:
                await claude_progress_msg.edit_text(
                    "❌ **Claude integration not available**\n\n"
                    "The Claude Code integration is not properly configured.",
                    parse_mode="Markdown",
                )
                return

            # Get current directory and session
            current_dir = context.user_data.get(
                "current_directory", settings.approved_directory
            )
            session_id = context.user_data.get("claude_session_id")

            # Process with Claude
            try:
                claude_response = await claude_integration.run_command(
                    prompt=processed_image.prompt,
                    working_directory=current_dir,
                    user_id=user_id,
                    session_id=session_id,
                )

                # Update session ID
                context.user_data["claude_session_id"] = claude_response.session_id

                # Format and send response
                from ..utils.formatting import ResponseFormatter

                formatter = ResponseFormatter(settings)
                formatted_messages = formatter.format_claude_response(
                    claude_response.content
                )

                # Delete progress message
                await claude_progress_msg.delete()

                # Send responses
                for i, message in enumerate(formatted_messages):
                    await update.message.reply_text(
                        message.text,
                        parse_mode=message.parse_mode,
                        reply_markup=message.reply_markup,
                        reply_to_message_id=(
                            update.message.message_id if i == 0 else None
                        ),
                    )

                    if i < len(formatted_messages) - 1:
                        await asyncio.sleep(0.5)

            except Exception as e:
                await claude_progress_msg.edit_text(
                    _format_error_message(str(e)), parse_mode="Markdown"
                )
                logger.error(
                    "Claude image processing failed", error=str(e), user_id=user_id
                )

        except Exception as e:
            logger.error("Image processing failed", error=str(e), user_id=user_id)
            await update.message.reply_text(
                f"❌ **Error processing image**\n\n{str(e)}", parse_mode="Markdown"
            )
    else:
        # Fall back to unsupported message
        await update.message.reply_text(
            "📸 **Photo Upload**\n\n"
            "Photo processing is not yet supported.\n\n"
            "**Currently supported:**\n"
            "• Text files (.py, .js, .md, etc.)\n"
            "• Configuration files\n"
            "• Documentation files\n\n"
            "**Coming soon:**\n"
            "• Image analysis\n"
            "• Screenshot processing\n"
            "• Diagram interpretation"
        )


def _estimate_text_processing_cost(text: str) -> float:
    """Estimate cost for processing text message."""
    # Base cost
    base_cost = 0.001

    # Additional cost based on length
    length_cost = len(text) * 0.00001

    # Additional cost for complex requests
    complex_keywords = [
        "analyze",
        "generate",
        "create",
        "build",
        "implement",
        "refactor",
        "optimize",
        "debug",
        "explain",
        "document",
    ]

    text_lower = text.lower()
    complexity_multiplier = 1.0

    for keyword in complex_keywords:
        if keyword in text_lower:
            complexity_multiplier += 0.5

    return (base_cost + length_cost) * min(complexity_multiplier, 3.0)


def _estimate_file_processing_cost(file_size: int) -> float:
    """Estimate cost for processing uploaded file."""
    # Base cost for file handling
    base_cost = 0.005

    # Additional cost based on file size (per KB)
    size_cost = (file_size / 1024) * 0.0001

    return base_cost + size_cost


async def _generate_placeholder_response(
    message_text: str, context: ContextTypes.DEFAULT_TYPE
) -> dict:
    """Generate placeholder response until Claude integration is implemented."""
    settings: Settings = context.bot_data["settings"]
    current_dir = getattr(
        context.user_data, "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Analyze the message for intent
    message_lower = message_text.lower()

    if any(
        word in message_lower for word in ["list", "show", "see", "directory", "files"]
    ):
        response_text = (
            f"🤖 **Claude Code Response** _(Placeholder)_\n\n"
            f"I understand you want to see files. Try using the `/ls` command to list files "
            f"in your current directory (`{relative_path}/`).\n\n"
            f"**Available commands:**\n"
            f"• `/ls` - List files\n"
            f"• `/cd <dir>` - Change directory\n"
            f"• `/projects` - Show projects\n\n"
            f"_Note: Full Claude Code integration will be available in the next phase._"
        )

    elif any(word in message_lower for word in ["create", "generate", "make", "build"]):
        response_text = (
            f"🤖 **Claude Code Response** _(Placeholder)_\n\n"
            f"I understand you want to create something! Once the Claude Code integration "
            f"is complete, I'll be able to:\n\n"
            f"• Generate code files\n"
            f"• Create project structures\n"
            f"• Write documentation\n"
            f"• Build complete applications\n\n"
            f"**Current directory:** `{relative_path}/`\n\n"
            f"_Full functionality coming soon!_"
        )

    elif any(word in message_lower for word in ["help", "how", "what", "explain"]):
        response_text = (
            f"🤖 **Claude Code Response** _(Placeholder)_\n\n"
            f"I'm here to help! Try using `/help` for available commands.\n\n"
            f"**What I can do now:**\n"
            f"• Navigate directories (`/cd`, `/ls`, `/pwd`)\n"
            f"• Show projects (`/projects`)\n"
            f"• Manage sessions (`/new`, `/status`)\n\n"
            f"**Coming soon:**\n"
            f"• Full Claude Code integration\n"
            f"• Code generation and editing\n"
            f"• File operations\n"
            f"• Advanced programming assistance"
        )

    else:
        response_text = (
            f"🤖 **Claude Code Response** _(Placeholder)_\n\n"
            f"I received your message: \"{message_text[:100]}{'...' if len(message_text) > 100 else ''}\"\n\n"
            f"**Current Status:**\n"
            f"• Directory: `{relative_path}/`\n"
            f"• Bot core: ✅ Active\n"
            f"• Claude integration: 🔄 Coming soon\n\n"
            f"Once Claude Code integration is complete, I'll be able to process your "
            f"requests fully and help with coding tasks!\n\n"
            f"For now, try the available commands like `/ls`, `/cd`, and `/help`."
        )

    return {"text": response_text, "parse_mode": "Markdown"}


def _update_working_directory_from_claude_response(
    claude_response, context, settings, user_id
):
    """Update the working directory based on Claude's response content."""
    import re
    from pathlib import Path

    # Look for directory changes in Claude's response
    # This searches for common patterns that indicate directory changes
    patterns = [
        r"(?:^|\n).*?cd\s+([^\s\n]+)",  # cd command
        r"(?:^|\n).*?Changed directory to:?\s*([^\s\n]+)",  # explicit directory change
        r"(?:^|\n).*?Current directory:?\s*([^\s\n]+)",  # current directory indication
        r"(?:^|\n).*?Working directory:?\s*([^\s\n]+)",  # working directory indication
    ]

    content = claude_response.content.lower()
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            try:
                # Clean up the path
                new_path = match.strip().strip("\"'`")

                # Handle relative paths
                if new_path.startswith("./") or new_path.startswith("../"):
                    new_path = (current_dir / new_path).resolve()
                elif not new_path.startswith("/"):
                    # Relative path without ./
                    new_path = (current_dir / new_path).resolve()
                else:
                    # Absolute path
                    new_path = Path(new_path).resolve()

                # Validate that the new path is within the approved directory
                if (
                    new_path.is_relative_to(settings.approved_directory)
                    and new_path.exists()
                ):
                    context.user_data["current_directory"] = new_path
                    logger.info(
                        "Updated working directory from Claude response",
                        old_dir=str(current_dir),
                        new_dir=str(new_path),
                        user_id=user_id,
                    )
                    return  # Take the first valid match

            except (ValueError, OSError) as e:
                # Invalid path, skip this match
                logger.debug(
                    "Invalid path in Claude response", path=match, error=str(e)
                )
                continue

```

### src\bot\handlers\__init__.py

**Розмір:** 0 байт

```python


```

### src\bot\middleware\auth.py

**Розмір:** 5,504 байт

```python
"""Telegram bot authentication middleware."""

from datetime import datetime
from typing import Any, Callable, Dict

import structlog

logger = structlog.get_logger()


async def auth_middleware(handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
    """Check authentication before processing messages.

    This middleware:
    1. Checks if user is authenticated
    2. Attempts authentication if not authenticated
    3. Updates session activity
    4. Logs authentication events
    """
    # Extract user information
    user_id = event.effective_user.id if event.effective_user else None
    username = (
        getattr(event.effective_user, "username", None)
        if event.effective_user
        else None
    )

    if not user_id:
        logger.warning("No user information in update")
        return

    # Get dependencies from context
    auth_manager = data.get("auth_manager")
    audit_logger = data.get("audit_logger")

    if not auth_manager:
        logger.error("Authentication manager not available in middleware context")
        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 Authentication system unavailable. Please try again later."
            )
        return

    # Check if user is already authenticated
    if auth_manager.is_authenticated(user_id):
        # Update session activity
        if auth_manager.refresh_session(user_id):
            session = auth_manager.get_session(user_id)
            logger.debug(
                "Session refreshed",
                user_id=user_id,
                username=username,
                auth_provider=session.auth_provider if session else None,
            )

        # Continue to handler
        return await handler(event, data)

    # User not authenticated - attempt authentication
    logger.info(
        "Attempting authentication for user", user_id=user_id, username=username
    )

    # Try to authenticate (providers will check whitelist and tokens)
    authentication_successful = await auth_manager.authenticate_user(user_id)

    # Log authentication attempt
    if audit_logger:
        await audit_logger.log_auth_attempt(
            user_id=user_id,
            success=authentication_successful,
            method="automatic",
            reason="message_received",
        )

    if authentication_successful:
        session = auth_manager.get_session(user_id)
        logger.info(
            "User authenticated successfully",
            user_id=user_id,
            username=username,
            auth_provider=session.auth_provider if session else None,
        )

        # Welcome message for new session
        if event.effective_message:
            await event.effective_message.reply_text(
                f"🔓 Welcome! You are now authenticated.\n"
                f"Session started at {datetime.utcnow().strftime('%H:%M:%S UTC')}"
            )

        # Continue to handler
        return await handler(event, data)

    else:
        # Authentication failed
        logger.warning("Authentication failed", user_id=user_id, username=username)

        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 **Authentication Required**\n\n"
                "You are not authorized to use this bot.\n"
                "Please contact the administrator for access.\n\n"
                f"Your Telegram ID: `{user_id}`\n"
                "Share this ID with the administrator to request access."
            )
        return  # Stop processing


async def require_auth(handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
    """Decorator-style middleware that requires authentication.

    This is a stricter version that only allows authenticated users.
    """
    user_id = event.effective_user.id if event.effective_user else None
    auth_manager = data.get("auth_manager")

    if not auth_manager or not auth_manager.is_authenticated(user_id):
        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 Authentication required to use this command."
            )
        return

    return await handler(event, data)


async def admin_required(handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
    """Middleware that requires admin privileges.

    Note: This is a placeholder - admin privileges would need to be
    implemented in the authentication system.
    """
    user_id = event.effective_user.id if event.effective_user else None
    auth_manager = data.get("auth_manager")

    if not auth_manager or not auth_manager.is_authenticated(user_id):
        if event.effective_message:
            await event.effective_message.reply_text("🔒 Authentication required.")
        return

    session = auth_manager.get_session(user_id)
    if not session or not session.user_info:
        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 Session information unavailable."
            )
        return

    # Check for admin permissions (placeholder logic)
    permissions = session.user_info.get("permissions", [])
    if "admin" not in permissions:
        if event.effective_message:
            await event.effective_message.reply_text(
                "🔒 **Admin Access Required**\n\n"
                "This command requires administrator privileges."
            )
        return

    return await handler(event, data)

```

### src\bot\middleware\rate_limit.py

**Розмір:** 7,536 байт

```python
"""Rate limiting middleware for Telegram bot."""

from typing import Any, Callable, Dict

import structlog

logger = structlog.get_logger()


async def rate_limit_middleware(
    handler: Callable, event: Any, data: Dict[str, Any]
) -> Any:
    """Check rate limits before processing messages.

    This middleware:
    1. Checks request rate limits
    2. Estimates and checks cost limits
    3. Logs rate limit violations
    4. Provides helpful error messages
    """
    user_id = event.effective_user.id if event.effective_user else None
    username = (
        getattr(event.effective_user, "username", None)
        if event.effective_user
        else None
    )

    if not user_id:
        logger.warning("No user information in update")
        return await handler(event, data)

    # Get dependencies from context
    rate_limiter = data.get("rate_limiter")
    audit_logger = data.get("audit_logger")

    if not rate_limiter:
        logger.error("Rate limiter not available in middleware context")
        # Don't block on missing rate limiter - this could be a config issue
        return await handler(event, data)

    # Estimate cost based on message content and type
    estimated_cost = estimate_message_cost(event)

    # Check rate limits
    allowed, message = await rate_limiter.check_rate_limit(
        user_id=user_id, cost=estimated_cost, tokens=1  # One token per message
    )

    if not allowed:
        logger.warning(
            "Rate limit exceeded",
            user_id=user_id,
            username=username,
            estimated_cost=estimated_cost,
            message=message,
        )

        # Log rate limit violation
        if audit_logger:
            await audit_logger.log_rate_limit_exceeded(
                user_id=user_id,
                limit_type="combined",
                current_usage=0,  # Would need to extract from rate_limiter
                limit_value=0,  # Would need to extract from rate_limiter
            )

        # Send user-friendly rate limit message
        if event.effective_message:
            await event.effective_message.reply_text(f"⏱️ {message}")
        return  # Stop processing

    # Rate limit check passed
    logger.debug(
        "Rate limit check passed",
        user_id=user_id,
        username=username,
        estimated_cost=estimated_cost,
    )

    # Continue to handler
    return await handler(event, data)


def estimate_message_cost(event: Any) -> float:
    """Estimate the cost of processing a message.

    This is a simple heuristic - in practice, you'd want more
    sophisticated cost estimation based on:
    - Message type (text, file, command)
    - Content complexity
    - Expected Claude usage
    """
    message = event.effective_message
    message_text = message.text if message else ""

    # Base cost for any message
    base_cost = 0.01

    # Additional cost based on message length
    length_cost = len(message_text) * 0.0001

    # Higher cost for certain types of messages
    if (message and message.document) or (message and message.photo):
        # File uploads cost more
        return base_cost + length_cost + 0.05

    if message_text.startswith("/"):
        # Commands cost more
        return base_cost + length_cost + 0.02

    # Check for complex operations keywords
    complex_keywords = [
        "analyze",
        "generate",
        "create",
        "build",
        "compile",
        "test",
        "debug",
        "refactor",
        "optimize",
        "explain",
    ]

    if any(keyword in message_text.lower() for keyword in complex_keywords):
        return base_cost + length_cost + 0.03

    return base_cost + length_cost


async def cost_tracking_middleware(
    handler: Callable, event: Any, data: Dict[str, Any]
) -> Any:
    """Track actual costs after processing.

    This middleware runs after the main handler to track
    actual costs incurred during processing.
    """
    user_id = event.from_user.id
    rate_limiter = data.get("rate_limiter")

    # Store start time for duration tracking
    import time

    start_time = time.time()

    try:
        # Execute the handler
        result = await handler(event, data)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Get actual cost from context if available
        actual_cost = data.get("actual_cost", 0.0)

        if actual_cost > 0 and rate_limiter:
            # Update cost tracking with actual cost
            # Note: This would require extending the rate limiter
            # to support post-processing cost updates
            logger.debug(
                "Actual cost tracked",
                user_id=user_id,
                actual_cost=actual_cost,
                processing_time=processing_time,
            )

        return result

    except Exception as e:
        # Log error but don't update costs for failed operations
        processing_time = time.time() - start_time
        logger.error(
            "Handler execution failed",
            user_id=user_id,
            processing_time=processing_time,
            error=str(e),
        )
        raise


async def burst_protection_middleware(
    handler: Callable, event: Any, data: Dict[str, Any]
) -> Any:
    """Additional burst protection for high-frequency requests.

    This middleware provides an additional layer of protection
    against burst attacks that might bypass normal rate limiting.
    """
    user_id = event.from_user.id

    # Get or create burst tracker
    burst_tracker = data.setdefault("burst_tracker", {})
    user_burst_data = burst_tracker.setdefault(
        user_id, {"recent_requests": [], "warnings_sent": 0}
    )

    import time

    current_time = time.time()

    # Clean old requests (older than 10 seconds)
    user_burst_data["recent_requests"] = [
        req_time
        for req_time in user_burst_data["recent_requests"]
        if current_time - req_time < 10
    ]

    # Add current request
    user_burst_data["recent_requests"].append(current_time)

    # Check for burst (more than 5 requests in 10 seconds)
    if len(user_burst_data["recent_requests"]) > 5:
        user_burst_data["warnings_sent"] += 1

        logger.warning(
            "Burst protection triggered",
            user_id=user_id,
            requests_in_window=len(user_burst_data["recent_requests"]),
            warnings_sent=user_burst_data["warnings_sent"],
        )

        # Progressive response based on warning count
        if user_burst_data["warnings_sent"] == 1:
            if event.effective_message:
                await event.effective_message.reply_text(
                    "⚠️ **Slow down!**\n\n"
                    "You're sending requests too quickly. "
                    "Please wait a moment between messages."
                )
        elif user_burst_data["warnings_sent"] <= 3:
            if event.effective_message:
                await event.effective_message.reply_text(
                    "🛑 **Rate limit warning**\n\n"
                    "Please reduce your request frequency to avoid being temporarily blocked."
                )
        else:
            if event.effective_message:
                await event.effective_message.reply_text(
                    "🚫 **Temporarily blocked**\n\n"
                    "Too many rapid requests. Please wait 30 seconds before trying again."
                )
            return  # Block this request

    return await handler(event, data)

```

### src\bot\middleware\security.py

**Розмір:** 12,414 байт

```python
"""Security middleware for input validation and threat detection."""

from typing import Any, Callable, Dict

import structlog

logger = structlog.get_logger()


async def security_middleware(
    handler: Callable, event: Any, data: Dict[str, Any]
) -> Any:
    """Validate inputs and detect security threats.

    This middleware:
    1. Validates message content for dangerous patterns
    2. Sanitizes file uploads
    3. Detects potential attacks
    4. Logs security violations
    """
    user_id = event.effective_user.id if event.effective_user else None
    username = (
        getattr(event.effective_user, "username", None)
        if event.effective_user
        else None
    )

    if not user_id:
        logger.warning("No user information in update")
        return await handler(event, data)

    # Get dependencies from context
    security_validator = data.get("security_validator")
    audit_logger = data.get("audit_logger")

    if not security_validator:
        logger.error("Security validator not available in middleware context")
        # Continue without validation (log error but don't block)
        return await handler(event, data)

    # Validate text content if present
    message = event.effective_message
    if message and message.text:
        is_safe, violation_type = await validate_message_content(
            message.text, security_validator, user_id, audit_logger
        )
        if not is_safe:
            await message.reply_text(
                f"🛡️ **Security Alert**\n\n"
                f"Your message contains potentially dangerous content and has been blocked.\n"
                f"Violation: {violation_type}\n\n"
                "If you believe this is an error, please contact the administrator."
            )
            return  # Block processing

    # Validate file uploads if present
    if message and message.document:
        is_safe, error_message = await validate_file_upload(
            message.document, security_validator, user_id, audit_logger
        )
        if not is_safe:
            await message.reply_text(
                f"🛡️ **File Upload Blocked**\n\n"
                f"{error_message}\n\n"
                "Please ensure your file meets security requirements."
            )
            return  # Block processing

    # Log successful security validation
    logger.debug(
        "Security validation passed",
        user_id=user_id,
        username=username,
        has_text=bool(message and message.text),
        has_document=bool(message and message.document),
    )

    # Continue to handler
    return await handler(event, data)


async def validate_message_content(
    text: str, security_validator: Any, user_id: int, audit_logger: Any
) -> tuple[bool, str]:
    """Validate message text content for security threats."""

    # Check for command injection patterns
    dangerous_patterns = [
        r";\s*rm\s+",
        r";\s*del\s+",
        r";\s*format\s+",
        r"`[^`]*`",
        r"\$\([^)]*\)",
        r"&&\s*rm\s+",
        r"\|\s*mail\s+",
        r">\s*/dev/",
        r"curl\s+.*\|\s*sh",
        r"wget\s+.*\|\s*sh",
        r"exec\s*\(",
        r"eval\s*\(",
    ]

    import re

    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            if audit_logger:
                await audit_logger.log_security_violation(
                    user_id=user_id,
                    violation_type="command_injection_attempt",
                    details=f"Dangerous pattern detected: {pattern}",
                    severity="high",
                    attempted_action="message_send",
                )

            logger.warning(
                "Command injection attempt detected",
                user_id=user_id,
                pattern=pattern,
                text_preview=text[:100],
            )
            return False, "Command injection attempt"

    # Check for path traversal attempts
    path_traversal_patterns = [
        r"\.\./.*",
        r"~\/.*",
        r"\/etc\/.*",
        r"\/var\/.*",
        r"\/usr\/.*",
        r"\/sys\/.*",
        r"\/proc\/.*",
    ]

    for pattern in path_traversal_patterns:
        if re.search(pattern, text):
            if audit_logger:
                await audit_logger.log_security_violation(
                    user_id=user_id,
                    violation_type="path_traversal_attempt",
                    details=f"Path traversal pattern detected: {pattern}",
                    severity="high",
                    attempted_action="message_send",
                )

            logger.warning(
                "Path traversal attempt detected",
                user_id=user_id,
                pattern=pattern,
                text_preview=text[:100],
            )
            return False, "Path traversal attempt"

    # Check for suspicious URLs or domains
    suspicious_patterns = [
        r"https?://[^/]*\.ru/",
        r"https?://[^/]*\.tk/",
        r"https?://[^/]*\.ml/",
        r"https?://bit\.ly/",
        r"https?://tinyurl\.com/",
        r"javascript:",
        r"data:text/html",
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            if audit_logger:
                await audit_logger.log_security_violation(
                    user_id=user_id,
                    violation_type="suspicious_url",
                    details=f"Suspicious URL pattern detected: {pattern}",
                    severity="medium",
                    attempted_action="message_send",
                )

            logger.warning("Suspicious URL detected", user_id=user_id, pattern=pattern)
            return False, "Suspicious URL detected"

    # Sanitize content using security validator
    sanitized = security_validator.sanitize_command_input(text)
    if len(sanitized) < len(text) * 0.5:  # More than 50% removed
        if audit_logger:
            await audit_logger.log_security_violation(
                user_id=user_id,
                violation_type="excessive_sanitization",
                details="More than 50% of content was dangerous",
                severity="medium",
                attempted_action="message_send",
            )

        logger.warning(
            "Excessive content sanitization required",
            user_id=user_id,
            original_length=len(text),
            sanitized_length=len(sanitized),
        )
        return False, "Content contains too many dangerous characters"

    return True, ""


async def validate_file_upload(
    document: Any, security_validator: Any, user_id: int, audit_logger: Any
) -> tuple[bool, str]:
    """Validate file uploads for security."""

    filename = getattr(document, "file_name", "unknown")
    file_size = getattr(document, "file_size", 0)
    mime_type = getattr(document, "mime_type", "unknown")

    # Validate filename
    is_valid, error_message = security_validator.validate_filename(filename)
    if not is_valid:
        if audit_logger:
            await audit_logger.log_security_violation(
                user_id=user_id,
                violation_type="dangerous_filename",
                details=f"Filename validation failed: {error_message}",
                severity="medium",
                attempted_action="file_upload",
            )

        logger.warning(
            "Dangerous filename detected",
            user_id=user_id,
            filename=filename,
            error=error_message,
        )
        return False, error_message

    # Check file size limits
    max_file_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_file_size:
        if audit_logger:
            await audit_logger.log_security_violation(
                user_id=user_id,
                violation_type="file_too_large",
                details=f"File size {file_size} exceeds limit {max_file_size}",
                severity="low",
                attempted_action="file_upload",
            )

        return False, f"File too large. Maximum size: {max_file_size // (1024*1024)}MB"

    # Check MIME type
    dangerous_mime_types = [
        "application/x-executable",
        "application/x-msdownload",
        "application/x-msdos-program",
        "application/x-dosexec",
        "application/x-winexe",
        "application/x-sh",
        "application/x-shellscript",
    ]

    if mime_type in dangerous_mime_types:
        if audit_logger:
            await audit_logger.log_security_violation(
                user_id=user_id,
                violation_type="dangerous_mime_type",
                details=f"Dangerous MIME type: {mime_type}",
                severity="high",
                attempted_action="file_upload",
            )

        logger.warning(
            "Dangerous MIME type detected",
            user_id=user_id,
            filename=filename,
            mime_type=mime_type,
        )
        return False, f"File type not allowed: {mime_type}"

    # Log successful file validation
    if audit_logger:
        await audit_logger.log_file_access(
            user_id=user_id,
            file_path=filename,
            action="upload_validated",
            success=True,
            file_size=file_size,
        )

    logger.info(
        "File upload validated",
        user_id=user_id,
        filename=filename,
        file_size=file_size,
        mime_type=mime_type,
    )

    return True, ""


async def threat_detection_middleware(
    handler: Callable, event: Any, data: Dict[str, Any]
) -> Any:
    """Advanced threat detection middleware.

    This middleware looks for patterns that might indicate
    sophisticated attacks or reconnaissance attempts.
    """
    user_id = event.effective_user.id if event.effective_user else None
    if not user_id:
        return await handler(event, data)

    audit_logger = data.get("audit_logger")

    # Track user behavior patterns
    user_behavior = data.setdefault("user_behavior", {})
    user_data = user_behavior.setdefault(
        user_id,
        {
            "message_count": 0,
            "failed_commands": 0,
            "path_requests": 0,
            "file_requests": 0,
            "first_seen": None,
        },
    )

    import time

    current_time = time.time()

    if user_data["first_seen"] is None:
        user_data["first_seen"] = current_time

    user_data["message_count"] += 1

    # Check for reconnaissance patterns
    message = event.effective_message
    text = message.text if message else ""

    # Suspicious commands that might indicate reconnaissance
    recon_patterns = [
        r"ls\s+/",
        r"find\s+/",
        r"locate\s+",
        r"which\s+",
        r"whereis\s+",
        r"ps\s+",
        r"netstat\s+",
        r"lsof\s+",
        r"env\s*$",
        r"printenv\s*$",
        r"whoami\s*$",
        r"id\s*$",
        r"uname\s+",
        r"cat\s+/etc/",
        r"cat\s+/proc/",
    ]

    import re

    recon_attempts = sum(
        1 for pattern in recon_patterns if re.search(pattern, text, re.IGNORECASE)
    )

    if recon_attempts > 0:
        user_data["recon_attempts"] = (
            user_data.get("recon_attempts", 0) + recon_attempts
        )

        # Alert if too many reconnaissance attempts
        if user_data["recon_attempts"] > 5:
            if audit_logger:
                await audit_logger.log_security_violation(
                    user_id=user_id,
                    violation_type="reconnaissance_attempt",
                    details=f"Multiple reconnaissance patterns detected: {user_data['recon_attempts']}",
                    severity="high",
                    attempted_action="reconnaissance",
                )

            logger.warning(
                "Reconnaissance attempt pattern detected",
                user_id=user_id,
                total_attempts=user_data["recon_attempts"],
                current_message=text[:100],
            )

            if event.effective_message:
                await event.effective_message.reply_text(
                    "🔍 **Suspicious Activity Detected**\n\n"
                    "Multiple reconnaissance-style commands detected. "
                    "This activity has been logged.\n\n"
                    "If you have legitimate needs, please contact the administrator."
                )

    return await handler(event, data)

```

### src\bot\middleware\__init__.py

**Розмір:** 272 байт

```python
"""Bot middleware for authentication, rate limiting, and security."""

from .auth import auth_middleware
from .rate_limit import rate_limit_middleware
from .security import security_middleware

__all__ = ["auth_middleware", "rate_limit_middleware", "security_middleware"]

```

### src\bot\utils\formatting.py

**Розмір:** 25,152 байт

```python
"""Format bot responses for optimal display."""

import re
from dataclasses import dataclass
from typing import Any, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ...config.settings import Settings


@dataclass
class FormattedMessage:
    """Represents a formatted message for Telegram."""

    text: str
    parse_mode: str = "Markdown"
    reply_markup: Optional[InlineKeyboardMarkup] = None

    def __len__(self) -> int:
        """Return length of message text."""
        return len(self.text)


class ResponseFormatter:
    """Format Claude responses for Telegram display."""

    def __init__(self, settings: Settings):
        """Initialize formatter with settings."""
        self.settings = settings
        self.max_message_length = 4000  # Telegram limit is 4096, leave some buffer
        self.max_code_block_length = 3000  # Max length for code blocks

    def format_claude_response(
        self, text: str, context: Optional[dict] = None
    ) -> List[FormattedMessage]:
        """Enhanced formatting with context awareness and semantic chunking."""
        # Clean and prepare text
        text = self._clean_text(text)

        # Check if we need semantic chunking (for complex content)
        if self._should_use_semantic_chunking(text):
            # Use enhanced semantic chunking for complex content
            chunks = self._semantic_chunk(text, context)
            messages = []
            for chunk in chunks:
                formatted = self._format_chunk(chunk)
                messages.extend(formatted)
        else:
            # Use original simple formatting for basic content
            text = self._format_code_blocks(text)
            messages = self._split_message(text)

        # Add context-aware quick actions to the last message
        if messages and self.settings.enable_quick_actions:
            messages[-1].reply_markup = self._get_contextual_keyboard(context)

        return messages if messages else [FormattedMessage("_(No content to display)_")]

    def _should_use_semantic_chunking(self, text: str) -> bool:
        """Determine if semantic chunking is needed."""
        # Use semantic chunking for complex content with multiple code blocks,
        # file operations, or very long text
        code_block_count = text.count("```")
        has_file_operations = any(
            indicator in text
            for indicator in [
                "Creating file",
                "Editing file",
                "Reading file",
                "Writing to",
                "Modified file",
                "Deleted file",
                "File created",
                "File updated",
            ]
        )
        is_very_long = len(text) > self.max_message_length * 2

        return code_block_count > 2 or has_file_operations or is_very_long

    def format_error_message(
        self, error: str, error_type: str = "Error"
    ) -> FormattedMessage:
        """Format error message with appropriate styling."""
        icon = {
            "Error": "❌",
            "Warning": "⚠️",
            "Info": "ℹ️",
            "Security": "🛡️",
            "Rate Limit": "⏱️",
        }.get(error_type, "❌")

        text = f"{icon} **{error_type}**\n\n{error}"

        return FormattedMessage(text, parse_mode="Markdown")

    def format_success_message(
        self, message: str, title: str = "Success"
    ) -> FormattedMessage:
        """Format success message with appropriate styling."""
        text = f"✅ **{title}**\n\n{message}"
        return FormattedMessage(text, parse_mode="Markdown")

    def format_info_message(
        self, message: str, title: str = "Info"
    ) -> FormattedMessage:
        """Format info message with appropriate styling."""
        text = f"ℹ️ **{title}**\n\n{message}"
        return FormattedMessage(text, parse_mode="Markdown")

    def format_code_output(
        self, output: str, language: str = "", title: str = "Output"
    ) -> List[FormattedMessage]:
        """Format code output with syntax highlighting."""
        if not output.strip():
            return [FormattedMessage(f"📄 **{title}**\n\n_(empty output)_")]

        # Add language hint if provided
        code_block = (
            f"```{language}\n{output}\n```" if language else f"```\n{output}\n```"
        )

        # Check if the code block is too long
        if len(code_block) > self.max_code_block_length:
            # Truncate and add notice
            truncated = output[: self.max_code_block_length - 100]
            code_block = f"```{language}\n{truncated}\n... (output truncated)\n```"

        text = f"📄 **{title}**\n\n{code_block}"

        return self._split_message(text)

    def format_file_list(
        self, files: List[str], directory: str = ""
    ) -> FormattedMessage:
        """Format file listing with appropriate icons."""
        if not files:
            text = f"📂 **{directory}**\n\n_(empty directory)_"
        else:
            file_lines = []
            for file in files[:50]:  # Limit to 50 items
                if file.endswith("/"):
                    file_lines.append(f"📁 {file}")
                else:
                    file_lines.append(f"📄 {file}")

            file_text = "\n".join(file_lines)
            if len(files) > 50:
                file_text += f"\n\n_... and {len(files) - 50} more items_"

            text = f"📂 **{directory}**\n\n{file_text}"

        return FormattedMessage(text, parse_mode="Markdown")

    def format_progress_message(
        self, message: str, percentage: Optional[float] = None
    ) -> FormattedMessage:
        """Format progress message with optional progress bar."""
        if percentage is not None:
            # Create simple progress bar
            filled = int(percentage / 10)
            empty = 10 - filled
            progress_bar = "▓" * filled + "░" * empty
            text = f"🔄 **{message}**\n\n{progress_bar} {percentage:.0f}%"
        else:
            text = f"🔄 **{message}**"

        return FormattedMessage(text, parse_mode="Markdown")

    def _semantic_chunk(self, text: str, context: Optional[dict]) -> List[dict]:
        """Split text into semantic chunks based on content type."""
        chunks = []

        # Identify different content sections
        sections = self._identify_sections(text)

        for section in sections:
            if section["type"] == "code_block":
                chunks.extend(self._chunk_code_block(section))
            elif section["type"] == "explanation":
                chunks.extend(self._chunk_explanation(section))
            elif section["type"] == "file_operations":
                chunks.append(self._format_file_operations_section(section))
            elif section["type"] == "mixed":
                chunks.extend(self._chunk_mixed_content(section))
            else:
                # Default text chunking
                chunks.extend(self._chunk_text(section))

        return chunks

    def _identify_sections(self, text: str) -> List[dict]:
        """Identify different content types in the text."""
        sections = []
        lines = text.split("\n")
        current_section = {"type": "text", "content": "", "start_line": 0}
        in_code_block = False
        code_start = 0

        for i, line in enumerate(lines):
            # Check for code block markers
            if line.strip().startswith("```"):
                if not in_code_block:
                    # Start of code block
                    if current_section["content"].strip():
                        sections.append(current_section)
                    in_code_block = True
                    code_start = i
                    current_section = {
                        "type": "code_block",
                        "content": line + "\n",
                        "start_line": i,
                    }
                else:
                    # End of code block
                    current_section["content"] += line + "\n"
                    sections.append(current_section)
                    in_code_block = False
                    current_section = {
                        "type": "text",
                        "content": "",
                        "start_line": i + 1,
                    }
            elif in_code_block:
                current_section["content"] += line + "\n"
            else:
                # Check for file operation patterns
                if self._is_file_operation_line(line):
                    if current_section["type"] != "file_operations":
                        if current_section["content"].strip():
                            sections.append(current_section)
                        current_section = {
                            "type": "file_operations",
                            "content": line + "\n",
                            "start_line": i,
                        }
                    else:
                        current_section["content"] += line + "\n"
                else:
                    # Regular text
                    if current_section["type"] != "text":
                        if current_section["content"].strip():
                            sections.append(current_section)
                        current_section = {
                            "type": "text",
                            "content": line + "\n",
                            "start_line": i,
                        }
                    else:
                        current_section["content"] += line + "\n"

        # Add the last section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _is_file_operation_line(self, line: str) -> bool:
        """Check if a line indicates file operations."""
        file_indicators = [
            "Creating file",
            "Editing file",
            "Reading file",
            "Writing to",
            "Modified file",
            "Deleted file",
            "File created",
            "File updated",
        ]
        return any(indicator in line for indicator in file_indicators)

    def _chunk_code_block(self, section: dict) -> List[dict]:
        """Handle code block chunking."""
        content = section["content"]
        if len(content) <= self.max_code_block_length:
            return [{"type": "code_block", "content": content, "format": "single"}]

        # Split large code blocks
        chunks = []
        lines = content.split("\n")
        current_chunk = lines[0] + "\n"  # Start with the ``` line

        for line in lines[1:-1]:  # Skip first and last ``` lines
            if len(current_chunk + line + "\n```\n") > self.max_code_block_length:
                current_chunk += "```"
                chunks.append(
                    {"type": "code_block", "content": current_chunk, "format": "split"}
                )
                current_chunk = "```\n" + line + "\n"
            else:
                current_chunk += line + "\n"

        current_chunk += lines[-1]  # Add the closing ```
        chunks.append(
            {"type": "code_block", "content": current_chunk, "format": "split"}
        )

        return chunks

    def _chunk_explanation(self, section: dict) -> List[dict]:
        """Handle explanation text chunking."""
        content = section["content"]
        if len(content) <= self.max_message_length:
            return [{"type": "explanation", "content": content}]

        # Split by paragraphs first
        paragraphs = content.split("\n\n")
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            if len(current_chunk + paragraph + "\n\n") > self.max_message_length:
                if current_chunk:
                    chunks.append(
                        {"type": "explanation", "content": current_chunk.strip()}
                    )
                current_chunk = paragraph + "\n\n"
            else:
                current_chunk += paragraph + "\n\n"

        if current_chunk:
            chunks.append({"type": "explanation", "content": current_chunk.strip()})

        return chunks

    def _chunk_mixed_content(self, section: dict) -> List[dict]:
        """Handle mixed content sections."""
        # For now, treat as regular text
        return self._chunk_text(section)

    def _chunk_text(self, section: dict) -> List[dict]:
        """Handle regular text chunking."""
        content = section["content"]
        if len(content) <= self.max_message_length:
            return [{"type": "text", "content": content}]

        # Split at natural break points
        chunks = []
        current_chunk = ""

        sentences = content.split(". ")
        for sentence in sentences:
            test_chunk = current_chunk + sentence + ". "
            if len(test_chunk) > self.max_message_length:
                if current_chunk:
                    chunks.append({"type": "text", "content": current_chunk.strip()})
                current_chunk = sentence + ". "
            else:
                current_chunk = test_chunk

        if current_chunk:
            chunks.append({"type": "text", "content": current_chunk.strip()})

        return chunks

    def _format_file_operations_section(self, section: dict) -> dict:
        """Format file operations section."""
        return {"type": "file_operations", "content": section["content"]}

    def _format_chunk(self, chunk: dict) -> List[FormattedMessage]:
        """Format individual chunks into FormattedMessage objects."""
        chunk_type = chunk["type"]
        content = chunk["content"]

        if chunk_type == "code_block":
            # Format code blocks with proper styling
            if chunk.get("format") == "split":
                title = (
                    "📄 **Code (continued)**"
                    if "continued" in content
                    else "📄 **Code**"
                )
            else:
                title = "📄 **Code**"

            text = f"{title}\n\n{content}"

        elif chunk_type == "file_operations":
            # Format file operations with icons
            text = f"📁 **File Operations**\n\n{content}"

        elif chunk_type == "explanation":
            # Regular explanation text
            text = content

        else:
            # Default text formatting
            text = content

        # Split if still too long
        return self._split_message(text)

    def _get_contextual_keyboard(
        self, context: Optional[dict]
    ) -> Optional[InlineKeyboardMarkup]:
        """Get context-aware quick action keyboard."""
        if not context:
            return self._get_quick_actions_keyboard()

        buttons = []

        # Add context-specific buttons
        if context.get("has_code"):
            buttons.append(
                [InlineKeyboardButton("💾 Save Code", callback_data="save_code")]
            )

        if context.get("has_file_operations"):
            buttons.append(
                [InlineKeyboardButton("📁 Show Files", callback_data="show_files")]
            )

        if context.get("has_errors"):
            buttons.append([InlineKeyboardButton("🔧 Debug", callback_data="debug")])

        # Add default actions
        default_buttons = [
            [InlineKeyboardButton("🔄 Continue", callback_data="continue")],
            [InlineKeyboardButton("💡 Explain", callback_data="explain")],
        ]
        buttons.extend(default_buttons)

        return InlineKeyboardMarkup(buttons) if buttons else None

    def _clean_text(self, text: str) -> str:
        """Clean text for Telegram display."""
        # Remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Escape special Markdown characters (but preserve intentional formatting)
        # Be careful not to escape characters inside code blocks
        text = self._escape_markdown_outside_code(text)

        return text.strip()

    def _escape_markdown_outside_code(self, text: str) -> str:
        """Escape Markdown characters outside of code blocks."""
        # This is a simplified approach - in practice, you might want more sophisticated parsing
        parts = []
        in_code_block = False
        in_inline_code = False

        lines = text.split("\n")
        for line in lines:
            if line.strip() == "```":
                in_code_block = not in_code_block
                parts.append(line)
            elif in_code_block:
                parts.append(line)
            else:
                # Handle inline code
                line_parts = line.split("`")
                for i, part in enumerate(line_parts):
                    if i % 2 == 0:  # Outside inline code
                        # Escape special characters
                        part = part.replace("_", r"\_").replace("*", r"\*")
                    line_parts[i] = part
                parts.append("`".join(line_parts))

        return "\n".join(parts)

    def _format_code_blocks(self, text: str) -> str:
        """Ensure code blocks are properly formatted for Telegram."""
        # Handle triple backticks with language specification
        pattern = r"```(\w+)?\n(.*?)```"

        def replace_code_block(match):
            lang = match.group(1) or ""
            code = match.group(2)

            # Telegram doesn't support language hints, but we can add them as comments
            if lang and lang.lower() not in ["text", "plain"]:
                # Add language as a comment at the top
                code = f"# {lang}\n{code}"

            # Ensure code block doesn't exceed length limits
            if len(code) > self.max_code_block_length:
                code = code[: self.max_code_block_length - 50] + "\n... (truncated)"

            return f"```\n{code}\n```"

        return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)

    def _split_message(self, text: str) -> List[FormattedMessage]:
        """Split long messages while preserving formatting."""
        if len(text) <= self.max_message_length:
            return [FormattedMessage(text)]

        messages = []
        current_lines = []
        current_length = 0
        in_code_block = False

        lines = text.split("\n")

        for line in lines:
            line_length = len(line) + 1  # +1 for newline

            # Check for code block markers
            if line.strip() == "```":
                in_code_block = not in_code_block

            # If this is a very long line that exceeds limit by itself, split it
            if line_length > self.max_message_length:
                # Split the line into chunks
                chunks = []
                for i in range(0, len(line), self.max_message_length - 100):
                    chunks.append(line[i : i + self.max_message_length - 100])

                for chunk in chunks:
                    chunk_length = len(chunk) + 1

                    if (
                        current_length + chunk_length > self.max_message_length
                        and current_lines
                    ):
                        # Save current message
                        if in_code_block:
                            current_lines.append("```")
                        messages.append(FormattedMessage("\n".join(current_lines)))

                        # Start new message
                        current_lines = []
                        current_length = 0
                        if in_code_block:
                            current_lines.append("```")
                            current_length = 4

                    current_lines.append(chunk)
                    current_length += chunk_length
                continue

            # Check if adding this line would exceed the limit
            if current_length + line_length > self.max_message_length and current_lines:
                # Close code block if we're in one
                if in_code_block:
                    current_lines.append("```")

                # Save current message
                messages.append(FormattedMessage("\n".join(current_lines)))

                # Start new message
                current_lines = []
                current_length = 0

                # Reopen code block if needed
                if in_code_block:
                    current_lines.append("```")
                    current_length = 4  # Length of '```\n'

            current_lines.append(line)
            current_length += line_length

        # Add remaining content
        if current_lines:
            # Close code block if needed
            if in_code_block:
                current_lines.append("```")
            messages.append(FormattedMessage("\n".join(current_lines)))

        return messages

    def _get_quick_actions_keyboard(self) -> InlineKeyboardMarkup:
        """Get quick actions inline keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🧪 Test", callback_data="quick:test"),
                InlineKeyboardButton("📦 Install", callback_data="quick:install"),
                InlineKeyboardButton("🎨 Format", callback_data="quick:format"),
            ],
            [
                InlineKeyboardButton("🔍 Find TODOs", callback_data="quick:find_todos"),
                InlineKeyboardButton("🔨 Build", callback_data="quick:build"),
                InlineKeyboardButton("📊 Git Status", callback_data="quick:git_status"),
            ],
        ]

        return InlineKeyboardMarkup(keyboard)

    def create_confirmation_keyboard(
        self, confirm_data: str, cancel_data: str = "confirm:no"
    ) -> InlineKeyboardMarkup:
        """Create a confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data=confirm_data),
                InlineKeyboardButton("❌ No", callback_data=cancel_data),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_navigation_keyboard(self, options: List[tuple]) -> InlineKeyboardMarkup:
        """Create navigation keyboard from options list.

        Args:
            options: List of (text, callback_data) tuples
        """
        keyboard = []
        current_row = []

        for text, callback_data in options:
            current_row.append(InlineKeyboardButton(text, callback_data=callback_data))

            # Create rows of 2 buttons
            if len(current_row) == 2:
                keyboard.append(current_row)
                current_row = []

        # Add remaining button if any
        if current_row:
            keyboard.append(current_row)

        return InlineKeyboardMarkup(keyboard)


class ProgressIndicator:
    """Helper for creating progress indicators."""

    @staticmethod
    def create_bar(
        percentage: float,
        length: int = 10,
        filled_char: str = "▓",
        empty_char: str = "░",
    ) -> str:
        """Create a progress bar."""
        filled = int((percentage / 100) * length)
        empty = length - filled
        return filled_char * filled + empty_char * empty

    @staticmethod
    def create_spinner(step: int) -> str:
        """Create a spinning indicator."""
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        return spinners[step % len(spinners)]

    @staticmethod
    def create_dots(step: int) -> str:
        """Create a dots indicator."""
        dots = ["", ".", "..", "..."]
        return dots[step % len(dots)]


class CodeHighlighter:
    """Simple code highlighting for common languages."""

    # Language file extensions mapping
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".sql": "sql",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
    }

    @classmethod
    def detect_language(cls, filename: str) -> str:
        """Detect programming language from filename."""
        from pathlib import Path

        ext = Path(filename).suffix.lower()
        return cls.LANGUAGE_EXTENSIONS.get(ext, "")

    @classmethod
    def format_code(cls, code: str, language: str = "", filename: str = "") -> str:
        """Format code with language detection."""
        if not language and filename:
            language = cls.detect_language(filename)

        if language:
            return f"```{language}\n{code}\n```"
        else:
            return f"```\n{code}\n```"

```

### src\bot\utils\__init__.py

**Розмір:** 29 байт

```python
"""Bot utilities package."""

```

### src\claude\exceptions.py

**Розмір:** 793 байт

```python
"""Claude-specific exceptions."""


class ClaudeError(Exception):
    """Base Claude error."""

    pass


class ClaudeTimeoutError(ClaudeError):
    """Operation timed out."""

    pass


class ClaudeProcessError(ClaudeError):
    """Process execution failed."""

    pass


class ClaudeParsingError(ClaudeError):
    """Failed to parse output."""

    pass


class ClaudeSessionError(ClaudeError):
    """Session management error."""

    pass


class ClaudeToolValidationError(ClaudeError):
    """Tool validation failed during Claude execution."""

    def __init__(
        self, message: str, blocked_tools: list = None, allowed_tools: list = None
    ):
        super().__init__(message)
        self.blocked_tools = blocked_tools or []
        self.allowed_tools = allowed_tools or []

```

### src\claude\facade.py

**Розмір:** 19,386 байт

```python
"""High-level Claude Code integration facade.

Provides simple interface for bot handlers.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import structlog

from ..config.settings import Settings
from .exceptions import ClaudeToolValidationError
from .integration import ClaudeProcessManager, ClaudeResponse, StreamUpdate
from .monitor import ToolMonitor
from .sdk_integration import ClaudeSDKManager
from .session import SessionManager

logger = structlog.get_logger()


class ClaudeIntegration:
    """Main integration point for Claude Code."""

    def __init__(
        self,
        config: Settings,
        process_manager: Optional[ClaudeProcessManager] = None,
        sdk_manager: Optional[ClaudeSDKManager] = None,
        session_manager: Optional[SessionManager] = None,
        tool_monitor: Optional[ToolMonitor] = None,
    ):
        """Initialize Claude integration facade."""
        self.config = config

        # Initialize both managers for fallback capability
        self.sdk_manager = (
            sdk_manager or ClaudeSDKManager(config) if config.use_sdk else None
        )
        self.process_manager = process_manager or ClaudeProcessManager(config)

        # Use SDK by default if configured
        if config.use_sdk:
            self.manager = self.sdk_manager
        else:
            self.manager = self.process_manager

        self.session_manager = session_manager
        self.tool_monitor = tool_monitor
        self._sdk_failed_count = 0  # Track SDK failures for adaptive fallback

    async def run_command(
        self,
        prompt: str,
        working_directory: Path,
        user_id: int,
        session_id: Optional[str] = None,
        on_stream: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Run Claude Code command with full integration."""
        logger.info(
            "Running Claude command",
            user_id=user_id,
            working_directory=str(working_directory),
            session_id=session_id,
            prompt_length=len(prompt),
        )

        # Get or create session
        session = await self.session_manager.get_or_create_session(
            user_id, working_directory, session_id
        )

        # Track streaming updates and validate tool calls
        tools_validated = True
        validation_errors = []
        blocked_tools = set()

        async def stream_handler(update: StreamUpdate):
            nonlocal tools_validated

            # Validate tool calls
            if update.tool_calls:
                for tool_call in update.tool_calls:
                    tool_name = tool_call["name"]
                    valid, error = await self.tool_monitor.validate_tool_call(
                        tool_name,
                        tool_call.get("input", {}),
                        working_directory,
                        user_id,
                    )

                    if not valid:
                        tools_validated = False
                        validation_errors.append(error)

                        # Track blocked tools
                        if "Tool not allowed:" in error:
                            blocked_tools.add(tool_name)

                        logger.error(
                            "Tool validation failed",
                            tool_name=tool_name,
                            error=error,
                            user_id=user_id,
                        )

                        # For critical tools, we should fail fast
                        if tool_name in ["Task", "Read", "Write", "Edit"]:
                            # Create comprehensive error message
                            admin_instructions = self._get_admin_instructions(
                                list(blocked_tools)
                            )
                            error_msg = self._create_tool_error_message(
                                list(blocked_tools),
                                self.config.claude_allowed_tools or [],
                                admin_instructions,
                            )

                            raise ClaudeToolValidationError(
                                error_msg,
                                blocked_tools=list(blocked_tools),
                                allowed_tools=self.config.claude_allowed_tools or [],
                            )

            # Pass to caller's handler
            if on_stream:
                try:
                    await on_stream(update)
                except Exception as e:
                    logger.warning("Stream callback failed", error=str(e))

        # Execute command
        try:
            # Only continue session if it's not a new session
            should_continue = bool(session_id) and not getattr(
                session, "is_new_session", False
            )

            # For new sessions, don't pass the temporary session_id to Claude Code
            claude_session_id = (
                None
                if getattr(session, "is_new_session", False)
                else session.session_id
            )

            response = await self._execute_with_fallback(
                prompt=prompt,
                working_directory=working_directory,
                session_id=claude_session_id,
                continue_session=should_continue,
                stream_callback=stream_handler,
            )

            # Check if tool validation failed
            if not tools_validated:
                logger.error(
                    "Command completed but tool validation failed",
                    validation_errors=validation_errors,
                )
                # Mark response as having errors and include validation details
                response.is_error = True
                response.error_type = "tool_validation_failed"

                # Extract blocked tool names for user feedback
                blocked_tools = []
                for error in validation_errors:
                    if "Tool not allowed:" in error:
                        tool_name = error.split("Tool not allowed: ")[1]
                        blocked_tools.append(tool_name)

                # Create user-friendly error message
                if blocked_tools:
                    tool_list = ", ".join(f"`{tool}`" for tool in blocked_tools)
                    response.content = (
                        f"🚫 **Tool Access Blocked**\n\n"
                        f"Claude tried to use tools not allowed:\n"
                        f"{tool_list}\n\n"
                        f"**What you can do:**\n"
                        f"• Contact the administrator to request access to these tools\n"
                        f"• Try rephrasing your request to use different approaches\n"
                        f"• Check what tools are currently available with `/status`\n\n"
                        f"**Currently allowed tools:**\n"
                        f"{', '.join(f'`{t}`' for t in self.config.claude_allowed_tools or [])}"
                    )
                else:
                    response.content = (
                        f"🚫 **Tool Validation Failed**\n\n"
                        f"Tools failed security validation. Try different approach.\n\n"
                        f"Details: {'; '.join(validation_errors)}"
                    )

            # Update session (this may change the session_id for new sessions)
            old_session_id = session.session_id
            await self.session_manager.update_session(session.session_id, response)

            # For new sessions, get the updated session_id from the session manager
            if hasattr(session, "is_new_session") and response.session_id:
                # The session_id has been updated to Claude's session_id
                final_session_id = response.session_id
            else:
                # Use the original session_id for continuing sessions
                final_session_id = old_session_id

            # Ensure response has the correct session_id
            response.session_id = final_session_id

            logger.info(
                "Claude command completed",
                session_id=response.session_id,
                cost=response.cost,
                duration_ms=response.duration_ms,
                num_turns=response.num_turns,
                is_error=response.is_error,
            )

            return response

        except Exception as e:
            logger.error(
                "Claude command failed",
                error=str(e),
                user_id=user_id,
                session_id=session.session_id,
            )
            raise

    async def _execute_with_fallback(
        self,
        prompt: str,
        working_directory: Path,
        session_id: Optional[str] = None,
        continue_session: bool = False,
        stream_callback: Optional[Callable] = None,
    ) -> ClaudeResponse:
        """Execute command with SDK->subprocess fallback on JSON decode errors."""
        # Try SDK first if configured
        if self.config.use_sdk and self.sdk_manager:
            try:
                logger.debug("Attempting Claude SDK execution")
                response = await self.sdk_manager.execute_command(
                    prompt=prompt,
                    working_directory=working_directory,
                    session_id=session_id,
                    continue_session=continue_session,
                    stream_callback=stream_callback,
                )
                # Reset failure count on success
                self._sdk_failed_count = 0
                return response

            except Exception as e:
                error_str = str(e)
                # Check if this is a JSON decode error that indicates SDK issues
                if (
                    "Failed to decode JSON" in error_str
                    or "JSON decode error" in error_str
                    or "TaskGroup" in error_str
                    or "ExceptionGroup" in error_str
                ):
                    self._sdk_failed_count += 1
                    logger.warning(
                        "Claude SDK failed with JSON/TaskGroup error, falling back to subprocess",
                        error=error_str,
                        failure_count=self._sdk_failed_count,
                        error_type=type(e).__name__,
                    )

                    # Use subprocess fallback
                    try:
                        logger.info("Executing with subprocess fallback")
                        response = await self.process_manager.execute_command(
                            prompt=prompt,
                            working_directory=working_directory,
                            session_id=session_id,
                            continue_session=continue_session,
                            stream_callback=stream_callback,
                        )
                        logger.info("Subprocess fallback succeeded")
                        return response

                    except Exception as fallback_error:
                        logger.error(
                            "Both SDK and subprocess failed",
                            sdk_error=error_str,
                            subprocess_error=str(fallback_error),
                        )
                        # Re-raise the original SDK error since it was the primary method
                        raise e
                else:
                    # For non-JSON errors, re-raise immediately
                    logger.error(
                        "Claude SDK failed with non-JSON error", error=error_str
                    )
                    raise
        else:
            # Use subprocess directly if SDK not configured
            logger.debug("Using subprocess execution (SDK disabled)")
            return await self.process_manager.execute_command(
                prompt=prompt,
                working_directory=working_directory,
                session_id=session_id,
                continue_session=continue_session,
                stream_callback=stream_callback,
            )

    async def continue_session(
        self,
        user_id: int,
        working_directory: Path,
        prompt: Optional[str] = None,
        on_stream: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> Optional[ClaudeResponse]:
        """Continue the most recent session."""
        logger.info(
            "Continuing session",
            user_id=user_id,
            working_directory=str(working_directory),
            has_prompt=bool(prompt),
        )

        # Get user's sessions
        sessions = await self.session_manager._get_user_sessions(user_id)

        # Find most recent session in this directory (exclude temporary sessions)
        matching_sessions = [
            s
            for s in sessions
            if s.project_path == working_directory
            and not s.session_id.startswith("temp_")
        ]

        if not matching_sessions:
            logger.info("No matching sessions found", user_id=user_id)
            return None

        # Get most recent
        latest_session = max(matching_sessions, key=lambda s: s.last_used)

        # Continue session
        return await self.run_command(
            prompt=prompt or "",
            working_directory=working_directory,
            user_id=user_id,
            session_id=latest_session.session_id,
            on_stream=on_stream,
        )

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return await self.session_manager.get_session_info(session_id)

    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        sessions = await self.session_manager._get_user_sessions(user_id)
        return [
            {
                "session_id": s.session_id,
                "project_path": str(s.project_path),
                "created_at": s.created_at.isoformat(),
                "last_used": s.last_used.isoformat(),
                "total_cost": s.total_cost,
                "message_count": s.message_count,
                "tools_used": s.tools_used,
                "expired": s.is_expired(self.config.session_timeout_hours),
            }
            for s in sessions
        ]

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        return await self.session_manager.cleanup_expired_sessions()

    async def get_tool_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        return self.tool_monitor.get_tool_stats()

    async def get_user_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user summary."""
        session_summary = await self.session_manager.get_user_session_summary(user_id)
        tool_usage = self.tool_monitor.get_user_tool_usage(user_id)

        return {
            "user_id": user_id,
            **session_summary,
            **tool_usage,
        }

    async def shutdown(self) -> None:
        """Shutdown integration and cleanup resources."""
        logger.info("Shutting down Claude integration")

        # Kill any active processes
        await self.manager.kill_all_processes()

        # Clean up expired sessions
        await self.cleanup_expired_sessions()

        logger.info("Claude integration shutdown complete")

    def _get_admin_instructions(self, blocked_tools: List[str]) -> str:
        """Generate admin instructions for enabling blocked tools."""
        instructions = []

        # Check if settings file exists
        settings_file = Path(".env")

        if blocked_tools:
            # Get current allowed tools and create merged list without duplicates
            current_tools = [
                "Read",
                "Write",
                "Edit",
                "Bash",
                "Glob",
                "Grep",
                "LS",
                "Task",
                "MultiEdit",
                "NotebookRead",
                "NotebookEdit",
                "WebFetch",
                "TodoRead",
                "TodoWrite",
                "WebSearch",
            ]
            merged_tools = list(
                dict.fromkeys(current_tools + blocked_tools)
            )  # Remove duplicates while preserving order
            merged_tools_str = ",".join(merged_tools)
            merged_tools_py = ", ".join(f'"{tool}"' for tool in merged_tools)

            instructions.append("**For Administrators:**")
            instructions.append("")

            if settings_file.exists():
                instructions.append(
                    "To enable these tools, add them to your `.env` file:"
                )
                instructions.append("```")
                instructions.append(f'CLAUDE_ALLOWED_TOOLS="{merged_tools_str}"')
                instructions.append("```")
            else:
                instructions.append("To enable these tools:")
                instructions.append("1. Create a `.env` file in your project root")
                instructions.append("2. Add the following line:")
                instructions.append("```")
                instructions.append(f'CLAUDE_ALLOWED_TOOLS="{merged_tools_str}"')
                instructions.append("```")

            instructions.append("")
            instructions.append("Or modify the default in `src/config/settings.py`:")
            instructions.append("```python")
            instructions.append("claude_allowed_tools: Optional[List[str]] = Field(")
            instructions.append(f"    default=[{merged_tools_py}],")
            instructions.append('    description="List of allowed Claude tools",')
            instructions.append(")")
            instructions.append("```")

        return "\n".join(instructions)

    def _create_tool_error_message(
        self,
        blocked_tools: List[str],
        allowed_tools: List[str],
        admin_instructions: str,
    ) -> str:
        """Create a comprehensive error message for tool validation failures."""
        tool_list = ", ".join(f"`{tool}`" for tool in blocked_tools)
        allowed_list = (
            ", ".join(f"`{tool}`" for tool in allowed_tools)
            if allowed_tools
            else "None"
        )

        message = [
            "🚫 **Tool Access Blocked**",
            "",
            f"Claude tried to use tools that are not currently allowed:",
            f"{tool_list}",
            "",
            "**Why this happened:**",
            "• Claude needs these tools to complete your request",
            "• These tools are not in the allowed tools list",
            "• This is a security feature to control what Claude can do",
            "",
            "**What you can do:**",
            "• Contact the administrator to request access to these tools",
            "• Try rephrasing your request to use different approaches",
            "• Use simpler requests that don't require these tools",
            "",
            "**Currently allowed tools:**",
            f"{allowed_list}",
            "",
            admin_instructions,
        ]

        return "\n".join(message)

```

### src\claude\integration.py

**Розмір:** 20,298 байт

```python
"""Claude Code subprocess management.

Features:
- Async subprocess execution
- Stream handling
- Timeout management
- Error recovery
"""

import asyncio
import json
import uuid
from asyncio.subprocess import Process
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import structlog

from ..config.settings import Settings
from .exceptions import (
    ClaudeParsingError,
    ClaudeProcessError,
    ClaudeTimeoutError,
)

logger = structlog.get_logger()


@dataclass
class ClaudeResponse:
    """Response from Claude Code."""

    content: str
    session_id: str
    cost: float
    duration_ms: int
    num_turns: int
    is_error: bool = False
    error_type: Optional[str] = None
    tools_used: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StreamUpdate:
    """Enhanced streaming update from Claude with richer context."""

    type: str  # 'assistant', 'user', 'system', 'result', 'tool_result', 'error', 'progress'
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None

    # Enhanced fields for better tracking
    timestamp: Optional[str] = None
    session_context: Optional[Dict] = None
    progress: Optional[Dict] = None
    error_info: Optional[Dict] = None

    # Execution tracking
    execution_id: Optional[str] = None
    parent_message_id: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this update represents an error."""
        return self.type == "error" or (
            self.metadata and self.metadata.get("is_error", False)
        )

    def get_tool_names(self) -> List[str]:
        """Extract tool names from tool calls."""
        if not self.tool_calls:
            return []
        return [call.get("name") for call in self.tool_calls if call.get("name")]

    def get_progress_percentage(self) -> Optional[int]:
        """Get progress percentage if available."""
        if self.progress:
            return self.progress.get("percentage")
        return None

    def get_error_message(self) -> Optional[str]:
        """Get error message if this is an error update."""
        if self.error_info:
            return self.error_info.get("message")
        elif self.is_error() and self.content:
            return self.content
        return None


class ClaudeProcessManager:
    """Manage Claude Code subprocess execution with memory optimization."""

    def __init__(self, config: Settings):
        """Initialize process manager with configuration."""
        self.config = config
        self.active_processes: Dict[str, Process] = {}

        # Memory optimization settings
        self.max_message_buffer = 1000  # Limit message history
        self.streaming_buffer_size = (
            65536  # 64KB streaming buffer for large JSON messages
        )

    async def execute_command(
        self,
        prompt: str,
        working_directory: Path,
        session_id: Optional[str] = None,
        continue_session: bool = False,
        stream_callback: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Execute Claude Code command."""
        # Build command
        cmd = self._build_command(prompt, session_id, continue_session)

        # Create process ID for tracking
        process_id = str(uuid.uuid4())

        logger.info(
            "Starting Claude Code process",
            process_id=process_id,
            working_directory=str(working_directory),
            session_id=session_id,
            continue_session=continue_session,
        )

        try:
            # Start process
            process = await self._start_process(cmd, working_directory)
            self.active_processes[process_id] = process

            # Handle output with timeout
            result = await asyncio.wait_for(
                self._handle_process_output(process, stream_callback),
                timeout=self.config.claude_timeout_seconds,
            )

            logger.info(
                "Claude Code process completed successfully",
                process_id=process_id,
                cost=result.cost,
                duration_ms=result.duration_ms,
            )

            return result

        except asyncio.TimeoutError:
            # Kill process on timeout
            if process_id in self.active_processes:
                self.active_processes[process_id].kill()
                await self.active_processes[process_id].wait()

            logger.error(
                "Claude Code process timed out",
                process_id=process_id,
                timeout_seconds=self.config.claude_timeout_seconds,
            )

            raise ClaudeTimeoutError(
                f"Claude Code timed out after {self.config.claude_timeout_seconds}s"
            )

        except Exception as e:
            logger.error(
                "Claude Code process failed",
                process_id=process_id,
                error=str(e),
            )
            raise

        finally:
            # Clean up
            if process_id in self.active_processes:
                del self.active_processes[process_id]

    def _build_command(
        self, prompt: str, session_id: Optional[str], continue_session: bool
    ) -> List[str]:
        """Build Claude Code command with arguments."""
        cmd = [self.config.claude_binary_path or "claude"]

        if continue_session and not prompt:
            # Continue existing session without new prompt
            cmd.extend(["--continue"])
            if session_id:
                cmd.extend(["--resume", session_id])
        elif session_id and prompt and continue_session:
            # Follow-up message in existing session - use resume with new prompt
            cmd.extend(["--resume", session_id, "-p", prompt])
        elif prompt:
            # New session with prompt (including new sessions with session_id)
            cmd.extend(["-p", prompt])
        else:
            # This shouldn't happen, but fallback to new session
            cmd.extend(["-p", ""])

        # Always use streaming JSON for real-time updates
        cmd.extend(["--output-format", "stream-json"])

        # stream-json requires --verbose when using --print mode
        cmd.extend(["--verbose"])

        # Add safety limits
        cmd.extend(["--max-turns", str(self.config.claude_max_turns)])

        # Add allowed tools if configured
        if (
            hasattr(self.config, "claude_allowed_tools")
            and self.config.claude_allowed_tools
        ):
            cmd.extend(["--allowedTools", ",".join(self.config.claude_allowed_tools)])

        logger.debug("Built Claude Code command", command=cmd)
        return cmd

    async def _start_process(self, cmd: List[str], cwd: Path) -> Process:
        """Start Claude Code subprocess."""
        return await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            # Limit memory usage
            limit=1024 * 1024 * 512,  # 512MB
        )

    async def _handle_process_output(
        self, process: Process, stream_callback: Optional[Callable]
    ) -> ClaudeResponse:
        """Memory-optimized output handling with bounded buffers."""
        message_buffer = deque(maxlen=self.max_message_buffer)
        result = None
        parsing_errors = []

        async for line in self._read_stream_bounded(process.stdout):
            try:
                msg = json.loads(line)

                # Enhanced validation
                if not self._validate_message_structure(msg):
                    parsing_errors.append(f"Invalid message structure: {line[:100]}")
                    continue

                message_buffer.append(msg)

                # Process immediately to avoid memory buildup
                update = self._parse_stream_message(msg)
                if update and stream_callback:
                    try:
                        await stream_callback(update)
                    except Exception as e:
                        logger.warning(
                            "Stream callback failed",
                            error=str(e),
                            update_type=update.type,
                        )

                # Check for final result
                if msg.get("type") == "result":
                    result = msg

            except json.JSONDecodeError as e:
                parsing_errors.append(f"JSON decode error: {e}")
                logger.warning(
                    "Failed to parse JSON line", line=line[:200], error=str(e)
                )
                continue

        # Enhanced error reporting
        if parsing_errors:
            logger.warning(
                "Parsing errors encountered",
                count=len(parsing_errors),
                errors=parsing_errors[:5],
            )

        # Wait for process to complete
        return_code = await process.wait()

        if return_code != 0:
            stderr = await process.stderr.read()
            error_msg = stderr.decode("utf-8", errors="replace")
            logger.error(
                "Claude Code process failed",
                return_code=return_code,
                stderr=error_msg,
            )

            # Check for specific error types
            if "usage limit reached" in error_msg.lower():
                # Extract reset time if available
                import re

                time_match = re.search(
                    r"reset at (\d+[apm]+)", error_msg, re.IGNORECASE
                )
                timezone_match = re.search(r"\(([^)]+)\)", error_msg)

                reset_time = time_match.group(1) if time_match else "later"
                timezone = timezone_match.group(1) if timezone_match else ""

                user_friendly_msg = (
                    f"⏱️ **Claude AI Usage Limit Reached**\n\n"
                    f"You've reached your Claude AI usage limit for this period.\n\n"
                    f"**When will it reset?**\n"
                    f"Your limit will reset at **{reset_time}**"
                    f"{f' ({timezone})' if timezone else ''}\n\n"
                    f"**What you can do:**\n"
                    f"• Wait for the limit to reset automatically\n"
                    f"• Try again after the reset time\n"
                    f"• Use simpler requests that require less processing\n"
                    f"• Contact support if you need a higher limit"
                )

                raise ClaudeProcessError(user_friendly_msg)

            # Generic error handling for other cases
            raise ClaudeProcessError(
                f"Claude Code exited with code {return_code}: {error_msg}"
            )

        if not result:
            logger.error("No result message received from Claude Code")
            raise ClaudeParsingError("No result message received from Claude Code")

        return self._parse_result(result, list(message_buffer))

    async def _read_stream(self, stream) -> AsyncIterator[str]:
        """Read lines from stream."""
        while True:
            line = await stream.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace").strip()

    async def _read_stream_bounded(self, stream) -> AsyncIterator[str]:
        """Read stream with memory bounds to prevent excessive memory usage."""
        buffer = b""

        while True:
            chunk = await stream.read(self.streaming_buffer_size)
            if not chunk:
                break

            buffer += chunk

            # Process complete lines
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                yield line.decode("utf-8", errors="replace").strip()

        # Process remaining buffer
        if buffer:
            yield buffer.decode("utf-8", errors="replace").strip()

    def _parse_stream_message(self, msg: Dict) -> Optional[StreamUpdate]:
        """Enhanced parsing with comprehensive message type support."""
        msg_type = msg.get("type")

        # Add support for more message types
        if msg_type == "assistant":
            return self._parse_assistant_message(msg)
        elif msg_type == "tool_result":
            return self._parse_tool_result_message(msg)
        elif msg_type == "user":
            return self._parse_user_message(msg)
        elif msg_type == "system":
            return self._parse_system_message(msg)
        elif msg_type == "error":
            return self._parse_error_message(msg)
        elif msg_type == "progress":
            return self._parse_progress_message(msg)

        # Unknown message type - log and continue
        logger.debug("Unknown message type", msg_type=msg_type, msg=msg)
        return None

    def _parse_assistant_message(self, msg: Dict) -> StreamUpdate:
        """Parse assistant message with enhanced context."""
        message = msg.get("message", {})
        content_blocks = message.get("content", [])

        # Get text content
        text_content = []
        tool_calls = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_content.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "name": block.get("name"),
                        "input": block.get("input", {}),
                        "id": block.get("id"),
                    }
                )

        return StreamUpdate(
            type="assistant",
            content="\n".join(text_content) if text_content else None,
            tool_calls=tool_calls if tool_calls else None,
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
            execution_id=msg.get("id"),
        )

    def _parse_tool_result_message(self, msg: Dict) -> StreamUpdate:
        """Parse tool execution results."""
        result = msg.get("result", {})
        content = result.get("content") if isinstance(result, dict) else str(result)

        return StreamUpdate(
            type="tool_result",
            content=content,
            metadata={
                "tool_use_id": msg.get("tool_use_id"),
                "is_error": (
                    result.get("is_error", False) if isinstance(result, dict) else False
                ),
                "execution_time_ms": (
                    result.get("execution_time_ms")
                    if isinstance(result, dict)
                    else None
                ),
            },
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
            error_info={"message": content} if result.get("is_error", False) else None,
        )

    def _parse_user_message(self, msg: Dict) -> StreamUpdate:
        """Parse user message."""
        message = msg.get("message", {})
        content = message.get("content", "")

        # Handle both string and block format content
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "\n".join(text_parts)

        return StreamUpdate(
            type="user",
            content=content if content else None,
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
        )

    def _parse_system_message(self, msg: Dict) -> StreamUpdate:
        """Parse system messages including init and other subtypes."""
        subtype = msg.get("subtype")

        if subtype == "init":
            # Initial system message with available tools
            return StreamUpdate(
                type="system",
                metadata={
                    "subtype": "init",
                    "tools": msg.get("tools", []),
                    "mcp_servers": msg.get("mcp_servers", []),
                    "model": msg.get("model"),
                    "cwd": msg.get("cwd"),
                    "permission_mode": msg.get("permissionMode"),
                },
                session_context={"session_id": msg.get("session_id")},
            )
        else:
            # Other system messages
            return StreamUpdate(
                type="system",
                content=msg.get("message", str(msg)),
                metadata={"subtype": subtype},
                timestamp=msg.get("timestamp"),
                session_context={"session_id": msg.get("session_id")},
            )

    def _parse_error_message(self, msg: Dict) -> StreamUpdate:
        """Parse error messages."""
        error_message = msg.get("message", msg.get("error", str(msg)))

        return StreamUpdate(
            type="error",
            content=error_message,
            error_info={
                "message": error_message,
                "code": msg.get("code"),
                "subtype": msg.get("subtype"),
            },
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
        )

    def _parse_progress_message(self, msg: Dict) -> StreamUpdate:
        """Parse progress update messages."""
        return StreamUpdate(
            type="progress",
            content=msg.get("message", msg.get("status")),
            progress={
                "percentage": msg.get("percentage"),
                "step": msg.get("step"),
                "total_steps": msg.get("total_steps"),
                "operation": msg.get("operation"),
            },
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
        )

    def _validate_message_structure(self, msg: Dict) -> bool:
        """Validate message has required structure."""
        required_fields = ["type"]
        return all(field in msg for field in required_fields)

    def _parse_result(self, result: Dict, messages: List[Dict]) -> ClaudeResponse:
        """Parse final result message."""
        # Extract tools used from messages
        tools_used = []
        for msg in messages:
            if msg.get("type") == "assistant":
                message = msg.get("message", {})
                for block in message.get("content", []):
                    if block.get("type") == "tool_use":
                        tools_used.append(
                            {
                                "name": block.get("name"),
                                "timestamp": msg.get("timestamp"),
                            }
                        )

        return ClaudeResponse(
            content=result.get("result", ""),
            session_id=result.get("session_id", ""),
            cost=result.get("cost_usd", 0.0),
            duration_ms=result.get("duration_ms", 0),
            num_turns=result.get("num_turns", 0),
            is_error=result.get("is_error", False),
            error_type=result.get("subtype") if result.get("is_error") else None,
            tools_used=tools_used,
        )

    async def kill_all_processes(self) -> None:
        """Kill all active processes."""
        logger.info(
            "Killing all active Claude processes", count=len(self.active_processes)
        )

        for process_id, process in self.active_processes.items():
            try:
                process.kill()
                await process.wait()
                logger.info("Killed Claude process", process_id=process_id)
            except Exception as e:
                logger.warning(
                    "Failed to kill process", process_id=process_id, error=str(e)
                )

        self.active_processes.clear()

    def get_active_process_count(self) -> int:
        """Get number of active processes."""
        return len(self.active_processes)

```

### src\claude\monitor.py

**Розмір:** 6,940 байт

```python
"""Monitor Claude's tool usage.

Features:
- Track tool calls
- Security validation
- Usage analytics
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from ..config.settings import Settings
from ..security.validators import SecurityValidator

logger = structlog.get_logger()


class ToolMonitor:
    """Monitor and validate Claude's tool usage."""

    def __init__(
        self, config: Settings, security_validator: Optional[SecurityValidator] = None
    ):
        """Initialize tool monitor."""
        self.config = config
        self.security_validator = security_validator
        self.tool_usage: Dict[str, int] = defaultdict(int)
        self.security_violations: List[Dict[str, Any]] = []

    async def validate_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        working_directory: Path,
        user_id: int,
    ) -> Tuple[bool, Optional[str]]:
        """Validate tool call before execution."""
        logger.debug(
            "Validating tool call",
            tool_name=tool_name,
            working_directory=str(working_directory),
            user_id=user_id,
        )

        # Check if tool is allowed
        if (
            hasattr(self.config, "claude_allowed_tools")
            and self.config.claude_allowed_tools
        ):
            if tool_name not in self.config.claude_allowed_tools:
                violation = {
                    "type": "disallowed_tool",
                    "tool_name": tool_name,
                    "user_id": user_id,
                    "working_directory": str(working_directory),
                }
                self.security_violations.append(violation)
                logger.warning("Tool not allowed", **violation)
                return False, f"Tool not allowed: {tool_name}"

        # Check if tool is explicitly disallowed
        if (
            hasattr(self.config, "claude_disallowed_tools")
            and self.config.claude_disallowed_tools
        ):
            if tool_name in self.config.claude_disallowed_tools:
                violation = {
                    "type": "explicitly_disallowed_tool",
                    "tool_name": tool_name,
                    "user_id": user_id,
                    "working_directory": str(working_directory),
                }
                self.security_violations.append(violation)
                logger.warning("Tool explicitly disallowed", **violation)
                return False, f"Tool explicitly disallowed: {tool_name}"

        # Validate file operations
        if tool_name in [
            "create_file",
            "edit_file",
            "read_file",
            "Write",
            "Edit",
            "Read",
        ]:
            file_path = tool_input.get("path") or tool_input.get("file_path")
            if not file_path:
                return False, "File path required"

            # Validate path security
            if self.security_validator:
                valid, resolved_path, error = self.security_validator.validate_path(
                    file_path, working_directory
                )

                if not valid:
                    violation = {
                        "type": "invalid_file_path",
                        "tool_name": tool_name,
                        "file_path": file_path,
                        "user_id": user_id,
                        "working_directory": str(working_directory),
                        "error": error,
                    }
                    self.security_violations.append(violation)
                    logger.warning("Invalid file path in tool call", **violation)
                    return False, error

        # Validate shell commands
        if tool_name in ["bash", "shell", "Bash"]:
            command = tool_input.get("command", "")

            # Check for dangerous commands
            dangerous_patterns = [
                "rm -rf",
                "sudo",
                "chmod 777",
                "curl",
                "wget",
                "nc ",
                "netcat",
                ">",
                ">>",
                "|",
                "&",
                ";",
                "$(",
                "`",
            ]

            for pattern in dangerous_patterns:
                if pattern in command.lower():
                    violation = {
                        "type": "dangerous_command",
                        "tool_name": tool_name,
                        "command": command,
                        "pattern": pattern,
                        "user_id": user_id,
                        "working_directory": str(working_directory),
                    }
                    self.security_violations.append(violation)
                    logger.warning("Dangerous command detected", **violation)
                    return False, f"Dangerous command pattern detected: {pattern}"

        # Track usage
        self.tool_usage[tool_name] += 1

        logger.debug("Tool call validated successfully", tool_name=tool_name)
        return True, None

    def get_tool_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        return {
            "total_calls": sum(self.tool_usage.values()),
            "by_tool": dict(self.tool_usage),
            "unique_tools": len(self.tool_usage),
            "security_violations": len(self.security_violations),
        }

    def get_security_violations(self) -> List[Dict[str, Any]]:
        """Get security violations."""
        return self.security_violations.copy()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.tool_usage.clear()
        self.security_violations.clear()
        logger.info("Tool monitor statistics reset")

    def get_user_tool_usage(self, user_id: int) -> Dict[str, Any]:
        """Get tool usage for specific user."""
        user_violations = [
            v for v in self.security_violations if v.get("user_id") == user_id
        ]

        return {
            "user_id": user_id,
            "security_violations": len(user_violations),
            "violation_types": list(set(v.get("type") for v in user_violations)),
        }

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if tool is allowed without validation."""
        # Check allowed list
        if (
            hasattr(self.config, "claude_allowed_tools")
            and self.config.claude_allowed_tools
        ):
            if tool_name not in self.config.claude_allowed_tools:
                return False

        # Check disallowed list
        if (
            hasattr(self.config, "claude_disallowed_tools")
            and self.config.claude_disallowed_tools
        ):
            if tool_name in self.config.claude_disallowed_tools:
                return False

        return True

```

### src\claude\parser.py

**Розмір:** 11,186 байт

```python
"""Parse Claude Code output formats.

Features:
- JSON parsing
- Stream parsing
- Error detection
- Tool extraction
"""

import json
import re
from typing import Any, Dict, List

import structlog

from .exceptions import ClaudeParsingError

logger = structlog.get_logger()


class OutputParser:
    """Parse various Claude Code output formats."""

    @staticmethod
    def parse_json_output(output: str) -> Dict[str, Any]:
        """Parse single JSON output."""
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON output", output=output[:200], error=str(e)
            )
            raise ClaudeParsingError(f"Failed to parse JSON output: {e}")

    @staticmethod
    def parse_stream_json(lines: List[str]) -> List[Dict[str, Any]]:
        """Parse streaming JSON output."""
        messages = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSON line", line=line)
                continue

        return messages

    @staticmethod
    def extract_code_blocks(content: str) -> List[Dict[str, str]]:
        """Extract code blocks from response."""
        code_blocks = []
        pattern = r"```(\w+)?\n(.*?)```"

        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2).strip()

            code_blocks.append({"language": language, "code": code})

        logger.debug("Extracted code blocks", count=len(code_blocks))
        return code_blocks

    @staticmethod
    def extract_file_operations(messages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract file operations from tool calls."""
        file_ops = []

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            message = msg.get("message", {})
            for block in message.get("content", []):
                if block.get("type") != "tool_use":
                    continue

                tool_name = block.get("name", "")
                tool_input = block.get("input", {})

                # Check for file-related tools
                if tool_name in [
                    "create_file",
                    "edit_file",
                    "read_file",
                    "Write",
                    "Edit",
                    "Read",
                ]:
                    file_ops.append(
                        {
                            "operation": tool_name,
                            "path": tool_input.get("path")
                            or tool_input.get("file_path"),
                            "content": tool_input.get("content")
                            or tool_input.get("new_string"),
                            "old_content": tool_input.get("old_string"),
                            "timestamp": msg.get("timestamp"),
                        }
                    )

        logger.debug("Extracted file operations", count=len(file_ops))
        return file_ops

    @staticmethod
    def extract_shell_commands(messages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract shell commands from tool calls."""
        shell_commands = []

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            message = msg.get("message", {})
            for block in message.get("content", []):
                if block.get("type") != "tool_use":
                    continue

                tool_name = block.get("name", "")
                tool_input = block.get("input", {})

                # Check for shell/bash tools
                if tool_name in ["bash", "shell", "Bash"]:
                    shell_commands.append(
                        {
                            "operation": tool_name,
                            "command": tool_input.get("command"),
                            "description": tool_input.get("description"),
                            "timestamp": msg.get("timestamp"),
                        }
                    )

        logger.debug("Extracted shell commands", count=len(shell_commands))
        return shell_commands

    @staticmethod
    def extract_response_text(messages: List[Dict]) -> str:
        """Extract all text content from assistant messages."""
        text_parts = []

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            message = msg.get("message", {})
            for block in message.get("content", []):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

        return "\n".join(text_parts)

    @staticmethod
    def extract_tool_results(messages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract tool results from tool_result messages."""
        tool_results = []

        for msg in messages:
            if msg.get("type") == "tool_result":
                result = msg.get("result", {})
                tool_results.append(
                    {
                        "tool_use_id": msg.get("tool_use_id"),
                        "content": result.get("content"),
                        "is_error": result.get("is_error", False),
                        "timestamp": msg.get("timestamp"),
                    }
                )

        logger.debug("Extracted tool results", count=len(tool_results))
        return tool_results

    @staticmethod
    def detect_errors(messages: List[Dict]) -> List[Dict[str, Any]]:
        """Detect errors in message stream."""
        errors = []

        for msg in messages:
            # Check for error messages
            if msg.get("is_error") or msg.get("type") == "error":
                errors.append(
                    {
                        "type": msg.get("type", "unknown"),
                        "subtype": msg.get("subtype"),
                        "message": msg.get("message", str(msg)),
                        "timestamp": msg.get("timestamp"),
                    }
                )

            # Check for tool result errors
            if msg.get("type") == "tool_result":
                result = msg.get("result", {})
                if result.get("is_error"):
                    errors.append(
                        {
                            "type": "tool_error",
                            "tool_use_id": msg.get("tool_use_id"),
                            "message": result.get("content", "Tool execution failed"),
                            "timestamp": msg.get("timestamp"),
                        }
                    )

        logger.debug("Detected errors", count=len(errors))
        return errors

    @staticmethod
    def summarize_session(messages: List[Dict]) -> Dict[str, Any]:
        """Create a summary of the session."""
        summary = {
            "total_messages": len(messages),
            "assistant_messages": 0,
            "user_messages": 0,
            "tool_calls": 0,
            "tool_results": 0,
            "errors": 0,
            "code_blocks": 0,
            "file_operations": 0,
            "shell_commands": 0,
        }

        full_text = ""

        for msg in messages:
            msg_type = msg.get("type")

            if msg_type == "assistant":
                summary["assistant_messages"] += 1

                # Extract text for analysis
                message = msg.get("message", {})
                for block in message.get("content", []):
                    if block.get("type") == "text":
                        full_text += block.get("text", "") + "\n"
                    elif block.get("type") == "tool_use":
                        summary["tool_calls"] += 1

            elif msg_type == "user":
                summary["user_messages"] += 1

            elif msg_type == "tool_result":
                summary["tool_results"] += 1

            elif msg.get("is_error") or msg_type == "error":
                summary["errors"] += 1

        # Analyze extracted content
        summary["code_blocks"] = len(OutputParser.extract_code_blocks(full_text))
        summary["file_operations"] = len(OutputParser.extract_file_operations(messages))
        summary["shell_commands"] = len(OutputParser.extract_shell_commands(messages))

        return summary


class ResponseFormatter:
    """Format Claude responses for Telegram display."""

    def __init__(self, max_message_length: int = 4000):
        """Initialize formatter."""
        self.max_message_length = max_message_length

    def format_response(self, content: str, include_metadata: bool = True) -> List[str]:
        """Format response content into Telegram messages."""
        if not content.strip():
            return ["_(Empty response)_"]

        # Split by code blocks first to preserve them
        parts = self._split_preserving_code_blocks(content)

        messages = []
        for part in parts:
            if len(part) <= self.max_message_length:
                messages.append(part)
            else:
                # Split long parts
                messages.extend(self._split_long_text(part))

        # Ensure we have at least one message
        if not messages:
            messages = ["_(No content to display)_"]

        return messages

    def _split_preserving_code_blocks(self, text: str) -> List[str]:
        """Split text while preserving code blocks."""
        parts = []
        current_part = ""
        in_code_block = False

        lines = text.split("\n")

        for line in lines:
            # Check for code block markers
            if line.strip().startswith("```"):
                in_code_block = not in_code_block

            line_with_newline = line + "\n"

            # If adding this line would exceed limit and we're not in a code block
            if (
                len(current_part + line_with_newline) > self.max_message_length
                and not in_code_block
                and current_part.strip()
            ):
                parts.append(current_part.rstrip())
                current_part = line_with_newline
            else:
                current_part += line_with_newline

        if current_part.strip():
            parts.append(current_part.rstrip())

        return parts

    def _split_long_text(self, text: str) -> List[str]:
        """Split text that's too long for a single message."""
        parts = []
        current = ""

        for char in text:
            if len(current + char) > self.max_message_length:
                if current:
                    parts.append(current)
                    current = char
                else:
                    # Single character somehow exceeds limit
                    parts.append(char)
                    current = ""
            else:
                current += char

        if current:
            parts.append(current)

        return parts

```

### src\claude\sdk_integration.py

**Розмір:** 15,963 байт

```python
"""Claude Code Python SDK integration.

Features:
- Native Claude Code SDK integration
- Async streaming support
- Tool execution management
- Session persistence
"""

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import structlog
from claude_code_sdk import (
    ClaudeCodeOptions,
    ClaudeSDKError,
    CLIConnectionError,
    CLINotFoundError,
    Message,
    ProcessError,
    query,
)
from claude_code_sdk.types import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from ..config.settings import Settings
from .exceptions import (
    ClaudeParsingError,
    ClaudeProcessError,
    ClaudeTimeoutError,
)

logger = structlog.get_logger()


def find_claude_cli(claude_cli_path: Optional[str] = None) -> Optional[str]:
    """Find Claude CLI in common locations."""
    import glob
    import shutil

    # First check if a specific path was provided via config or env
    if claude_cli_path:
        if os.path.exists(claude_cli_path) and os.access(claude_cli_path, os.X_OK):
            return claude_cli_path

    # Check CLAUDE_CLI_PATH environment variable
    env_path = os.environ.get("CLAUDE_CLI_PATH")
    if env_path and os.path.exists(env_path) and os.access(env_path, os.X_OK):
        return env_path

    # Check if claude is already in PATH
    claude_path = shutil.which("claude")
    if claude_path:
        return claude_path

    # Check common installation locations
    common_paths = [
        # NVM installations
        os.path.expanduser("~/.nvm/versions/node/*/bin/claude"),
        # Direct npm global install
        os.path.expanduser("~/.npm-global/bin/claude"),
        os.path.expanduser("~/node_modules/.bin/claude"),
        # System locations
        "/usr/local/bin/claude",
        "/usr/bin/claude",
        # Windows locations (for cross-platform support)
        os.path.expanduser("~/AppData/Roaming/npm/claude.cmd"),
    ]

    for pattern in common_paths:
        matches = glob.glob(pattern)
        if matches:
            # Return the first match
            return matches[0]

    return None


def update_path_for_claude(claude_cli_path: Optional[str] = None) -> bool:
    """Update PATH to include Claude CLI if found."""
    claude_path = find_claude_cli(claude_cli_path)

    if claude_path:
        # Add the directory containing claude to PATH
        claude_dir = os.path.dirname(claude_path)
        current_path = os.environ.get("PATH", "")

        if claude_dir not in current_path:
            os.environ["PATH"] = f"{claude_dir}:{current_path}"
            logger.info("Updated PATH for Claude CLI", claude_path=claude_path)

        return True

    return False


@dataclass
class ClaudeResponse:
    """Response from Claude Code SDK."""

    content: str
    session_id: str
    cost: float
    duration_ms: int
    num_turns: int
    is_error: bool = False
    error_type: Optional[str] = None
    tools_used: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StreamUpdate:
    """Streaming update from Claude SDK."""

    type: str  # 'assistant', 'user', 'system', 'result'
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None


class ClaudeSDKManager:
    """Manage Claude Code SDK integration."""

    def __init__(self, config: Settings):
        """Initialize SDK manager with configuration."""
        self.config = config
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Try to find and update PATH for Claude CLI
        if not update_path_for_claude(config.claude_cli_path):
            logger.warning(
                "Claude CLI not found in PATH or common locations. "
                "SDK may fail if Claude is not installed or not in PATH."
            )

        # Set up environment for Claude Code SDK if API key is provided
        # If no API key is provided, the SDK will use existing CLI authentication
        if config.anthropic_api_key_str:
            os.environ["ANTHROPIC_API_KEY"] = config.anthropic_api_key_str
            logger.info("Using provided API key for Claude SDK authentication")
        else:
            logger.info("No API key provided, using existing Claude CLI authentication")

    async def execute_command(
        self,
        prompt: str,
        working_directory: Path,
        session_id: Optional[str] = None,
        continue_session: bool = False,
        stream_callback: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Execute Claude Code command via SDK."""
        start_time = asyncio.get_event_loop().time()

        logger.info(
            "Starting Claude SDK command",
            working_directory=str(working_directory),
            session_id=session_id,
            continue_session=continue_session,
        )

        try:
            # Build Claude Code options
            options = ClaudeCodeOptions(
                max_turns=self.config.claude_max_turns,
                cwd=str(working_directory),
                allowed_tools=self.config.claude_allowed_tools,
            )

            # Collect messages
            messages = []
            cost = 0.0
            tools_used = []

            # Execute with streaming and timeout
            await asyncio.wait_for(
                self._execute_query_with_streaming(
                    prompt, options, messages, stream_callback
                ),
                timeout=self.config.claude_timeout_seconds,
            )

            # Extract cost and tools from result message
            cost = 0.0
            tools_used = []
            for message in messages:
                if isinstance(message, ResultMessage):
                    cost = getattr(message, "total_cost_usd", 0.0) or 0.0
                    tools_used = self._extract_tools_from_messages(messages)
                    break

            # Calculate duration
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            # Get or create session ID
            final_session_id = session_id or str(uuid.uuid4())

            # Update session
            self._update_session(final_session_id, messages)

            return ClaudeResponse(
                content=self._extract_content_from_messages(messages),
                session_id=final_session_id,
                cost=cost,
                duration_ms=duration_ms,
                num_turns=len(
                    [
                        m
                        for m in messages
                        if isinstance(m, (UserMessage, AssistantMessage))
                    ]
                ),
                tools_used=tools_used,
            )

        except asyncio.TimeoutError:
            logger.error(
                "Claude SDK command timed out",
                timeout_seconds=self.config.claude_timeout_seconds,
            )
            raise ClaudeTimeoutError(
                f"Claude SDK timed out after {self.config.claude_timeout_seconds}s"
            )

        except CLINotFoundError as e:
            logger.error("Claude CLI not found", error=str(e))
            error_msg = (
                "Claude Code not found. Please ensure Claude is installed:\n"
                "  npm install -g @anthropic-ai/claude-code\n\n"
                "If already installed, try one of these:\n"
                "  1. Add Claude to your PATH\n"
                "  2. Create a symlink: ln -s $(which claude) /usr/local/bin/claude\n"
                "  3. Set CLAUDE_CLI_PATH environment variable"
            )
            raise ClaudeProcessError(error_msg)

        except ProcessError as e:
            logger.error(
                "Claude process failed",
                error=str(e),
                exit_code=getattr(e, "exit_code", None),
            )
            raise ClaudeProcessError(f"Claude process error: {str(e)}")

        except CLIConnectionError as e:
            logger.error("Claude connection error", error=str(e))
            raise ClaudeProcessError(f"Failed to connect to Claude: {str(e)}")

        except ClaudeSDKError as e:
            logger.error("Claude SDK error", error=str(e))
            raise ClaudeProcessError(f"Claude SDK error: {str(e)}")

        except Exception as e:
            # Handle ExceptionGroup from TaskGroup operations (Python 3.11+)
            if type(e).__name__ == "ExceptionGroup" or hasattr(e, "exceptions"):
                logger.error(
                    "Task group error in Claude SDK",
                    error=str(e),
                    error_type=type(e).__name__,
                    exception_count=len(getattr(e, "exceptions", [])),
                    exceptions=[
                        str(ex) for ex in getattr(e, "exceptions", [])[:3]
                    ],  # Log first 3 exceptions
                )
                # Extract the most relevant exception from the group
                exceptions = getattr(e, "exceptions", [e])
                main_exception = exceptions[0] if exceptions else e
                raise ClaudeProcessError(
                    f"Claude SDK task error: {str(main_exception)}"
                )

            # Check if it's an ExceptionGroup disguised as a regular exception
            elif hasattr(e, "__notes__") and "TaskGroup" in str(e):
                logger.error(
                    "TaskGroup related error in Claude SDK",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise ClaudeProcessError(f"Claude SDK task error: {str(e)}")

            else:
                logger.error(
                    "Unexpected error in Claude SDK",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise ClaudeProcessError(f"Unexpected error: {str(e)}")

    async def _execute_query_with_streaming(
        self, prompt: str, options, messages: List, stream_callback: Optional[Callable]
    ) -> None:
        """Execute query with streaming and collect messages."""
        try:
            async for message in query(prompt=prompt, options=options):
                messages.append(message)

                # Handle streaming callback
                if stream_callback:
                    try:
                        await self._handle_stream_message(message, stream_callback)
                    except Exception as callback_error:
                        logger.warning(
                            "Stream callback failed",
                            error=str(callback_error),
                            error_type=type(callback_error).__name__,
                        )
                        # Continue processing even if callback fails

        except Exception as e:
            # Handle both ExceptionGroups and regular exceptions
            if type(e).__name__ == "ExceptionGroup" or hasattr(e, "exceptions"):
                logger.error(
                    "TaskGroup error in streaming execution",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            else:
                logger.error(
                    "Error in streaming execution",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            # Re-raise to be handled by the outer try-catch
            raise

    async def _handle_stream_message(
        self, message: Message, stream_callback: Callable[[StreamUpdate], None]
    ) -> None:
        """Handle streaming message from claude-code-sdk."""
        try:
            if isinstance(message, AssistantMessage):
                # Extract content from assistant message
                content = getattr(message, "content", [])
                if content and isinstance(content, list):
                    # Extract text from TextBlock objects
                    text_parts = []
                    for block in content:
                        if hasattr(block, "text"):
                            text_parts.append(block.text)
                    if text_parts:
                        update = StreamUpdate(
                            type="assistant",
                            content="\n".join(text_parts),
                        )
                        await stream_callback(update)
                elif content:
                    # Fallback for non-list content
                    update = StreamUpdate(
                        type="assistant",
                        content=str(content),
                    )
                    await stream_callback(update)

                # Check for tool calls (if available in the message structure)
                # Note: This depends on the actual claude-code-sdk message structure

            elif isinstance(message, UserMessage):
                content = getattr(message, "content", "")
                if content:
                    update = StreamUpdate(
                        type="user",
                        content=content,
                    )
                    await stream_callback(update)

        except Exception as e:
            logger.warning("Stream callback failed", error=str(e))

    def _extract_content_from_messages(self, messages: List[Message]) -> str:
        """Extract content from message list."""
        content_parts = []

        for message in messages:
            if isinstance(message, AssistantMessage):
                content = getattr(message, "content", [])
                if content and isinstance(content, list):
                    # Extract text from TextBlock objects
                    for block in content:
                        if hasattr(block, "text"):
                            content_parts.append(block.text)
                elif content:
                    # Fallback for non-list content
                    content_parts.append(str(content))

        return "\n".join(content_parts)

    def _extract_tools_from_messages(
        self, messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """Extract tools used from message list."""
        tools_used = []
        current_time = asyncio.get_event_loop().time()

        for message in messages:
            if isinstance(message, AssistantMessage):
                content = getattr(message, "content", [])
                if content and isinstance(content, list):
                    for block in content:
                        if isinstance(block, ToolUseBlock):
                            tools_used.append(
                                {
                                    "name": getattr(block, "tool_name", "unknown"),
                                    "timestamp": current_time,
                                    "input": getattr(block, "tool_input", {}),
                                }
                            )

        return tools_used

    def _update_session(self, session_id: str, messages: List[Message]) -> None:
        """Update session data."""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "messages": [],
                "created_at": asyncio.get_event_loop().time(),
            }

        session_data = self.active_sessions[session_id]
        session_data["messages"] = messages
        session_data["last_used"] = asyncio.get_event_loop().time()

    async def kill_all_processes(self) -> None:
        """Kill all active processes (no-op for SDK)."""
        logger.info("Clearing active SDK sessions", count=len(self.active_sessions))
        self.active_sessions.clear()

    def get_active_process_count(self) -> int:
        """Get number of active sessions."""
        return len(self.active_sessions)

```

### src\claude\session.py

**Розмір:** 12,305 байт

```python
"""Claude Code session management.

Features:
- Session state tracking
- Multi-project support
- Session persistence
- Cleanup policies
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import structlog

from ..config.settings import Settings

if TYPE_CHECKING:
    from .integration import ClaudeResponse as CLIClaudeResponse
    from .sdk_integration import ClaudeResponse as SDKClaudeResponse

# Union type for both CLI and SDK responses
ClaudeResponse = Union["CLIClaudeResponse", "SDKClaudeResponse"]

logger = structlog.get_logger()


@dataclass
class ClaudeSession:
    """Claude Code session state."""

    session_id: str
    user_id: int
    project_path: Path
    created_at: datetime
    last_used: datetime
    total_cost: float = 0.0
    total_turns: int = 0
    message_count: int = 0
    tools_used: List[str] = field(default_factory=list)
    is_new_session: bool = False  # True if session hasn't been sent to Claude Code yet

    def is_expired(self, timeout_hours: int) -> bool:
        """Check if session has expired."""
        age = datetime.utcnow() - self.last_used
        return age > timedelta(hours=timeout_hours)

    def update_usage(self, response: ClaudeResponse) -> None:
        """Update session with usage from response."""
        self.last_used = datetime.utcnow()
        self.total_cost += response.cost
        self.total_turns += response.num_turns
        self.message_count += 1

        # Track unique tools
        if response.tools_used:
            for tool in response.tools_used:
                tool_name = tool.get("name")
                if tool_name and tool_name not in self.tools_used:
                    self.tools_used.append(tool_name)

    def to_dict(self) -> Dict:
        """Convert session to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "project_path": str(self.project_path),
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "total_cost": self.total_cost,
            "total_turns": self.total_turns,
            "message_count": self.message_count,
            "tools_used": self.tools_used,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ClaudeSession":
        """Create session from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            project_path=Path(data["project_path"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]),
            total_cost=data.get("total_cost", 0.0),
            total_turns=data.get("total_turns", 0),
            message_count=data.get("message_count", 0),
            tools_used=data.get("tools_used", []),
        )


class SessionStorage:
    """Abstract base class for session storage."""

    async def save_session(self, session: ClaudeSession) -> None:
        """Save session to storage."""
        raise NotImplementedError

    async def load_session(self, session_id: str) -> Optional[ClaudeSession]:
        """Load session from storage."""
        raise NotImplementedError

    async def delete_session(self, session_id: str) -> None:
        """Delete session from storage."""
        raise NotImplementedError

    async def get_user_sessions(self, user_id: int) -> List[ClaudeSession]:
        """Get all sessions for a user."""
        raise NotImplementedError

    async def get_all_sessions(self) -> List[ClaudeSession]:
        """Get all sessions."""
        raise NotImplementedError


class InMemorySessionStorage(SessionStorage):
    """In-memory session storage for development/testing."""

    def __init__(self):
        """Initialize in-memory storage."""
        self.sessions: Dict[str, ClaudeSession] = {}

    async def save_session(self, session: ClaudeSession) -> None:
        """Save session to memory."""
        self.sessions[session.session_id] = session
        logger.debug("Session saved to memory", session_id=session.session_id)

    async def load_session(self, session_id: str) -> Optional[ClaudeSession]:
        """Load session from memory."""
        session = self.sessions.get(session_id)
        if session:
            logger.debug("Session loaded from memory", session_id=session_id)
        return session

    async def delete_session(self, session_id: str) -> None:
        """Delete session from memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug("Session deleted from memory", session_id=session_id)

    async def get_user_sessions(self, user_id: int) -> List[ClaudeSession]:
        """Get all sessions for a user."""
        return [
            session for session in self.sessions.values() if session.user_id == user_id
        ]

    async def get_all_sessions(self) -> List[ClaudeSession]:
        """Get all sessions."""
        return list(self.sessions.values())


class SessionManager:
    """Manage Claude Code sessions."""

    def __init__(self, config: Settings, storage: SessionStorage):
        """Initialize session manager."""
        self.config = config
        self.storage = storage
        self.active_sessions: Dict[str, ClaudeSession] = {}

    async def get_or_create_session(
        self,
        user_id: int,
        project_path: Path,
        session_id: Optional[str] = None,
    ) -> ClaudeSession:
        """Get existing session or create new one."""
        logger.info(
            "Getting or creating session",
            user_id=user_id,
            project_path=str(project_path),
            session_id=session_id,
        )

        # Check for existing session
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if not session.is_expired(self.config.session_timeout_hours):
                logger.debug("Using active session", session_id=session_id)
                return session

        # Try to load from storage
        if session_id:
            session = await self.storage.load_session(session_id)
            if session and not session.is_expired(self.config.session_timeout_hours):
                self.active_sessions[session_id] = session
                logger.info("Loaded session from storage", session_id=session_id)
                return session

        # Check user session limit
        user_sessions = await self._get_user_sessions(user_id)
        if len(user_sessions) >= self.config.max_sessions_per_user:
            # Remove oldest session
            oldest = min(user_sessions, key=lambda s: s.last_used)
            await self.remove_session(oldest.session_id)
            logger.info(
                "Removed oldest session due to limit",
                removed_session_id=oldest.session_id,
                user_id=user_id,
            )

        # Create new session with temporary ID until Claude Code provides real session_id
        temp_session_id = f"temp_{str(uuid.uuid4())}"
        new_session = ClaudeSession(
            session_id=temp_session_id,
            user_id=user_id,
            project_path=project_path,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
        )

        # Mark as new session (not from Claude Code yet)
        new_session.is_new_session = True

        # Save to storage
        await self.storage.save_session(new_session)
        self.active_sessions[new_session.session_id] = new_session

        logger.info(
            "Created new session",
            session_id=new_session.session_id,
            user_id=user_id,
            project_path=str(project_path),
        )

        return new_session

    async def update_session(self, session_id: str, response: ClaudeResponse) -> None:
        """Update session with response data."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            old_session_id = session.session_id

            # For new sessions, update to Claude's actual session ID
            if (
                hasattr(session, "is_new_session")
                and session.is_new_session
                and response.session_id
            ):
                # Remove old temporary session
                del self.active_sessions[old_session_id]
                await self.storage.delete_session(old_session_id)

                # Update session with Claude's session ID
                session.session_id = response.session_id
                session.is_new_session = False

                # Store with new session ID
                self.active_sessions[response.session_id] = session

                logger.info(
                    "Session ID updated from temporary to Claude session ID",
                    old_session_id=old_session_id,
                    new_session_id=response.session_id,
                )
            elif hasattr(session, "is_new_session") and session.is_new_session:
                # Mark as no longer new even if no session_id from Claude
                session.is_new_session = False

            session.update_usage(response)

            # Persist to storage
            await self.storage.save_session(session)

            logger.debug(
                "Session updated",
                session_id=session.session_id,
                total_cost=session.total_cost,
                message_count=session.message_count,
            )

    async def remove_session(self, session_id: str) -> None:
        """Remove session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        await self.storage.delete_session(session_id)
        logger.info("Session removed", session_id=session_id)

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        logger.info("Starting session cleanup")

        all_sessions = await self.storage.get_all_sessions()
        expired_count = 0

        for session in all_sessions:
            if session.is_expired(self.config.session_timeout_hours):
                await self.remove_session(session.session_id)
                expired_count += 1

        logger.info("Session cleanup completed", expired_sessions=expired_count)
        return expired_count

    async def _get_user_sessions(self, user_id: int) -> List[ClaudeSession]:
        """Get all sessions for a user."""
        return await self.storage.get_user_sessions(user_id)

    async def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information."""
        session = self.active_sessions.get(session_id)

        if not session:
            session = await self.storage.load_session(session_id)

        if session:
            return {
                "session_id": session.session_id,
                "project": str(session.project_path),
                "created": session.created_at.isoformat(),
                "last_used": session.last_used.isoformat(),
                "cost": session.total_cost,
                "turns": session.total_turns,
                "messages": session.message_count,
                "tools_used": session.tools_used,
                "expired": session.is_expired(self.config.session_timeout_hours),
            }

        return None

    async def get_user_session_summary(self, user_id: int) -> Dict:
        """Get summary of user's sessions."""
        sessions = await self._get_user_sessions(user_id)

        total_cost = sum(s.total_cost for s in sessions)
        total_messages = sum(s.message_count for s in sessions)
        active_sessions = [
            s for s in sessions if not s.is_expired(self.config.session_timeout_hours)
        ]

        return {
            "user_id": user_id,
            "total_sessions": len(sessions),
            "active_sessions": len(active_sessions),
            "total_cost": total_cost,
            "total_messages": total_messages,
            "projects": list(set(str(s.project_path) for s in sessions)),
        }

```

### src\claude\__init__.py

**Розмір:** 945 байт

```python
"""Claude Code integration module."""

from .exceptions import (
    ClaudeError,
    ClaudeParsingError,
    ClaudeProcessError,
    ClaudeSessionError,
    ClaudeTimeoutError,
)
from .facade import ClaudeIntegration
from .integration import ClaudeProcessManager, ClaudeResponse, StreamUpdate
from .monitor import ToolMonitor
from .parser import OutputParser, ResponseFormatter
from .session import (
    ClaudeSession,
    InMemorySessionStorage,
    SessionManager,
    SessionStorage,
)

__all__ = [
    # Exceptions
    "ClaudeError",
    "ClaudeParsingError",
    "ClaudeProcessError",
    "ClaudeSessionError",
    "ClaudeTimeoutError",
    # Main integration
    "ClaudeIntegration",
    # Core components
    "ClaudeProcessManager",
    "ClaudeResponse",
    "StreamUpdate",
    "SessionManager",
    "SessionStorage",
    "InMemorySessionStorage",
    "ClaudeSession",
    "ToolMonitor",
    "OutputParser",
    "ResponseFormatter",
]

```

### src\config\environments.py

**Розмір:** 2,275 байт

```python
"""Environment-specific configuration overrides."""

from typing import Any, Dict


class DevelopmentConfig:
    """Development environment overrides."""

    debug: bool = True
    development_mode: bool = True
    log_level: str = "DEBUG"
    rate_limit_requests: int = 100  # More lenient for testing
    claude_timeout_seconds: int = 600  # Longer timeout for debugging
    enable_telemetry: bool = False

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Return config as dictionary."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_")
            and not callable(value)
            and not isinstance(value, classmethod)
        }


class TestingConfig:
    """Testing environment configuration."""

    debug: bool = True
    development_mode: bool = True
    database_url: str = "sqlite:///:memory:"
    approved_directory: str = "/tmp/test_projects"
    enable_telemetry: bool = False
    claude_timeout_seconds: int = 30  # Faster timeout for tests
    rate_limit_requests: int = 1000  # No rate limiting in tests
    session_timeout_hours: int = 1  # Short session timeout for testing

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Return config as dictionary."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_")
            and not callable(value)
            and not isinstance(value, classmethod)
        }


class ProductionConfig:
    """Production environment configuration."""

    debug: bool = False
    development_mode: bool = False
    log_level: str = "INFO"
    enable_telemetry: bool = True
    # Use stricter defaults for production
    claude_max_cost_per_user: float = 5.0  # Lower cost limit
    rate_limit_requests: int = 5  # Stricter rate limiting
    session_timeout_hours: int = 12  # Shorter session timeout

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Return config as dictionary."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_")
            and not callable(value)
            and not isinstance(value, classmethod)
        }

```

### src\config\features.py

**Розмір:** 3,408 байт

```python
"""Feature flag management."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .settings import Settings


class FeatureFlags:
    """Feature flag management system."""

    def __init__(self, settings: "Settings"):
        """Initialize with settings."""
        self.settings = settings

    @property
    def mcp_enabled(self) -> bool:
        """Check if Model Context Protocol is enabled."""
        return self.settings.enable_mcp and self.settings.mcp_config_path is not None

    @property
    def git_enabled(self) -> bool:
        """Check if Git integration is enabled."""
        return self.settings.enable_git_integration

    @property
    def file_uploads_enabled(self) -> bool:
        """Check if file uploads are enabled."""
        return self.settings.enable_file_uploads

    @property
    def quick_actions_enabled(self) -> bool:
        """Check if quick action buttons are enabled."""
        return self.settings.enable_quick_actions

    @property
    def telemetry_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self.settings.enable_telemetry

    @property
    def token_auth_enabled(self) -> bool:
        """Check if token-based authentication is enabled."""
        return (
            self.settings.enable_token_auth
            and self.settings.auth_token_secret is not None
        )

    @property
    def webhook_enabled(self) -> bool:
        """Check if webhook mode is enabled."""
        return self.settings.webhook_url is not None

    @property
    def development_features_enabled(self) -> bool:
        """Check if development features are enabled."""
        return self.settings.development_mode

    @property
    def claude_availability_monitor(self) -> bool:
        """Check if Claude CLI availability monitoring is enabled."""
        return self.settings.claude_availability.enabled

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Generic feature check by name."""
        feature_map = {
            "mcp": self.mcp_enabled,
            "git": self.git_enabled,
            "file_uploads": self.file_uploads_enabled,
            "quick_actions": self.quick_actions_enabled,
            "telemetry": self.telemetry_enabled,
            "token_auth": self.token_auth_enabled,
            "webhook": self.webhook_enabled,
            "development": self.development_features_enabled,
            "claude_availability_monitor": self.claude_availability_monitor,
        }
        return feature_map.get(feature_name, False)

    def get_enabled_features(self) -> list[str]:
        """Get list of all enabled features."""
        features = []
        if self.mcp_enabled:
            features.append("mcp")
        if self.git_enabled:
            features.append("git")
        if self.file_uploads_enabled:
            features.append("file_uploads")
        if self.quick_actions_enabled:
            features.append("quick_actions")
        if self.telemetry_enabled:
            features.append("telemetry")
        if self.token_auth_enabled:
            features.append("token_auth")
        if self.webhook_enabled:
            features.append("webhook")
        if self.development_features_enabled:
            features.append("development")
        if self.claude_availability_monitor:
            features.append("claude_availability_monitor")
        return features

```

### src\config\loader.py

**Розмір:** 6,316 байт

```python
"""Configuration loading with environment detection."""

import os
from pathlib import Path
from typing import Any, Optional

import structlog
from dotenv import load_dotenv

from src.exceptions import ConfigurationError, InvalidConfigError

from .environments import DevelopmentConfig, ProductionConfig, TestingConfig
from .settings import Settings

logger = structlog.get_logger()


def load_config(
    env: Optional[str] = None, config_file: Optional[Path] = None
) -> Settings:
    """Load configuration based on environment.

    Args:
        env: Environment name (development, testing, production)
        config_file: Optional path to configuration file

    Returns:
        Configured Settings instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    # Load .env file explicitly
    env_file = config_file or Path(".env")
    if env_file.exists():
        logger.info("Loading .env file", path=str(env_file))
        load_dotenv(env_file)
    else:
        logger.warning("No .env file found", path=str(env_file))

    # Determine environment
    env = env or os.getenv("ENVIRONMENT", "development")
    logger.info("Loading configuration", environment=env)

    try:
        # Debug: Log key environment variables before Settings creation
        logger.debug(
            "Environment variables check",
            telegram_bot_token_set=bool(os.getenv("TELEGRAM_BOT_TOKEN")),
            telegram_bot_username=os.getenv("TELEGRAM_BOT_USERNAME"),
            approved_directory=os.getenv("APPROVED_DIRECTORY"),
            debug_mode=os.getenv("DEBUG"),
        )

        # Load base settings from environment variables
        # pydantic-settings will automatically read from environment variables
        settings = Settings()  # type: ignore[call-arg]

        # Apply environment-specific overrides
        settings = _apply_environment_overrides(settings, env)

        # Validate configuration
        _validate_config(settings)

        logger.info(
            "Configuration loaded successfully",
            environment=env,
            debug=settings.debug,
            approved_directory=str(settings.approved_directory),
            features_enabled=_get_enabled_features_summary(settings),
        )

        return settings

    except Exception as e:
        logger.error("Failed to load configuration", error=str(e), environment=env)
        raise ConfigurationError(f"Configuration loading failed: {e}") from e


def _apply_environment_overrides(settings: Settings, env: Optional[str]) -> Settings:
    """Apply environment-specific configuration overrides."""
    overrides = {}

    if env == "development":
        overrides = DevelopmentConfig.as_dict()
    elif env == "testing":
        overrides = TestingConfig.as_dict()
    elif env == "production":
        overrides = ProductionConfig.as_dict()
    else:
        logger.warning("Unknown environment, using default settings", environment=env)

    # Apply overrides
    for key, value in overrides.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
            logger.debug(
                "Applied environment override", key=key, value=value, environment=env
            )

    return settings


def _validate_config(settings: Settings) -> None:
    """Perform additional runtime validation."""
    # Check file system permissions
    try:
        if not os.access(settings.approved_directory, os.R_OK | os.X_OK):
            raise InvalidConfigError(
                f"Cannot access approved directory: {settings.approved_directory}"
            )
    except OSError as e:
        raise InvalidConfigError(f"Error accessing approved directory: {e}") from e

    # Validate feature dependencies
    if settings.enable_mcp and not settings.mcp_config_path:
        raise InvalidConfigError("MCP enabled but no config path provided")

    if settings.enable_token_auth and not settings.auth_token_secret:
        raise InvalidConfigError("Token auth enabled but no secret provided")

    # Validate database path for SQLite
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_path
        if db_path:
            # Ensure parent directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate rate limiting settings
    if settings.rate_limit_requests <= 0:
        raise InvalidConfigError("rate_limit_requests must be positive")

    if settings.rate_limit_window <= 0:
        raise InvalidConfigError("rate_limit_window must be positive")

    if settings.claude_timeout_seconds <= 0:
        raise InvalidConfigError("claude_timeout_seconds must be positive")

    # Validate cost limits
    if settings.claude_max_cost_per_user <= 0:
        raise InvalidConfigError("claude_max_cost_per_user must be positive")


def _get_enabled_features_summary(settings: Settings) -> list[str]:
    """Get a summary of enabled features for logging."""
    features = []
    if settings.enable_mcp:
        features.append("mcp")
    if settings.enable_git_integration:
        features.append("git")
    if settings.enable_file_uploads:
        features.append("file_uploads")
    if settings.enable_quick_actions:
        features.append("quick_actions")
    if settings.enable_token_auth:
        features.append("token_auth")
    if settings.webhook_url:
        features.append("webhook")
    return features


def create_test_config(**overrides: Any) -> Settings:
    """Create configuration for testing with optional overrides.

    Args:
        **overrides: Configuration values to override

    Returns:
        Settings instance configured for testing
    """
    # Start with testing defaults
    test_values = TestingConfig.as_dict()

    # Add required fields for testing
    test_values.update(
        {
            "telegram_bot_token": "test_token_123",
            "telegram_bot_username": "test_bot",
            "approved_directory": "/tmp/test_projects",
        }
    )

    # Apply any overrides
    test_values.update(overrides)

    # Ensure test directory exists
    test_dir = Path(test_values["approved_directory"])
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create settings with test values
    settings = Settings(**test_values)

    return settings

```

### src\config\settings.py

**Розмір:** 9,711 байт

```python
"""Configuration management using Pydantic Settings.

Features:
- Environment variable loading
- Type validation
- Default values
- Computed properties
- Environment-specific settings
"""

from datetime import time
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.constants import (
    DEFAULT_CLAUDE_MAX_COST_PER_USER,
    DEFAULT_CLAUDE_MAX_TURNS,
    DEFAULT_CLAUDE_TIMEOUT_SECONDS,
    DEFAULT_DATABASE_URL,
    DEFAULT_MAX_SESSIONS_PER_USER,
    DEFAULT_RATE_LIMIT_BURST,
    DEFAULT_RATE_LIMIT_REQUESTS,
    DEFAULT_RATE_LIMIT_WINDOW,
    DEFAULT_SESSION_TIMEOUT_HOURS,
)


class ClaudeAvailabilitySettings(BaseModel):
    """Settings for Claude CLI availability monitoring."""
    
    enabled: bool = Field(default=False, description="Whether Claude CLI availability monitoring is enabled")
    check_interval_seconds: int = Field(default=60, description="Check interval in seconds")
    notify_chat_ids: List[int] = Field(default_factory=list, description="Chat IDs to notify")
    dnd_start: time = Field(default=time(23, 0), description="DND start time (Europe/Kyiv)")
    dnd_end: time = Field(default=time(8, 0), description="DND end time (Europe/Kyiv)")
    debounce_ok_count: int = Field(default=2, description="Number of consecutive OK checks to confirm availability")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Bot settings
    telegram_bot_token: SecretStr = Field(
        ..., description="Telegram bot token from BotFather"
    )
    telegram_bot_username: str = Field(..., description="Bot username without @")

    # Security
    approved_directory: Path = Field(..., description="Base directory for projects")
    allowed_users: Optional[List[int]] = Field(
        None, description="Allowed Telegram user IDs"
    )
    enable_token_auth: bool = Field(
        False, description="Enable token-based authentication"
    )
    auth_token_secret: Optional[SecretStr] = Field(
        None, description="Secret for auth tokens"
    )

    # Claude settings
    claude_binary_path: Optional[str] = Field(
        None, description="Path to Claude CLI binary (deprecated)"
    )
    claude_cli_path: Optional[str] = Field(
        None, description="Path to Claude CLI executable"
    )
    anthropic_api_key: Optional[SecretStr] = Field(
        None,
        description="Anthropic API key for Claude SDK (optional if logged into Claude CLI)",
    )
    claude_model: str = Field(
        "claude-3-5-sonnet-20241022", description="Claude model to use"
    )
    claude_max_turns: int = Field(
        DEFAULT_CLAUDE_MAX_TURNS, description="Max conversation turns"
    )
    claude_timeout_seconds: int = Field(
        DEFAULT_CLAUDE_TIMEOUT_SECONDS, description="Claude timeout"
    )
    claude_max_cost_per_user: float = Field(
        DEFAULT_CLAUDE_MAX_COST_PER_USER, description="Max cost per user"
    )
    use_sdk: bool = Field(True, description="Use Python SDK instead of CLI subprocess")
    claude_allowed_tools: Optional[List[str]] = Field(
        default=[
            "Read",
            "Write",
            "Edit",
            "Bash",
            "Glob",
            "Grep",
            "LS",
            "Task",
            "MultiEdit",
            "NotebookRead",
            "NotebookEdit",
            "WebFetch",
            "TodoRead",
            "TodoWrite",
            "WebSearch",
        ],
        description="List of allowed Claude tools",
    )
    claude_disallowed_tools: Optional[List[str]] = Field(
        default=["git commit", "git push"],
        description="List of explicitly disallowed Claude tools/commands",
    )

    # Rate limiting
    rate_limit_requests: int = Field(
        DEFAULT_RATE_LIMIT_REQUESTS, description="Requests per window"
    )
    rate_limit_window: int = Field(
        DEFAULT_RATE_LIMIT_WINDOW, description="Rate limit window seconds"
    )
    rate_limit_burst: int = Field(
        DEFAULT_RATE_LIMIT_BURST, description="Burst capacity"
    )

    # Storage
    database_url: str = Field(
        DEFAULT_DATABASE_URL, description="Database connection URL"
    )
    session_timeout_hours: int = Field(
        DEFAULT_SESSION_TIMEOUT_HOURS, description="Session timeout"
    )
    session_timeout_minutes: int = Field(
        default=120,
        description="Session timeout in minutes",
        ge=10,
        le=1440,  # Max 24 hours
    )
    max_sessions_per_user: int = Field(
        DEFAULT_MAX_SESSIONS_PER_USER, description="Max concurrent sessions"
    )

    # Features
    enable_mcp: bool = Field(False, description="Enable Model Context Protocol")
    mcp_config_path: Optional[Path] = Field(
        None, description="MCP configuration file path"
    )
    enable_git_integration: bool = Field(True, description="Enable git commands")
    enable_file_uploads: bool = Field(True, description="Enable file upload handling")
    enable_quick_actions: bool = Field(True, description="Enable quick action buttons")
    claude_availability: ClaudeAvailabilitySettings = Field(default_factory=ClaudeAvailabilitySettings)

    # Monitoring
    log_level: str = Field("INFO", description="Logging level")
    enable_telemetry: bool = Field(False, description="Enable anonymous telemetry")
    sentry_dsn: Optional[str] = Field(None, description="Sentry DSN for error tracking")

    # Development
    debug: bool = Field(False, description="Enable debug mode")
    development_mode: bool = Field(False, description="Enable development features")

    # Webhook settings (optional)
    webhook_url: Optional[str] = Field(None, description="Webhook URL for bot")
    webhook_port: int = Field(8443, description="Webhook port")
    webhook_path: str = Field("/webhook", description="Webhook path")
    
    # ✅ New field: path to target project
    target_project_path: Path = Field(
        default=Path("/app/target_project"),
        description="Path to target project for Claude CLI operations"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @field_validator("allowed_users", mode="before")
    @classmethod
    def parse_allowed_users(cls, v: Any) -> Optional[List[int]]:
        """Parse comma-separated user IDs."""
        if isinstance(v, str):
            return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
        return v  # type: ignore[no-any-return]

    @field_validator("approved_directory")
    @classmethod
    def validate_approved_directory(cls, v: Any) -> Path:
        """Ensure approved directory exists and is absolute."""
        if isinstance(v, str):
            v = Path(v)

        path = v.resolve()
        if not path.exists():
            raise ValueError(f"Approved directory does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Approved directory is not a directory: {path}")
        return path  # type: ignore[no-any-return]

    @field_validator("mcp_config_path", mode="before")
    @classmethod
    def validate_mcp_config(cls, v: Any, info: Any) -> Optional[Path]:
        """Validate MCP configuration path if MCP is enabled."""
        # Note: In Pydantic v2, we'll need to check enable_mcp after model creation
        if v and isinstance(v, str):
            v = Path(v)
        if v and not v.exists():
            raise ValueError(f"MCP config file does not exist: {v}")
        return v  # type: ignore[no-any-return]

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: Any) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()  # type: ignore[no-any-return]

    @model_validator(mode="after")
    def validate_cross_field_dependencies(self) -> "Settings":
        """Validate dependencies between fields."""
        # Check auth token requirements
        if self.enable_token_auth and not self.auth_token_secret:
            raise ValueError(
                "auth_token_secret required when enable_token_auth is True"
            )

        # Check MCP requirements
        if self.enable_mcp and not self.mcp_config_path:
            raise ValueError("mcp_config_path required when enable_mcp is True")

        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not (self.debug or self.development_mode)

    @property
    def database_path(self) -> Optional[Path]:
        """Extract path from SQLite database URL."""
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.replace("sqlite:///", "")
            return Path(db_path).resolve()
        return None

    @property
    def telegram_token_str(self) -> str:
        """Get Telegram token as string."""
        return self.telegram_bot_token.get_secret_value()

    @property
    def auth_secret_str(self) -> Optional[str]:
        """Get auth token secret as string."""
        if self.auth_token_secret:
            return self.auth_token_secret.get_secret_value()
        return None

    @property
    def anthropic_api_key_str(self) -> Optional[str]:
        """Get Anthropic API key as string."""
        return (
            self.anthropic_api_key.get_secret_value()
            if self.anthropic_api_key
            else None
        )

```

### src\config\__init__.py

**Розмір:** 390 байт

```python
"""Configuration module."""

from .environments import DevelopmentConfig, ProductionConfig, TestingConfig
from .features import FeatureFlags
from .loader import create_test_config, load_config
from .settings import Settings

__all__ = [
    "Settings",
    "load_config",
    "create_test_config",
    "DevelopmentConfig",
    "ProductionConfig",
    "TestingConfig",
    "FeatureFlags",
]

```

### src\security\audit.py

**Розмір:** 14,504 байт

```python
"""Security audit logging.

Features:
- All authentication attempts
- Command execution
- File access
- Security violations
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

# from src.exceptions import SecurityError  # Future use

logger = structlog.get_logger()


@dataclass
class AuditEvent:
    """Security audit event."""

    timestamp: datetime
    user_id: int
    event_type: str
    success: bool
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/logging."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditStorage:
    """Abstract interface for audit event storage."""

    async def store_event(self, event: AuditEvent) -> None:
        """Store audit event."""
        raise NotImplementedError

    async def get_events(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Retrieve audit events with filters."""
        raise NotImplementedError

    async def get_security_violations(
        self, user_id: Optional[int] = None, limit: int = 100
    ) -> List[AuditEvent]:
        """Get security violations."""
        raise NotImplementedError


class InMemoryAuditStorage(AuditStorage):
    """In-memory audit storage for development/testing."""

    def __init__(self, max_events: int = 10000):
        self.events: List[AuditEvent] = []
        self.max_events = max_events

    async def store_event(self, event: AuditEvent) -> None:
        """Store event in memory."""
        self.events.append(event)

        # Trim old events if we exceed limit
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

        # Log high-risk events immediately
        if event.risk_level in ["high", "critical"]:
            logger.warning(
                "High-risk security event",
                event_type=event.event_type,
                user_id=event.user_id,
                risk_level=event.risk_level,
                details=event.details,
            )

    async def get_events(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Get filtered events."""
        filtered_events = self.events

        # Apply filters
        if user_id is not None:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]

        if event_type is not None:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        if start_time is not None:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time is not None:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        # Sort by timestamp (newest first) and limit
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)
        return filtered_events[:limit]

    async def get_security_violations(
        self, user_id: Optional[int] = None, limit: int = 100
    ) -> List[AuditEvent]:
        """Get security violations."""
        return await self.get_events(
            user_id=user_id, event_type="security_violation", limit=limit
        )


class AuditLogger:
    """Security audit logger."""

    def __init__(self, storage: AuditStorage):
        self.storage = storage
        logger.info("Audit logger initialized")

    async def log_auth_attempt(
        self,
        user_id: int,
        success: bool,
        method: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log authentication attempt."""
        risk_level = "medium" if not success else "low"

        event = AuditEvent(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            event_type="auth_attempt",
            success=success,
            details={"method": method, "reason": reason},
            ip_address=ip_address,
            risk_level=risk_level,
        )

        await self.storage.store_event(event)

        logger.info(
            "Authentication attempt logged",
            user_id=user_id,
            method=method,
            success=success,
            reason=reason,
        )

    async def log_session_event(
        self,
        user_id: int,
        action: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log session-related events."""
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            event_type="session",
            success=success,
            details={"action": action, **(details or {})},
            risk_level="low",
        )

        await self.storage.store_event(event)

    async def log_command(
        self,
        user_id: int,
        command: str,
        args: List[str],
        success: bool,
        working_directory: Optional[str] = None,
        execution_time: Optional[float] = None,
        exit_code: Optional[int] = None,
    ) -> None:
        """Log command execution."""
        # Determine risk level based on command
        risk_level = self._assess_command_risk(command, args)

        event = AuditEvent(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            event_type="command",
            success=success,
            details={
                "command": command,
                "args": args[:10],  # Limit args for storage
                "working_directory": working_directory,
                "execution_time": execution_time,
                "exit_code": exit_code,
            },
            risk_level=risk_level,
        )

        await self.storage.store_event(event)

        logger.info(
            "Command execution logged",
            user_id=user_id,
            command=command,
            success=success,
            risk_level=risk_level,
        )

    async def log_file_access(
        self,
        user_id: int,
        file_path: str,
        action: str,  # read, write, delete, create
        success: bool,
        file_size: Optional[int] = None,
    ) -> None:
        """Log file access."""
        # Assess risk based on file path and action
        risk_level = self._assess_file_access_risk(file_path, action)

        event = AuditEvent(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            event_type="file_access",
            success=success,
            details={"file_path": file_path, "action": action, "file_size": file_size},
            risk_level=risk_level,
        )

        await self.storage.store_event(event)

    async def log_security_violation(
        self,
        user_id: int,
        violation_type: str,
        details: str,
        severity: str = "medium",
        attempted_action: Optional[str] = None,
    ) -> None:
        """Log security violation."""
        # Map severity to risk level
        risk_mapping = {"low": "medium", "medium": "high", "high": "critical"}
        risk_level = risk_mapping.get(severity, "high")

        event = AuditEvent(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            event_type="security_violation",
            success=False,  # Security violations are always failures
            details={
                "violation_type": violation_type,
                "details": details,
                "severity": severity,
                "attempted_action": attempted_action,
            },
            risk_level=risk_level,
        )

        await self.storage.store_event(event)

        logger.warning(
            "Security violation logged",
            user_id=user_id,
            violation_type=violation_type,
            severity=severity,
            details=details,
        )

    async def log_rate_limit_exceeded(
        self,
        user_id: int,
        limit_type: str,  # request, cost
        current_usage: float,
        limit_value: float,
    ) -> None:
        """Log rate limit exceeded."""
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            event_type="rate_limit_exceeded",
            success=False,
            details={
                "limit_type": limit_type,
                "current_usage": current_usage,
                "limit_value": limit_value,
                "utilization": current_usage / limit_value if limit_value > 0 else 0,
            },
            risk_level="low",
        )

        await self.storage.store_event(event)

    def _assess_command_risk(self, command: str, args: List[str]) -> str:
        """Assess risk level of command execution."""
        high_risk_commands = {
            "rm",
            "del",
            "delete",
            "format",
            "fdisk",
            "dd",
            "chmod",
            "chown",
            "sudo",
            "su",
            "passwd",
            "curl",
            "wget",
            "ssh",
            "scp",
            "rsync",
        }

        medium_risk_commands = {
            "git",
            "npm",
            "pip",
            "docker",
            "kubectl",
            "make",
            "cmake",
            "gcc",
            "python",
            "node",
        }

        command_lower = command.lower()

        if any(risky in command_lower for risky in high_risk_commands):
            return "high"
        elif any(risky in command_lower for risky in medium_risk_commands):
            return "medium"
        else:
            return "low"

    def _assess_file_access_risk(self, file_path: str, action: str) -> str:
        """Assess risk level of file access."""
        sensitive_paths = [
            "/etc/",
            "/var/",
            "/usr/",
            "/sys/",
            "/proc/",
            "/.env",
            "/.ssh/",
            "/.aws/",
            "/secrets/",
            "config",
            "password",
            "key",
            "token",
        ]

        risky_actions = {"delete", "write"}

        path_lower = file_path.lower()

        # High risk: sensitive paths with write/delete
        if action in risky_actions and any(
            sensitive in path_lower for sensitive in sensitive_paths
        ):
            return "high"

        # Medium risk: any sensitive path access or risky actions
        if (
            any(sensitive in path_lower for sensitive in sensitive_paths)
            or action in risky_actions
        ):
            return "medium"

        return "low"

    async def get_user_activity_summary(
        self, user_id: int, hours: int = 24
    ) -> Dict[str, Any]:
        """Get activity summary for user."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        events = await self.storage.get_events(
            user_id=user_id, start_time=start_time, limit=1000
        )

        # Aggregate statistics
        summary: Dict[str, Any] = {
            "user_id": user_id,
            "period_hours": hours,
            "total_events": len(events),
            "event_types": {},
            "risk_levels": {},
            "success_rate": 0,
            "security_violations": 0,
            "last_activity": None,
        }

        if events:
            summary["last_activity"] = events[0].timestamp.isoformat()

            successful_events = 0
            for event in events:
                # Count by type
                event_type = event.event_type
                summary["event_types"][event_type] = (
                    summary["event_types"].get(event_type, 0) + 1
                )

                # Count by risk level
                risk_level = event.risk_level
                summary["risk_levels"][risk_level] = (
                    summary["risk_levels"].get(risk_level, 0) + 1
                )

                # Count successes
                if event.success:
                    successful_events += 1

                # Count security violations
                if event.event_type == "security_violation":
                    summary["security_violations"] += 1

            summary["success_rate"] = successful_events / len(events)

        return summary

    async def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data."""
        # Get recent events (last 24 hours)
        start_time = datetime.utcnow() - timedelta(hours=24)
        recent_events = await self.storage.get_events(start_time=start_time, limit=1000)

        # Get security violations
        violations = await self.storage.get_security_violations(limit=100)

        dashboard: Dict[str, Any] = {
            "period": "24_hours",
            "total_events": len(recent_events),
            "security_violations": len(violations),
            "active_users": len(set(e.user_id for e in recent_events)),
            "risk_distribution": {},
            "top_violation_types": {},
            "authentication_failures": 0,
        }

        # Analyze events
        for event in recent_events:
            # Risk distribution
            risk = event.risk_level
            dashboard["risk_distribution"][risk] = (
                dashboard["risk_distribution"].get(risk, 0) + 1
            )

            # Authentication failures
            if event.event_type == "auth_attempt" and not event.success:
                dashboard["authentication_failures"] += 1

        # Analyze violations
        for violation in violations:
            violation_type = violation.details.get("violation_type", "unknown")
            dashboard["top_violation_types"][violation_type] = (
                dashboard["top_violation_types"].get(violation_type, 0) + 1
            )

        return dashboard

```

### src\security\auth.py

**Розмір:** 11,347 байт

```python
"""Authentication system supporting multiple methods.

Features:
- Telegram ID whitelist
- Token-based authentication
- Session management
- Audit logging
"""

import hashlib
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from src.exceptions import SecurityError

# from src.exceptions import AuthenticationError  # Future use

logger = structlog.get_logger()


@dataclass
class UserSession:
    """User session data."""

    user_id: int
    auth_provider: str
    created_at: datetime
    last_activity: datetime
    user_info: Optional[Dict[str, Any]] = None
    session_timeout: timedelta = timedelta(hours=24)

    def __post_init__(self) -> None:
        if self.last_activity is None:
            self.last_activity = self.created_at

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() - self.last_activity > self.session_timeout

    def refresh(self) -> None:
        """Refresh session activity."""
        self.last_activity = datetime.utcnow()


class AuthProvider(ABC):
    """Base authentication provider."""

    @abstractmethod
    async def authenticate(self, user_id: int, credentials: Dict[str, Any]) -> bool:
        """Verify user credentials."""
        pass

    @abstractmethod
    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information."""
        pass


class WhitelistAuthProvider(AuthProvider):
    """Whitelist-based authentication."""

    def __init__(self, allowed_users: List[int], allow_all_dev: bool = False):
        self.allowed_users = set(allowed_users)
        self.allow_all_dev = allow_all_dev
        logger.info(
            "Whitelist auth provider initialized",
            allowed_users=len(self.allowed_users),
            allow_all_dev=allow_all_dev,
        )

    async def authenticate(self, user_id: int, credentials: Dict[str, Any]) -> bool:
        """Authenticate user against whitelist."""
        is_allowed = self.allow_all_dev or user_id in self.allowed_users
        logger.info(
            "Whitelist authentication attempt", user_id=user_id, success=is_allowed
        )
        return is_allowed

    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information if whitelisted."""
        if self.allow_all_dev or user_id in self.allowed_users:
            return {
                "user_id": user_id,
                "auth_type": "whitelist" + ("_dev" if self.allow_all_dev else ""),
                "permissions": ["basic"],
            }
        return None


class TokenStorage(ABC):
    """Abstract token storage interface."""

    @abstractmethod
    async def store_token(
        self, user_id: int, token_hash: str, expires_at: datetime
    ) -> None:
        """Store token hash for user."""
        pass

    @abstractmethod
    async def get_user_token(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get token data for user."""
        pass

    @abstractmethod
    async def revoke_token(self, user_id: int) -> None:
        """Revoke token for user."""
        pass


class InMemoryTokenStorage(TokenStorage):
    """In-memory token storage for development/testing."""

    def __init__(self) -> None:
        self._tokens: Dict[int, Dict[str, Any]] = {}

    async def store_token(
        self, user_id: int, token_hash: str, expires_at: datetime
    ) -> None:
        """Store token hash in memory."""
        self._tokens[user_id] = {
            "hash": token_hash,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
        }

    async def get_user_token(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get token data from memory."""
        token_data = self._tokens.get(user_id)
        if token_data and token_data["expires_at"] > datetime.utcnow():
            return token_data
        elif token_data:
            # Token expired, remove it
            del self._tokens[user_id]
        return None

    async def revoke_token(self, user_id: int) -> None:
        """Remove token from memory."""
        self._tokens.pop(user_id, None)


class TokenAuthProvider(AuthProvider):
    """Token-based authentication."""

    def __init__(
        self,
        secret: str,
        storage: TokenStorage,
        token_lifetime: timedelta = timedelta(days=30),
    ):
        self.secret = secret
        self.storage = storage
        self.token_lifetime = token_lifetime
        logger.info("Token auth provider initialized")

    async def authenticate(self, user_id: int, credentials: Dict[str, Any]) -> bool:
        """Authenticate using token."""
        token = credentials.get("token")
        if not token:
            logger.warning(
                "Token authentication failed: no token provided", user_id=user_id
            )
            return False

        stored_token = await self.storage.get_user_token(user_id)
        if not stored_token:
            logger.warning(
                "Token authentication failed: no stored token", user_id=user_id
            )
            return False

        is_valid = self._verify_token(token, stored_token["hash"])
        logger.info("Token authentication attempt", user_id=user_id, success=is_valid)
        return is_valid

    async def generate_token(self, user_id: int) -> str:
        """Generate new authentication token."""
        token = secrets.token_urlsafe(32)
        hashed = self._hash_token(token)
        expires_at = datetime.utcnow() + self.token_lifetime

        await self.storage.store_token(user_id, hashed, expires_at)

        logger.info(
            "Token generated", user_id=user_id, expires_at=expires_at.isoformat()
        )
        return token

    async def revoke_token(self, user_id: int) -> None:
        """Revoke user's token."""
        await self.storage.revoke_token(user_id)
        logger.info("Token revoked", user_id=user_id)

    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information if token is valid."""
        token_data = await self.storage.get_user_token(user_id)
        if token_data:
            return {
                "user_id": user_id,
                "auth_type": "token",
                "permissions": ["basic", "advanced"],
                "token_created": token_data["created_at"].isoformat(),
                "token_expires": token_data["expires_at"].isoformat(),
            }
        return None

    def _hash_token(self, token: str) -> str:
        """Hash token for secure storage."""
        return hashlib.sha256(f"{token}{self.secret}".encode()).hexdigest()

    def _verify_token(self, token: str, stored_hash: str) -> bool:
        """Verify token against stored hash."""
        return self._hash_token(token) == stored_hash


class AuthenticationManager:
    """Main authentication manager supporting multiple providers."""

    def __init__(self, providers: List[AuthProvider]):
        if not providers:
            raise SecurityError("At least one authentication provider is required")

        self.providers = providers
        self.sessions: Dict[int, UserSession] = {}
        logger.info("Authentication manager initialized", providers=len(self.providers))

    async def authenticate_user(
        self, user_id: int, credentials: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Try authentication with all providers."""
        credentials = credentials or {}

        # Clean expired sessions first
        self._cleanup_expired_sessions()

        # Try each provider
        for provider in self.providers:
            try:
                if await provider.authenticate(user_id, credentials):
                    await self._create_session(user_id, provider)
                    logger.info(
                        "User authenticated successfully",
                        user_id=user_id,
                        provider=provider.__class__.__name__,
                    )
                    return True
            except Exception as e:
                logger.error(
                    "Authentication provider error",
                    user_id=user_id,
                    provider=provider.__class__.__name__,
                    error=str(e),
                )

        logger.warning("Authentication failed for user", user_id=user_id)
        return False

    async def _create_session(self, user_id: int, provider: AuthProvider) -> None:
        """Create authenticated session."""
        user_info = await provider.get_user_info(user_id)
        self.sessions[user_id] = UserSession(
            user_id=user_id,
            auth_provider=provider.__class__.__name__,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            user_info=user_info,
        )

        logger.info(
            "Session created", user_id=user_id, provider=provider.__class__.__name__
        )

    def is_authenticated(self, user_id: int) -> bool:
        """Check if user has active session."""
        session = self.sessions.get(user_id)
        if session and not session.is_expired():
            return True
        elif session:
            # Remove expired session
            del self.sessions[user_id]
            logger.info("Expired session removed", user_id=user_id)
        return False

    def get_session(self, user_id: int) -> Optional[UserSession]:
        """Get user session if valid."""
        if self.is_authenticated(user_id):
            return self.sessions[user_id]
        return None

    def refresh_session(self, user_id: int) -> bool:
        """Refresh user session activity."""
        session = self.get_session(user_id)
        if session:
            session.refresh()
            return True
        return False

    def end_session(self, user_id: int) -> None:
        """End user session."""
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info("Session ended", user_id=user_id)

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        expired_sessions = [
            user_id
            for user_id, session in self.sessions.items()
            if session.is_expired()
        ]

        for user_id in expired_sessions:
            del self.sessions[user_id]

        if expired_sessions:
            logger.info("Expired sessions cleaned up", count=len(expired_sessions))

    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        self._cleanup_expired_sessions()
        return len(self.sessions)

    def get_session_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get session information for user."""
        session = self.get_session(user_id)
        if session:
            return {
                "user_id": session.user_id,
                "auth_provider": session.auth_provider,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "is_expired": session.is_expired(),
                "user_info": session.user_info,
            }
        return None

```

### src\security\rate_limiter.py

**Розмір:** 10,493 байт

```python
"""Rate limiting implementation with multiple strategies.

Features:
- Token bucket algorithm
- Cost-based limiting
- Per-user tracking
- Burst handling
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import structlog

from ..config.settings import Settings

logger = structlog.get_logger()


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""

    capacity: int
    tokens: float
    last_update: datetime
    refill_rate: float = 1.0  # tokens per second

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on time passed."""
        now = datetime.utcnow()
        elapsed = (now - self.last_update).total_seconds()
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
        self.last_update = now

    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait before tokens are available."""
        self._refill()
        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate

    def get_status(self) -> Dict[str, float]:
        """Get current bucket status."""
        self._refill()
        return {
            "capacity": self.capacity,
            "tokens": self.tokens,
            "utilization": (self.capacity - self.tokens) / self.capacity,
            "refill_rate": self.refill_rate,
        }


class RateLimiter:
    """Main rate limiting system with request and cost-based limits."""

    def __init__(self, config: Settings):
        self.config = config
        self.request_buckets: Dict[int, RateLimitBucket] = {}
        self.cost_tracker: Dict[int, float] = defaultdict(float)
        self.cost_reset_time: Dict[int, datetime] = {}
        self.locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Calculate refill rate from config
        self.refill_rate = (
            self.config.rate_limit_requests / self.config.rate_limit_window
        )

        logger.info(
            "Rate limiter initialized",
            requests_per_window=self.config.rate_limit_requests,
            window_seconds=self.config.rate_limit_window,
            burst_capacity=self.config.rate_limit_burst,
            max_cost_per_user=self.config.claude_max_cost_per_user,
            refill_rate=self.refill_rate,
        )

    async def check_rate_limit(
        self, user_id: int, cost: float = 1.0, tokens: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """Check if request is allowed under rate limits."""
        async with self.locks[user_id]:
            # Check request rate limit
            rate_allowed, rate_message = self._check_request_rate(user_id, tokens)
            if not rate_allowed:
                logger.warning(
                    "Request rate limit exceeded",
                    user_id=user_id,
                    tokens_requested=tokens,
                )
                return False, rate_message

            # Check cost limit
            cost_allowed, cost_message = self._check_cost_limit(user_id, cost)
            if not cost_allowed:
                logger.warning(
                    "Cost limit exceeded",
                    user_id=user_id,
                    cost_requested=cost,
                    current_usage=self.cost_tracker[user_id],
                )
                return False, cost_message

            # If both checks pass, consume resources
            self._consume_request_tokens(user_id, tokens)
            self._track_cost(user_id, cost)

            logger.debug(
                "Rate limit check passed", user_id=user_id, cost=cost, tokens=tokens
            )
            return True, None

    def _check_request_rate(
        self, user_id: int, tokens: int
    ) -> Tuple[bool, Optional[str]]:
        """Check request rate limit."""
        bucket = self._get_or_create_bucket(user_id)

        if bucket.consume(tokens):
            return True, None

        wait_time = bucket.get_wait_time(tokens)
        status = bucket.get_status()

        message = (
            f"Rate limit exceeded. Please wait {wait_time:.1f} seconds "
            f"before making more requests. "
            f"Bucket: {status['tokens']:.1f}/{status['capacity']} tokens available."
        )
        return False, message

    def _check_cost_limit(
        self, user_id: int, cost: float
    ) -> Tuple[bool, Optional[str]]:
        """Check cost-based limit."""
        # Reset cost tracker if enough time has passed
        self._maybe_reset_cost_tracker(user_id)

        current_cost = self.cost_tracker[user_id]
        if current_cost + cost > self.config.claude_max_cost_per_user:
            remaining = max(0, self.config.claude_max_cost_per_user - current_cost)
            message = (
                f"Cost limit exceeded. Remaining budget: ${remaining:.2f}. "
                f"Current usage: ${current_cost:.2f}/"
                f"${self.config.claude_max_cost_per_user:.2f}"
            )
            return False, message

        return True, None

    def _consume_request_tokens(self, user_id: int, tokens: int) -> None:
        """Consume tokens from request bucket."""
        bucket = self._get_or_create_bucket(user_id)
        bucket.consume(tokens)

    def _track_cost(self, user_id: int, cost: float) -> None:
        """Track cost usage for user."""
        self.cost_tracker[user_id] += cost

        logger.debug(
            "Cost tracked",
            user_id=user_id,
            cost=cost,
            total_usage=self.cost_tracker[user_id],
        )

    def _get_or_create_bucket(self, user_id: int) -> RateLimitBucket:
        """Get or create rate limit bucket for user."""
        if user_id not in self.request_buckets:
            self.request_buckets[user_id] = RateLimitBucket(
                capacity=self.config.rate_limit_burst,
                tokens=self.config.rate_limit_burst,
                last_update=datetime.utcnow(),
                refill_rate=self.refill_rate,
            )
            logger.debug("Created rate limit bucket", user_id=user_id)

        return self.request_buckets[user_id]

    def _maybe_reset_cost_tracker(self, user_id: int) -> None:
        """Reset cost tracker if reset period has passed."""
        now = datetime.utcnow()
        last_reset = self.cost_reset_time.get(user_id, now - timedelta(days=1))

        # Reset daily (configurable)
        reset_interval = timedelta(hours=24)
        if now - last_reset >= reset_interval:
            old_cost = self.cost_tracker[user_id]
            self.cost_tracker[user_id] = 0
            self.cost_reset_time[user_id] = now

            if old_cost > 0:
                logger.info(
                    "Cost tracker reset",
                    user_id=user_id,
                    old_cost=old_cost,
                    reset_time=now.isoformat(),
                )

    async def reset_user_limits(self, user_id: int) -> None:
        """Reset all limits for a user (admin function)."""
        async with self.locks[user_id]:
            # Reset cost tracking
            old_cost = self.cost_tracker[user_id]
            self.cost_tracker[user_id] = 0
            self.cost_reset_time[user_id] = datetime.utcnow()

            # Reset request bucket
            if user_id in self.request_buckets:
                self.request_buckets[user_id].tokens = self.request_buckets[
                    user_id
                ].capacity
                self.request_buckets[user_id].last_update = datetime.utcnow()

            logger.info("User limits reset", user_id=user_id, old_cost=old_cost)

    def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get current rate limit status for user."""
        # Get request bucket status
        bucket = self._get_or_create_bucket(user_id)
        bucket_status = bucket.get_status()

        # Get cost status
        self._maybe_reset_cost_tracker(user_id)
        current_cost = self.cost_tracker[user_id]
        cost_remaining = max(0, self.config.claude_max_cost_per_user - current_cost)

        return {
            "request_bucket": bucket_status,
            "cost_usage": {
                "current": current_cost,
                "limit": self.config.claude_max_cost_per_user,
                "remaining": cost_remaining,
                "utilization": current_cost / self.config.claude_max_cost_per_user,
            },
            "last_reset": self.cost_reset_time.get(
                user_id, datetime.utcnow()
            ).isoformat(),
        }

    def get_global_status(self) -> Dict[str, Any]:
        """Get global rate limiter statistics."""
        return {
            "active_users": len(self.request_buckets),
            "total_cost_tracked": sum(self.cost_tracker.values()),
            "config": {
                "requests_per_window": self.config.rate_limit_requests,
                "window_seconds": self.config.rate_limit_window,
                "burst_capacity": self.config.rate_limit_burst,
                "max_cost_per_user": self.config.claude_max_cost_per_user,
                "refill_rate": self.refill_rate,
            },
        }

    async def cleanup_inactive_users(
        self, inactive_threshold: timedelta = timedelta(hours=24)
    ) -> int:
        """Clean up rate limit data for inactive users."""
        now = datetime.utcnow()
        inactive_users = []

        # Find users with old buckets
        for user_id, bucket in self.request_buckets.items():
            if now - bucket.last_update > inactive_threshold:
                inactive_users.append(user_id)

        # Clean up data
        for user_id in inactive_users:
            self.request_buckets.pop(user_id, None)
            self.cost_tracker.pop(user_id, None)
            self.cost_reset_time.pop(user_id, None)
            self.locks.pop(user_id, None)

        if inactive_users:
            logger.info(
                "Cleaned up inactive users",
                count=len(inactive_users),
                threshold_hours=inactive_threshold.total_seconds() / 3600,
            )

        return len(inactive_users)

```

### src\security\validators.py

**Розмір:** 12,326 байт

```python
"""Input validation and security checks.

Features:
- Path traversal prevention
- Command injection prevention
- File type validation
- Input sanitization
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

# from src.exceptions import SecurityError  # Future use

logger = structlog.get_logger()


class SecurityValidator:
    """Security validation for user inputs."""

    # Dangerous patterns for path traversal and injection
    DANGEROUS_PATTERNS = [
        r"\.\.",  # Parent directory
        r"~",  # Home directory expansion
        r"\$\{",  # Variable expansion ${...}
        r"\$\(",  # Command substitution $(...)
        r"\$[A-Za-z_]",  # Environment variable expansion $VAR
        r"`",  # Command substitution with backticks
        r";",  # Command chaining
        r"&&",  # Command chaining (AND)
        r"\|\|",  # Command chaining (OR)
        r">",  # Output redirection
        r"<",  # Input redirection
        r"\|(?!\|)",  # Piping (but not ||)
        r"&(?!&)",  # Background execution (but not &&)
        r"#.*",  # Comments (potential for injection)
        r"\x00",  # Null byte
    ]

    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".md",
        ".txt",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".xml",
        ".html",
        ".css",
        ".scss",
        ".less",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".bat",
        ".cmd",
        ".r",
        ".scala",
        ".clj",
        ".hs",
        ".elm",
        ".vue",
        ".svelte",
        ".lock",
    }

    # Forbidden filenames and patterns
    FORBIDDEN_FILENAMES = {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        ".ssh",
        ".aws",
        ".docker",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "shadow",
        "passwd",
        "hosts",
        "sudoers",
        ".bash_history",
        ".zsh_history",
        ".mysql_history",
        ".psql_history",
    }

    # Dangerous file patterns
    DANGEROUS_FILE_PATTERNS = [
        r".*\.key$",  # Key files
        r".*\.pem$",  # Certificate files
        r".*\.p12$",  # Certificate files
        r".*\.pfx$",  # Certificate files
        r".*\.crt$",  # Certificate files
        r".*\.cer$",  # Certificate files
        r".*_rsa$",  # SSH keys
        r".*_dsa$",  # SSH keys
        r".*_ecdsa$",  # SSH keys
        r".*\.exe$",  # Executables
        r".*\.dll$",  # Windows libraries
        r".*\.so$",  # Shared objects
        r".*\.dylib$",  # macOS libraries
        r".*\.bat$",  # Batch files
        r".*\.cmd$",  # Command files
        r".*\.msi$",  # Installers
        r".*\.rar$",  # Archives (potentially dangerous)
    ]

    def __init__(self, approved_directory: Path):
        """Initialize validator with approved directory."""
        self.approved_directory = approved_directory.resolve()
        logger.info(
            "Security validator initialized",
            approved_directory=str(self.approved_directory),
        )

    def validate_path(
        self, user_path: str, current_dir: Optional[Path] = None
    ) -> Tuple[bool, Optional[Path], Optional[str]]:
        """Validate and resolve user-provided path.

        Returns:
            Tuple of (is_valid, resolved_path, error_message)
        """
        try:
            # Basic input validation
            if not user_path or not user_path.strip():
                return False, None, "Empty path not allowed"

            user_path = user_path.strip()

            # Check for dangerous patterns
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, user_path, re.IGNORECASE):
                    logger.warning(
                        "Dangerous pattern detected in path",
                        path=user_path,
                        pattern=pattern,
                    )
                    return (
                        False,
                        None,
                        f"Invalid path: contains forbidden pattern '{pattern}'",
                    )

            # Handle path resolution
            current_dir = current_dir or self.approved_directory

            if user_path.startswith("/"):
                # Absolute path - use as-is
                target = Path(user_path)
            else:
                # Relative path
                target = current_dir / user_path

            # Resolve path and check boundaries
            target = target.resolve()

            # Ensure target is within approved directory
            if not self._is_within_directory(target, self.approved_directory):
                logger.warning(
                    "Path traversal attempt detected",
                    requested_path=user_path,
                    resolved_path=str(target),
                    approved_directory=str(self.approved_directory),
                )
                return False, None, "Access denied: path outside approved directory"

            logger.debug(
                "Path validation successful",
                original_path=user_path,
                resolved_path=str(target),
            )
            return True, target, None

        except Exception as e:
            logger.error("Path validation error", path=user_path, error=str(e))
            return False, None, f"Invalid path: {str(e)}"

    def _is_within_directory(self, path: Path, directory: Path) -> bool:
        """Check if path is within directory."""
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            return False

    def validate_filename(self, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate uploaded filename.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic checks
        if not filename or not filename.strip():
            return False, "Empty filename not allowed"

        filename = filename.strip()

        # Check for path separators in filename
        if "/" in filename or "\\" in filename:
            logger.warning("Path separator in filename", filename=filename)
            return False, "Invalid filename: contains path separators"

        # Check for forbidden patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                logger.warning(
                    "Dangerous pattern in filename", filename=filename, pattern=pattern
                )
                return False, "Invalid filename: contains forbidden pattern"

        # Check for forbidden filenames
        if filename.lower() in {name.lower() for name in self.FORBIDDEN_FILENAMES}:
            logger.warning("Forbidden filename", filename=filename)
            return False, f"Forbidden filename: {filename}"

        # Check for dangerous file patterns
        for pattern in self.DANGEROUS_FILE_PATTERNS:
            if re.match(pattern, filename, re.IGNORECASE):
                logger.warning(
                    "Dangerous file pattern", filename=filename, pattern=pattern
                )
                return False, f"File type not allowed: {filename}"

        # Check extension
        path_obj = Path(filename)
        ext = path_obj.suffix.lower()

        if ext and ext not in self.ALLOWED_EXTENSIONS:
            logger.warning(
                "File extension not allowed", filename=filename, extension=ext
            )
            return False, f"File type not allowed: {ext}"

        # Check for hidden files (starting with .)
        if filename.startswith(".") and filename not in {".gitignore", ".gitkeep"}:
            logger.warning("Hidden file upload attempt", filename=filename)
            return False, "Hidden files not allowed"

        # Check filename length
        if len(filename) > 255:
            return False, "Filename too long (max 255 characters)"

        logger.debug("Filename validation successful", filename=filename)
        return True, None

    def sanitize_command_input(self, text: str) -> str:
        """Sanitize text input for commands.

        This removes potentially dangerous characters but preserves
        the structure needed for legitimate commands.
        """
        if not text:
            return ""

        # Remove dangerous characters but preserve basic ones
        # Note: This is very restrictive - adjust based on actual needs
        sanitized = re.sub(r"[`$;|&<>#\x00-\x1f\x7f]", "", text)

        # Limit length to prevent buffer overflow attacks
        max_length = 1000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            logger.warning(
                "Command input truncated",
                original_length=len(text),
                truncated_length=len(sanitized),
            )

        # Remove excessive whitespace
        sanitized = " ".join(sanitized.split())

        if sanitized != text:
            logger.debug(
                "Command input sanitized",
                original=text[:100],  # Log first 100 chars
                sanitized=sanitized[:100],
            )

        return sanitized

    def validate_command_args(
        self, args: List[str]
    ) -> Tuple[bool, List[str], Optional[str]]:
        """Validate and sanitize command arguments.

        Returns:
            Tuple of (is_valid, sanitized_args, error_message)
        """
        if not args:
            return True, [], None

        sanitized_args = []

        for arg in args:
            # Check for dangerous patterns
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, arg, re.IGNORECASE):
                    logger.warning(
                        "Dangerous pattern in command arg", arg=arg, pattern=pattern
                    )
                    return False, [], "Invalid argument: contains forbidden pattern"

            # Sanitize argument
            sanitized = self.sanitize_command_input(arg)
            if not sanitized and arg:  # If original had content but sanitized is empty
                logger.warning("Command argument completely sanitized", original=arg)
                return (
                    False,
                    [],
                    f"Invalid argument: '{arg}' contains only forbidden characters",
                )

            sanitized_args.append(sanitized)

        return True, sanitized_args, None

    def is_safe_directory_name(self, dirname: str) -> bool:
        """Check if directory name is safe for creation."""
        if not dirname or not dirname.strip():
            return False

        dirname = dirname.strip()

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, dirname, re.IGNORECASE):
                return False

        # Check for path separators
        if "/" in dirname or "\\" in dirname:
            return False

        # Check for forbidden names
        if dirname.lower() in {name.lower() for name in self.FORBIDDEN_FILENAMES}:
            return False

        # Check for hidden directories
        if dirname.startswith("."):
            return False

        # Check length
        if len(dirname) > 100:
            return False

        return True

    def get_security_summary(self) -> Dict[str, Any]:
        """Get summary of security validation rules."""
        return {
            "approved_directory": str(self.approved_directory),
            "allowed_extensions": sorted(list(self.ALLOWED_EXTENSIONS)),
            "forbidden_filenames": sorted(list(self.FORBIDDEN_FILENAMES)),
            "dangerous_patterns_count": len(self.DANGEROUS_PATTERNS),
            "dangerous_file_patterns_count": len(self.DANGEROUS_FILE_PATTERNS),
            "max_filename_length": 255,
            "max_command_length": 1000,
        }

```

### src\security\__init__.py

**Розмір:** 1,056 байт

```python
"""Security framework for Claude Code Telegram Bot.

This module provides comprehensive security features including:
- Multi-layer authentication (whitelist and token-based)
- Rate limiting with token bucket algorithm
- Path traversal and injection prevention
- Input validation and sanitization
- Security audit logging

Key Components:
- AuthenticationManager: Main authentication system
- RateLimiter: Request and cost-based rate limiting
- SecurityValidator: Input validation and path security
- AuditLogger: Security event logging
"""

from .audit import AuditEvent, AuditLogger
from .auth import (
    AuthenticationManager,
    AuthProvider,
    TokenAuthProvider,
    UserSession,
    WhitelistAuthProvider,
)
from .rate_limiter import RateLimitBucket, RateLimiter
from .validators import SecurityValidator

__all__ = [
    "AuthProvider",
    "WhitelistAuthProvider",
    "TokenAuthProvider",
    "AuthenticationManager",
    "UserSession",
    "RateLimiter",
    "RateLimitBucket",
    "SecurityValidator",
    "AuditLogger",
    "AuditEvent",
]

```

### src\storage\database.py

**Розмір:** 9,317 байт

```python
"""Database connection and initialization.

Features:
- Connection pooling
- Automatic migrations
- Health checks
- Schema versioning
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Tuple

import aiosqlite
import structlog

logger = structlog.get_logger()

# Initial schema migration
INITIAL_SCHEMA = """
-- Core Tables

-- Users table
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    telegram_username TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_allowed BOOLEAN DEFAULT FALSE,
    total_cost REAL DEFAULT 0.0,
    message_count INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 0
);

-- Sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_cost REAL DEFAULT 0.0,
    total_turns INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Messages table
CREATE TABLE messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prompt TEXT NOT NULL,
    response TEXT,
    cost REAL DEFAULT 0.0,
    duration_ms INTEGER,
    error TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Tool usage table
CREATE TABLE tool_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_id INTEGER,
    tool_name TEXT NOT NULL,
    tool_input JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (message_id) REFERENCES messages(message_id)
);

-- Audit log table
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_data JSON,
    success BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- User tokens table (for token auth)
CREATE TABLE user_tokens (
    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Cost tracking table
CREATE TABLE cost_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    daily_cost REAL DEFAULT 0.0,
    request_count INTEGER DEFAULT 0,
    UNIQUE(user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Indexes for performance
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_project_path ON sessions(project_path);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_cost_tracking_user_date ON cost_tracking(user_id, date);
"""


class DatabaseManager:
    """Manage database connections and initialization."""

    def __init__(self, database_url: str):
        """Initialize database manager."""
        self.database_path = self._parse_database_url(database_url)
        self._connection_pool = []
        self._pool_size = 5
        self._pool_lock = asyncio.Lock()

    def _parse_database_url(self, database_url: str) -> Path:
        """Parse database URL to path."""
        if database_url.startswith("sqlite:///"):
            return Path(database_url[10:])
        elif database_url.startswith("sqlite://"):
            return Path(database_url[9:])
        else:
            return Path(database_url)

    async def initialize(self):
        """Initialize database and run migrations."""
        logger.info("Initializing database", path=str(self.database_path))

        # Ensure directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Run migrations
        await self._run_migrations()

        # Initialize connection pool
        await self._init_pool()

        logger.info("Database initialization complete")

    async def _run_migrations(self):
        """Run database migrations."""
        async with aiosqlite.connect(self.database_path) as conn:
            conn.row_factory = aiosqlite.Row

            # Enable foreign keys
            await conn.execute("PRAGMA foreign_keys = ON")

            # Get current version
            current_version = await self._get_schema_version(conn)
            logger.info("Current schema version", version=current_version)

            # Run migrations
            migrations = self._get_migrations()
            for version, migration in migrations:
                if version > current_version:
                    logger.info("Running migration", version=version)
                    await conn.executescript(migration)
                    await self._set_schema_version(conn, version)

            await conn.commit()

    async def _get_schema_version(self, conn: aiosqlite.Connection) -> int:
        """Get current schema version."""
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """
        )

        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 0

    async def _set_schema_version(self, conn: aiosqlite.Connection, version: int):
        """Set schema version."""
        await conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)", (version,)
        )

    def _get_migrations(self) -> List[Tuple[int, str]]:
        """Get migration scripts."""
        return [
            (1, INITIAL_SCHEMA),
            (
                2,
                """
                -- Add analytics views
                CREATE VIEW IF NOT EXISTS daily_stats AS
                SELECT 
                    date(timestamp) as date,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_messages,
                    SUM(cost) as total_cost,
                    AVG(duration_ms) as avg_duration
                FROM messages
                GROUP BY date(timestamp);

                CREATE VIEW IF NOT EXISTS user_stats AS
                SELECT 
                    u.user_id,
                    u.telegram_username,
                    COUNT(DISTINCT s.session_id) as total_sessions,
                    COUNT(m.message_id) as total_messages,
                    SUM(m.cost) as total_cost,
                    MAX(m.timestamp) as last_activity
                FROM users u
                LEFT JOIN sessions s ON u.user_id = s.user_id
                LEFT JOIN messages m ON u.user_id = m.user_id
                GROUP BY u.user_id;
                """,
            ),
        ]

    async def _init_pool(self):
        """Initialize connection pool."""
        logger.info("Initializing connection pool", size=self._pool_size)

        async with self._pool_lock:
            for _ in range(self._pool_size):
                conn = await aiosqlite.connect(self.database_path)
                conn.row_factory = aiosqlite.Row
                await conn.execute("PRAGMA foreign_keys = ON")
                self._connection_pool.append(conn)

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get database connection from pool."""
        async with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
            else:
                conn = await aiosqlite.connect(self.database_path)
                conn.row_factory = aiosqlite.Row
                await conn.execute("PRAGMA foreign_keys = ON")

        try:
            yield conn
        finally:
            async with self._pool_lock:
                if len(self._connection_pool) < self._pool_size:
                    self._connection_pool.append(conn)
                else:
                    await conn.close()

    async def close(self):
        """Close all connections in pool."""
        logger.info("Closing database connections")

        async with self._pool_lock:
            for conn in self._connection_pool:
                await conn.close()
            self._connection_pool.clear()

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False

```

### src\storage\facade.py

**Розмір:** 10,793 байт

```python
"""Unified storage interface.

Provides simple API for the rest of the application.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import structlog

from ..claude.integration import ClaudeResponse
from .database import DatabaseManager
from .models import (
    AuditLogModel,
    MessageModel,
    SessionModel,
    ToolUsageModel,
    UserModel,
)
from .repositories import (
    AnalyticsRepository,
    AuditLogRepository,
    CostTrackingRepository,
    MessageRepository,
    SessionRepository,
    ToolUsageRepository,
    UserRepository,
)

logger = structlog.get_logger()


class Storage:
    """Main storage interface."""

    def __init__(self, database_url: str):
        """Initialize storage with database URL."""
        self.db_manager = DatabaseManager(database_url)
        self.users = UserRepository(self.db_manager)
        self.sessions = SessionRepository(self.db_manager)
        self.messages = MessageRepository(self.db_manager)
        self.tools = ToolUsageRepository(self.db_manager)
        self.audit = AuditLogRepository(self.db_manager)
        self.costs = CostTrackingRepository(self.db_manager)
        self.analytics = AnalyticsRepository(self.db_manager)

    async def initialize(self):
        """Initialize storage system."""
        logger.info("Initializing storage system")
        await self.db_manager.initialize()
        logger.info("Storage system initialized")

    async def close(self):
        """Close storage connections."""
        logger.info("Closing storage system")
        await self.db_manager.close()

    async def health_check(self) -> bool:
        """Check storage system health."""
        return await self.db_manager.health_check()

    # High-level operations

    async def save_claude_interaction(
        self,
        user_id: int,
        session_id: str,
        prompt: str,
        response: ClaudeResponse,
        ip_address: Optional[str] = None,
    ):
        """Save complete Claude interaction."""
        logger.info(
            "Saving Claude interaction",
            user_id=user_id,
            session_id=session_id,
            cost=response.cost,
        )

        # Save message
        message = MessageModel(
            message_id=None,
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            prompt=prompt,
            response=response.content,
            cost=response.cost,
            duration_ms=response.duration_ms,
            error=response.error_type if response.is_error else None,
        )

        message_id = await self.messages.save_message(message)

        # Save tool usage
        if response.tools_used:
            for tool in response.tools_used:
                tool_usage = ToolUsageModel(
                    id=None,
                    session_id=session_id,
                    message_id=message_id,
                    tool_name=tool["name"],
                    tool_input=tool.get("input", {}),
                    timestamp=datetime.utcnow(),
                    success=not response.is_error,
                    error_message=response.error_type if response.is_error else None,
                )
                await self.tools.save_tool_usage(tool_usage)

        # Update cost tracking
        await self.costs.update_daily_cost(user_id, response.cost)

        # Update user stats
        user = await self.users.get_user(user_id)
        if user:
            user.total_cost += response.cost
            user.message_count += 1
            user.last_active = datetime.utcnow()
            await self.users.update_user(user)

        # Update session stats
        session = await self.sessions.get_session(session_id)
        if session:
            session.total_cost += response.cost
            session.total_turns += response.num_turns
            session.message_count += 1
            session.last_used = datetime.utcnow()
            await self.sessions.update_session(session)

        # Log audit event
        audit_event = AuditLogModel(
            id=None,
            user_id=user_id,
            event_type="claude_interaction",
            event_data={
                "session_id": session_id,
                "cost": response.cost,
                "duration_ms": response.duration_ms,
                "num_turns": response.num_turns,
                "is_error": response.is_error,
                "tools_used": [t["name"] for t in response.tools_used],
            },
            success=not response.is_error,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
        )
        await self.audit.log_event(audit_event)

    async def get_or_create_user(
        self, user_id: int, username: Optional[str] = None
    ) -> UserModel:
        """Get or create user."""
        user = await self.users.get_user(user_id)

        if not user:
            logger.info("Creating new user", user_id=user_id, username=username)
            user = UserModel(
                user_id=user_id,
                telegram_username=username,
                first_seen=datetime.utcnow(),
                last_active=datetime.utcnow(),
                is_allowed=False,  # Default to not allowed
            )
            await self.users.create_user(user)

        return user

    async def create_session(
        self, user_id: int, project_path: str, session_id: str
    ) -> SessionModel:
        """Create new session."""
        session = SessionModel(
            session_id=session_id,
            user_id=user_id,
            project_path=project_path,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
        )

        await self.sessions.create_session(session)

        # Update user session count
        user = await self.users.get_user(user_id)
        if user:
            user.session_count += 1
            await self.users.update_user(user)

        return session

    async def log_security_event(
        self,
        user_id: int,
        event_type: str,
        event_data: Dict[str, Any],
        success: bool = True,
        ip_address: Optional[str] = None,
    ):
        """Log security-related event."""
        audit_event = AuditLogModel(
            id=None,
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
            success=success,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
        )
        await self.audit.log_event(audit_event)

    async def log_bot_event(
        self,
        user_id: int,
        event_type: str,
        event_data: Dict[str, Any],
        success: bool = True,
    ):
        """Log bot-related event."""
        audit_event = AuditLogModel(
            id=None,
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
            success=success,
            timestamp=datetime.utcnow(),
        )
        await self.audit.log_event(audit_event)

    # Convenience methods

    async def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed."""
        user = await self.users.get_user(user_id)
        return user.is_allowed if user else False

    async def get_user_session_summary(self, user_id: int) -> Dict[str, Any]:
        """Get user session summary."""
        sessions = await self.sessions.get_user_sessions(user_id, active_only=False)
        active_sessions = [s for s in sessions if s.is_active]

        return {
            "total_sessions": len(sessions),
            "active_sessions": len(active_sessions),
            "total_cost": sum(s.total_cost for s in sessions),
            "total_messages": sum(s.message_count for s in sessions),
            "projects": list(set(s.project_path for s in sessions)),
        }

    async def get_session_history(
        self, session_id: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Get session history with messages and tools."""
        session = await self.sessions.get_session(session_id)
        if not session:
            return None

        messages = await self.messages.get_session_messages(session_id, limit)
        tools = await self.tools.get_session_tool_usage(session_id)

        return {
            "session": session.to_dict(),
            "messages": [m.to_dict() for m in messages],
            "tool_usage": [t.to_dict() for t in tools],
        }

    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Cleanup old data."""
        logger.info("Starting data cleanup", days=days)

        # Cleanup old sessions
        sessions_cleaned = await self.sessions.cleanup_old_sessions(days)

        logger.info("Data cleanup complete", sessions_cleaned=sessions_cleaned)

        return {"sessions_cleaned": sessions_cleaned}

    async def get_user_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user dashboard data."""
        # Get user info
        user = await self.users.get_user(user_id)
        if not user:
            return None

        # Get user stats
        stats = await self.analytics.get_user_stats(user_id)

        # Get recent sessions
        sessions = await self.sessions.get_user_sessions(user_id, active_only=True)

        # Get recent messages
        messages = await self.messages.get_user_messages(user_id, limit=10)

        # Get recent audit log
        audit_logs = await self.audit.get_user_audit_log(user_id, limit=20)

        # Get daily costs
        daily_costs = await self.costs.get_user_daily_costs(user_id, days=30)

        return {
            "user": user.to_dict(),
            "stats": stats,
            "recent_sessions": [s.to_dict() for s in sessions[:5]],
            "recent_messages": [m.to_dict() for m in messages],
            "recent_audit": [a.to_dict() for a in audit_logs],
            "daily_costs": [c.to_dict() for c in daily_costs],
        }

    async def get_admin_dashboard(self) -> Dict[str, Any]:
        """Get admin dashboard data."""
        # Get system stats
        system_stats = await self.analytics.get_system_stats()

        # Get all users
        users = await self.users.get_all_users()

        # Get recent audit log
        recent_audit = await self.audit.get_recent_audit_log(hours=24)

        # Get total costs
        total_costs = await self.costs.get_total_costs(days=30)

        # Get tool stats
        tool_stats = await self.tools.get_tool_stats()

        return {
            "system_stats": system_stats,
            "users": [u.to_dict() for u in users],
            "recent_audit": [a.to_dict() for a in recent_audit],
            "total_costs": total_costs,
            "tool_stats": tool_stats,
        }

```

### src\storage\models.py

**Розмір:** 7,386 байт

```python
"""Data models for storage.

Using dataclasses for simplicity and type safety.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import aiosqlite


@dataclass
class UserModel:
    """User data model."""

    user_id: int
    telegram_username: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_active: Optional[datetime] = None
    is_allowed: bool = False
    total_cost: float = 0.0
    message_count: int = 0
    session_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ["first_seen", "last_active"]:
            if data[key]:
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "UserModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        for field in ["first_seen", "last_active"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)


@dataclass
class SessionModel:
    """Session data model."""

    session_id: str
    user_id: int
    project_path: str
    created_at: datetime
    last_used: datetime
    total_cost: float = 0.0
    total_turns: int = 0
    message_count: int = 0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ["created_at", "last_used"]:
            if data[key]:
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "SessionModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        for field in ["created_at", "last_used"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)

    def is_expired(self, timeout_hours: int) -> bool:
        """Check if session has expired."""
        if not self.last_used:
            return True

        age = datetime.utcnow() - self.last_used
        return age.total_seconds() > (timeout_hours * 3600)


@dataclass
class MessageModel:
    """Message data model."""

    session_id: str
    user_id: int
    timestamp: datetime
    prompt: str
    message_id: Optional[int] = None
    response: Optional[str] = None
    cost: float = 0.0
    duration_ms: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        if data["timestamp"]:
            data["timestamp"] = data["timestamp"].isoformat()
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "MessageModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)


@dataclass
class ToolUsageModel:
    """Tool usage data model."""

    session_id: str
    tool_name: str
    timestamp: datetime
    id: Optional[int] = None
    message_id: Optional[int] = None
    tool_input: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        if data["timestamp"]:
            data["timestamp"] = data["timestamp"].isoformat()
        # Convert tool_input to JSON string if present
        if data["tool_input"]:
            data["tool_input"] = json.dumps(data["tool_input"])
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "ToolUsageModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Parse JSON fields
        if data.get("tool_input"):
            try:
                data["tool_input"] = json.loads(data["tool_input"])
            except (json.JSONDecodeError, TypeError):
                data["tool_input"] = {}

        return cls(**data)


@dataclass
class AuditLogModel:
    """Audit log data model."""

    user_id: int
    event_type: str
    timestamp: datetime
    id: Optional[int] = None
    event_data: Optional[Dict[str, Any]] = None
    success: bool = True
    ip_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        if data["timestamp"]:
            data["timestamp"] = data["timestamp"].isoformat()
        # Convert event_data to JSON string if present
        if data["event_data"]:
            data["event_data"] = json.dumps(data["event_data"])
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "AuditLogModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Parse JSON fields
        if data.get("event_data"):
            try:
                data["event_data"] = json.loads(data["event_data"])
            except (json.JSONDecodeError, TypeError):
                data["event_data"] = {}

        return cls(**data)


@dataclass
class CostTrackingModel:
    """Cost tracking data model."""

    user_id: int
    date: str  # ISO date format (YYYY-MM-DD)
    daily_cost: float = 0.0
    request_count: int = 0
    id: Optional[int] = None

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "CostTrackingModel":
        """Create from database row."""
        return cls(**dict(row))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class UserTokenModel:
    """User token data model."""

    user_id: int
    token_hash: str
    created_at: datetime
    token_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ["created_at", "expires_at", "last_used"]:
            if data[key]:
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "UserTokenModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        for field in ["created_at", "expires_at", "last_used"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)

    def is_expired(self) -> bool:
        """Check if token has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

```

### src\storage\repositories.py

**Розмір:** 23,085 байт

```python
"""Data access layer using repository pattern.

Features:
- Clean data access API
- Query optimization
- Error handling
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import structlog

from .database import DatabaseManager
from .models import (
    AuditLogModel,
    CostTrackingModel,
    MessageModel,
    SessionModel,
    ToolUsageModel,
    UserModel,
)

logger = structlog.get_logger()


class UserRepository:
    """User data access."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository."""
        self.db = db_manager

    async def get_user(self, user_id: int) -> Optional[UserModel]:
        """Get user by ID."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return UserModel.from_row(row) if row else None

    async def create_user(self, user: UserModel) -> UserModel:
        """Create new user."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, telegram_username, first_seen, last_active, is_allowed)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    user.user_id,
                    user.telegram_username,
                    user.first_seen or datetime.utcnow(),
                    user.last_active or datetime.utcnow(),
                    user.is_allowed,
                ),
            )
            await conn.commit()

            logger.info(
                "Created user", user_id=user.user_id, username=user.telegram_username
            )
            return user

    async def update_user(self, user: UserModel):
        """Update user data."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                UPDATE users 
                SET telegram_username = ?, last_active = ?, 
                    total_cost = ?, message_count = ?, session_count = ?
                WHERE user_id = ?
            """,
                (
                    user.telegram_username,
                    user.last_active or datetime.utcnow(),
                    user.total_cost,
                    user.message_count,
                    user.session_count,
                    user.user_id,
                ),
            )
            await conn.commit()

    async def get_allowed_users(self) -> List[int]:
        """Get list of allowed user IDs."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT user_id FROM users WHERE is_allowed = TRUE"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def set_user_allowed(self, user_id: int, allowed: bool):
        """Set user allowed status."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                "UPDATE users SET is_allowed = ? WHERE user_id = ?", (allowed, user_id)
            )
            await conn.commit()

            logger.info("Updated user permissions", user_id=user_id, allowed=allowed)

    async def get_all_users(self) -> List[UserModel]:
        """Get all users."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM users ORDER BY first_seen DESC")
            rows = await cursor.fetchall()
            return [UserModel.from_row(row) for row in rows]


class SessionRepository:
    """Session data access."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository."""
        self.db = db_manager

    async def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get session by ID."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = await cursor.fetchone()
            return SessionModel.from_row(row) if row else None

    async def create_session(self, session: SessionModel) -> SessionModel:
        """Create new session."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO sessions 
                (session_id, user_id, project_path, created_at, last_used)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.user_id,
                    session.project_path,
                    session.created_at,
                    session.last_used,
                ),
            )
            await conn.commit()

            logger.info(
                "Created session",
                session_id=session.session_id,
                user_id=session.user_id,
            )
            return session

    async def update_session(self, session: SessionModel):
        """Update session data."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                UPDATE sessions 
                SET last_used = ?, total_cost = ?, total_turns = ?, 
                    message_count = ?, is_active = ?
                WHERE session_id = ?
            """,
                (
                    session.last_used,
                    session.total_cost,
                    session.total_turns,
                    session.message_count,
                    session.is_active,
                    session.session_id,
                ),
            )
            await conn.commit()

    async def get_user_sessions(
        self, user_id: int, active_only: bool = True
    ) -> List[SessionModel]:
        """Get sessions for user."""
        async with self.db.get_connection() as conn:
            query = "SELECT * FROM sessions WHERE user_id = ?"
            params = [user_id]

            if active_only:
                query += " AND is_active = TRUE"

            query += " ORDER BY last_used DESC"

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [SessionModel.from_row(row) for row in rows]

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """Mark old sessions as inactive."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE sessions 
                SET is_active = FALSE 
                WHERE last_used < datetime('now', '-' || ? || ' days')
                  AND is_active = TRUE
            """,
                (days,),
            )
            await conn.commit()

            affected = cursor.rowcount
            logger.info("Cleaned up old sessions", count=affected, days=days)
            return affected

    async def get_sessions_by_project(self, project_path: str) -> List[SessionModel]:
        """Get sessions for a specific project."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM sessions 
                WHERE project_path = ? AND is_active = TRUE
                ORDER BY last_used DESC
            """,
                (project_path,),
            )
            rows = await cursor.fetchall()
            return [SessionModel.from_row(row) for row in rows]


class MessageRepository:
    """Message data access."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository."""
        self.db = db_manager

    async def save_message(self, message: MessageModel) -> int:
        """Save message and return ID."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO messages 
                (session_id, user_id, timestamp, prompt, response, cost, duration_ms, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    message.session_id,
                    message.user_id,
                    message.timestamp,
                    message.prompt,
                    message.response,
                    message.cost,
                    message.duration_ms,
                    message.error,
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_session_messages(
        self, session_id: str, limit: int = 50
    ) -> List[MessageModel]:
        """Get messages for session."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM messages 
                WHERE session_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """,
                (session_id, limit),
            )
            rows = await cursor.fetchall()
            return [MessageModel.from_row(row) for row in rows]

    async def get_user_messages(
        self, user_id: int, limit: int = 100
    ) -> List[MessageModel]:
        """Get messages for user."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM messages 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """,
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            return [MessageModel.from_row(row) for row in rows]

    async def get_recent_messages(self, hours: int = 24) -> List[MessageModel]:
        """Get recent messages."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM messages 
                WHERE timestamp > datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp DESC
            """,
                (hours,),
            )
            rows = await cursor.fetchall()
            return [MessageModel.from_row(row) for row in rows]


class ToolUsageRepository:
    """Tool usage data access."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository."""
        self.db = db_manager

    async def save_tool_usage(self, tool_usage: ToolUsageModel) -> int:
        """Save tool usage and return ID."""
        async with self.db.get_connection() as conn:
            tool_input_json = (
                json.dumps(tool_usage.tool_input) if tool_usage.tool_input else None
            )

            cursor = await conn.execute(
                """
                INSERT INTO tool_usage 
                (session_id, message_id, tool_name, tool_input, timestamp, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    tool_usage.session_id,
                    tool_usage.message_id,
                    tool_usage.tool_name,
                    tool_input_json,
                    tool_usage.timestamp,
                    tool_usage.success,
                    tool_usage.error_message,
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_session_tool_usage(self, session_id: str) -> List[ToolUsageModel]:
        """Get tool usage for session."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM tool_usage 
                WHERE session_id = ? 
                ORDER BY timestamp DESC
            """,
                (session_id,),
            )
            rows = await cursor.fetchall()
            return [ToolUsageModel.from_row(row) for row in rows]

    async def get_user_tool_usage(self, user_id: int) -> List[ToolUsageModel]:
        """Get tool usage for user."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT tu.* FROM tool_usage tu
                JOIN sessions s ON tu.session_id = s.session_id
                WHERE s.user_id = ?
                ORDER BY tu.timestamp DESC
            """,
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [ToolUsageModel.from_row(row) for row in rows]

    async def get_tool_stats(self) -> List[Dict[str, any]]:
        """Get tool usage statistics."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT 
                    tool_name,
                    COUNT(*) as usage_count,
                    COUNT(DISTINCT session_id) as sessions_used,
                    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as error_count
                FROM tool_usage
                GROUP BY tool_name
                ORDER BY usage_count DESC
            """
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


class AuditLogRepository:
    """Audit log data access."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository."""
        self.db = db_manager

    async def log_event(self, audit_log: AuditLogModel) -> int:
        """Log audit event and return ID."""
        async with self.db.get_connection() as conn:
            event_data_json = (
                json.dumps(audit_log.event_data) if audit_log.event_data else None
            )

            cursor = await conn.execute(
                """
                INSERT INTO audit_log 
                (user_id, event_type, event_data, success, timestamp, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    audit_log.user_id,
                    audit_log.event_type,
                    event_data_json,
                    audit_log.success,
                    audit_log.timestamp,
                    audit_log.ip_address,
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_user_audit_log(
        self, user_id: int, limit: int = 100
    ) -> List[AuditLogModel]:
        """Get audit log for user."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM audit_log 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """,
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            return [AuditLogModel.from_row(row) for row in rows]

    async def get_recent_audit_log(self, hours: int = 24) -> List[AuditLogModel]:
        """Get recent audit log entries."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM audit_log 
                WHERE timestamp > datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp DESC
            """,
                (hours,),
            )
            rows = await cursor.fetchall()
            return [AuditLogModel.from_row(row) for row in rows]


class CostTrackingRepository:
    """Cost tracking data access."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository."""
        self.db = db_manager

    async def update_daily_cost(self, user_id: int, cost: float, date: str = None):
        """Update daily cost for user."""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO cost_tracking (user_id, date, daily_cost, request_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, date) 
                DO UPDATE SET 
                    daily_cost = daily_cost + ?,
                    request_count = request_count + 1
            """,
                (user_id, date, cost, cost),
            )
            await conn.commit()

    async def get_user_daily_costs(
        self, user_id: int, days: int = 30
    ) -> List[CostTrackingModel]:
        """Get user's daily costs."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM cost_tracking 
                WHERE user_id = ? AND date >= date('now', '-' || ? || ' days')
                ORDER BY date DESC
            """,
                (user_id, days),
            )
            rows = await cursor.fetchall()
            return [CostTrackingModel.from_row(row) for row in rows]

    async def get_total_costs(self, days: int = 30) -> List[Dict[str, any]]:
        """Get total costs by day."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT 
                    date,
                    SUM(daily_cost) as total_cost,
                    SUM(request_count) as total_requests,
                    COUNT(DISTINCT user_id) as active_users
                FROM cost_tracking 
                WHERE date >= date('now', '-' || ? || ' days')
                GROUP BY date
                ORDER BY date DESC
            """,
                (days,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


class AnalyticsRepository:
    """Analytics and reporting."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository."""
        self.db = db_manager

    async def get_user_stats(self, user_id: int) -> Dict[str, any]:
        """Get user statistics."""
        async with self.db.get_connection() as conn:
            # User summary
            cursor = await conn.execute(
                """
                SELECT 
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(*) as total_messages,
                    SUM(cost) as total_cost,
                    AVG(cost) as avg_cost,
                    MAX(timestamp) as last_activity,
                    AVG(duration_ms) as avg_duration
                FROM messages
                WHERE user_id = ?
            """,
                (user_id,),
            )

            summary = dict(await cursor.fetchone())

            # Daily usage (last 30 days)
            cursor = await conn.execute(
                """
                SELECT 
                    date(timestamp) as date,
                    COUNT(*) as messages,
                    SUM(cost) as cost,
                    COUNT(DISTINCT session_id) as sessions
                FROM messages
                WHERE user_id = ? AND timestamp >= datetime('now', '-30 days')
                GROUP BY date(timestamp)
                ORDER BY date DESC
            """,
                (user_id,),
            )

            daily_usage = [dict(row) for row in await cursor.fetchall()]

            # Most used tools
            cursor = await conn.execute(
                """
                SELECT 
                    tu.tool_name,
                    COUNT(*) as usage_count
                FROM tool_usage tu
                JOIN sessions s ON tu.session_id = s.session_id
                WHERE s.user_id = ?
                GROUP BY tu.tool_name
                ORDER BY usage_count DESC
                LIMIT 10
            """,
                (user_id,),
            )

            top_tools = [dict(row) for row in await cursor.fetchall()]

            return {
                "summary": summary,
                "daily_usage": daily_usage,
                "top_tools": top_tools,
            }

    async def get_system_stats(self) -> Dict[str, any]:
        """Get system-wide statistics."""
        async with self.db.get_connection() as conn:
            # Overall stats
            cursor = await conn.execute(
                """
                SELECT 
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(*) as total_messages,
                    SUM(cost) as total_cost,
                    AVG(duration_ms) as avg_duration
                FROM messages
            """
            )

            overall = dict(await cursor.fetchone())

            # Active users (last 7 days)
            cursor = await conn.execute(
                """
                SELECT COUNT(DISTINCT user_id) as active_users
                FROM messages
                WHERE timestamp > datetime('now', '-7 days')
            """
            )

            active_users = (await cursor.fetchone())[0]
            overall["active_users_7d"] = active_users

            # Top users by cost
            cursor = await conn.execute(
                """
                SELECT 
                    u.user_id,
                    u.telegram_username,
                    SUM(m.cost) as total_cost,
                    COUNT(m.message_id) as total_messages
                FROM messages m
                JOIN users u ON m.user_id = u.user_id
                GROUP BY u.user_id
                ORDER BY total_cost DESC
                LIMIT 10
            """
            )

            top_users = [dict(row) for row in await cursor.fetchall()]

            # Tool usage stats
            cursor = await conn.execute(
                """
                SELECT 
                    tool_name,
                    COUNT(*) as usage_count,
                    COUNT(DISTINCT session_id) as sessions_used
                FROM tool_usage
                GROUP BY tool_name
                ORDER BY usage_count DESC
                LIMIT 10
            """
            )

            tool_stats = [dict(row) for row in await cursor.fetchall()]

            # Daily activity (last 30 days)
            cursor = await conn.execute(
                """
                SELECT 
                    date(timestamp) as date,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_messages,
                    SUM(cost) as total_cost
                FROM messages
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY date(timestamp)
                ORDER BY date DESC
            """
            )

            daily_activity = [dict(row) for row in await cursor.fetchall()]

            return {
                "overall": overall,
                "top_users": top_users,
                "tool_stats": tool_stats,
                "daily_activity": daily_activity,
            }

```

### src\storage\session_storage.py

**Розмір:** 9,073 байт

```python
"""Persistent session storage implementation.

Replaces the in-memory session storage with SQLite persistence.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import structlog

from ..claude.session import ClaudeSession, SessionStorage
from .database import DatabaseManager
from .models import SessionModel, UserModel

logger = structlog.get_logger()


class SQLiteSessionStorage(SessionStorage):
    """SQLite-based session storage."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize with database manager."""
        self.db_manager = db_manager

    async def _ensure_user_exists(
        self, user_id: int, username: Optional[str] = None
    ) -> None:
        """Ensure user exists in database before creating session."""
        async with self.db_manager.get_connection() as conn:
            # Check if user exists
            cursor = await conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
            )
            user_exists = await cursor.fetchone()

            if not user_exists:
                # Create user record
                now = datetime.utcnow()
                await conn.execute(
                    """
                    INSERT INTO users (user_id, telegram_username, first_seen, last_active, is_allowed)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        now,
                        now,
                        True,
                    ),  # Allow user by default for now
                )
                await conn.commit()

                logger.info(
                    "Created user record for session",
                    user_id=user_id,
                    username=username,
                )

    async def save_session(self, session: ClaudeSession) -> None:
        """Save session to database."""
        # Ensure user exists before creating session
        await self._ensure_user_exists(session.user_id)

        session_model = SessionModel(
            session_id=session.session_id,
            user_id=session.user_id,
            project_path=str(session.project_path),
            created_at=session.created_at,
            last_used=session.last_used,
            total_cost=session.total_cost,
            total_turns=session.total_turns,
            message_count=session.message_count,
        )

        async with self.db_manager.get_connection() as conn:
            # Try to update first
            cursor = await conn.execute(
                """
                UPDATE sessions 
                SET last_used = ?, total_cost = ?, total_turns = ?, message_count = ?
                WHERE session_id = ?
            """,
                (
                    session_model.last_used,
                    session_model.total_cost,
                    session_model.total_turns,
                    session_model.message_count,
                    session_model.session_id,
                ),
            )

            # If no rows were updated, insert new record
            if cursor.rowcount == 0:
                await conn.execute(
                    """
                    INSERT INTO sessions 
                    (session_id, user_id, project_path, created_at, last_used, 
                     total_cost, total_turns, message_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_model.session_id,
                        session_model.user_id,
                        session_model.project_path,
                        session_model.created_at,
                        session_model.last_used,
                        session_model.total_cost,
                        session_model.total_turns,
                        session_model.message_count,
                    ),
                )

            await conn.commit()

        logger.debug(
            "Session saved to database",
            session_id=session.session_id,
            user_id=session.user_id,
        )

    async def load_session(self, session_id: str) -> Optional[ClaudeSession]:
        """Load session from database."""
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            session_model = SessionModel.from_row(row)

            # Convert to ClaudeSession
            claude_session = ClaudeSession(
                session_id=session_model.session_id,
                user_id=session_model.user_id,
                project_path=Path(session_model.project_path),
                created_at=session_model.created_at,
                last_used=session_model.last_used,
                total_cost=session_model.total_cost,
                total_turns=session_model.total_turns,
                message_count=session_model.message_count,
                tools_used=[],  # Tools are tracked separately in tool_usage table
            )

            logger.debug(
                "Session loaded from database",
                session_id=session_id,
                user_id=claude_session.user_id,
            )

            return claude_session

    async def delete_session(self, session_id: str) -> None:
        """Delete session from database."""
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                "UPDATE sessions SET is_active = FALSE WHERE session_id = ?",
                (session_id,),
            )
            await conn.commit()

        logger.debug("Session marked as inactive", session_id=session_id)

    async def get_user_sessions(self, user_id: int) -> List[ClaudeSession]:
        """Get all active sessions for a user."""
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM sessions 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY last_used DESC
            """,
                (user_id,),
            )
            rows = await cursor.fetchall()

            sessions = []
            for row in rows:
                session_model = SessionModel.from_row(row)
                claude_session = ClaudeSession(
                    session_id=session_model.session_id,
                    user_id=session_model.user_id,
                    project_path=Path(session_model.project_path),
                    created_at=session_model.created_at,
                    last_used=session_model.last_used,
                    total_cost=session_model.total_cost,
                    total_turns=session_model.total_turns,
                    message_count=session_model.message_count,
                    tools_used=[],  # Tools are tracked separately
                )
                sessions.append(claude_session)

            return sessions

    async def get_all_sessions(self) -> List[ClaudeSession]:
        """Get all active sessions."""
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE is_active = TRUE ORDER BY last_used DESC"
            )
            rows = await cursor.fetchall()

            sessions = []
            for row in rows:
                session_model = SessionModel.from_row(row)
                claude_session = ClaudeSession(
                    session_id=session_model.session_id,
                    user_id=session_model.user_id,
                    project_path=Path(session_model.project_path),
                    created_at=session_model.created_at,
                    last_used=session_model.last_used,
                    total_cost=session_model.total_cost,
                    total_turns=session_model.total_turns,
                    message_count=session_model.message_count,
                    tools_used=[],  # Tools are tracked separately
                )
                sessions.append(claude_session)

            return sessions

    async def cleanup_expired_sessions(self, timeout_hours: int) -> int:
        """Mark expired sessions as inactive."""
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE sessions 
                SET is_active = FALSE 
                WHERE last_used < datetime('now', '-' || ? || ' hours')
                  AND is_active = TRUE
            """,
                (timeout_hours,),
            )
            await conn.commit()

            affected = cursor.rowcount
            logger.info(
                "Cleaned up expired sessions",
                count=affected,
                timeout_hours=timeout_hours,
            )
            return affected

```

### src\storage\__init__.py

**Розмір:** 0 байт

```python


```

### src\utils\constants.py

**Розмір:** 1,760 байт

```python
"""Application-wide constants."""

# Version info
APP_NAME = "Claude Code Telegram Bot"
APP_DESCRIPTION = "Telegram bot for remote Claude Code access"

# Default limits
DEFAULT_CLAUDE_TIMEOUT_SECONDS = 300
DEFAULT_CLAUDE_MAX_TURNS = 10
DEFAULT_CLAUDE_MAX_COST_PER_USER = 10.0

DEFAULT_RATE_LIMIT_REQUESTS = 10
DEFAULT_RATE_LIMIT_WINDOW = 60
DEFAULT_RATE_LIMIT_BURST = 20

DEFAULT_SESSION_TIMEOUT_HOURS = 24
DEFAULT_MAX_SESSIONS_PER_USER = 5

# Message limits
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
SAFE_MESSAGE_LENGTH = 4000  # Leave room for formatting

# Session limits
MAX_SESSION_LENGTH = 1000  # Maximum messages per session

# File limits
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".xml",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".sh",
    ".bash",
}

# Security patterns to block
DANGEROUS_PATTERNS = [
    r"\.\.",  # Parent directory
    r"~",  # Home directory
    r"\$",  # Variable expansion
    r"`",  # Command substitution
    r";",  # Command chaining
    r"&&",  # Command chaining
    r"\|\|",  # Command chaining
    r">",  # Redirection
    r"<",  # Redirection
    r"\|",  # Piping
]

# Database defaults
DEFAULT_DATABASE_URL = "sqlite:///data/bot.db"
DEFAULT_BACKUP_RETENTION_DAYS = 30

# Claude Code defaults
DEFAULT_CLAUDE_BINARY = "claude"
DEFAULT_CLAUDE_OUTPUT_FORMAT = "stream-json"

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

```

### src\utils\__init__.py

**Розмір:** 0 байт

```python


```

---

## Статистика

- **Оброблено файлів:** 52
- **Пропущено сервісних файлів:** 3
- **Загальний розмір:** 521,610 байт (509.4 KB)
- **Дата створення:** 2025-09-08 21:12:58
