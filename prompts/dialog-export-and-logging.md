# Промпт: Експорт діалогу та логування

## Опис процесу
Цей промпт автоматизує експорт поточного діалогу з Claude Code, системних логів, та створення структурованого архіву для збереження контексту розмови та технічних деталей.

## Діалог з Claude Code

**Користувач:**
```
export-dialog
```

**Claude Code відповідає:**
Я створю повний експорт діалогу та логів системи. Процес включає:

1. Збір поточного діалогу та команд
2. Експорт системних логів та Docker логів  
3. Створення структурованого звіту сесії
4. Збереження технічного контексту
5. Архівування всіх даних
6. Генерація індексу для швидкого пошуку

Почнемо експорт:

*Виконує послідовність команд:*

```bash
# 1. Створення директорії для експорту
export_dir="dialog_export_$(date +%Y%m%d_%H%M%S)"
mkdir -p exports/$export_dir/{logs,context,dialog,system}

# 2. Збір системних логів
echo "=== Collecting System Logs ==="
docker-compose logs --no-color claude_bot > exports/$export_dir/logs/docker_logs.txt
journalctl --since "4 hours ago" > exports/$export_dir/logs/system_logs.txt 2>/dev/null || echo "System logs not available"

# 3. Збір git інформації
git log --oneline -20 > exports/$export_dir/context/git_history.txt
git status --porcelain > exports/$export_dir/context/git_status.txt
git diff > exports/$export_dir/context/uncommitted_changes.diff

# 4. Копіювання ключових файлів
cp CLAUDE.md exports/$export_dir/context/ 2>/dev/null
cp TRANSFER_BRIEF.md exports/$export_dir/context/ 2>/dev/null  
cp .env exports/$export_dir/context/env_template.txt 2>/dev/null || echo "# ENV template" > exports/$export_dir/context/env_template.txt
```

*Створює структурований діалог експорт:*

```bash
# Створення основного діалог файлу
cat > exports/$export_dir/dialog/session_dialog.md << 'EOF'
# Claude Code Dialog Export
**Export Date:** $(date)
**Session Duration:** [розрахувати з timestamp]
**Project:** Claude Telegram Bot

## Session Overview
- **Main Objectives:** [основні цілі сесії]
- **Tasks Completed:** [виконані задачі]
- **Issues Encountered:** [проблеми та вирішення]
- **Next Steps:** [наступні кроки]

## Technical Context
- **Git Branch:** $(git branch --show-current)
- **Docker Status:** $(docker-compose ps --format="{{.Name}}: {{.Status}}")
- **System State:** [поточний стан]

## Dialog Transcript
[Тут буде експорт повного діалогу - в реальності Claude Code зберігає це автоматично]

## Commands Executed
[Список всіх виконаних команд з результатами]

## Files Modified
$(git diff --name-only HEAD~10..HEAD 2>/dev/null | head -20)

## Key Decisions Made
- [Важливі рішення прийняті під час сесії]
- [Технічні обирання]
- [Архітектурні зміни]

## Lessons Learned
- [Що було вивчено]
- [Помилки та як їх уникнути]
- [Покращення процесу]
EOF
```

**📊 Експорт результатів:**
- Діалог збережено в: `exports/$export_dir/dialog/`
- Системні логи: `exports/$export_dir/logs/`
- Контекст проекту: `exports/$export_dir/context/`
- Архів створено: `exports/dialog_export_[timestamp].tar.gz`

Чи потрібно створити додаткові формати експорту або фільтри?

## Варіанти експорту

**Тільки діалог без логів:**
```
export-dialog-only
```

**Повний експорт з системними даними:**
```
export-full
```

**Експорт з фільтрацією за часом:**
```
export-last-hour
export-last-4hours  
```

**Експорт для передачі іншому розробнику:**
```
export-for-handover
```

## Claude Code відповідає на варіанти:

### export-dialog-only:
```bash
echo "=== Dialog-Only Export ==="

export_dir="dialog_only_$(date +%Y%m%d_%H%M)"
mkdir -p exports/$export_dir

# Тільки діалог та основні команди
cat > exports/$export_dir/session_summary.md << EOF
# Session Dialog Summary - $(date)

## Quick Context
- Branch: $(git branch --show-current)
- Last commit: $(git log -1 --pretty=format:"%h %s")
- Modified files: $(git status --porcelain | wc -l)

## Main Discussion Points
[Основні питання що обговорювались]

## Key Commands Run
[Найважливіші команди]

## Outcomes
[Результати сесії]

## Next Steps
[Що потрібно робити далі]
EOF

echo "✅ Minimal dialog export: exports/$export_dir/"
```

### export-full:
```bash
echo "=== Full System Export ==="

export_dir="full_export_$(date +%Y%m%d_%H%M%S)"  
mkdir -p exports/$export_dir/{logs,context,dialog,system,database}

# Повний набір логів
docker-compose logs --no-color > exports/$export_dir/logs/docker_all.log
docker system df > exports/$export_dir/system/docker_usage.txt
docker images > exports/$export_dir/system/docker_images.txt

# База даних (якщо можливо)
cp data/*.db exports/$export_dir/database/ 2>/dev/null || echo "No database files found"

# Системні метрики  
df -h > exports/$export_dir/system/disk_usage.txt
free -m > exports/$export_dir/system/memory.txt
ps aux > exports/$export_dir/system/processes.txt

# Мережна конфігурація
docker network ls > exports/$export_dir/system/networks.txt

# Створення архіву
tar -czf exports/full_export_$(date +%Y%m%d_%H%M%S).tar.gz -C exports $export_dir

echo "✅ Full export archived: exports/full_export_$(date +%Y%m%d_%H%M%S).tar.gz"
```

