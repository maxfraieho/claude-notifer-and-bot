#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Розширений Аудитор Логіки Telegram Бота (Claude Code)
Фокус: Реальні проблеми досвіду користувача (User Experience), особливо для української локалізації

Автор: AI Асистент
Мова звітів: Українська
Версія: 3.0
"""

import os
import re
import ast
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Callable
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
                r'NotImplementedError'
            ],
            'silent_failures': [
                r'except\s*:\s*pass(?!\s*#)',
                r'except\s*:\s*continue(?!\s*#)',
                r'try:.*?except.*?:\s*return\s+None',
                r'try:.*?except.*?:\s*break'
            ],
            'user_facing_errors': [
                r'reply_text\([rf]?["\'][^"\']*(?:Exception|Error|Failed|Invalid|Timeout|Permission)[^"\']*["\']',
                r'await.*?reply.*?code\s*\d+',
                r'raise\s+\w+Error\(["\'].*?["\']\)'
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
                r'⚠️.*?[A-Z][a-z]+.*?Error',
                r'✅.*?[A-Z][a-z]+.*?Success'
            ],
            'poor_error_messages': [
                r'reply_text\(["\']❌[^"\']*["\'].*?\)',  # Загальні повідомлення помилок
                r'Exception.*?str\(e\)',  # Сирий текст виключення
                r'raise\s+Exception\([\'"][^\'"]',
                r'logger\.error\([\'"][^\'"]'
            ],
            'hardcoded_strings': [
                r'reply_text\([rf]?["\']([^"\']{10,}[^"\']*)["\']',  # Довгі рядки в reply_text
                r'send_message\([rf]?["\']([^"\']{10,}[^"\']*)["\']',
                r'answer\([rf]?["\']([^"\']{10,}[^"\']*)["\']',
                r'edit_message_text\([rf]?["\']([^"\']{10,}[^"\']*)["\']'
            ],
            'missing_localization': [
                r't\([^)]*["\']([^"\']+\.[^"\']+)["\']',  # Виклики локалізації
                r't_sync\([^)]*["\']([^"\']+\.[^"\']+)["\']'
            ]
        }

        # Відомі команди, які мають бути реалізовані (з help та інтерфейсу)
        self.advertised_commands = {
            'start', 'help', 'new', 'continue', 'ls', 'cd', 'pwd', 'projects',
            'status', 'export', 'actions', 'git', 'schedules', 'add_schedule',
            'settings', 'history', 'debug', 'explain'
        }

        # Кеш AST для файлів
        self.ast_cache = {}
        self.function_locations = {}  # Зберігає місцезнаходження функцій

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
        logger.info("🔍 Початок повного аудиту...")
        python_files = list(self.source_dir.rglob("*.py"))
        
        total_files = len(python_files)
        logger.info(f"Знайдено {total_files} Python-файлів для аналізу")
        
        for i, file_path in enumerate(python_files, 1):
            logger.info(f"Аналіз файлу {i}/{total_files}: {file_path}")
            try:
                self.analyze_file(file_path)
            except Exception as e:
                logger.error(f"Помилка при аналізі {file_path}: {e}")

        # Додаткові перевірки
        self.check_advertised_commands()
        self.validate_localization_keys()
        self.analyze_user_journeys()
        self.test_integration_points()
        
        logger.info("✅ Повний аудит завершено!")

    def analyze_file(self, file_path: Path):
        """Аналізує окремий файл за допомогою AST та регулярних виразів."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                tree = ast.parse(source_code)
                self.ast_cache[file_path] = tree
                
                # Зберігаємо місцезнаходження функцій для подальшого аналізу
                self._extract_function_locations(file_path, tree)
                
        except Exception as e:
            logger.error(f"Не вдалося розібрати AST для {file_path}: {e}")
            return

        # 1. Пошук критичних проблем
        self._find_critical_issues(file_path, source_code)
        
        # 2. Пошук проблем локалізації та UX
        self._find_localization_and_ux_issues(file_path, source_code)
        
        # 3. Аналіз кнопок
        self._analyze_buttons(file_path, source_code)

    def _extract_function_locations(self, file_path: Path, tree: ast.AST):
        """Витягує місцезнаходження функцій з AST для подальшого аналізу."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                if func_name not in self.function_locations:
                    self.function_locations[func_name] = []
                self.function_locations[func_name].append({
                    'file': str(file_path),
                    'line': node.lineno,
                    'end_line': getattr(node, 'end_lineno', node.lineno)
                })

    def _find_critical_issues(self, file_path: Path, source_code: str):
        """Шукає критичні проблеми: мертві команди, тихі збої, помилки для користувача."""
        lines = source_code.split('\n')
        
        for pattern_name, patterns in self.CRITICAL_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, source_code, re.DOTALL):
                    line_num = source_code[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                    
                    issue = {
                        'file': str(file_path),
                        'line': line_num,
                        'pattern_type': pattern_name,
                        'match': match.group(0),
                        'line_content': line_content,
                        'command_or_button': match.group(1) if len(match.groups()) > 0 else None
                    }
                    
                    # Додатковий аналіз для мертвих команд
                    if pattern_name == 'dead_commands' and issue['command_or_button']:
                        command = issue['command_or_button']
                        if command in self.advertised_commands:
                            issue['severity'] = 'critical'
                            issue['description'] = f"Команда /{command} оголошена, але не реалізована або містить NotImplementedError"
                    
                    self.findings['critical'].append(issue)
                    logger.warning(f"Критична проблема у {file_path}:{line_num} - {pattern_name}")

    def _find_localization_and_ux_issues(self, file_path: Path, source_code: str):
        """Шукає проблеми з локалізацією та UX: змішані мови, жорстко закодовані рядки."""
        lines = source_code.split('\n')
        
        # Пошук змішаних мов
        for pattern in self.UX_PATTERNS['mixed_languages']:
            for match in re.finditer(pattern, source_code):
                line_num = source_code[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                
                issue = {
                    'file': str(file_path),
                    'line': line_num,
                    'type': 'mixed_languages',
                    'snippet': match.group(0),
                    'line_content': line_content,
                    'severity': 'high'
                }
                self.findings['localization'].append(issue)
                logger.info(f"Змішана мова у {file_path}:{line_num}")

        # Пошук жорстко закодованих рядків
        for pattern in self.UX_PATTERNS['hardcoded_strings']:
            for match in re.finditer(pattern, source_code):
                text = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                
                # Ігноруємо рядки, які виглядають як шляхи, змінні або технічні повідомлення
                if any(ignore in text for ignore in ['{', '}', '%s', '%d', 'http', '.py', '__', '://', 'API', 'ID', 'token']):
                    continue
                
                # Перевіряємо, чи це не ключ перекладу (не містить крапок або має пробіли)
                if '.' not in text and ' ' in text and len(text) > 5:
                    issue = {
                        'file': str(file_path),
                        'line': line_num,
                        'type': 'hardcoded_string',
                        'text': text,
                        'line_content': line_content,
                        'severity': 'high'
                    }
                    self.findings['localization'].append(issue)
                    logger.info(f"Жорстко закодований рядок у {file_path}:{line_num} - '{text}'")

        # Пошук відсутніх перекладів
        for pattern in self.UX_PATTERNS['missing_localization']:
            for match in re.finditer(pattern, source_code):
                key = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                
                # Перевіряємо, чи ключ існує в обох мовах
                if key not in self.translation_keys['en']:
                    issue = {
                        'file': str(file_path),
                        'line': line_num,
                        'type': 'missing_translation',
                        'key': key,
                        'missing_in': 'en',
                        'line_content': line_content,
                        'severity': 'medium'
                    }
                    self.findings['localization'].append(issue)
                    logger.warning(f"Ключ перекладу {key} відсутній в en.json")
                
                if key not in self.translation_keys['uk']:
                    issue = {
                        'file': str(file_path),
                        'line': line_num,
                        'type': 'missing_translation',
                        'key': key,
                        'missing_in': 'uk',
                        'line_content': line_content,
                        'severity': 'critical'  # Для української мови це критично
                    }
                    self.findings['localization'].append(issue)
                    logger.warning(f"Ключ перекладу {key} відсутній в uk.json")

    def _analyze_buttons(self, file_path: Path, source_code: str):
        """Аналізує кнопки та їхні callback_data."""
        pattern = r'InlineKeyboardButton\(["\']([^"\']+)["\'].*?callback_data=["\']([^"\']+)["\']'
        lines = source_code.split('\n')
        
        for match in re.finditer(pattern, source_code):
            button_text = match.group(1)
            callback_data = match.group(2)
            line_num = source_code[:match.start()].count('\n') + 1
            line_content = lines[line_num - 1] if line_num <= len(lines) else ""

            # Перевіряємо, чи існує обробник для цього callback_data
            handler_exists = False
            
            # Шукаємо обробник в AST
            if file_path in self.ast_cache:
                tree = self.ast_cache[file_path]
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Шукаємо виклики register_callback або подібні
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                                if child.func.id in ['register_callback', 'add_handler', 'CommandHandler']:
                                    if len(child.args) > 0 and isinstance(child.args[0], ast.Str):
                                        if child.args[0].s == callback_data:
                                            handler_exists = True
                                            break
                            elif isinstance(child, ast.Assign):
                                # Шукаємо словники з callback_data
                                if isinstance(child.value, ast.Dict):
                                    for key, value in zip(child.value.keys, child.value.values):
                                        if isinstance(key, ast.Str) and key.s == callback_data:
                                            handler_exists = True
                                            break
                    
                    if handler_exists:
                        break
            
            # Також перевіряємо за іменем функції
            if not handler_exists:
                # Спробуємо знайти функцію з іменем, що відповідає callback_data
                possible_function_names = [
                    f"{callback_data}_callback",
                    f"handle_{callback_data}",
                    callback_data
                ]
                
                for func_name in possible_function_names:
                    if func_name in self.function_locations:
                        handler_exists = True
                        break
            
            issue = {
                'file': str(file_path),
                'line': line_num,
                'button_text': button_text,
                'callback_data': callback_data,
                'handler_exists': handler_exists,
                'line_content': line_content,
                'severity': 'critical' if not handler_exists else 'info'
            }
            self.findings['buttons'].append(issue)
            
            if not handler_exists:
                logger.error(f"Кнопка '{button_text}' (callback: {callback_data}) не має обробника у {file_path}:{line_num}")

    def check_advertised_commands(self):
        """Перевіряє, чи всі оголошені команди мають реалізацію."""
        logger.info("🔍 Перевірка оголошених команд...")
        
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
                    'description': f"Команда /{cmd} оголошена в інтерфейсі, але не має обробника",
                    'severity': 'critical'
                }
                self.findings['critical'].append(issue)
                logger.error(f"❗ Критично: Команда /{cmd} не реалізована!")

    def validate_localization_keys(self):
        """Перевіряє, чи всі ключі перекладу присутні в обох мовах."""
        logger.info("🌍 Перевірка повноти перекладів...")
        
        missing_in_uk = self.translation_keys['en'] - self.translation_keys['uk']
        missing_in_en = self.translation_keys['uk'] - self.translation_keys['en']

        for key in missing_in_uk:
            issue = {
                'key': key,
                'missing_in': 'uk',
                'type': 'missing_translation',
                'severity': 'critical'  # Для української мови це критично
            }
            self.findings['localization'].append(issue)
            logger.error(f"❗ Критично: Відсутній український переклад для ключа '{key}'")

        for key in missing_in_en:
            issue = {
                'key': key,
                'missing_in': 'en',
                'type': 'missing_translation',
                'severity': 'medium'
            }
            self.findings['localization'].append(issue)
            logger.warning(f"Попередження: Відсутній англійський переклад для ключа '{key}'")

    def analyze_user_journeys(self):
        """Аналізує повні шляхи взаємодії користувача."""
        logger.info("🗺️ Аналіз шляхів взаємодії користувача...")
        
        # Визначаємо основні шляхи користувача
        user_journeys = {
            'start_new_session': ['/start', '/new', '/ls', '/cd', '/help'],
            'quick_actions': ['/actions', 'continue', 'export_session', 'save_code'],
            'project_management': ['/projects', '/git', '/schedules'],
            'settings': ['/settings', 'lang:select', 'toggle_language']
        }
        
        # Перевіряємо кожен шлях
        for journey_name, commands in user_journeys.items():
            journey_issues = []
            
            for cmd in commands:
                if cmd.startswith('/'):
                    # Це команда
                    if not any(issue.get('command') == cmd[1:] for issue in self.findings['critical'] if issue.get('status') == 'not_implemented'):
                        # Команда реалізована
                        pass
                    else:
                        journey_issues.append(f"Команда {cmd} не реалізована")
                else:
                    # Це callback
                    if not any(btn.get('callback_data') == cmd and btn.get('handler_exists') for btn in self.findings['buttons']):
                        journey_issues.append(f"Callback {cmd} не має обробника")
            
            if journey_issues:
                issue = {
                    'journey': journey_name,
                    'issues': journey_issues,
                    'type': 'broken_user_journey',
                    'severity': 'high'
                }
                self.findings['ux'].append(issue)
                logger.warning(f"Зламаний шлях користувача '{journey_name}': {', '.join(journey_issues)}")

    def test_integration_points(self):
        """Тестує точки інтеграції зовнішніх систем."""
        logger.info("🔌 Тестування точок інтеграції...")
        
        integration_patterns = {
            'claude_cli': [
                r'claude\s+ask',
                r'claude\s+--version',
                r'from\s+...claude\s+import',
                r'ClaudeIntegration',
                r'ClaudeProcessManager'
            ],
            'file_system': [
                r'os\.(listdir|chdir|getcwd|path)',
                r'shutil\.',
                r'open\(',
                r'with\s+open\('
            ],
            'database': [
                r'import\s+sqlite3',
                r'from\s+aiosqlite',
                r'SessionManager',
                r'StorageManager'
            ],
            'docker': [
                r'docker\s+exec',
                r'docker\s+run',
                r'container',
                r'Dockerfile'
            ]
        }
        
        python_files = list(self.source_dir.rglob("*.py"))
        
        for integration_type, patterns in integration_patterns.items():
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for pattern in patterns:
                        for match in re.finditer(pattern, content):
                            line_num = content[:match.start()].count('\n') + 1
                            
                            # Перевіряємо, чи є належна обробка помилок
                            has_error_handling = False
                            
                            # Шукаємо try-except блоки навколо цього рядка
                            lines = content.split('\n')
                            start_line = max(0, line_num - 5)
                            end_line = min(len(lines), line_num + 5)
                            
                            context = "\n".join(lines[start_line:end_line])
                            if 'try:' in context and ('except' in context or 'finally' in context):
                                has_error_handling = True
                            
                            if not has_error_handling:
                                issue = {
                                    'file': str(file_path),
                                    'line': line_num,
                                    'integration_type': integration_type,
                                    'pattern': pattern,
                                    'match': match.group(0),
                                    'type': 'integration_without_error_handling',
                                    'severity': 'high',
                                    'description': f"Точка інтеграції '{integration_type}' без належної обробки помилок"
                                }
                                self.findings['integration'].append(issue)
                                logger.warning(f"Інтеграція без обробки помилок: {integration_type} у {file_path}:{line_num}")
                                
                except Exception as e:
                    logger.error(f"Помилка при аналізі інтеграції у {file_path}: {e}")

    def generate_report(self) -> str:
        """Генерує звіт про знахідки українською мовою."""
        report_lines = []
        report_lines.append("# 🎯 РОЗШИРЕНИЙ АУДИТ ДОСВІДУ КОРИСТУВАЧА\n")
        report_lines.append(f"**Згенеровано:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_lines.append(f"**Проаналізовано файлів:** {len(self.ast_cache)}\n\n")

        total_issues = sum(len(v) for v in self.findings.values())
        critical_issues = len([i for i in self.findings['critical'] + self.findings['localization'] + self.findings['buttons'] if i.get('severity') == 'critical'])
        high_issues = len([i for i in self.findings['critical'] + self.findings['localization'] + self.findings['ux'] + self.findings['integration'] if i.get('severity') == 'high'])
        medium_issues = len([i for i in self.findings['localization'] if i.get('severity') == 'medium'])
        
        report_lines.append("## 📊 ЗАГАЛЬНИЙ ЗВІТ\n")
        report_lines.append(f"- **Всього проблем знайдено:** {total_issues}\n")
        report_lines.append(f"- **🔴 Критичних (потрібно виправити негайно):** {critical_issues}\n")
        report_lines.append(f"- **🟠 Високого пріоритету (потрібно виправити цього тижня):** {high_issues}\n")
        report_lines.append(f"- **🟡 Середнього пріоритету (поліпшення інтерфейсу):** {medium_issues}\n\n")

        # Критичні проблеми
        critical_findings = [i for i in self.findings['critical'] + self.findings['localization'] + self.findings['buttons'] if i.get('severity') == 'critical']
        if len(critical_findings) > 0:
            report_lines.append("## 🔴 КРИТИЧНІ ПРОБЛЕМИ (ВИПРАВИТИ НЕГАЙНО)\n")
            for i, issue in enumerate(critical_findings, 1):
                if 'command' in issue:
                    report_lines.append(f"### C{i}: НЕПРАЦЮЮЧА КОМАНДА\n")
                    report_lines.append(f"**Проблема:** Команда `/{issue['command']}` оголошена, але не реалізована\n")
                    report_lines.append(f"**Що бачить користувач:** Набирає `/{issue['command']}` → отримує помилку або нічого\n")
                    report_lines.append(f"**Рішення:** Реалізувати обробник команди або прибрати з довідки/меню\n\n")
                elif issue.get('type') == 'missing_translation' and issue.get('missing_in') == 'uk':
                    report_lines.append(f"### C{i}: ВІДСУТНІЙ УКРАЇНСЬКИЙ ПЕРЕКЛАД\n")
                    report_lines.append(f"**Ключ:** `{issue['key']}`\n")
                    report_lines.append(f"**Що бачить користувач:** Замість тексту може показуватися ключ перекладу або англійський текст\n")
                    report_lines.append(f"**Рішення:** Додати переклад у `uk.json` файл\n\n")
                elif 'callback_data' in issue and not issue.get('handler_exists', True):
                    report_lines.append(f"### C{i}: НЕПРАЦЮЮЧА КНОПКА\n")
                    report_lines.append(f"**Текст кнопки:** `{issue['button_text']}`\n")
                    report_lines.append(f"**Callback:** `{issue['callback_data']}`\n")
                    report_lines.append(f"**Файл:** `{issue['file']}` (рядок {issue['line']})\n")
                    report_lines.append(f"**Що бачить користувач:** Натискає кнопку → нічого не відбувається або помилка\n")
                    report_lines.append(f"**Рішення:** Реалізувати обробник або прибрати кнопку\n\n")
                else:
                    report_lines.append(f"### C{i}: {issue.get('pattern_type', 'Невідома проблема')}\n")
                    report_lines.append(f"**Файл:** `{issue['file']}` (рядок {issue['line']})\n")
                    report_lines.append(f"**Код:** `{issue.get('match', issue.get('line_content', ''))}`\n")
                    report_lines.append(f"**Рішення:** Перевірити логіку обробки та додати коректну відповідь користувачу\n\n")

        # Проблеми високого пріоритету
        high_findings = [i for i in self.findings['critical'] + self.findings['localization'] + self.findings['ux'] + self.findings['integration'] if i.get('severity') == 'high']
        if len(high_findings) > 0:
            report_lines.append("## 🟠 ПРОБЛЕМИ ВИСОКОГО ПРІОРИТЕТУ (ВИПРАВИТИ ЦЬОГО ТИЖНЯ)\n")
            for i, issue in enumerate(high_findings, 1):
                if issue.get('type') == 'mixed_languages':
                    report_lines.append(f"### H{i}: ЗМІШАНІ МОВИ\n")
                    report_lines.append(f"**Файл:** `{issue['file']}` (рядок {issue['line']})\n")
                    report_lines.append(f"**Фрагмент:** `{issue['snippet']}`\n")
                    report_lines.append(f"**Що бачить користувач:** Український інтерфейс з англійськими помилками\n")
                    report_lines.append(f"**Рішення:** Перекласти повідомлення повністю українською\n\n")
                elif issue.get('type') == 'hardcoded_string':
                    report_lines.append(f"### H{i}: ЖОРСТКО ЗАКОДОВАНИЙ РЯДОК\n")
                    report_lines.append(f"**Файл:** `{issue['file']}` (рядок {issue['line']})\n")
                    report_lines.append(f"**Текст:** `{issue['text']}`\n")
                    report_lines.append(f"**Що бачить користувач:** Текст, який не змінюється при зміні мови\n")
                    report_lines.append(f"**Рішення:** Винести текст у файли перекладів та використовувати функцію локалізації\n\n")
                elif issue.get('type') == 'broken_user_journey':
                    report_lines.append(f"### H{i}: ЗЛАМАНИЙ ШЛЯХ КОРИСТУВАЧА\n")
                    report_lines.append(f"**Шлях:** `{issue['journey']}`\n")
                    report_lines.append(f"**Проблеми:** {', '.join(issue['issues'])}\n")
                    report_lines.append(f"**Що бачить користувач:** Не може завершити очікувану дію\n")
                    report_lines.append(f"**Рішення:** Реалізувати відсутні команди або обробники кнопок\n\n")
                elif issue.get('type') == 'integration_without_error_handling':
                    report_lines.append(f"### H{i}: ІНТЕГРАЦІЯ БЕЗ ОБРОБКИ ПОМИЛОК\n")
                    report_lines.append(f"**Тип інтеграції:** `{issue['integration_type']}`\n")
                    report_lines.append(f"**Файл:** `{issue['file']}` (рядок {issue['line']})\n")
                    report_lines.append(f"**Що бачить користувач:** Технічні помилки замість зрозумілих повідомлень\n")
                    report_lines.append(f"**Рішення:** Додати try-except блоки з локалізованими повідомленнями про помилки\n\n")

        # Проблеми середнього пріоритету
        medium_findings = [i for i in self.findings['localization'] if i.get('severity') == 'medium']
        if len(medium_findings) > 0:
            report_lines.append("## 🟡 ПРОБЛЕМИ СЕРЕДНЬОГО ПРІОРИТЕТУ (ПОЛІПШЕННЯ ІНТЕРФЕЙСУ)\n")
            for i, issue in enumerate(medium_findings, 1):
                if issue.get('type') == 'missing_translation' and issue.get('missing_in') == 'en':
                    report_lines.append(f"### M{i}: ВІДСУТНІЙ АНГЛІЙСЬКИЙ ПЕРЕКЛАД\n")
                    report_lines.append(f"**Ключ:** `{issue['key']}`\n")
                    report_lines.append(f"**Рішення:** Додати переклад у `en.json` файл для підтримки англомовних користувачів\n\n")

        if total_issues == 0:
            report_lines.append("## 🎉 ВІТАЄМО!\n")
            report_lines.append("Критичних проблем не знайдено. Бот готовий до використання!\n")

        # Додамо метрики якості
        report_lines.append("## 📈 МЕТРИКИ ЯКОСТІ\n")
        metrics = self.get_quality_metrics()
        report_lines.append(f"- **Покриття українською локалізацією:** {metrics['localization_coverage_uk']}\n")
        report_lines.append(f"- **Критичних проблем:** {metrics['critical_issues_count']}\n")
        report_lines.append(f"- **Жорстко закодованих рядків:** {metrics['hardcoded_strings_count']}\n")
        report_lines.append(f"- **Відсутніх українських перекладів:** {metrics['missing_translations_uk']}\n")
        report_lines.append(f"- **Реалізованих оголошених команд:** {metrics['advertised_commands_implemented']} з {len(self.advertised_commands)}\n")

        return "\n".join(report_lines)

    def save_report(self, filename: str = "advanced_audit_report_ua.md"):
        """Зберігає звіт у файл."""
        report_content = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logger.info(f"✅ Звіт збережено у {filename}")

    def get_quality_metrics(self) -> Dict[str, Any]:
        """Повертає метрики якості."""
        total_keys = len(self.translation_keys['en'])
        uk_coverage = len(self.translation_keys['uk']) / total_keys if total_keys > 0 else 0

        return {
            'localization_coverage_uk': f"{uk_coverage:.1%}",
            'critical_issues_count': len([i for i in self.findings['critical'] + self.findings['localization'] + self.findings['buttons'] if i.get('severity') == 'critical']),
            'hardcoded_strings_count': len([i for i in self.findings['localization'] if i.get('type') == 'hardcoded_string']),
            'missing_translations_uk': len([i for i in self.findings['localization'] if i.get('missing_in') == 'uk']),
            'advertised_commands_implemented': len(self.advertised_commands) - len([i for i in self.findings['critical'] if i.get('status') == 'not_implemented'])
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
        logger.info("✅ Аудит завершено успішно!")

if __name__ == "__main__":
    # Створюємо аудитора
    auditor = AdvancedBotAuditor(source_dir="src", report_lang="uk")
    
    # Запускаємо повний аудит
    auditor.run_full_audit()
    
    print("\n🎉 Аудит завершено успішно!")
    print("📄 Звіт збережено у файлі: advanced_audit_report_ua.md")
    print("🔍 Перегляньте звіт для виправлення проблем у боті!")