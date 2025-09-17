#!/usr/bin/env python3
"""
ULTIMATE PLUS AUDITOR v6 - Розширений аналізатор для виявлення проблем з кнопками, перекладами та логікою
Виявляє специфічні проблеми з локалізацією, callback handlers та UI consistency
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Issue:
    category: str
    severity: str
    file_path: str
    line_number: int
    description: str
    code_snippet: str = ""
    fix_suggestion: str = ""

class UltimatePlusAuditor:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues: List[Issue] = []
        self.translation_keys: Dict[str, Set[str]] = {}
        self.callback_handlers: Set[str] = set()
        self.button_callbacks: Set[str] = set()
        self.used_translation_keys: Set[str] = set()
        self.undefined_translation_keys: Set[str] = set()
        
    def audit(self) -> List[Issue]:
        """Виконати повний аудит проекту"""
        print("🔍 Запуск Ultimate Plus Audit v6...")
        
        # Завантажити переклади
        self._load_translation_keys()
        
        # Знайти всі Python файли
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            if "venv" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                self._audit_python_file(file_path)
            except Exception as e:
                self.issues.append(Issue(
                    category="PARSING_ERROR",
                    severity="HIGH",
                    file_path=str(file_path),
                    line_number=0,
                    description=f"Помилка парсингу файлу: {e}"
                ))
        
        # Спеціальні перевірки
        self._audit_callback_coverage()
        self._audit_translation_coverage()
        self._audit_button_consistency()
        self._audit_hardcoded_strings()
        
        return sorted(self.issues, key=lambda x: (x.severity, x.category))
    
    def _load_translation_keys(self):
        """Завантажити ключі перекладів з JSON файлів"""
        translation_dir = self.project_root / "src" / "localization" / "translations"
        
        for lang_file in translation_dir.glob("*.json"):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                lang_code = lang_file.stem
                self.translation_keys[lang_code] = set()
                self._extract_translation_keys(data, "", self.translation_keys[lang_code])
                
            except Exception as e:
                self.issues.append(Issue(
                    category="TRANSLATION_ERROR",
                    severity="HIGH",
                    file_path=str(lang_file),
                    line_number=0,
                    description=f"Помилка завантаження перекладів: {e}"
                ))
    
    def _extract_translation_keys(self, data: Union[dict, str], prefix: str, keys_set: Set[str]):
        """Рекурсивно витягнути ключі перекладів"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key.startswith("_"):  # Пропустити мета-ключі
                    continue
                new_prefix = f"{prefix}.{key}" if prefix else key
                self._extract_translation_keys(value, new_prefix, keys_set)
        else:
            keys_set.add(prefix)
    
    def _audit_python_file(self, file_path: Path):
        """Аудит одного Python файлу"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            tree = ast.parse(content)
            
            # Різні типи аналізу
            self._check_callback_handlers(tree, file_path, lines)
            self._check_button_definitions(tree, file_path, lines)
            self._check_translation_usage(tree, file_path, lines)
            self._check_hardcoded_ukrainian(file_path, lines)
            self._check_hardcoded_english(file_path, lines)
            self._check_string_concatenation(tree, file_path, lines)
            self._check_missing_error_handling(tree, file_path, lines)
            self._check_button_callback_consistency(tree, file_path, lines)
            
        except Exception as e:
            self.issues.append(Issue(
                category="FILE_ERROR",
                severity="MEDIUM",
                file_path=str(file_path),
                line_number=0,
                description=f"Помилка обробки файлу: {e}"
            ))
    
    def _check_callback_handlers(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити callback handlers"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.endswith('_callback'):
                self.callback_handlers.add(node.name)
            
            # Перевірити CallbackQueryHandler
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Name) and 
                    node.func.id == 'CallbackQueryHandler'):
                    
                    if len(node.args) == 0:
                        self.issues.append(Issue(
                            category="CALLBACK_ERROR",
                            severity="HIGH",
                            file_path=str(file_path),
                            line_number=getattr(node, 'lineno', 0),
                            description="CallbackQueryHandler без handler функції",
                            code_snippet=lines[getattr(node, 'lineno', 1) - 1] if lines else "",
                            fix_suggestion="Додайте handler функцію в CallbackQueryHandler"
                        ))
    
    def _check_button_definitions(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити визначення кнопок"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # InlineKeyboardButton
                if (isinstance(node.func, ast.Name) and 
                    node.func.id == 'InlineKeyboardButton'):
                    
                    callback_data = None
                    button_text = None
                    
                    # Знайти callback_data
                    for keyword in node.keywords:
                        if keyword.arg == 'callback_data':
                            if isinstance(keyword.value, ast.Constant):
                                callback_data = keyword.value.value
                                self.button_callbacks.add(callback_data)
                    
                    # Знайти text кнопки
                    if node.args:
                        if isinstance(node.args[0], ast.Constant):
                            button_text = node.args[0].value
                        elif isinstance(node.args[0], ast.Call):
                            # Перевірити чи це виклик функції t()
                            if not self._is_translation_call(node.args[0]):
                                self.issues.append(Issue(
                                    category="BUTTON_TEXT_ERROR",
                                    severity="MEDIUM",
                                    file_path=str(file_path),
                                    line_number=getattr(node, 'lineno', 0),
                                    description="Текст кнопки не використовує локалізацію",
                                    code_snippet=lines[getattr(node, 'lineno', 1) - 1] if lines else "",
                                    fix_suggestion="Використовуйте await t(context, user_id, 'key') для тексту кнопки"
                                ))
                    
                    # Перевірити чи є hardcoded text
                    if button_text and isinstance(button_text, str):
                        if self._is_ukrainian_text(button_text) or self._is_english_text(button_text):
                            self.issues.append(Issue(
                                category="HARDCODED_BUTTON_TEXT",
                                severity="HIGH",
                                file_path=str(file_path),
                                line_number=getattr(node, 'lineno', 0),
                                description=f"Hardcoded текст кнопки: '{button_text}'",
                                code_snippet=lines[getattr(node, 'lineno', 1) - 1] if lines else "",
                                fix_suggestion=f"Замінити на await t(context, user_id, 'buttons.{self._suggest_key(button_text)}')"
                            ))
    
    def _check_translation_usage(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити використання функції t()"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if self._is_translation_call(node):
                    # Витягнути ключ перекладу
                    if len(node.args) >= 3 and isinstance(node.args[2], ast.Constant):
                        translation_key = node.args[2].value
                        self.used_translation_keys.add(translation_key)
                        
                        # Перевірити чи існує ключ в перекладах
                        key_exists = False
                        for lang_keys in self.translation_keys.values():
                            if translation_key in lang_keys:
                                key_exists = True
                                break
                        
                        if not key_exists:
                            self.undefined_translation_keys.add(translation_key)
                            self.issues.append(Issue(
                                category="UNDEFINED_TRANSLATION_KEY",
                                severity="HIGH",
                                file_path=str(file_path),
                                line_number=getattr(node, 'lineno', 0),
                                description=f"Невизначений ключ перекладу: '{translation_key}'",
                                code_snippet=lines[getattr(node, 'lineno', 1) - 1] if lines else "",
                                fix_suggestion=f"Додайте ключ '{translation_key}' в файли перекладів"
                            ))
    
    def _check_hardcoded_ukrainian(self, file_path: Path, lines: List[str]):
        """Перевірити hardcoded українські рядки"""
        ukrainian_patterns = [
            r'["\'].*[а-яєіїґ].*["\']',  # Містить українські літери
            r'["\'].*(помилка|ошибка|error).*["\']',  # Слова помилки
            r'["\'].*(команда|кнопка|меню|налаштування).*["\']',  # UI термінологія
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in ukrainian_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Пропустити коментарі та docstrings
                    if line.strip().startswith('#') or '"""' in line or "'''" in line:
                        continue
                        
                    # Пропустити якщо вже використовує t()
                    if 'await t(' in line or 't(' in line:
                        continue
                    
                    matched_text = match.group()
                    self.issues.append(Issue(
                        category="HARDCODED_UKRAINIAN",
                        severity="HIGH",
                        file_path=str(file_path),
                        line_number=i,
                        description=f"Hardcoded українській текст: {matched_text}",
                        code_snippet=line.strip(),
                        fix_suggestion=f"Замінити на await t(context, user_id, 'appropriate.key')"
                    ))
    
    def _check_hardcoded_english(self, file_path: Path, lines: List[str]):
        """Перевірити hardcoded англійські рядки в UI"""
        english_ui_patterns = [
            r'["\'].*\b(error|failed|success|loading|processing|completed)\b.*["\']',
            r'["\'].*\b(button|menu|settings|help|status|export)\b.*["\']',
            r'["\'].*(❌|✅|🔄|📊|⚙️|📁|🆕).*["\']',  # З емодзі
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in english_ui_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    if line.strip().startswith('#') or '"""' in line:
                        continue
                    if 'await t(' in line or 't(' in line:
                        continue
                        
                    matched_text = match.group()
                    self.issues.append(Issue(
                        category="HARDCODED_ENGLISH",
                        severity="MEDIUM",
                        file_path=str(file_path),
                        line_number=i,
                        description=f"Hardcoded англійський UI текст: {matched_text}",
                        code_snippet=line.strip(),
                        fix_suggestion="Використати локалізацію замість hardcoded тексту"
                    ))
    
    def _check_string_concatenation(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити конкатенацію рядків замість форматування"""
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                if (isinstance(node.left, ast.Constant) and isinstance(node.left.value, str) and
                    isinstance(node.right, ast.Constant) and isinstance(node.right.value, str)):
                    
                    self.issues.append(Issue(
                        category="STRING_CONCATENATION",
                        severity="LOW",
                        file_path=str(file_path),
                        line_number=getattr(node, 'lineno', 0),
                        description="Конкатенація рядків замість f-strings",
                        code_snippet=lines[getattr(node, 'lineno', 1) - 1] if lines else "",
                        fix_suggestion="Використовуйте f-strings або .format()"
                    ))
    
    def _check_missing_error_handling(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити відсутність обробки помилок"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:  # except: без типу
                    # Перевірити чи є pass або просто логування
                    if (len(node.body) == 1 and 
                        isinstance(node.body[0], ast.Pass)):
                        
                        self.issues.append(Issue(
                            category="SILENT_FAILURE",
                            severity="CRITICAL",
                            file_path=str(file_path),
                            line_number=getattr(node, 'lineno', 0),
                            description="Silent failure - except: pass",
                            code_snippet=lines[getattr(node, 'lineno', 1) - 1] if lines else "",
                            fix_suggestion="Використати safe_user_error() або proper error handling"
                        ))
    
    def _check_button_callback_consistency(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """Перевірити consistency між кнопками та callback handlers"""
        # Знайти всі callback_data у кнопках
        button_callbacks_in_file = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Name) and 
                    node.func.id == 'InlineKeyboardButton'):
                    
                    for keyword in node.keywords:
                        if keyword.arg == 'callback_data':
                            if isinstance(keyword.value, ast.Constant):
                                button_callbacks_in_file.add(keyword.value.value)
        
        # Знайти всі pattern у CallbackQueryHandler
        handler_patterns = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Name) and 
                    node.func.id == 'CallbackQueryHandler'):
                    
                    for keyword in node.keywords:
                        if keyword.arg == 'pattern':
                            if isinstance(keyword.value, ast.Constant):
                                handler_patterns.add(keyword.value.value)
        
        # Перевірити неспівпадіння
        for callback in button_callbacks_in_file:
            if not any(re.match(pattern, callback) for pattern in handler_patterns):
                self.issues.append(Issue(
                    category="MISSING_CALLBACK_HANDLER",
                    severity="HIGH",
                    file_path=str(file_path),
                    line_number=0,
                    description=f"Відсутній handler для callback: '{callback}'",
                    fix_suggestion=f"Додати CallbackQueryHandler з pattern для '{callback}'"
                ))
    
    def _audit_callback_coverage(self):
        """Перевірити покриття callback handlers"""
        uncovered_callbacks = self.button_callbacks - {
            cb for cb in self.button_callbacks 
            if any(cb.startswith(prefix) for prefix in ['action:', 'schedule:', 'git:', 'export:'])
        }
        
        for callback in uncovered_callbacks:
            self.issues.append(Issue(
                category="UNCOVERED_CALLBACK",
                severity="HIGH",
                file_path="GLOBAL",
                line_number=0,
                description=f"Callback без handler: '{callback}'",
                fix_suggestion=f"Додати handler для callback '{callback}'"
            ))
    
    def _audit_translation_coverage(self):
        """Перевірити покриття перекладів"""
        if 'uk' in self.translation_keys and 'en' in self.translation_keys:
            uk_keys = self.translation_keys['uk']
            en_keys = self.translation_keys['en']
            
            # Ключі тільки в українській
            uk_only = uk_keys - en_keys
            for key in uk_only:
                self.issues.append(Issue(
                    category="MISSING_ENGLISH_TRANSLATION",
                    severity="MEDIUM",
                    file_path="src/localization/translations/en.json",
                    line_number=0,
                    description=f"Відсутній англійський переклад для ключа: '{key}'",
                    fix_suggestion=f"Додати переклад для '{key}' в en.json"
                ))
            
            # Ключі тільки в англійській
            en_only = en_keys - uk_keys
            for key in en_only:
                self.issues.append(Issue(
                    category="MISSING_UKRAINIAN_TRANSLATION",
                    severity="MEDIUM",
                    file_path="src/localization/translations/uk.json",
                    line_number=0,
                    description=f"Відсутній український переклад для ключа: '{key}'",
                    fix_suggestion=f"Додати переклад для '{key}' в uk.json"
                ))
    
    def _audit_button_consistency(self):
        """Перевірити consistency кнопок"""
        # Перевірити чи всі використані ключі існують
        for key in self.undefined_translation_keys:
            if key.startswith('buttons.'):
                self.issues.append(Issue(
                    category="BUTTON_TRANSLATION_MISSING",
                    severity="HIGH",
                    file_path="GLOBAL",
                    line_number=0,
                    description=f"Відсутній переклад для кнопки: '{key}'",
                    fix_suggestion=f"Додати переклад '{key}' в файли локалізації"
                ))
    
    def _audit_hardcoded_strings(self):
        """Загальна перевірка hardcoded рядків"""
        # Статистика
        hardcoded_count = len([i for i in self.issues if 'HARDCODED' in i.category])
        if hardcoded_count > 0:
            self.issues.append(Issue(
                category="HARDCODED_SUMMARY",
                severity="HIGH",
                file_path="GLOBAL",
                line_number=0,
                description=f"Знайдено {hardcoded_count} hardcoded рядків",
                fix_suggestion="Замінити всі hardcoded рядки на локалізацію"
            ))
    
    def _is_translation_call(self, node: ast.Call) -> bool:
        """Перевірити чи це виклик функції t()"""
        return (isinstance(node.func, ast.Name) and node.func.id == 't') or \
               (isinstance(node.func, ast.Attribute) and node.func.attr == 't')
    
    def _is_ukrainian_text(self, text: str) -> bool:
        """Перевірити чи містить текст українські літери"""
        return bool(re.search(r'[а-яєіїґ]', text, re.IGNORECASE))
    
    def _is_english_text(self, text: str) -> bool:
        """Перевірити чи це англійський UI текст"""
        ui_words = ['error', 'failed', 'success', 'loading', 'button', 'menu', 'settings']
        return any(word in text.lower() for word in ui_words)
    
    def _suggest_key(self, text: str) -> str:
        """Запропонувати ключ для тексту"""
        # Простий алгоритм для генерації ключа
        text = re.sub(r'[^\w\s]', '', text.lower())
        text = re.sub(r'\s+', '_', text.strip())
        return text[:30]  # Обмежити довжину

def generate_report(issues: List[Issue]) -> str:
    """Згенерувати звіт у markdown форматі"""
    if not issues:
        return "🎉 **PERFECT CODE!** Проблем не знайдено."
    
    # Групування за категоріями
    by_category = defaultdict(list)
    by_severity = defaultdict(int)
    
    for issue in issues:
        by_category[issue.category].append(issue)
        by_severity[issue.severity] += 1
    
    report = []
    report.append("# 🔍 ULTIMATE PLUS AUDIT REPORT v6")
    report.append(f"**Дата:** {os.popen('date').read().strip()}")
    report.append("")
    
    # Статистика
    report.append("## 📊 СТАТИСТИКА")
    report.append(f"- 🔴 **CRITICAL:** {by_severity['CRITICAL']}")
    report.append(f"- 🟠 **HIGH:** {by_severity['HIGH']}")
    report.append(f"- 🟡 **MEDIUM:** {by_severity['MEDIUM']}")
    report.append(f"- 🟢 **LOW:** {by_severity['LOW']}")
    report.append(f"- **ЗАГАЛОМ:** {len(issues)}")
    report.append("")
    
    # Топ проблеми
    report.append("## 🚨 КРИТИЧНІ ПРОБЛЕМИ")
    critical_issues = [i for i in issues if i.severity == 'CRITICAL']
    if critical_issues:
        for i, issue in enumerate(critical_issues[:10], 1):
            report.append(f"### {i}. {issue.description}")
            report.append(f"**Файл:** `{issue.file_path}:{issue.line_number}`")
            if issue.code_snippet:
                report.append(f"**Код:** `{issue.code_snippet}`")
            if issue.fix_suggestion:
                report.append(f"**Виправлення:** {issue.fix_suggestion}")
            report.append("")
    else:
        report.append("✅ Критичних проблем не знайдено!")
        report.append("")
    
    # Проблеми з кнопками
    button_issues = [i for i in issues if 'BUTTON' in i.category or 'CALLBACK' in i.category]
    if button_issues:
        report.append("## 🔘 ПРОБЛЕМИ З КНОПКАМИ ТА CALLBACKS")
        for issue in button_issues[:15]:
            report.append(f"- **{issue.severity}:** {issue.description} (`{issue.file_path}:{issue.line_number}`)")
        report.append("")
    
    # Проблеми з локалізацією
    localization_issues = [i for i in issues if 'TRANSLATION' in i.category or 'HARDCODED' in i.category]
    if localization_issues:
        report.append("## 🌐 ПРОБЛЕМИ З ЛОКАЛІЗАЦІЄЮ")
        for issue in localization_issues[:20]:
            report.append(f"- **{issue.severity}:** {issue.description} (`{issue.file_path}:{issue.line_number}`)")
        report.append("")
    
    # Рекомендації
    report.append("## 💡 ПРІОРИТЕТНІ ДІЇ")
    report.append("1. **Виправити всі CRITICAL проблеми** - вони блокують функціональність")
    report.append("2. **Додати відсутні callback handlers** - кнопки не працюють")
    report.append("3. **Завершити локалізацію** - замінити hardcoded тексти")
    report.append("4. **Перевірити consistency перекладів** - uk.json vs en.json")
    report.append("5. **Додати missing translation keys** - уникнути помилок в runtime")
    report.append("")
    
    return "\n".join(report)

def main():
    if len(sys.argv) < 2:
        print("Usage: python smart_audit_v6_ultimate_plus.py <project_root>")
        sys.exit(1)
    
    project_root = sys.argv[1]
    auditor = UltimatePlusAuditor(project_root)
    issues = auditor.audit()
    
    report = generate_report(issues)
    
    # Зберегти звіт
    output_file = Path(project_root) / "audit_report_v6_ultimate_plus.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Аудит завершено! Звіт збережено: {output_file}")
    print(f"📊 Знайдено проблем: {len(issues)}")
    
    # Показати топ-5 критичних проблем
    critical = [i for i in issues if i.severity == 'CRITICAL']
    if critical:
        print("\n🚨 ТОП КРИТИЧНІ ПРОБЛЕМИ:")
        for i, issue in enumerate(critical[:5], 1):
            print(f"{i}. {issue.description} ({issue.file_path}:{issue.line_number})")

if __name__ == "__main__":
    main()