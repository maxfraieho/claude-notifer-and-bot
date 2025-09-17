# MCP (Model Context Protocol) - Практичні приклади

## 🎯 Готові сценарії використання

### 📊 Аналіз проекту

**Мета**: Комплексний аналіз стану проекту через різні MCP сервери

```bash
# 1. Налаштування серверів
/mcpadd filesystem
# Вкажіть шлях: /home/user/my-project

/mcpadd git  
# Вкажіть репозиторій: /home/user/my-project

/mcpadd github
# Введіть GitHub токен

# 2. Аналіз файлової структури
/mcpselect project-files
/mcpask Проаналізуй структуру проекту та знайди:
- Незвичайні файли або директорії
- Великі файли (>1MB) 
- Дублікати коду
- Файли без документації

# 3. Перевірка Git статусу
/mcpselect project-git
/mcpask Покажи детальний статус git репозиторію:
- Незафіксовані зміни
- Статус всіх гілок
- Останні 10 комітів з описами
- Конфлікти та проблеми

# 4. GitHub Issues та PR
/mcpselect project-github
/mcpask Проаналізуй стан проекту на GitHub:
- Відкриті issues за пріоритетами  
- Pull requests що очікують review
- Contributors та їх активність
- Release notes останньої версії
```

**Очікуваний результат**: Комплексний звіт про стан проекту з трьох джерел

---

### 🔍 Дослідження бази даних

**Мета**: Аналіз структури та даних PostgreSQL бази

```bash
# 1. Підключення до бази
/mcpadd postgres
# Connection string: postgresql://user:pass@localhost:5432/mydb

# 2. Дослідження схеми
/mcpselect main-database
/mcpask Дослідь структуру бази даних:
- Покажи всі таблиці з кількістю записів
- Знайди таблиці без primary key
- Покажи foreign key зв'язки
- Виведи розмір кожної таблиці

# 3. Аналіз даних
/mcpask Проаналізуй якість даних:
- Знайди NULL значення в критичних полях
- Покажи дублікати в унікальних полях  
- Знайди аномалії в датах (майбутні дати)
- Статистика по користувачах за останній місяць

# 4. Оптимізація
/mcpask Запропонуй оптимізації:
- Таблиці без індексів на часто використовуваних полях
- Повільні запити (з EXPLAIN)
- Таблиці кандидати на партиціонування
- Поля кандидати на денормалізацію
```

**Очікуваний результат**: Детальний аналіз БД з рекомендаціями

---

### 🌐 Аудит веб-сайту

**Мета**: Комплексна перевірка веб-сайту за допомогою Playwright

```bash
# 1. Налаштування Web Automation
/mcpadd playwright
# Додаткової конфігурації не потрібно

# 2. Перевірка доступності
/mcpselect web-audit
/mcpask Перевір доступність сайту https://example.com:
- Час завантаження головної сторінки
- Перевір всі посилання на 404 помилки
- Протестуй форми (контакти, реєстрація)
- Перевір мобільну версію

# 3. SEO аудит
/mcpask Проведи SEO аудит:
- Перевір meta теги (title, description)
- Знайди відсутні alt теги на зображеннях
- Перевір structured data (JSON-LD)
- Аналіз швидкості завантаження

# 4. Безпека
/mcpask Перевір безпеку сайту:
- HTTPS конфігурація
- Content Security Policy заголовки
- Перевір форми на XSS захист
- Знайди exposed sensitive information
```

**Очікуваний результат**: Комплексний звіт про стан веб-сайту

---

### 📈 Бізнес аналітика

**Мета**: Аналіз бізнес-метрик з бази даних

```bash
# 1. Підключення до продакшн БД (read-only)
/mcpadd postgres
# Connection string: postgresql://readonly:pass@prod.db:5432/analytics

# 2. Продажі та конверсія
/mcpselect analytics-db
/mcpask Проаналізуй продажі за останні 30 днів:
- Загальний обсяг продажів по днях
- Топ-10 товарів за виручкою
- Конверсія по джерелах трафіку
- AOV (середній чек) по сегментах користувачів

# 3. Користувачі та поведінка
/mcpask Дослідь поведінку користувачів:
- Нові vs повернуті користувачі
- Retention rate по когортах
- Найпопулярніші сторінки/функції
- Точки виходу в воронці продажів

# 4. Тренди та прогнози
/mcpask Знайди тренди та аномалії:
- Порівняй цей місяць з попереднім
- Виділи сезонні паттерни
- Знайди аномальні дні (різкі спади/зростання)
- Прогноз на наступний місяць на основі трендів
```

