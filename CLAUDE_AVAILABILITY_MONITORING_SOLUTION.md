# 🔍 СИСТЕМА МОНІТОРИНГУ ДОСТУПНОСТІ CLAUDE CLI

## 🎯 **ПРОБЛЕМА**

**Поточна ситуація:**
- Користувач надсилає запит до Claude CLI
- Отримує не локалізовану помилку англійською
- Не знає коли Claude стане доступний
- Немає проактивних сповіщень про статус

## 💡 **ТЕХНІЧНЕ РІШЕННЯ**

### 🏗️ **Архітектура системи моніторингу**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Request  │───▶│  Availability    │───▶│  Smart Response │
│                 │    │  Check Service   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │  Notification    │
                    │  Service         │
                    └──────────────────┘
```

### 🔧 **Компоненти системи**

#### **1. Claude Availability Checker**
- Перевірка статусу перед кожним запитом
- Кешування результатів (30 сек)
- Автоматичне відновлення після збоїв

#### **2. Smart Request Router**
- Інтерцепція запитів до Claude
- Попередня перевірка доступності
- Українська локалізація помилок

#### **3. Proactive Notification System**
- Моніторинг статусу кожні 2 хвилини
- Повідомлення в групу при зміні статусу
- Налаштування включення/виключення

#### **4. Status Dashboard**
- Команда `/claude_status` - поточний статус
- Історія доступності за останні 24 години
- Прогноз часу відновлення

## 🛠️ **ДЕТАЛЬНИЙ ПЛАН РЕАЛІЗАЦІЇ**

### **Крок 1: Розширення існуючої системи моніторингу**

#### **Файл: `src/bot/features/claude_availability_monitor.py`**
```python
class ClaudeAvailabilityMonitor:
    def __init__(self):
        self.last_status = None
        self.last_check_time = None
        self.cache_duration = 30  # секунд
        self.check_interval = 120  # 2 хвилини

    async def check_availability_with_details(self):
        """Розширена перевірка з деталями про причину недоступності"""

    async def is_claude_available_cached(self):
        """Кешована перевірка доступності"""

    async def notify_status_change(self, old_status, new_status):
        """Повідомлення про зміну статусу в групу"""
```

#### **Файл: `src/bot/middleware/claude_availability.py` (НОВИЙ)**
```python
class ClaudeAvailabilityMiddleware:
    """Middleware для перевірки доступності перед запитами"""

    async def __call__(self, handler, event, data):
        if self.is_claude_request(event):
            if not await self.check_availability():
                return await self.handle_unavailable(event)
        return await handler(event, data)
```

### **Крок 2: Інтеграція з існуючим потоком**

#### **Модифікація: `src/bot/handlers/message.py`**
```python
# Додати перевірку перед викликом Claude
async def handle_text_message(update, context):
    # ... existing code ...

    # Перевірка доступності Claude
    availability_monitor = context.bot_data.get("claude_availability_monitor")
    if availability_monitor:
        is_available, status_info = await availability_monitor.check_availability_with_details()
        if not is_available:
            await send_unavailable_message(update, status_info)
            return

    # ... continue with Claude request ...
```

### **Крок 3: Українська локалізація помилок**

#### **Файл: `src/localization/translations/uk.json`**
```json
{
  "claude_status": {
    "unavailable": "🔴 Claude зараз недоступний",
    "checking": "🟡 Перевіряю доступність Claude...",
    "available": "🟢 Claude доступний",
    "rate_limited": "⏳ Claude тимчасово обмежений (rate limit)",
    "auth_expired": "🔑 Потрібна повторна авторизація Claude",
    "network_error": "🌐 Проблеми з мережею",
    "unknown_error": "❓ Невідома помилка Claude",

    "estimated_recovery": "Очікується відновлення через: {time}",
    "check_again": "Перевірте статус командою /claude_status",
    "notification_enabled": "✅ Сповіщення про статус увімкнено",
    "notification_disabled": "❌ Сповіщення про статус вимкнено"
  }
}
```

### **Крок 4: Команди управління**

#### **Нові команди в `src/bot/handlers/command.py`:**

```python
async def claude_status_command(update, context):
    """Команда /claude_status - показати поточний статус"""

async def toggle_claude_notifications_command(update, context):
    """Команда /claude_notifications - увімкнути/вимкнути сповіщення"""

async def claude_history_command(update, context):
    """Команда /claude_history - історія доступності за 24 год"""
