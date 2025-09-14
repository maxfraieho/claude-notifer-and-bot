# Промпт: Збереження стану розробки та контексту

## Опис процесу
Цей промпт автоматизує процес збереження поточного стану розробки, включаючи оновлення TRANSFER_BRIEF.md, CLAUDE.md та створення snapshot поточного діалогу для забезпечення безперервності роботи.

## Діалог з Claude Code

**Користувач:**
```
save-state
```

**Claude Code відповідає:**
Я створю повний snapshot поточного стану розробки. Процес включає:

1. Аналіз поточного стану git репозиторію
2. Збір інформації про активні задачі та прогрес
3. Оновлення TRANSFER_BRIEF.md з поточним станом
4. Оновлення CLAUDE.md з новими інструкціями (при необхідності)
5. Створення backup конфігурації та даних
6. Експорт поточного діалогу
7. Документування наступних кроків

Почнемо збереження стану:

*Виконує послідовність команд:*

```bash
# 1. Аналіз поточного стану git
echo "=== Current Git State ==="
git status --porcelain
git log --oneline -5
git branch --show-current

# 2. Збір системної інформації
echo "=== System State ==="
docker-compose ps --format="table {{.Name}}\t{{.Status}}\t{{.RunningFor}}"
docker exec claude-code-bot claude auth status 2>/dev/null || echo "Claude auth: Not available"

# 3. Перевірка критичних файлів
ls -la .env CLAUDE.md TRANSFER_BRIEF.md README.md 2>/dev/null
```

*Аналізує поточну роботу та контекст:*

**📊 Поточний стан системи:**
- Активна гілка: [назва гілки]
- Незакомічені зміни: [кількість файлів]
- Статус контейнерів: [статус Docker]
- Останні коміти: [останні 3 коміти]

**📝 Активні задачі та прогрес:**
[На основі аналізу todo lists, uncommitted changes, recent commits]

Тепер я оновлю документацію стану проекту:

*Оновлює TRANSFER_BRIEF.md:*

```markdown
# TRANSFER_BRIEF.md Update

## Поточний стан проекту ($(date))

### Активні задачі
- [Поточна задача з деталями]
- [Прогрес виконання]

### Останні зміни  
- [Опис останніх змін в коді]
- [Файли які були модифіковані]

### Системний стан
- Git branch: [branch]
- Docker status: [status] 
- Claude auth: [status]

### Наступні кроки
1. [Конкретні наступні дії]
2. [Пріоритети]
3. [Потенційні проблеми]

### Технічні нотатки
- [Важливі технічні деталі]
- [Конфігурації які потрібно пам'ятати]
```

**✅ Стан збережено успішно:**
- TRANSFER_BRIEF.md оновлено
- Створено backup поточної конфігурації
- Зафіксовано стан системи
- Документовано наступні кроки

Чи потрібно створити коміт з поточними змінами або експортувати діалог?

## Варіанти збереження стану

**Швидке збереження без коміту:**
```
quick-save
```

**Повне збереження з комітом:**
```
save-and-commit
```

**Збереження критичного стану:**
```
emergency-save
```

**Планове збереження в кінці сесії:**
```
session-end-save
```

## Claude Code відповідає на варіанти:

### quick-save:
```bash
echo "=== Quick State Save ==="

# Швидке оновлення transfer brief
cat > TRANSFER_BRIEF_SNAPSHOT.md << EOF
# Quick State Snapshot - $(date)

## Current Status
- Branch: $(git branch --show-current)
- Uncommitted changes: $(git status --porcelain | wc -l) files
- Last commit: $(git log -1 --pretty=format:"%h %s")
- Docker: $(docker-compose ps --format="{{.Status}}" claude_bot 2>/dev/null || echo "Not running")

## Active Work
[Описати поточну роботу основними пунктами]

## Next Actions
[Список наступних дій]

## Notes
[Важливі нотатки для продовження]
EOF

echo "✅ Quick snapshot created: TRANSFER_BRIEF_SNAPSHOT.md"
```

### save-and-commit:
```bash
echo "=== Save State with Commit ==="

# Оновлення основного transfer brief
# [Детальне оновлення TRANSFER_BRIEF.md з повною інформацією]

# Створення коміту з current state
git add TRANSFER_BRIEF.md
git add CLAUDE.md  # якщо було оновлено
git commit -m "docs: update project state and transfer brief

- Current development status saved
- Next steps documented  
- System state captured

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

echo "✅ State saved and committed to git"
```

