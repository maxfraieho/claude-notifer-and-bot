# Universal Bot Restart Script

## 📋 Огляд

`bot-restart.sh` - це универсальний скрипт для запуску та перезапуску Claude Code Telegram бота. Він забезпечує повне очищення всіх процесів, сесій та тимчасових файлів перед запуском нової інстанції бота.

## ✨ Можливості

- ✅ **Повне очищення** - вбиває всі існуючі процеси бота
- ✅ **Очищення сесій** - закриває всі background bash сесії
- ✅ **Очищення файлів** - видаляє тимчасові файли та restart info
- ✅ **Режим економії пам'яті** - запускає з оптимізованими налаштуваннями Python
- ✅ **Poetry інтеграція** - використовує Poetry для управління залежностями
- ✅ **Безпечне завершення** - спочатку graceful shutdown, потім force kill

## 🚀 Використання

### Запуск з консолі

```bash
# Перейти до директорії проекту
cd /home/vokov/projects/claude-notifer-and-bot

# Запустити універсальний скрипт
./bot-restart.sh
```

### Перезапуск з Telegram

Використовуйте команду `/restart` в боті. Бот автоматично:
1. Збереже інформацію про перезапуск
2. Виконає `bot-restart.sh`
3. Після перезапуску покаже локалізоване меню старту

## ⚙️ Оптимізації пам'яті

Скрипт встановлює наступні змінні середовища:

```bash
export PYTHONOPTIMIZE=1          # Оптимізовані байт-коди
export PYTHONDONTWRITEBYTECODE=1 # Не створювати .pyc файли
export PYTHONMALLOC=malloc       # Використовувати системний malloc
export MALLOC_TRIM_THRESHOLD_=100000  # Агресивне звільнення пам'яті
```

Запускає Python з флагом `-O` для додаткової оптимізації.

## 🔍 Процес очищення

1. **Пошук процесів** - знаходить всі процеси `python.*src.main`
2. **Graceful shutdown** - відправляє SIGTERM
3. **Force kill** - якщо потрібно, використовує SIGKILL
4. **Очищення background сесій** - закриває висячі bash процеси
5. **Перевірка** - підтверджує що всі процеси закриті
6. **Очищення файлів** - видаляє тимчасові файли

## 📝 Лог виводу

Скрипт надає детальний лог:

```
🔄 Universal Bot Restart Script
===============================
⚠️  Running as root - this is normal in containers
Thu Sep 25 08:42:48 UTC 2025: Starting bot restart procedure...
🔍 Looking for bot processes...
📋 Found PIDs: 18841
⏹️  Attempting graceful shutdown...
💀 Force killing remaining processes: 18841
✅ Cleaned up bot processes
🧹 Cleaning up background bash sessions...
✅ Background sessions cleaned
🔍 Verifying cleanup...
✅ All bot processes stopped
🗑️  Cleaning temporary files...
✅ Temporary files cleaned
⏳ Waiting for system cleanup...
🚀 Starting bot with memory optimization...
🔧 Environment configured for memory optimization
🔄 Starting bot...
```

## 🔄 Інтеграція з командою /restart

Команда `/restart` в боті тепер використовує цей скрипт:

1. Зберігає restart info в `/tmp/claude_bot_restart_info.json`
2. Викликає `bot-restart.sh` через `os.execl()`
3. Скрипт очищує все і запускає бота
4. Бот при старті читає restart info і показує локалізоване меню

## ⚠️ Важливо

- Скрипт призначений для роботи в контейнері (root користувач)
- Вимагає наявність `pyproject.toml` та `src/main.py`
- Використовує Poetry для управління залежностями
- Автоматично встановлює PATH для Poetry

## 🐛 Налагодження

Якщо бот не запускається:

1. Перевірте що ви в правильній директорії
2. Переконайтесь що `pyproject.toml` існує
3. Перевірте що Poetry встановлений
4. Запустіть з мануальним логуванням: `./bot-restart.sh 2>&1 | tee restart.log`

## 📁 Файли

- `bot-restart.sh` - основний скрипт перезапуску
- `/tmp/claude_bot_restart_info.json` - тимчасові дані перезапуску
- `src/bot/handlers/command.py` - інтеграція команди `/restart`
- `src/bot/core.py` - обробка restart info при старті