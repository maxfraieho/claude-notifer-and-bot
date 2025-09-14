# Промпт: Відновлення сесії та початковий запуск

## Опис процесу
Цей промпт автоматизує процес відновлення роботи після перерв у зв'язку з Claude Code - включаючи п'ятигодинні обмеження, розриви з'єднання, перезапуск системи або інші форс-мажорні ситуації.

## Діалог з Claude Code

**Користувач:**
```
recovery-startup
```

**Claude Code відповідає:**
Я виконаю процес відновлення сесії після перерви. Це включає:

1. Аналіз поточного стану системи та репозиторію
2. Завантаження контексту з документації проекту
3. Перевірка статусу всіх сервісів
4. Відновлення робочого середовища
5. Синхронізація з останніми змінами
6. Валідація готовності до роботи

Почнемо відновлення:

*Виконує послідовність команд:*

```bash
# 1. Базова діагностика системи
echo "=== System Recovery Analysis ==="
date
pwd
whoami

# 2. Перевірка git статусу для розуміння поточного стану
git status
git log --oneline -5

# 3. Перевірка статусу Docker контейнерів
docker-compose ps

# 4. Перевірка основних файлів конфігурації
ls -la .env docker-compose.yml CLAUDE.md TRANSFER_BRIEF.md 2>/dev/null
```

*Читає ключові файли для відновлення контексту:*

```python
# Завантаження контексту з проекту
files_to_analyze = [
    'CLAUDE.md',           # Інструкції проекту
    'TRANSFER_BRIEF.md',   # Останній стан розробки  
    'README.md',           # Загальний опис
    'DEPLOYMENT.md'        # Деплой інструкції
]

for file in files_to_analyze:
    if file_exists(file):
        read_and_analyze(file)
```

**Аналіз стану та контексту:**

На основі аналізу я виявив:

**📊 Поточний стан системи:**
- Git: [статус змін, активна гілка]
- Docker: [статус контейнерів]
- Останні зміни: [опис останніх комітів]

**📋 Контекст з документації:**
- Поточна задача: [з TRANSFER_BRIEF.md]
- Останні дії: [з логів та документації]
- Критичні налаштування: [з CLAUDE.md]

**🔧 Необхідні дії для відновлення:**
1. [Конкретні кроки на основі аналізу]
2. [Потенційні проблеми та їх вирішення]
3. [Рекомендації по продовженню роботи]

Чи хочете, щоб я виконав автоматичне відновлення або маєте специфічні питання?

## Варіанти відновлення

**Швидке відновлення без змін:**
```
quick-recovery
```

**Повне відновлення з синхронізацією:**
```
full-recovery
```

**Відновлення з аналізом змін:**
```
recovery-with-analysis
```

**Відновлення після критичного збою:**
```
emergency-recovery
```

## Claude Code відповідає на варіанти:

### quick-recovery:
```bash
echo "=== Quick Recovery Process ==="

# Мінімальна діагностика
git status --porcelain
docker-compose ps --format="table {{.Name}}\t{{.Status}}"

# Перевірка критичних сервісів
if docker-compose ps | grep -q "Up"; then
    echo "✅ Система працює"
else
    echo "⚠️ Потрібен перезапуск контейнерів"
    docker-compose up -d
fi

# Завантаження останнього контексту
echo "📋 Останній контекст:"
tail -20 TRANSFER_BRIEF.md 2>/dev/null || echo "Transfer brief не знайдено"

echo "✅ Швидке відновлення завершено"
```

### full-recovery:
```bash
echo "=== Full Recovery Process ==="

# 1. Синхронізація з remote
git fetch origin
git status

# 2. Аналіз змін з останньої сесії
echo "=== Changes since last session ==="
git log --since="6 hours ago" --oneline

# 3. Перезапуск всіх сервісів
docker-compose down
docker-compose up -d --build

# 4. Перевірка авторизації Claude
claude auth status

# 5. Валідація системи
docker-compose logs --tail=20 claude_bot
docker exec claude-code-bot python -c "
from src.main import create_bot_application
print('✅ Application validated')
"

echo "✅ Повне відновлення завершено"
```

