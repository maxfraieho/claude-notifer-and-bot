#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Розширений Аудитор Логіки Telegram Бота (для Claude Code Telegram Bot)
Фокус: Реальні проблеми досвіду користувача (UX), особливо для української локалізації

Автор: AI Асистент
Мова звітів: Українська
"""

import os
import re
import ast
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
import sys

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedBotAuditor:
    """Головний клас аудитора, який аналізує бот на реальні проблеми UX."""

    def __init__(self, source_dir: str = "src", report_lang: str = "uk"):
        """
        Ініціалізація аудитора.

        :param source_dir: Шлях до директорії з вихідним кодом (за замовчуванням "src")
        :param report_lang: Мова звіту ("uk" або "en")
        """
        self.source_dir = Path(source_dir)
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Директорію {source_dir} не знайдено")

        self.report_lang = report_lang
        self.findings = {
            'critical': [],
            'localization': [],
            'ux': [],
            'integration': [],
            'buttons': []
        }

        # Шляхи до файлів перекладів
        self.translations = {}
        self.translation_files = {
            'en': self.source_dir / "localization" / "translations" / "en.json",
            'uk': self.source_dir / "localization" / "translations" / "uk.json"
        }

        # Завантажені ключі перекладів
        self.translation_keys = {'en': set(), 'uk': set()}

        # Патерни для виявлення критичних проблем
        self.CRITICAL_PATTERNS = {
            'dead_commands': [
                r'@register_command\(["\'](\w+)["\'].*?async def.*?raise NotImplementedError',
                r'CommandHandler\(["\'](\w+)["\'].*?pass\b',
                r'reply_text\([rf]?["\'][^"\']*Error[^"\']*["\'].*?# TODO',
            ],
            'silent_failures': [
                r'except\s*:\s*pass(?!\s*#)',
                r'except\s*:\s*continue(?!\s*#)',
                r'try:.*?except.*?:\s*return\s+None',
            ],
            'user_facing_errors': [
                r'reply_text\([rf]?["\'][^"\']*(?:Exception|Error|Failed|Invalid|Timeout)[^"\']*["\']',
                r'await.*?reply.*?code\s*\d+',
            ],
            'broken_buttons': [
                r'InlineKeyboardButton\(["\']([^"\']+)["\'].*?callback_data=["\'](\w+)["\']'
            ]
        }

        # Патерни для виявлення проблем UX
        self.UX_PATTERNS = {
            'mixed_languages': [
                r'[а-яіїєґА-ЯІЇЄҐ]+.*?[a-zA-Z].*?reply_text',  # Український + англійський текст
                r'❌.*?[A-Z][a-z]+.*?Error',  # Англійська помилка з українським емодзі
            ],
            'poor_error_messages': [
                r'reply_text\(["\']❌[^"\']*["\'].*?\)',  # Загальні повідомлення помилок
                r'Exception.*?str\(e\)',  # Сирий текст виключення
            ],
            'hardcoded_strings': [
                r'reply_text\([rf]?["\']([^"\']{10,}[^"\']*)["\']',  # Довгі рядки в reply_text
                r'send_message\([rf]?["\']([^"\']{10,}[^"\']*)["\']',
            ]
        }

        # Відомі команди, які мають бути реалізовані (з help та інтерфейсу)
        self.advertised_commands = {
            'start', 'help', 'new', 'continue', 'ls', 'cd', 'pwd', 'projects',
            'status', 'export', 'actions', 'git', 'schedules', 'add_schedule'
        }

        # Кеш AST для файлів
        self.ast_cache = {}

        # Завантажуємо переклади при ініціалізації
        self.load_translations()

    def load_translations(self):
        """Завантажує файли перекладів та збирає всі ключі."""
        for lang, path in self.translation_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.translations[lang] = data
                    self.translation_keys[lang] = self._extract_all_keys(data)
                    logger.info(f"Завантажено {lang} переклади з {path}")
            except Exception as e:
                logger.error(f"Не вдалося завантажити {lang} переклади: {e}")
                self.translations[lang] = {}
                self.translation_keys[lang] = set()

    def _extract_all_keys(self, data: Any, prefix: str = "") -> Set[str]:
        """Рекурсивно витягує всі ключі з JSON-структури."""
        keys = set()
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.add(full_key)
                keys.update(self._extract_all_keys(value, full_key))
        return keys

    def scan_all_files(self):
        """Сканує всі Python-файли в директорії та запускає модулі аудиту."""
        logger.info("Початок повного аудиту...")
        python_files = list(self.source_dir.rglob("*.py"))

        for file_path in python_files:
            logger.info(f"Аналіз файлу: {file_path}")
            try:
                self.analyze_file(file_path)
            except Exception as e:
                logger.error(f"Помилка при аналізі {file_path}: {e}")

        # Додаткові перевірки
        self.check_advertised_commands()
        self.validate_localization_keys()

    def analyze_file(self, file_path: Path):
        """Аналізує окремий файл за допомогою AST та регулярних виразів."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                tree = ast.parse(source_code)
                self.ast_cache[file_path] = tree
        except Exception as e:
            logger.error(f"Не вдалося розібрати AST для {file_path}: {e}")
            return

        # 1. Пошук критичних проблем
        self._find_critical_issues(file_path, source_code)
        
        # 2. Пошук проблем локалізації та UX
        self._find_localization_and_ux_issues(file_path, source_code)
        
        # 3. Аналіз кнопок
        self._analyze_buttons(file_path, source_code)

    def _find_critical_issues(self, file_path: Path, source_code: str):
        """Шукає критичні проблеми: мертві команди, тихі збої, помилки для користувача."""
        for pattern_name, patterns in self.CRITICAL_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, source_code, re.DOTALL):
                    issue = {
                        'file': str(file_path),
                        'line': source_code[:match.start()].count('\n') + 1,
                        'pattern_type': pattern_name,
                        'match': match.group(0),
                        'command_or_button': match.group(1) if len(match.groups()) > 0 else None
                    }
                    self.findings['critical'].append(issue)
                    logger.warning(f"Критична проблема у {file_path}:{issue['line']} - {pattern_name}")

    def _find_localization_and_ux_issues(self, file_path: Path, source_code: str):
        """Шукає проблеми з локалізацією та UX: змішані мови, жорстко закодовані рядки."""
        # Пошук змішаних мов
        for pattern in self.UX_PATTERNS['mixed_languages']:
            for match in re.finditer(pattern, source_code):
                issue = {
                    'file': str(file_path),
                    'line': source_code[:match.start()].count('\n') + 1,
                    'type': 'mixed_languages',
                    'snippet': match.group(0)
                }
                self.findings['localization'].append(issue)
                logger.info(f"Змішана мова у {file_path}:{issue['line']}")

        # Пошук жорстко закодованих рядків
        for pattern in self.UX_PATTERNS['hardcoded_strings']:
            for match in re.finditer(pattern, source_code):
                text = match.group(1)
                # Ігноруємо рядки, які виглядають як шляхи, змінні або технічні повідомлення
                if any(ignore in text for ignore in ['{', '}', '%s', '%d', 'http', '.py', '__']):
                    continue
                # Перевіряємо, чи це не ключ перекладу (не містить крапок або має пробіли)
                if '.' not in text and ' ' in text:
                    issue = {
                        'file': str(file_path),
                        'line': source_code[:match.start()].count('\n') + 1,
                        'type': 'hardcoded_string',
                        'text': text
                    }
                    self.findings['localization'].append(issue)
                    logger.info(f"Жорстко закодований рядок у {file_path}:{issue['line']} - '{text}'")

    def _analyze_buttons(self, file_path: Path, source_code: str):
        """Аналізує кнопки та їхні callback_data."""
        pattern = r'InlineKeyboardButton\(["\']([^"\']+)["\'].*?callback_data=["\']([^"\']+)["\']'
        for match in re.finditer(pattern, source_code):
            button_text = match.group(1)
            callback_data = match.group(2)
            line_num = source_code[:match.start()].count('\n') + 1

            # Тимчасово припускаємо, що всі callback_data мають обробники (потрібна глибша перевірка)
            # У майбутньому можна додати пошук функцій-обробників за іменем callback_data
            issue = {
                'file': str(file_path),
                'line': line_num,
                'button_text': button_text,
                'callback_data': callback_data,
                'status': 'assumed_working'  # Потрібна подальша перевірка
            }
            self.findings['buttons'].append(issue)

    def check_advertised_commands(self):
        """Перевіряє, чи всі оголошені команди мають реалізацію."""
        # Знаходимо всі зареєстровані команди у коді
        implemented_commands = set()
        python_files = list(self.source_dir.rglob("*.py"))
        
        command_pattern = r'CommandHandler\(["\'](\w+)["\']'
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for match in re.finditer(command_pattern, content):
                        implemented_commands.add(match.group(1))
            except Exception:
                continue

        # Порівнюємо з оголошеними командами
        for cmd in self.advertised_commands:
            if cmd not in implemented_commands:
                issue = {
                    'command': cmd,
                    'status': 'not_implemented',
                    'description': f"Команда /{cmd} оголошена в інтерфейсі, але не має обробника"
                }
                self.findings['critical'].append(issue)
                logger.error(f"Команда /{cmd} не реалізована!")

    def validate_localization_keys(self):
        """Перевіряє, чи всі ключі перекладу присутні в обох мовах."""
        missing_in_uk = self.translation_keys['en'] - self.translation_keys['uk']
        missing_in_en = self.translation_keys['uk'] - self.translation_keys['en']

        for key in missing_in_uk:
            issue = {
                'key': key,
                'missing_in': 'uk',
                'type': 'missing_translation'
            }
            self.findings['localization'].append(issue)

        for key in missing_in_en:
            issue = {
                'key': key,
                'missing_in': 'en',
                'type': 'missing_translation'
            }
            self.findings['localization'].append(issue)

    def generate_report(self) -> str:
        """Генерує звіт про знахідки українською мовою."""
        report_lines = []
        report_lines.append("# 🎯 РОЗШИРЕНИЙ АУДИТ ДОСВІДУ КОРИСТУВАЧА\n")
        report_lines.append(f"**Згенеровано:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_lines.append(f"**Проаналізовано файлів:** {len(self.ast_cache)}\n\n")

        total_issues = sum(len(v) for v in self.findings.values())
        report_lines.append("## 📊 ЗАГАЛЬНИЙ ЗВІТ\n")
        report_lines.append(f"- **Всього проблем знайдено:** {total_issues}\n")
        report_lines.append(f"- **Критичних (блокують користувача):** {len(self.findings['critical'])}\n")
        report_lines.append(f"- **Проблем локалізації:** {len(self.findings['localization'])}\n")
        report_lines.append(f"- **Проблем UX/інтерфейсу:** {len(self.findings['ux']) + len(self.findings['buttons'])}\n")
        report_lines.append(f"- **Проблем інтеграції:** {len(self.findings['integration'])}\n\n")

        if len(self.findings['critical']) > 0:
            report_lines.append("## 🔴 КРИТИЧНІ ПРОБЛЕМИ (ВИПРАВИТИ НЕГАЙНО)\n")
            for i, issue in enumerate(self.findings['critical'], 1):
                if 'command' in issue:
                    report_lines.append(f"### C{i}: НЕПРАЦЮЮЧА КОМАНДА\n")
                    report_lines.append(f"**Проблема:** Команда `/{issue['command']}` оголошена, але не реалізована\n")
                    report_lines.append(f"**Що бачить користувач:** Набирає `/{issue['command']}` → отримує помилку або нічого\n")
                    report_lines.append(f"**Рішення:** Реалізувати обробник команди або прибрати з довідки/меню\n\n")
                else:
                    report_lines.append(f"### C{i}: {issue.get('pattern_type', 'Невідома проблема')}\n")
                    report_lines.append(f"**Файл:** `{issue['file']}` (рядок {issue['line']})\n")
                    report_lines.append(f"**Код:** `{issue['match']}`\n")
                    report_lines.append(f"**Рішення:** Перевірити логіку обробки та додати коректну відповідь користувачу\n\n")

        if len(self.findings['localization']) > 0:
            report_lines.append("## 🌐 ПРОБЛЕМИ ЛОКАЛІЗАЦІЇ (ВИПРАВИТИ НА ЦЬОМУ ТИЖНІ)\n")
            for i, issue in enumerate(self.findings['localization'], 1):
                if issue.get('type') == 'missing_translation':
                    report_lines.append(f"### L{i}: ВІДСУТНІЙ ПЕРЕКЛАД\n")
                    report_lines.append(f"**Ключ:** `{issue['key']}`\n")
                    report_lines.append(f"**Відсутній у:** {issue['missing_in']}\n")
                    report_lines.append(f"**Рішення:** Додати переклад у відповідний JSON-файл\n\n")
                elif issue.get('type') == 'hardcoded_string':
                    report_lines.append(f"### L{i}: ЖОРСТКО ЗАКОДОВАНИЙ РЯДОК\n")
                    report_lines.append(f"**Файл:** `{issue['file']}` (рядок {issue['line']})\n")
                    report_lines.append(f"**Текст:** `{issue['text']}`\n")
                    report_lines.append(f"**Рішення:** Винести текст у файли перекладів та використовувати функцію локалізації\n\n")
                elif issue.get('type') == 'mixed_languages':
                    report_lines.append(f"### L{i}: ЗМІШАНІ МОВИ\n")
                    report_lines.append(f"**Файл:** `{issue['file']}` (рядок {issue['line']})\n")
                    report_lines.append(f"**Фрагмент:** `{issue['snippet']}`\n")
                    report_lines.append(f"**Рішення:** Перекласти повідомлення повністю українською або англійською\n\n")

        if len(self.findings['buttons']) > 0:
            report_lines.append("## 🎮 ПРОБЛЕМИ З КНОПКАМИ\n")
            dead_buttons = [b for b in self.findings['buttons'] if b.get('status') == 'dead']
            for i, button in enumerate(dead_buttons, 1):
                report_lines.append(f"### B{i}: НЕПРАЦЮЮЧА КНОПКА\n")
                report_lines.append(f"**Текст кнопки:** `{button['button_text']}`\n")
                report_lines.append(f"**Callback:** `{button['callback_data']}`\n")
                report_lines.append(f"**Файл:** `{button['file']}` (рядок {button['line']})\n")
                report_lines.append(f"**Рішення:** Реалізувати обробник або прибрати кнопку\n\n")

        if total_issues == 0:
            report_lines.append("## 🎉 ВІТАЄМО!\n")
            report_lines.append("Критичних проблем не знайдено. Бот готовий до використання!\n")

        return "\n".join(report_lines)

    def save_report(self, filename: str = "advanced_audit_report_ua.md"):
        """Зберігає звіт у файл."""
        report_content = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logger.info(f"Звіт збережено у {filename}")

    def get_quality_metrics(self) -> Dict[str, Any]:
        """Повертає метрики якості."""
        total_keys = len(self.translation_keys['en'])
        uk_coverage = len(self.translation_keys['uk']) / total_keys if total_keys > 0 else 0

        return {
            'localization_coverage_uk': f"{uk_coverage:.1%}",
            'critical_issues_count': len(self.findings['critical']),
            'hardcoded_strings_count': len([i for i in self.findings['localization'] if i.get('type') == 'hardcoded_string']),
            'missing_translations_uk': len([i for i in self.findings['localization'] if i.get('missing_in') == 'uk']),
            'advertised_commands_implemented': len(self.advertised_commands) - len([i for i in self.findings['critical'] if 'command' in i])
        }

    def run_full_audit(self):
        """Запускає повний аудит і зберігає звіт."""
        logger.info("🚀 Запуск повного аудиту...")
        self.scan_all_files()
        self.save_report()
        metrics = self.get_quality_metrics()
        logger.info("📊 Метрики якості:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value}")
        logger.info("✅ Аудит завершено!")

if __name__ == "__main__":
    auditor = AdvancedBotAuditor(source_dir="src", report_lang="uk")
    auditor.run_full_audit()