**Очікуваний результат**: Бізнес-інсайти та рекомендації

---

### 🔧 DevOps моніторинг

**Мета**: Моніторинг інфраструктури через файли логів

```bash
# 1. Доступ до логів сервера
/mcpadd filesystem
# Шлях: /var/log/myapp

# 2. Аналіз логів помилок
/mcpselect server-logs
/mcpask Проаналізуй логи за останню добу:
- Топ помилок за частотою
- Критичні помилки (500, fatal)
- Повільні запити (>5 секунд)
- Підозрілі IP адреси

# 3. Продуктивність
/mcpask Оціни продуктивність системи:
- Середній час відгуку по ендпоінтах
- Пікові навантаження по годинах
- Memory usage patterns
- Disk I/O bottlenecks

# 4. Безпека
/mcpask Перевір безпеку:
- Спроби брутфорс атак
- Незвичайні UserAgent strings  
- Доступи до захищених ресурсів
- Geo-локація підозрілих запитів
```

**Очікуваний результат**: Звіт про стан інфраструктури

---

## 🛠️ Приклади інтеграції кількох серверів

### Автоматизований CI/CD аудит

```bash
# Файли + Git + GitHub
/mcpselect project-files
/mcpask Перевір якість коду перед релізом

/mcpselect project-git  
/mcpask Покажи зміни з останнього тегу

/mcpselect project-github
/mcpask Перевір чи всі CI checks пройшли
```

### Міграція даних з валідацією

```bash
# Old DB + New DB + Files для логування
/mcpselect old-database
/mcpask Експортуй дані користувачів у JSON

/mcpselect migration-files
/mcpask Збережи експорт у файл users_export.json

/mcpselect new-database  
/mcpask Імпортуй і валідуй дані з JSON файлу
```

### Код-рев'ю з контекстом

```bash
# Git + Files + GitHub
/mcpselect project-git
/mcpask Покажи зміни в останньому коміті

/mcpselect project-files
/mcpask Проаналізуй вплив змін на архітектуру

/mcpselect project-github
/mcpask Створи детальний code review для PR #123
```

---

## 💡 Поради по ефективному використанню

### Шаблони запитів

**Для аналізу коду:**
```
/mcpask Проаналізуй [файл/директорію] на предмет:
- Code quality issues
- Security vulnerabilities  
- Performance bottlenecks
- Best practices violations
- Documentation coverage
```

**Для дослідження даних:**
```
/mcpask Дослідь таблицю [table_name]:
- Схема та індекси
- Розподіл даних по колонках
- Залежності та зв'язки
- Аномалії та дублікати
- Статистика використання
```

**Для Git аналізу:**
```
/mcpask Покажи Git статистику:
- Активність contributors за [період]
- Топ файлів за кількістю змін
- Тренди розміру кодобази
- Hotspots (часто змінювані файли)
- Конфлікти та проблемні merge
```

### Автоматизація рутинних задач

**Щоденна перевірка проекту:**
```bash
#!/bin/bash
# Скрипт для автоматизації через API

# Morning health check
curl -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
  -d chat_id=$CHAT_ID \
  -d text="/mcpstatus"

curl -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
  -d chat_id=$CHAT_ID \
  -d text="/mcpselect project-git && /mcpask Покажи зміни за останні 24 години"
```

**Моніторинг бази даних:**
```sql
-- Створіть view для регулярного аналізу
CREATE VIEW daily_health_check AS
SELECT 
  table_name,
  row_count,
  size_mb,
  last_vacuum,
  index_usage
FROM information_schema.tables;
```

Потім:
```bash
/mcpask Покажи результати daily_health_check view та виділи проблеми
```

### Комплексні workflow

**Feature Development Flow:**
```bash
# 1. Планування
/mcpselect project-github
/mcpask Проаналізуй issue #456 та запропонуй план імплементації

# 2. Розробка  
/mcpselect project-files
/mcpask Створи структуру файлів для нової фічі

# 3. Код-рев'ю
/mcpselect project-git
/mcpask Покажи diff та потенційні проблеми

# 4. Тестування
/mcpselect project-files  
/mcpask Проаналізуй покриття тестами нового коду

# 5. Деплой
/mcpselect project-github
/mcpask Створи PR з детальним описом змін
```