### recovery-with-analysis:
```bash
echo "=== Recovery with Deep Analysis ==="

# Детальний аналіз всіх змін
echo "1. Git Analysis:"
git log --graph --oneline --all -10

echo "2. File Changes Analysis:"
git diff --name-status HEAD~5..HEAD

echo "3. Recent Activity:"
ls -lt | head -10

echo "4. System Health:"
docker stats --no-stream
docker-compose logs --since=1h claude_bot | grep -i error

# Читання всіх ключових файлів
echo "5. Context Analysis:"
```

### emergency-recovery:
```bash
echo "=== Emergency Recovery Process ==="

# Backup поточного стану
backup_dir="emergency_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p backups/$backup_dir
cp -r data backups/$backup_dir/ 2>/dev/null
git stash push -m "Emergency backup before recovery"

# Повна перебудова
docker-compose down -v
docker system prune -f
docker-compose up -d --build --force-recreate

# Відновлення критичних налаштувань
if [ -f backups/latest_working/.env ]; then
    cp backups/latest_working/.env ./
    echo "✅ Відновлено конфігурацію"
fi

echo "🚨 Екстрене відновлення завершено"
```

## Автоматичний аналіз контексту

Після будь-якого відновлення Claude автоматично:

```python
# Завантаження та аналіз контексту
context_files = {
    'CLAUDE.md': 'project_instructions',
    'TRANSFER_BRIEF.md': 'current_state', 
    'README.md': 'project_overview',
    'DEPLOYMENT.md': 'deployment_info'
}

current_context = {}
for file, context_type in context_files.items():
    if file_exists(file):
        content = read_file(file)
        current_context[context_type] = analyze_content(content)

# Визначення поточного завдання
current_task = extract_current_task(current_context['current_state'])
pending_actions = extract_pending_actions(current_context)
system_status = check_system_status()

# Генерація звіту
generate_recovery_report(current_context, current_task, system_status)
```

## Інтелектуальне питання контексту

**Claude Code автоматично запитує:**

🤔 **Поточна ситуація потребує уваги:**
- Є незакомічені зміни в git - чи потрібно їх зберегти?
- Контейнер не працює - перезапустити?
- Знайдено застарілі налаштування - оновити?
- Останнє завдання: [опис] - продовжити роботу?

**Рекомендовані дії:**
1. `continue-task` - продовжити останнє завдання
2. `new-session` - почати нову роботу
3. `fix-issues` - спочатку виправити проблеми
4. `full-sync` - повна синхронізація

## Профілактичні перевірки

При кожному відновленні виконуються:

```bash
# Здоров'я системи
echo "=== Health Checks ==="
docker-compose ps | grep -v "Up" && echo "⚠️ Containers need attention"

# Дисковий простір
df -h | awk '$5 > 80 {print "⚠️ Disk space low: " $5 " used on " $6}'

# Авторизація
claude auth status || echo "⚠️ Claude authentication needed"

# Мережа
ping -c 1 google.com >/dev/null || echo "⚠️ Network connectivity issues"

# Логи на помилки
docker-compose logs --since=30m claude_bot 2>&1 | grep -i error | tail -5
```

## Коли використовувати
- ✅ Після п'ятигодинного обмеження Claude Code
- ✅ Після розриву з'єднання або перезапуску системи  
- ✅ При поверненні до роботи після перерви
- ✅ Після критичних збоїв системи
- ✅ При підозрі на втрату контексту
- ✅ Перед початком важливих задач

## Безпечні практики відновлення
- 🔒 Завжди створює backup перед змінами
- 📊 Аналізує всі системи перед продовженням роботи
- 🔍 Перевіряє цілісність даних та конфігурації
- 📝 Документує стан відновлення в логах
- ⚡ Пропонує варіанти дій на основі аналізу