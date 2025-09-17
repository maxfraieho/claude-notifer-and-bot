"""
DND Prompt Manager - Управління промптами для Do Not Disturb періоду
Дозволяє додавати, редагувати та зберігати промпти у markdown форматі
"""

import asyncio
import json
import os
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import structlog

logger = structlog.get_logger()

@dataclass
class DNDPrompt:
    """Структура DND промпту"""
    id: str
    title: str
    description: str
    prompt_content: str
    tags: List[str]
    priority: int  # 1-10, де 10 - найвищий
    created_at: str
    updated_at: str
    enabled: bool = True
    category: str = "general"
    estimated_duration: int = 30  # хвилини
    required_tools: List[str] = None
    
    def __post_init__(self):
        if self.required_tools is None:
            self.required_tools = []

class DNDPromptManager:
    """Менеджер для управління DND промптами"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.prompts_dir = data_dir / "dnd_prompts"
        self.prompts_dir.mkdir(exist_ok=True)
        
        self.config_file = self.prompts_dir / "config.json"
        self.prompts: Dict[str, DNDPrompt] = {}
        
        # Завантажити існуючі промпти
        asyncio.create_task(self.load_prompts())
    
    async def load_prompts(self) -> Dict[str, DNDPrompt]:
        """Завантажити всі промпти з файлів"""
        try:
            # Завантажити конфігурацію
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # Завантажити промпти з markdown файлів
            self.prompts = {}
            
            for md_file in self.prompts_dir.glob("*.md"):
                if md_file.name == "README.md":
                    continue
                    
                prompt = await self._load_prompt_from_markdown(md_file)
                if prompt:
                    self.prompts[prompt.id] = prompt
            
            logger.info(f"Завантажено {len(self.prompts)} DND промптів")
            return self.prompts
            
        except Exception as e:
            logger.error(f"Помилка завантаження промптів: {e}")
            return {}
    
    async def _load_prompt_from_markdown(self, file_path: Path) -> Optional[DNDPrompt]:
        """Завантажити промпт з markdown файлу"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Парсинг метаданих з YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    import yaml
                    metadata = yaml.safe_load(parts[1])
                    prompt_content = parts[2].strip()
                    
                    return DNDPrompt(
                        id=metadata.get('id', file_path.stem),
                        title=metadata.get('title', file_path.stem),
                        description=metadata.get('description', ''),
                        prompt_content=prompt_content,
                        tags=metadata.get('tags', []),
                        priority=metadata.get('priority', 5),
                        created_at=metadata.get('created_at', datetime.now().isoformat()),
                        updated_at=metadata.get('updated_at', datetime.now().isoformat()),
                        enabled=metadata.get('enabled', True),
                        category=metadata.get('category', 'general'),
                        estimated_duration=metadata.get('estimated_duration', 30),
                        required_tools=metadata.get('required_tools', [])
                    )
            
            # Якщо немає frontmatter, створити базовий промпт
            return DNDPrompt(
                id=file_path.stem,
                title=file_path.stem.replace('_', ' ').title(),
                description=f"Промпт з файлу {file_path.name}",
                prompt_content=content,
                tags=[],
                priority=5,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Помилка завантаження промпту з {file_path}: {e}")
            return None
    
    async def add_prompt(self, prompt: DNDPrompt) -> bool:
        """Додати новий промпт"""
        try:
            # Перевірити унікальність ID
            if prompt.id in self.prompts:
                logger.warning(f"Промпт з ID '{prompt.id}' вже існує")
                return False
            
            # Зберегти в пам'яті
            self.prompts[prompt.id] = prompt
            
            # Зберегти в файл
            await self._save_prompt_to_markdown(prompt)
            
            logger.info(f"Додано новий DND промпт: {prompt.title}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка додавання промпту: {e}")
            return False
    
    async def _save_prompt_to_markdown(self, prompt: DNDPrompt) -> None:
        """Зберегти промпт у markdown файл"""
        file_path = self.prompts_dir / f"{prompt.id}.md"
        
        # Створити YAML frontmatter
        metadata = {
            'id': prompt.id,
            'title': prompt.title,
            'description': prompt.description,
            'tags': prompt.tags,
            'priority': prompt.priority,
            'created_at': prompt.created_at,
            'updated_at': prompt.updated_at,
            'enabled': prompt.enabled,
            'category': prompt.category,
            'estimated_duration': prompt.estimated_duration,
            'required_tools': prompt.required_tools
        }
        
        import yaml
        frontmatter = yaml.dump(metadata, allow_unicode=True, default_flow_style=False)
        
        content = f"---\n{frontmatter}---\n\n{prompt.prompt_content}"
        
        file_path.write_text(content, encoding='utf-8')
    
    async def update_prompt(self, prompt_id: str, updates: Dict[str, Any]) -> bool:
        """Оновити існуючий промпт"""
        try:
            if prompt_id not in self.prompts:
                logger.warning(f"Промпт з ID '{prompt_id}' не знайдено")
                return False
            
            # Оновити промпт
            prompt = self.prompts[prompt_id]
            for key, value in updates.items():
                if hasattr(prompt, key):
                    setattr(prompt, key, value)
            
            prompt.updated_at = datetime.now().isoformat()
            
            # Зберегти зміни
            await self._save_prompt_to_markdown(prompt)
            
            logger.info(f"Оновлено DND промпт: {prompt.title}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка оновлення промпту: {e}")
            return False
    
    async def delete_prompt(self, prompt_id: str) -> bool:
        """Видалити промпт"""
        try:
            if prompt_id not in self.prompts:
                logger.warning(f"Промпт з ID '{prompt_id}' не знайдено")
                return False
            
            # Видалити з пам'яті
            del self.prompts[prompt_id]
            
            # Видалити файл
            file_path = self.prompts_dir / f"{prompt_id}.md"
            if file_path.exists():
                file_path.unlink()
            
            logger.info(f"Видалено DND промпт: {prompt_id}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка видалення промпту: {e}")
            return False
    
    async def get_prompt(self, prompt_id: str) -> Optional[DNDPrompt]:
        """Отримати промпт за ID"""
        return self.prompts.get(prompt_id)
    
    async def list_prompts(self, category: Optional[str] = None, 
                          enabled_only: bool = True) -> List[DNDPrompt]:
        """Отримати список промптів"""
        prompts = list(self.prompts.values())
        
        if enabled_only:
            prompts = [p for p in prompts if p.enabled]
        
        if category:
            prompts = [p for p in prompts if p.category == category]
        
        # Сортувати за пріоритетом
        return sorted(prompts, key=lambda p: (-p.priority, p.title))
    
    async def get_prompts_for_execution(self, max_duration: int = 120) -> List[DNDPrompt]:
        """Отримати промпти для виконання в DND період"""
        suitable_prompts = []
        
        for prompt in self.prompts.values():
            if (prompt.enabled and 
                prompt.estimated_duration <= max_duration):
                suitable_prompts.append(prompt)
        
        # Сортувати за пріоритетом
        return sorted(suitable_prompts, key=lambda p: -p.priority)
    
    async def create_sample_prompts(self) -> None:
        """Створити приклади промптів"""
        sample_prompts = [
            DNDPrompt(
                id="code_review_daily",
                title="Щоденне ревю коду",
                description="Автоматичний аналіз змін в коді за день",
                prompt_content="""Виконай комплексне ревю коду проекту:

1. Проаналізуй останні зміни в git репозиторії
2. Перевір код на відповідність стандартам
3. Знайди потенційні проблеми безпеки
4. Запропонуй покращення архітектури
5. Створи звіт з рекомендаціями

Використовуй команди:
- `git log --oneline --since="1 day ago"`
- `git diff HEAD~1..HEAD`
- Аналізуй файли через Read tool
- Створи markdown звіт з висновками""",
                tags=["code-review", "git", "analysis"],
                priority=8,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                category="code-quality",
                estimated_duration=45,
                required_tools=["Read", "Bash", "Write"]
            ),
            
            DNDPrompt(
                id="security_audit",
                title="Аудит безпеки",
                description="Перевірка системи на вразливості",
                prompt_content="""Проведи аудит безпеки проекту:

1. Сканування залежностей на відомі вразливості
2. Перевірка конфігураційних файлів
3. Аналіз authentication та authorization логіки
4. Перевірка input validation
5. Огляд логування та моніторингу

Створи детальний звіт з:
- Знайденими проблемами
- Рівнем критичності
- Планом усунення
- Рекомендаціями для покращення""",
                tags=["security", "audit", "vulnerabilities"],
                priority=9,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                category="security",
                estimated_duration=60,
                required_tools=["Read", "Bash", "Grep", "Write"]
            ),
            
            DNDPrompt(
                id="documentation_update",
                title="Оновлення документації",
                description="Автоматичне оновлення README та документації",
                prompt_content="""Оновлення проектної документації:

1. Проаналізуй поточний стан коду
2. Перевір актуальність README.md
3. Оновлення API документації
4. Перевір приклади коду в документації
5. Додай нові функції в документацію

Результат:
- Оновлений README.md
- Актуальна документація API
- Приклади використання
- Changelog з останніми змінами""",
                tags=["documentation", "readme", "api"],
                priority=6,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                category="documentation",
                estimated_duration=30,
                required_tools=["Read", "Write", "Edit"]
            ),
            
            DNDPrompt(
                id="performance_analysis",
                title="Аналіз продуктивності",
                description="Пошук bottlenecks та оптимізація",
                prompt_content="""Аналіз продуктивності системи:

1. Профілювання критичних частин коду
2. Аналіз database queries
3. Перевірка memory usage
4. Оптимізація алгоритмів
5. Рекомендації з покращення

Створи звіт з:
- Виявленими bottlenecks
- Метриками продуктивності
- Планом оптимізації
- Очікуваними покращеннями""",
                tags=["performance", "optimization", "profiling"],
                priority=7,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                category="optimization",
                estimated_duration=40,
                required_tools=["Read", "Bash", "Write"]
            )
        ]
        
        for prompt in sample_prompts:
            await self.add_prompt(prompt)
    
    async def export_prompts(self, file_path: Path) -> bool:
        """Експортувати всі промпти в JSON"""
        try:
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'prompts': [asdict(prompt) for prompt in self.prompts.values()]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Експортовано {len(self.prompts)} промптів в {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка експорту промптів: {e}")
            return False
    
    async def import_prompts(self, file_path: Path) -> int:
        """Імпортувати промпти з JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            for prompt_data in data.get('prompts', []):
                prompt = DNDPrompt(**prompt_data)
                if await self.add_prompt(prompt):
                    imported_count += 1
            
            logger.info(f"Імпортовано {imported_count} промптів з {file_path}")
            return imported_count
            
        except Exception as e:
            logger.error(f"Помилка імпорту промптів: {e}")
            return 0

async def create_default_readme(prompts_dir: Path) -> None:
    """Створити README для папки промптів"""
    readme_content = """# DND Prompts - Промпти для Do Not Disturb періоду

Ця папка містить промпти, які виконуються автоматично під час DND періоду (23:00-08:00).

## Структура файлів

Кожен промпт зберігається у окремому `.md` файлі з YAML frontmatter:

```yaml
---
id: unique_prompt_id
title: Назва промпту
description: Опис того, що робить промпт
tags: [tag1, tag2, tag3]
priority: 8  # 1-10, де 10 - найвищий пріоритет
created_at: 2025-01-15T10:30:00
updated_at: 2025-01-15T10:30:00
enabled: true
category: code-quality
estimated_duration: 45  # хвилини
required_tools: [Read, Write, Bash]
---

Тут йде сам промпт у markdown форматі...
```

## Категорії промптів

- **code-quality**: Ревю коду, рефакторинг
- **security**: Аудит безпеки, сканування вразливостей  
- **documentation**: Оновлення документації
- **optimization**: Аналіз продуктивності
- **testing**: Автоматизоване тестування
- **maintenance**: Технічне обслуговування

## Використання

Промпти автоматично виконуються системою scheduled prompts під час DND періоду.
Пріоритет виконання визначається полем `priority` (вищі цифри = вищий пріоритет).

## Додавання нових промптів

1. Створіть новий `.md` файл з унікальним ім'ям
2. Додайте YAML frontmatter з метаданими
3. Опишіть промпт у markdown форматі
4. Система автоматично підхопить новий промпт

## Приклади

Дивіться існуючі файли `.md` в цій папці для прикладів структури та формату.
"""
    
    readme_path = prompts_dir / "README.md"
    readme_path.write_text(readme_content, encoding='utf-8')