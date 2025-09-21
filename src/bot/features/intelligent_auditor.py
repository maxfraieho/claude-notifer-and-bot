#!/usr/bin/env python3
"""
Intelligent Telegram Bot Auditor - поєднує статичний аналіз з Claude CLI інтелектом
Виявляє структурні, логічні та архітектурні проблеми в Telegram ботах
"""

import ast
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class AuditIssue:
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    file_path: str
    line_number: int
    description: str
    code_snippet: str = ""
    fix_suggestion: str = ""
    claude_analysis: str = ""  # Додатковий аналіз від Claude
    group: str = ""  # Група проблем для batch fixing

@dataclass
class AuditResult:
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    issues: List[AuditIssue]
    claude_summary: str = ""
    recommendations: List[str] = None

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []

class IntelligentTelegramBotAuditor:
    """Розумний аудитор для Telegram ботів з Claude CLI інтеграцією"""

    def __init__(self, project_root: str, claude_integration=None):
        self.project_root = Path(project_root)
        self.claude_integration = claude_integration
        self.issues: List[AuditIssue] = []

        # Дані для аналізу
        self.translation_keys: Dict[str, Set[str]] = {}
        self.callback_handlers: Set[str] = set()
        self.button_callbacks: Set[str] = set()
        self.used_translation_keys: Set[str] = set()
        self.command_handlers: Set[str] = set()

        # Конфігурація аналізу
        self.analysis_config = {
            "enable_claude_analysis": True,
            "claude_analysis_threshold": "HIGH",  # Мінімальна серйозність для Claude аналізу
            "group_similar_issues": True,
            "max_claude_calls": 10  # Обмеження викликів Claude
        }

    async def run_audit(self, focus_area: Optional[str] = None) -> AuditResult:
        """Запустити повний аудит з Claude інтеграцією"""
        logger.info("Starting intelligent bot audit", project_root=str(self.project_root), focus_area=focus_area)

        # 1. Статичний аналіз (на базі існуючого скрипта)
        await self._run_static_analysis(focus_area)

        # 2. Групування схожих проблем
        if self.analysis_config["group_similar_issues"]:
            self._group_similar_issues()

        # 3. Claude інтелектуальний аналіз
        if self.analysis_config["enable_claude_analysis"] and self.claude_integration:
            await self._run_claude_analysis()

        # 4. Генерація рекомендацій
        recommendations = await self._generate_recommendations()

        # 5. Підготовка результату
        result = self._prepare_audit_result(recommendations)

        logger.info("Audit completed",
                   total_issues=result.total_issues,
                   critical=result.critical_count,
                   high=result.high_count)

        return result

    async def _run_static_analysis(self, focus_area: Optional[str] = None):
        """Запустити статичний аналіз коду"""
        logger.info("Running static analysis")

        # Завантажити переклади
        self._load_translation_keys()

        # Знайти всі Python файли
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            try:
                await self._analyze_python_file(file_path, focus_area)
            except Exception as e:
                self.issues.append(AuditIssue(
                    category="PARSING_ERROR",
                    severity="HIGH",
                    file_path=str(file_path),
                    line_number=0,
                    description=f"Помилка парсингу файлу: {e}",
                    group="parsing_errors"
                ))

        # Спеціальні перевірки
        self._audit_callback_coverage()
        self._audit_translation_coverage()
        self._audit_architecture_issues()

    def _should_skip_file(self, file_path: Path) -> bool:
        """Перевірити чи потрібно пропустити файл"""
        skip_patterns = ["venv", "__pycache__", ".git", "node_modules", ".pytest_cache"]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    async def _analyze_python_file(self, file_path: Path, focus_area: Optional[str] = None):
        """Проаналізувати один Python файл"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            tree = ast.parse(content)

            # Різні типи аналізу залежно від focus_area
            if not focus_area or focus_area == "callbacks":
                self._check_callback_handlers(tree, file_path, lines)
                self._check_button_callback_consistency(tree, file_path, lines)

            if not focus_area or focus_area == "localization":
                self._check_translation_usage(tree, file_path, lines)
                self._check_hardcoded_strings(file_path, lines)

            if not focus_area or focus_area == "security":
                self._check_security_issues(tree, file_path, lines)

            if not focus_area or focus_area == "architecture":
                self._check_architecture_patterns(tree, file_path, lines)

        except Exception as e:
            logger.error("Failed to analyze file", file_path=str(file_path), error=str(e))

    def _check_callback_handlers(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити callback handlers (розширена версія)"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.endswith('_callback') or 'callback' in node.name:
                    self.callback_handlers.add(node.name)

                    # Перевірити чи є await query.answer()
                    has_answer = False
                    for subnode in ast.walk(node):
                        if (isinstance(subnode, ast.Call) and
                            isinstance(subnode.func, ast.Attribute) and
                            subnode.func.attr == 'answer'):
                            has_answer = True
                            break

                    if not has_answer:
                        self.issues.append(AuditIssue(
                            category="CALLBACK_NO_ANSWER",
                            severity="MEDIUM",
                            file_path=str(file_path),
                            line_number=getattr(node, 'lineno', 0),
                            description=f"Callback {node.name} не викликає query.answer()",
                            code_snippet=lines[getattr(node, 'lineno', 1) - 1] if lines else "",
                            fix_suggestion="Додати await query.answer() на початок callback функції",
                            group="callback_missing_answer"
                        ))

    def _check_security_issues(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити проблеми безпеки"""
        for node in ast.walk(tree):
            # Перевірити SQL injection можливості
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Attribute) and
                    node.func.attr in ['execute', 'query']):

                    # Перевірити чи використовується string formatting в SQL
                    for arg in node.args:
                        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                            self.issues.append(AuditIssue(
                                category="SQL_INJECTION_RISK",
                                severity="CRITICAL",
                                file_path=str(file_path),
                                line_number=getattr(node, 'lineno', 0),
                                description="Можливий SQL injection через string formatting",
                                code_snippet=lines[getattr(node, 'lineno', 1) - 1] if lines else "",
                                fix_suggestion="Використовувати parameterized queries",
                                group="security_sql"
                            ))

    def _check_architecture_patterns(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити архітектурні паттерни"""
        # Перевірити великі функції
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = getattr(node, 'end_lineno', 0) - getattr(node, 'lineno', 0)
                if func_lines > 50:
                    self.issues.append(AuditIssue(
                        category="LARGE_FUNCTION",
                        severity="MEDIUM",
                        file_path=str(file_path),
                        line_number=getattr(node, 'lineno', 0),
                        description=f"Функція {node.name} занадто велика ({func_lines} рядків)",
                        fix_suggestion="Розбити функцію на менші частини",
                        group="architecture_large_functions"
                    ))

    def _group_similar_issues(self):
        """Групувати схожі проблеми для batch вирішення"""
        groups = defaultdict(list)

        for issue in self.issues:
            if issue.group:
                groups[issue.group].append(issue)

        # Оновити описи для груп
        for group_name, group_issues in groups.items():
            if len(group_issues) > 1:
                for issue in group_issues:
                    issue.description = f"[ГРУПА: {len(group_issues)} схожих] {issue.description}"

    async def _run_claude_analysis(self):
        """Запустити інтелектуальний аналіз через Claude CLI"""
        if not self.claude_integration:
            logger.warning("Claude integration not available for intelligent analysis")
            return

        # Вибрати проблеми для Claude аналізу
        high_priority_issues = [
            issue for issue in self.issues
            if issue.severity in ["CRITICAL", "HIGH"]
        ][:self.analysis_config["max_claude_calls"]]

        logger.info("Running Claude analysis", issues_count=len(high_priority_issues))

        for issue in high_priority_issues:
            try:
                claude_analysis = await self._get_claude_analysis_for_issue(issue)
                issue.claude_analysis = claude_analysis
            except Exception as e:
                logger.error("Claude analysis failed for issue",
                           issue_description=issue.description, error=str(e))

    async def _get_claude_analysis_for_issue(self, issue: AuditIssue) -> str:
        """Отримати Claude аналіз для конкретної проблеми"""
        prompt = self._build_claude_prompt_for_issue(issue)

        try:
            response = await self.claude_integration.run_command(
                prompt=prompt,
                working_directory=self.project_root,
                user_id=0  # System user for audit
            )

            if response and response.content:
                return response.content.strip()
            else:
                return "Claude аналіз недоступний"

        except Exception as e:
            logger.error("Failed to get Claude analysis", error=str(e))
            return f"Помилка Claude аналізу: {str(e)}"

    def _build_claude_prompt_for_issue(self, issue: AuditIssue) -> str:
        """Побудувати промпт для Claude аналізу проблеми"""

        # Читаємо контекст навколо проблеми
        context_lines = self._get_file_context(issue.file_path, issue.line_number)

        prompt = f"""
**АУДИТ TELEGRAM БОТА - ІНТЕЛЕКТУАЛЬНИЙ АНАЛІЗ ПРОБЛЕМИ**

**Тип проблеми:** {issue.category}
**Серйозність:** {issue.severity}
**Опис:** {issue.description}
**Файл:** {issue.file_path}:{issue.line_number}

**Код навколо проблеми:**
```python
{context_lines}
```

**Поточна рекомендація:** {issue.fix_suggestion}

**ЗАВДАННЯ:**
1. Проаналізуйте проблему з точки зору архітектури Telegram ботів
2. Оцініть потенційний вплив на користувачів
3. Запропонуйте конкретне рішення з кодом
4. Визначте чи може ця проблема призвести до інших проблем
5. Оцініте пріоритет виправлення (1-10)

**КОНТЕКСТ ПРОЕКТУ:**
- Це Claude Code Telegram Bot з локалізацією
- Використовується python-telegram-bot бібліотека
- Є система callback handlers та inline keyboards
- Підтримується українська та англійська мови

Дайте детальний аналіз і практичні рекомендації.
"""
        return prompt

    def _get_file_context(self, file_path: str, line_number: int, context_size: int = 10) -> str:
        """Отримати контекст навколо проблемної лінії"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            start = max(0, line_number - context_size - 1)
            end = min(len(lines), line_number + context_size)

            context_lines = []
            for i in range(start, end):
                prefix = ">>> " if i == line_number - 1 else "    "
                context_lines.append(f"{prefix}{i+1:3d}: {lines[i].rstrip()}")

            return "\n".join(context_lines)

        except Exception as e:
            return f"Не вдалося прочитати контекст: {e}"

    async def _generate_recommendations(self) -> List[str]:
        """Згенерувати загальні рекомендації на основі знайдених проблем"""
        recommendations = []

        # Аналіз патернів проблем
        category_counts = defaultdict(int)
        severity_counts = defaultdict(int)

        for issue in self.issues:
            category_counts[issue.category] += 1
            severity_counts[issue.severity] += 1

        # Рекомендації на основі критичних проблем
        if severity_counts["CRITICAL"] > 0:
            recommendations.append(f"🚨 НЕГАЙНО виправити {severity_counts['CRITICAL']} критичних проблем")

        # Рекомендації на основі категорій
        if category_counts["CALLBACK_ERROR"] > 3:
            recommendations.append("🔘 Провести ревізію всіх callback handlers - багато проблем")

        if category_counts["HARDCODED_UKRAINIAN"] > 5:
            recommendations.append("🌐 Завершити міграцію на локалізацію - забагато hardcoded тексту")

        # Загальні рекомендації
        if len(self.issues) > 20:
            recommendations.append("📊 Розглянути впровадження CI/CD з автоматичними перевірками")

        return recommendations

    def _prepare_audit_result(self, recommendations: List[str]) -> AuditResult:
        """Підготувати фінальний результат аудиту"""
        severity_counts = defaultdict(int)

        for issue in self.issues:
            severity_counts[issue.severity] += 1

        return AuditResult(
            total_issues=len(self.issues),
            critical_count=severity_counts["CRITICAL"],
            high_count=severity_counts["HIGH"],
            medium_count=severity_counts["MEDIUM"],
            low_count=severity_counts["LOW"],
            issues=sorted(self.issues, key=lambda x: (x.severity, x.category)),
            recommendations=recommendations
        )

    def _load_translation_keys(self):
        """Завантажити ключі перекладів (спрощена версія з original script)"""
        translation_dir = self.project_root / "src" / "localization" / "translations"

        if not translation_dir.exists():
            return

        for lang_file in translation_dir.glob("*.json"):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                lang_code = lang_file.stem
                self.translation_keys[lang_code] = set()
                self._extract_translation_keys(data, "", self.translation_keys[lang_code])

            except Exception as e:
                logger.error("Failed to load translations", file=str(lang_file), error=str(e))

    def _extract_translation_keys(self, data: Union[dict, str], prefix: str, keys_set: Set[str]):
        """Рекурсивно витягнути ключі перекладів"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key.startswith("_"):
                    continue
                new_prefix = f"{prefix}.{key}" if prefix else key
                self._extract_translation_keys(value, new_prefix, keys_set)
        else:
            keys_set.add(prefix)

    def _audit_callback_coverage(self):
        """Перевірити покриття callback handlers"""
        # Спрощена версія - тут можна додати більш складну логіку
        pass

    def _audit_translation_coverage(self):
        """Перевірити покриття перекладів"""
        if 'uk' in self.translation_keys and 'en' in self.translation_keys:
            uk_keys = self.translation_keys['uk']
            en_keys = self.translation_keys['en']

            # Знайти неспівпадіння
            missing_in_en = uk_keys - en_keys
            missing_in_uk = en_keys - uk_keys

            for key in missing_in_en:
                self.issues.append(AuditIssue(
                    category="MISSING_TRANSLATION",
                    severity="MEDIUM",
                    file_path="src/localization/translations/en.json",
                    line_number=0,
                    description=f"Відсутній англійський переклад: {key}",
                    fix_suggestion=f"Додати переклад для ключа '{key}'",
                    group="missing_translations_en"
                ))

    def _audit_architecture_issues(self):
        """Перевірити архітектурні проблеми"""
        # Тут можна додати перевірки специфічні для архітектури ботів
        pass

    def _check_translation_usage(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити використання перекладів (спрощено)"""
        pass

    def _check_hardcoded_strings(self, file_path: Path, lines: List[str]):
        """Перевірити hardcoded рядки (спрощено)"""
        pass

    def _check_button_callback_consistency(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити consistency кнопок та callbacks (спрощено)"""
        pass

def format_audit_report(result: AuditResult) -> str:
    """Форматувати звіт аудиту для Telegram"""

    if result.total_issues == 0:
        return "🎉 **PERFECT CODE!** Проблем не знайдено в коді бота."

    report = []
    report.append(f"🔍 **ІНТЕЛЕКТУАЛЬНИЙ АУДИТ БОТА**")
    report.append(f"📊 **Загалом проблем:** {result.total_issues}")
    report.append("")

    # Статистика серйозності
    report.append("**Розподіл за серйозністю:**")
    if result.critical_count > 0:
        report.append(f"🔴 CRITICAL: {result.critical_count}")
    if result.high_count > 0:
        report.append(f"🟠 HIGH: {result.high_count}")
    if result.medium_count > 0:
        report.append(f"🟡 MEDIUM: {result.medium_count}")
    if result.low_count > 0:
        report.append(f"🟢 LOW: {result.low_count}")
    report.append("")

    # Топ критичні проблеми
    critical_issues = [i for i in result.issues if i.severity == "CRITICAL"][:5]
    if critical_issues:
        report.append("🚨 **КРИТИЧНІ ПРОБЛЕМИ:**")
        for i, issue in enumerate(critical_issues, 1):
            report.append(f"{i}. {issue.description}")
            report.append(f"   📁 `{issue.file_path}:{issue.line_number}`")
            if issue.claude_analysis:
                report.append(f"   🤖 Claude: {issue.claude_analysis[:100]}...")
        report.append("")

    # Рекомендації
    if result.recommendations:
        report.append("💡 **РЕКОМЕНДАЦІЇ:**")
        for rec in result.recommendations:
            report.append(f"• {rec}")
        report.append("")

    # Claude загальний аналіз
    if result.claude_summary:
        report.append(f"🧠 **CLAUDE АНАЛІЗ:**\n{result.claude_summary[:500]}...")

    return "\n".join(report)