### emergency-save:
```bash
echo "=== Emergency State Save ==="

# Створення повного backup
emergency_dir="emergency_state_$(date +%Y%m%d_%H%M%S)"
mkdir -p backups/$emergency_dir

# Backup всіх критичних файлів
cp TRANSFER_BRIEF.md backups/$emergency_dir/ 2>/dev/null
cp CLAUDE.md backups/$emergency_dir/ 2>/dev/null  
cp .env backups/$emergency_dir/ 2>/dev/null
cp -r data backups/$emergency_dir/ 2>/dev/null

# Git stash з поточними змінами
git stash push -m "Emergency state save - $(date)"

# Створення emergency brief
cat > EMERGENCY_TRANSFER_BRIEF.md << EOF
# EMERGENCY STATE SAVE - $(date)

## Critical Information
[Найважливіша інформація для продовження роботи]

## System State Before Emergency
- Git: $(git stash list | head -1)
- Docker: $(docker-compose ps --format="{{.Status}}")
- Files backed up to: backups/$emergency_dir/

## Recovery Instructions
1. Restore from backups/$emergency_dir/
2. Apply git stash if needed: git stash pop
3. Restart containers: docker-compose up -d

## Emergency Context
[Що саме призвело до emergency save]
EOF

echo "🚨 Emergency state saved to backups/$emergency_dir/"
echo "📝 Recovery instructions in EMERGENCY_TRANSFER_BRIEF.md"
```

### session-end-save:
```bash
echo "=== End of Session State Save ==="

# Детальний аналіз всієї сесії
session_summary="SESSION_SUMMARY_$(date +%Y%m%d_%H%M).md"

cat > $session_summary << EOF
# Development Session Summary - $(date)

## Session Overview
- Duration: [час роботи]
- Main objectives: [основні цілі сесії]
- Achievements: [що було досягнуто]

## Code Changes
$(git diff --stat HEAD~5..HEAD 2>/dev/null || echo "No recent changes")

## Files Modified
$(git diff --name-only HEAD~5..HEAD 2>/dev/null || echo "No files modified")

## Commits Made
$(git log --oneline --since="4 hours ago" || echo "No commits")

## System State
- Branch: $(git branch --show-current)
- Status: $(git status --porcelain | wc -l) uncommitted changes
- Docker: $(docker-compose ps --format="{{.Status}}" 2>/dev/null)

## Next Session Preparation
### Priority Tasks
1. [Найважливіші задачі на наступну сесію]
2. [Continuation points]

### Environment Notes  
- [Важливі налаштування для збереження]
- [Potential issues to watch for]

### Context for Next Claude
- [Key information for new Claude instance]
- [Project state and objectives]
EOF

# Оновлення основного TRANSFER_BRIEF
# [Повне оновлення з усією інформацією сесії]

echo "✅ Session state saved to $session_summary"
echo "📋 TRANSFER_BRIEF.md updated for next session"
```

## Автоматичне визначення стану

Claude автоматично аналізує:

```python
def analyze_current_state():
    state = {
        'git_status': check_git_status(),
        'docker_status': check_docker_status(),
        'recent_activity': analyze_recent_changes(),
        'active_tasks': extract_current_tasks(),
        'system_health': check_system_health(),
        'critical_files': check_critical_files()
    }
    
    # Визначення пріоритетів для збереження
    priorities = determine_save_priorities(state)
    
    # Генерація контексту для наступної сесії
    next_session_context = generate_session_context(state, priorities)
    
    return {
        'current_state': state,
        'save_priorities': priorities,
        'next_context': next_session_context
    }
```

## Структура збереженого стану

### TRANSFER_BRIEF.md розділи:
```markdown
## Поточний стан проекту
- Дата та час збереження
- Активна гілка та коміти
- Статус системи

## Активні задачі
- Поточна робота 
- Прогрес виконання
- Заблоковані задачі

## Технічні деталі
- Конфігурація середовища
- Критичні налаштування
- Відомі проблеми

## Наступні кроки
- Пріоритетні задачі
- План дій
- Потенційні ризики

## Контекст для наступної сесії
- Що потрібно пам'ятати
- Важливі файли
- Команди для швидкого старту
```

## Коли використовувати
- 🕐 Перед закінченням робочої сесії
- 🚨 При критичних змінах або помилках
- ⏰ Перед досягненням 5-годинного ліміту  
- 🔄 Після важливих milestone в розробці
- 🛑 При необхідності переривання роботи
- 📱 Перед перемиканням на інші задачі

## Автоматичні тригери збереження
- Відслідковування часу сесії (попередження за 30 хв до ліміту)
- Детекція критичних операцій (деплой, міграції)
- Моніторинг системних помилок
- Великі зміни в коді (>10 файлів модифіковано)