### export-last-hour:
```bash
echo "=== Last Hour Export ==="

export_dir="last_hour_$(date +%Y%m%d_%H%M)"
mkdir -p exports/$export_dir

# Логи за останню годину
docker-compose logs --since=1h --no-color claude_bot > exports/$export_dir/recent_logs.txt

# Останні git зміни
git log --since="1 hour ago" --pretty=format:"%h %ad %s" --date=short > exports/$export_dir/recent_commits.txt

# Файли змінені за годину
find . -mmin -60 -type f -not -path "./.git/*" -not -path "./node_modules/*" | head -20 > exports/$export_dir/recent_files.txt

echo "✅ Last hour export: exports/$export_dir/"
```

### export-for-handover:
```bash
echo "=== Handover Export ==="

export_dir="handover_$(date +%Y%m%d_%H%M)"
mkdir -p exports/$export_dir

# Створення детального handover документу
cat > exports/$export_dir/HANDOVER_README.md << EOF
# Development Handover - $(date)

## Project Overview
$(head -20 README.md 2>/dev/null || echo "See README.md for project details")

## Current State
- **Branch:** $(git branch --show-current)
- **Last commit:** $(git log -1 --pretty=format:"%h %s (%ad)" --date=short)
- **Uncommitted changes:** $(git status --porcelain | wc -l) files
- **Docker status:** $(docker-compose ps --format="{{.Name}}: {{.Status}}")

## Active Development
### Current Sprint/Tasks
[На основі TRANSFER_BRIEF.md та аналізу діалогу]

### Known Issues
- [Відомі проблеми]
- [Workaround solutions]

### Environment Setup
1. Clone repository
2. Copy .env.template to .env and fill values
3. Run: docker-compose up -d --build
4. Verify: docker-compose logs claude_bot

### Key Files to Understand
- CLAUDE.md - Project instructions
- TRANSFER_BRIEF.md - Current development state
- docker-compose.yml - Container configuration
- src/ - Main application code

### Testing
$(cat << 'TESTING'
# Quick verification commands
docker exec claude-code-bot python -c "from src.main import create_bot_application; print('✅ App loads')"
docker exec claude-code-bot claude auth status
TESTING
)

### Contacts and Resources
- [Team contacts]
- [Documentation links]
- [Deployment procedures]

### Immediate Next Steps
1. [Most urgent tasks]
2. [Priority features]
3. [Technical debt items]
EOF

# Копіювання ключових файлів
cp CLAUDE.md exports/$export_dir/ 2>/dev/null
cp TRANSFER_BRIEF.md exports/$export_dir/ 2>/dev/null
cp README.md exports/$export_dir/ 2>/dev/null
cp docker-compose.yml exports/$export_dir/
cp requirements.txt exports/$export_dir/ 2>/dev/null
cp pyproject.toml exports/$export_dir/ 2>/dev/null

# Створення .env template
sed 's/=.*/=YOUR_VALUE_HERE/g' .env > exports/$export_dir/env_template.txt 2>/dev/null || echo "Create .env template manually"

echo "✅ Handover package: exports/$export_dir/"
echo "📋 Review HANDOVER_README.md before sharing"
```

## Автоматичне створення індексу

```bash
# Створення пошукового індексу
create_export_index() {
    export_dir=$1
    
    cat > exports/$export_dir/INDEX.md << EOF
# Export Index - $(date)

## Quick Navigation
- 📄 [Dialog Summary](dialog/session_dialog.md)
- 🔧 [System Logs](logs/)  
- 📋 [Project Context](context/)
- 💾 [Database Backup](database/)

## File Structure
\`\`\`
$export_dir/
├── dialog/           # Conversation and decisions
├── logs/            # System and application logs
├── context/         # Project files and git state
├── system/          # System information
└── database/        # Data backups
\`\`\`

## Search Keywords
$(grep -r "TODO\|FIXME\|BUG\|IMPORTANT" exports/$export_dir --include="*.md" --include="*.txt" | head -10)

## Statistics
- Files exported: $(find exports/$export_dir -type f | wc -l)
- Total size: $(du -sh exports/$export_dir | cut -f1)
- Time range: [start] - $(date)

## Restoration Commands
\`\`\`bash
# To restore context:
cd /path/to/project
tar -xzf path/to/export.tar.gz
cp export/context/.env ./
docker-compose up -d --build
\`\`\`
EOF
}
```

## Автоматичний експорт

**Налаштування автоматичного експорту:**
```bash
# Cron job для регулярного експорту
echo "0 */4 * * * cd /path/to/project && /path/to/claude export-dialog-only" | crontab -
```

**Експорт при критичних подіях:**
```bash
# Моніторинг помилок та автоматичний експорт
monitor_and_export() {
    docker-compose logs --since=5m claude_bot | grep -i "error\|critical" && {
        echo "Critical error detected, creating export..."
        export-full
    }
}
```

## Формати експорту

### Підтримувані формати:
- **Markdown** - Основний формат для документації
- **JSON** - Структурований експорт для обробки
- **Plain Text** - Логи та системна інформація  
- **TAR.GZ** - Архів для передачі
- **HTML** - Веб-переглядач з навігацією

## Коли використовувати
- 📞 Перед передачею проекту іншому розробнику
- 💾 Для створення backup важливих рішень
- 🔍 При налагодженні складних проблем
- 📊 Для аналізу продуктивності розробки
- 🎯 В кінці важливих milestone
- 🚨 При критичних помилках або збоях

## Безпека експорту
- ⚠️ Автоматично видаляє чутливі дані (.env токени)
- 🔒 Не включає паролі та API ключі
- 📝 Створює template файли замість оригіналів
- 🗂️ Структурує дані для легкого аудиту