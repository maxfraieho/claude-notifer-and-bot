# Промпт: Відновлення контексту з Transfer Brief

## Опис процесу
Цей промпт автоматизує швидке відновлення контексту роботи на основі TRANSFER_BRIEF.md та інших документів проекту, забезпечуючи безперервність розробки між сесіями.

## Діалог з Claude Code

**Користувач:**
```
restore-context
```

**Claude Code відповідає:**
Я відновлю контекст роботи з документації проекту. Процес включає:

1. Читання та аналіз TRANSFER_BRIEF.md
2. Завантаження контексту з CLAUDE.md
3. Аналіз поточного стану git репозиторію
4. Перевірка статусу системи
5. Визначення поточних задач та пріоритетів
6. Підготовка до продовження роботи

Почнемо відновлення контексту:

*Виконує послідовність команд:*

```bash
# 1. Перевірка наявності ключових файлів
echo "=== Context Files Check ==="
ls -la TRANSFER_BRIEF.md CLAUDE.md README.md 2>/dev/null | grep -E '\.(md)$'

# 2. Базовий аналіз системи
git status --porcelain
docker-compose ps --format="table {{.Name}}\t{{.Status}}\t{{.RunningFor}}"
```

*Читає та аналізує документацію:*

**📋 Завантажений контекст:**

**Поточний стан проекту (з TRANSFER_BRIEF.md):**
- Останнє оновлення: [дата з файлу]
- Активні задачі: [список задач]
- Поточний прогрес: [статус виконання]
- Критичні примітки: [важливі нюанси]

**Конфігурація проекту (з CLAUDE.md):**
- Тип проекту: Claude Telegram Bot
- Основні команди: [команди розробки]
- Архітектурні особливості: [ключові моменти]

**Системний стан:**
- Git гілка: [поточна гілка]
- Незакомічені зміни: [кількість змін]
- Docker статус: [статус контейнерів]

**🎯 Ідентифіковані наступні кроки:**
1. [Конкретна задача з пріоритетом]
2. [Наступна задача]
3. [Потенційні проблеми для перевірки]

Готовий продовжити роботу. Що саме потрібно зробити?

## Варіанти відновлення контексту

**Швидке відновлення тільки з brief:**
```
quick-context
```

**Повне відновлення з аналізом змін:**
```
deep-context-restore
```

**Відновлення з перевіркою стану системи:**
```
context-with-health-check
```

**Відновлення для нової задачі:**
```
context-for-new-task
```

## Claude Code відповідає на варіанти:

### quick-context:
```bash
echo "=== Quick Context Restoration ==="

# Читання тільки критичних файлів
echo "📋 Current Brief:"
tail -20 TRANSFER_BRIEF.md 2>/dev/null | head -10

echo "⚡ Quick Status:"
git branch --show-current
git status --porcelain | wc -l && echo "uncommitted changes"
docker-compose ps --format "{{.Name}}: {{.Status}}" | head -3

echo "✅ Quick context loaded"
```

### deep-context-restore:
*Виконує повний аналіз всіх доступних файлів контексту:*

```python
# Читання та аналіз всіх контекстних файлів
context_files = [
    'TRANSFER_BRIEF.md',
    'CLAUDE.md', 
    'README.md',
    'DEPLOYMENT.md'
]

for file in context_files:
    analyze_file_for_context(file)

# Аналіз останніх змін
recent_commits = get_recent_commits(limit=10)
modified_files = get_modified_files()
system_state = check_full_system_state()

# Генерація повного контексту
generate_comprehensive_context_report()
```

**Детальний звіт відновлення:**
- 📊 Повна картина проекту
- 🔍 Аналіз останніх змін
- ⚠️ Виявлені потенційні проблеми
- 📈 Рекомендації по продовженню

### context-with-health-check:
```bash
echo "=== Context Restore + Health Check ==="

# Відновлення контексту
echo "1. Loading context..."
head -30 TRANSFER_BRIEF.md

# Перевірка здоров'я системи
echo "2. System health check..."
docker-compose ps
docker exec claude-code-bot claude auth status 2>/dev/null || echo "⚠️ Claude auth needs attention"

# Перевірка критичних сервісів
echo "3. Service validation..."
curl -s http://localhost:8080/health 2>/dev/null || echo "ℹ️ Health endpoint not available"

# Аналіз ресурсів
echo "4. Resource check..."
df -h | grep -E '(8[0-9]|9[0-9])%' && echo "⚠️ Low disk space detected"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo "✅ Context restored with health validation"
```