```

### **Крок 5: Налаштування сповіщень**

#### **Конфігурація в `.env`:**
```env
# Claude Availability Monitoring
CLAUDE_AVAILABILITY_MONITOR=true
CLAUDE_AVAILABILITY_CHECK_INTERVAL=120  # секунди
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=-1001234567890,6412868393
CLAUDE_AVAILABILITY_CACHE_DURATION=30  # секунди

# Notification settings
CLAUDE_NOTIFICATIONS_ENABLED=true
CLAUDE_NOTIFICATIONS_INCLUDE_RECOVERY_TIME=true
```

## 📊 **ПРИКЛАДИ КОРИСТУВАЦЬКОГО ДОСВІДУ**

### **Сценарій 1: Claude недоступний**
```
Користувач: "Проаналізуй цей код"
Бот: 🔴 Claude зараз недоступний (rate limit)
     ⏳ Очікується відновлення через: 45 хвилин

     💡 Я повідомлю в групу, коли Claude стане доступний
     📋 Використайте /claude_status для перевірки
```

### **Сценарій 2: Відновлення роботи**
```
Повідомлення в групу:
🟢 Claude знову доступний!
⏰ Час недоступності: 1 година 23 хвилини
✅ Можна продовжувати роботу
```

### **Сценарій 3: Налаштування сповіщень**
```
/claude_notifications

⚙️ Налаштування сповіщень Claude

🔔 Статус: ✅ Увімкнено
📢 Група сповіщень: Розробка
⏰ Інтервал перевірки: 2 хвилини

┌─────────────────────────────┐
│ ❌ Вимкнути  │ ⚙️ Налашт. │
│ 📊 Історія   │ 🔄 Статус  │
└─────────────────────────────┘
```

## 🎯 **ПЕРЕВАГИ РІШЕННЯ**

### **1. Користувацький досвід**
- ✅ Миттєве українське повідомлення про проблему
- ✅ Прогноз часу відновлення
- ✅ Проактивні сповіщення

### **2. Ефективність**
- ✅ Кешування результатів перевірки
- ✅ Зменшення непотрібних запитів
- ✅ Автоматичне відновлення

### **3. Моніторинг**
- ✅ Історія доступності
- ✅ Статистика збоїв
- ✅ Налаштування сповіщень

### **4. Інтеграція**
- ✅ Використання існуючої архітектури
- ✅ Мінімальні зміни в основному коді
- ✅ Зворотна сумісність

## 🚀 **ЕТАПИ ВПРОВАДЖЕННЯ**

### **Етап 1 (1-2 дні): Базовий моніторинг**
1. ✅ Розширити existing availability monitor
2. ✅ Додати українську локалізацію
3. ✅ Інтегрувати з message handler

### **Етап 2 (2-3 дні): Розумні сповіщення**
1. ✅ Додати команди управління
2. ✅ Налаштування в групах
3. ✅ Прогноз часу відновлення

### **Етап 3 (1-2 дні): Покращений UX**
1. ✅ Статистика та історія
2. ✅ Персональні налаштування
3. ✅ Детальна діагностика

## 📋 **ГОТОВИЙ ПРОМПТ ДЛЯ РОЗРОБНИКА**

```markdown
# ЗАВДАННЯ: Реалізація системи моніторингу доступності Claude CLI

## МЕТА
Створити розумну систему, що:
1. Перевіряє доступність Claude перед кожним запитом
2. Показує локалізовані українські повідомлення про помилки
3. Надсилає проактивні сповіщення в групу про зміни статусу
4. Дозволяє користувачам керувати сповіщеннями

## ТЕХНІЧНІ ВИМОГИ
1. Розширити existing ClaudeAvailabilityMonitor
2. Додати middleware для intercepting Claude requests
3. Інтегрувати з Ukrainian localization system
4. Створити команди /claude_status, /claude_notifications
5. Налаштувати group notifications через .env

## ПРІОРИТЕТ
Високий - покращує UX та зменшує фрустрацію користувачів

## ОЧІКУВАНИЙ РЕЗУЛЬТАТ
Користувачі отримають:
- Миттєві українські повідомлення про недоступність
- Прогноз часу відновлення
- Автоматичні сповіщення про відновлення роботи
- Можливість налаштувати сповіщення
```

---
*Автор: Claude AI System Analyst*
*Дата: 2025-09-21*
*Статус: Готово до розробки*