**Data Analysis Flow:**
```bash
# 1. Exploration
/mcpselect analytics-db
/mcpask Дослідь нову таблицю customer_events

# 2. Validation
/mcpask Перевір якість даних за останній тиждень

# 3. Analysis  
/mcpask Знайди інсайти про поведінку користувачів

# 4. Reporting
/mcpselect report-files
/mcpask Створи markdown звіт з візуалізаціями
```

---

## 🚀 Продвинуті техніки

### Кастомні промпти для специфічних задач

**Security Audit Prompt:**
```
/mcpask Виконай security audit як експерт з безпеки:

КРИТЕРІЇ ПЕРЕВІРКИ:
✓ Authentication mechanisms
✓ Authorization controls  
✓ Input validation
✓ Output encoding
✓ Session management
✓ Error handling
✓ Logging security events

ФОРМАТ ВІДПОВІДІ:
🔴 Critical: [опис]
🟡 Medium: [опис]  
🟢 Low: [опис]
✅ Good practices: [опис]

РЕКОМЕНДАЦІЇ:
- Конкретні кроки для виправлення
- Посилання на best practices
- Пріоритизація виправлень
```

**Performance Analysis Prompt:**
```
/mcpask Проведи performance аналіз як експерт з оптимізації:

МЕТРИКИ ДЛЯ АНАЛІЗУ:
📊 Response times (p50, p95, p99)
💾 Memory usage patterns
🔄 CPU utilization
💿 Disk I/O metrics
🌐 Network latency

BOTTLENECKS:
- Database queries
- External API calls
- File system operations
- Memory allocations

РЕКОМЕНДАЦІЇ:
- Quick wins (< 1 день)
- Medium term (1-2 тижні)
- Long term (> 1 місяць)
```

### Автоматизовані звіти

**Щотижневий звіт проекту:**
```bash
# Створіть команду-макрос
/mcpask Створи щотижневий звіт проекту:

📊 МЕТРИКИ РОЗРОБКИ (Git):
- Commits цього тижня vs минулого
- Contributors активність
- Code churn (додано/видалено рядків)
- Hotspots (найбільш змінювані файли)

🐛 ЯКІСТЬ КОДУ (Files):  
- Нові TODO/FIXME коментарі
- Code coverage зміни
- Lint violations тренди
- Technical debt індикатори

🎯 ПРОДУКТОВІ МЕТРИКИ (GitHub):
- Закриті vs відкриті issues
- PR throughput та час review
- Release notes підготовка
- User feedback з issues

📈 РЕКОМЕНДАЦІЇ:
- Пріоритетні завдання на наступний тиждень
- Проблемні області що потребують уваги
- Process improvements
```

### Інтеграція з зовнішніми системами

**Slack Integration via Files:**
```bash
# 1. Створити звіт
/mcpselect monitoring-files
/mcpask Створи JSON звіт про стан системи для Slack webhook

# 2. Відправити через webhook (зовнішній скрипт)
curl -X POST "https://hooks.slack.com/services/..." \
  -H "Content-Type: application/json" \
  -d @system_report.json
```

**Jira Integration:**
```bash
# Генерація Jira tickets з аналізу
/mcpselect project-files  
/mcpask Проаналізуй код та створи CSV файл з bugs для імпорту в Jira:
- Title
- Description  
- Priority
- Component
- Assignee (based on git blame)
```

---

## 📝 Чек-листи для різних сценаріїв

### ✅ Pre-deployment Checklist

```bash
# Security
/mcpselect project-files
/mcpask Перевір відсутність hardcoded secrets та API keys

# Performance  
/mcpask Знайди потенційні performance bottlenecks

# Code Quality
/mcpask Перевір coverage тестами критичного функціоналу

# Git
/mcpselect project-git
/mcpask Підтверди що всі зміни закоммічені

# Infrastructure
/mcpselect deployment-logs
/mcpask Перевір стан production середовища
```

### ✅ Incident Response Checklist

```bash
# Immediate Assessment
/mcpselect error-logs
/mcpask Знайди корінь проблеми в логах за останню годину

# Impact Analysis  
/mcpselect monitoring-db
/mcpask Оціни вплив на користувачів та бізнес-метрики

# Communication
/mcpselect incident-files
/mcpask Створи incident report template з timeline

# Resolution Tracking
/mcpask Задокументуй кроки до вирішення проблеми
```

---

*Ці приклади демонструють потужність MCP системи для автоматизації різноманітних DevOps, аналітичних та розробницьких задач. Адаптуйте їх під свої потреби!*