### context-for-new-task:
```bash
echo "=== Context for New Task ==="

# Базовий контекст
echo "📋 Project Overview:"
head -15 README.md

# Поточний стан для нової задачі
echo "🔧 Ready for new development:"
echo "- Branch: $(git branch --show-current)"
echo "- Clean state: $(git status --porcelain | wc -l) pending changes"
echo "- Services: $(docker-compose ps --format "{{.Status}}" | grep -c "Up") running"

# Рекомендації
echo "💡 Ready to:"
echo "  • Створити нову feature branch"
echo "  • Продовжити поточну роботу"
echo "  • Виправити критичні issues"

echo "Що плануєте робити?"
```

## Інтелектуальний аналіз контексту

Claude автоматично аналізує та екстрактує:

```python
def extract_context_intelligence(transfer_brief_content):
    """Розумний аналіз Transfer Brief для відновлення контексту"""
    
    # Пошук активних задач
    active_tasks = extract_section(content, "## Активні задачі")
    current_priorities = extract_section(content, "## Пріоритети")
    
    # Аналіз технічного стану
    tech_issues = find_patterns(content, r"(ERROR|FIXME|TODO|BLOCKER)")
    next_steps = extract_section(content, "## Наступні кроки")
    
    # Визначення контексту
    project_phase = determine_project_phase(content)
    urgency_level = assess_urgency(active_tasks, tech_issues)
    
    return {
        'active_tasks': prioritize_tasks(active_tasks),
        'technical_context': analyze_tech_state(),
        'immediate_actions': generate_action_plan(next_steps),
        'risk_factors': identify_risks(tech_issues),
        'continuation_point': find_continuation_point()
    }
```

## Автоматичні підказки

На основі аналізу Claude надає конкретні рекомендації:

**🎯 Рекомендовані дії:**
- `continue-feature-X` - продовжити розробку функції X
- `fix-critical-issue` - виправити критичну проблему  
- `deploy-updates` - застосувати готові оновлення
- `test-recent-changes` - протестувати останні зміни

**⚠️ Потребує уваги:**
- Незакомічені зміни потребують review
- Контейнер не відповідає - можливо потрібен перезапуск
- Авторизація Claude застаріла

## Контекстні запитання

Claude може запитати для уточнення:

**🤔 Уточнюючі запитання:**
- Продовжити роботу над [останньою задачею] або почати нову?
- Чи потрібно спочатку виправити [знайдену проблему]?
- Застосувати [незакомічені зміни] або створити новий commit?
- Оновити документацію перед продовженням розробки?

## Швидкі команди відновлення

**Інтерактивні опції після відновлення контексту:**
```bash
# Швидкі дії доступні після restore-context
echo "Quick actions available:"
echo "  'continue' - продовжити останню задачу"
echo "  'status' - детальний стан системи"  
echo "  'clean' - очистити та підготувати середовище"
echo "  'deploy' - застосувати зміни"
echo "  'test' - запустити тести"
```

## Відновлення в критичних ситуаціях

**Якщо TRANSFER_BRIEF.md недоступний:**
```bash
echo "=== Emergency Context Recovery ==="

# Відновлення з git логів
git log --oneline -10 | while read commit; do
    echo "Recent: $commit"
done

# Аналіз файлів проекту
echo "Modified files analysis:"
find . -mtime -1 -type f -not -path "./.git/*" | head -10

# Перевірка backup файлів
ls -la backups/*/TRANSFER_BRIEF.md 2>/dev/null | tail -1
```

**Відновлення з emergency backup:**
```bash
# Пошук останнього робочого стану
latest_backup=$(ls -t backups/*/TRANSFER_BRIEF.md 2>/dev/null | head -1)
if [ -n "$latest_backup" ]; then
    echo "Found backup context: $latest_backup"
    cat "$latest_backup"
fi
```

## Коли використовувати
- 🌅 На початку нової робочої сесії
- 🔄 Після перерви у розробці
- 👥 При передачі проекту між розробниками
- 🚨 Після критичних збоїв системи
- 📅 При поверненні до проекту через час
- 🎯 Перед початком нової функціональності

## Метрики успішного відновлення
- ✅ Всі критичні файли прочитані
- ✅ Системний стан перевірений
- ✅ Активні задачі ідентифіковані
- ✅ Наступні кроки визначені
- ✅ Потенційні проблеми виявлені
- ✅ Готовність до продовження роботи підтверджена