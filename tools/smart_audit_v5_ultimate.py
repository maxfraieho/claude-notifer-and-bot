#!/usr/bin/env python3
"""
Smart Audit v5 Ultimate - Найточніший аудитор для знаходження ВСІХ проблем бота
Створено на основі реального тестування та виявлених проблем
"""

import os
import re
import ast
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audit_v5.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UltimateAuditor:
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.src_path = self.project_path / "src"
        self.issues = defaultdict(list)
        self.stats = defaultdict(int)
        
        # Load localization files
        self.translations = self._load_translations()
        
        # Critical patterns based on real testing
        self.critical_patterns = {
            'missing_main_menu_handler': [
                r'Unknown Action.*main_menu',
                r'callback_data.*main_menu',
                r'action.*main_menu'
            ],
            'missing_callback_handlers': [
                r'Unknown Action.*create_new',
                r'Unknown Action.*advanced', 
                r'Unknown Action.*change_dnd',
                r'Невідома дія.*create_new',
                r'Невідома дія.*advanced',
                r'Невідома дія.*change_dnd'
            ],
            'encoding_issues': [
                r'\?\?',  # Question marks instead of emojis
                r'\\u[0-9a-fA-F]{4}',  # Unicode escape sequences
                r'\\x[0-9a-fA-F]{2}'   # Hex escape sequences
            ],
            'hardcoded_ukrainian': [
                r'["\']❌ Невідома дія["\']',
                r'["\']❌ Помилка["\']', 
                r'["\']✅ [^"\']*["\']',
                r'["\'][📊🔧⚡💾🆕🔄][^"\']*["\']'
            ],
            'mixed_languages_critical': [
                r'Unknown Action.*[а-яіїєґА-ЯІЇЄҐ]',
                r'[а-яіїєґА-ЯІЇЄҐ].*Unknown Action',
                r'Error.*[а-яіїєґА-ЯІЇЄҐ]',
                r'[а-яіїєґА-ЯІЇЄҐ].*Error'
            ],
            'broken_schedule_handlers': [
                r'schedule.*create_new',
                r'schedule.*advanced',
                r'schedule.*change_dnd'
            ],
            'missing_t_calls': [
                r'reply_text\(["\'][^"\']*[а-яіїєґА-ЯІЇЄҐ][^"\']*["\']',
                r'edit_message_text\(["\'][^"\']*[а-яіїєґА-ЯІЇЄҐ][^"\']*["\']',
                r'send_message\(["\'][^"\']*[а-яіїєґА-ЯІЇЄҐ][^"\']*["\']'
            ]
        }

    def _load_translations(self) -> Dict[str, Dict]:
        """Load translation files"""
        translations = {}
        
        for lang in ['en', 'uk']:
            try:
                trans_path = self.src_path / "localization" / "translations" / f"{lang}.json"
                if trans_path.exists():
                    with open(trans_path, 'r', encoding='utf-8') as f:
                        translations[lang] = json.load(f)
                        logger.info(f"Loaded {lang} translations from {trans_path}")
            except Exception as e:
                logger.error(f"Failed to load {lang} translations: {e}")
                translations[lang] = {}
        
        return translations

    def audit_callback_handlers(self):
        """Audit callback handlers - найкритичніша проблема"""
        logger.info("🔍 Аудит callback handlers...")
        
        callback_file = self.src_path / "bot" / "handlers" / "callback.py"
        if not callback_file.exists():
            self.issues['critical'].append({
                'file': str(callback_file),
                'line': 0,
                'issue': 'callback.py file not found',
                'description': 'Файл callback.py відсутній - критична проблема',
                'priority': 'CRITICAL'
            })
            return

        content = callback_file.read_text(encoding='utf-8')
        
        # Check for main_menu handler
        if 'main_menu' not in content or 'def.*main_menu' not in content:
            self.issues['critical'].append({
                'file': str(callback_file),
                'line': 0, 
                'issue': 'missing_main_menu_handler',
                'description': 'Відсутній handler для main_menu - причина "Unknown Action: main_menu"',
                'priority': 'CRITICAL',
                'fix': 'Додати async def handle_main_menu_callback'
            })

        # Check for schedule handlers
        missing_schedule_handlers = ['create_new', 'advanced', 'change_dnd']
        for handler in missing_schedule_handlers:
            if f'schedule.*{handler}' not in content:
                self.issues['critical'].append({
                    'file': str(callback_file),
                    'line': 0,
                    'issue': f'missing_schedule_{handler}_handler', 
                    'description': f'Відсутній handler для schedule:{handler}',
                    'priority': 'CRITICAL'
                })

    def audit_encoding_issues(self):
        """Audit encoding and emoji issues"""
        logger.info("🔍 Аудит encoding issues...")
        
        for py_file in self.src_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for question marks instead of emojis
                    if re.search(r'\?\?', line) and any(word in line for word in ['Status', 'Directory', 'Session']):
                        self.issues['critical'].append({
                            'file': str(py_file),
                            'line': i,
                            'issue': 'emoji_encoding_broken',
                            'description': f'Емодзі показуються як ?? у рядку: {line.strip()}',
                            'priority': 'HIGH',
                            'fix': 'Перевірити encoding та використання емодзі'
                        })
                        
            except UnicodeDecodeError:
                self.issues['critical'].append({
                    'file': str(py_file),
                    'line': 0,
                    'issue': 'file_encoding_broken',
                    'description': 'Файл має неправильне encoding',
                    'priority': 'CRITICAL'
                })

    def audit_hardcoded_ukrainian(self):
        """Audit hardcoded Ukrainian strings"""
        logger.info("🔍 Аудит hardcoded Ukrainian strings...")
        
        for py_file in self.src_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for hardcoded Ukrainian error messages
                    if re.search(r'["\']❌ Невідома дія["\']', line):
                        self.issues['high'].append({
                            'file': str(py_file),
                            'line': i,
                            'issue': 'hardcoded_ukrainian_error',
                            'description': f'Hardcoded Ukrainian error: {line.strip()}',
                            'priority': 'HIGH',
                            'fix': 'Замінити на await t(context, user_id, "callback_errors.unknown_action")'
                        })
                        
                    # Check for mixed languages  
                    if re.search(r'Unknown Action.*[а-яіїєґА-ЯІЇЄҐ]', line):
                        self.issues['critical'].append({
                            'file': str(py_file),
                            'line': i,
                            'issue': 'mixed_languages_in_error',
                            'description': f'Mixed English/Ukrainian: {line.strip()}',
                            'priority': 'CRITICAL'
                        })
                        
            except Exception as e:
                logger.error(f"Error reading {py_file}: {e}")

    def audit_missing_translations(self):
        """Audit missing translation keys"""
        logger.info("🔍 Аудит missing translations...")
        
        # Required keys based on testing
        required_keys = [
            'callback_errors.unknown_action',
            'callback_errors.action_not_implemented', 
            'schedule.create_new',
            'schedule.advanced',
            'schedule.change_dnd',
            'commands.main_menu.title',
            'buttons.main_menu'
        ]
        
        for lang in ['uk', 'en']:
            translations = self.translations.get(lang, {})
            
            for key in required_keys:
                if not self._get_nested_key(translations, key):
                    self.issues['high'].append({
                        'file': f'src/localization/translations/{lang}.json',
                        'line': 0,
                        'issue': f'missing_translation_key_{lang}',
                        'description': f'Відсутній ключ перекладу: {key}',
                        'priority': 'HIGH',
                        'fix': f'Додати переклад для {key}'
                    })

    def _get_nested_key(self, d: dict, key: str):
        """Get nested dictionary key like 'a.b.c'"""
        keys = key.split('.')
        value = d
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return None

    def audit_critical_files_structure(self):
        """Audit critical file structure"""
        logger.info("🔍 Аудит critical files structure...")
        
        critical_files = [
            'src/bot/handlers/callback.py',
            'src/bot/handlers/command.py', 
            'src/bot/handlers/scheduled_prompts_handler.py',
            'src/localization/translations/uk.json',
            'src/localization/translations/en.json'
        ]
        
        for file_path in critical_files:
            full_path = self.project_path / file_path
            if not full_path.exists():
                self.issues['critical'].append({
                    'file': file_path,
                    'line': 0,
                    'issue': 'critical_file_missing',
                    'description': f'Критичний файл відсутній: {file_path}',
                    'priority': 'CRITICAL'
                })

    def run_comprehensive_audit(self):
        """Run comprehensive audit"""
        logger.info("🚀 Запуск comprehensive audit v5...")
        
        # Core audits
        self.audit_critical_files_structure()
        self.audit_callback_handlers()
        self.audit_encoding_issues()
        self.audit_hardcoded_ukrainian()
        self.audit_missing_translations()
        
        # Count issues by priority
        for priority in ['critical', 'high', 'medium', 'low']:
            self.stats[priority] = len(self.issues[priority])
        
        self.stats['total'] = sum(self.stats.values())
        
        logger.info(f"🔍 Audit complete. Found {self.stats['total']} issues:")
        logger.info(f"  🔴 Critical: {self.stats['critical']}")
        logger.info(f"  🟠 High: {self.stats['high']}")
        logger.info(f"  🟡 Medium: {self.stats['medium']}")
        logger.info(f"  🟢 Low: {self.stats['low']}")

    def generate_report(self):
        """Generate detailed report"""
        report_lines = [
            "# 🎯 ULTIMATE AUDIT REPORT v5 - Критичні проблеми після тестування",
            "",
            f"**Згенеровано:** {os.popen('date').read().strip()}",
            "",
            f"**Всього проблем знайдено:** {self.stats['total']}",
            "",
            f"- **🔴 Критичних (негайно виправити):** {self.stats['critical']}",
            f"- **🟠 Високого пріоритету (цього тижня):** {self.stats['high']}",
            f"- **🟡 Середнього пріоритету:** {self.stats['medium']}",
            f"- **🟢 Низького пріоритету:** {self.stats['low']}",
            "",
            "## 🔴 КРИТИЧНІ ПРОБЛЕМИ (ВИПРАВИТИ НЕГАЙНО)",
            ""
        ]
        
        # Add critical issues
        for i, issue in enumerate(self.issues['critical'], 1):
            report_lines.extend([
                f"### C{i}: {issue['issue'].upper().replace('_', ' ')}",
                "",
                f"**Файл:** `{issue['file']}:{issue['line']}`",
                "",
                f"**Проблема:** {issue['description']}",
                "",
                f"**Пріоритет:** {issue['priority']}",
                ""
            ])
            
            if 'fix' in issue:
                report_lines.extend([
                    f"**Рішення:** {issue['fix']}",
                    ""
                ])
            
            report_lines.append("")
        
        # Add high priority issues
        if self.issues['high']:
            report_lines.extend([
                "## 🟠 ВИСОКИЙ ПРІОРИТЕТ",
                ""
            ])
            
            for i, issue in enumerate(self.issues['high'], 1):
                report_lines.extend([
                    f"### H{i}: {issue['issue']}",
                    f"- **Файл:** `{issue['file']}:{issue['line']}`",
                    f"- **Проблема:** {issue['description']}",
                    ""
                ])
        
        # Add summary
        report_lines.extend([
            "## 📊 СТАТИСТИКА",
            "",
            f"- Проаналізовано файлів: {len(list(self.src_path.rglob('*.py')))}",
            f"- Критичних проблем: {self.stats['critical']}",
            f"- Проблем високого пріоритету: {self.stats['high']}",
            f"- Загальна кількість проблем: {self.stats['total']}",
            "",
            "## 🎯 НАСТУПНІ КРОКИ",
            "",
            "1. **Негайно виправити критичні проблеми** (відсутні callback handlers)",
            "2. **Виправити encoding issues** (емодзі показуються як ??)",
            "3. **Замінити hardcoded Ukrainian strings** на локалізацію",
            "4. **Додати відсутні переклади**",
            "5. **Протестувати всі команди та кнопки**",
            "",
            "🚀 **Після виправлення цих проблем бот стане повністю функціональним!**"
        ])
        
        return "\n".join(report_lines)

def main():
    auditor = UltimateAuditor()
    auditor.run_comprehensive_audit()
    
    # Generate and save report
    report = auditor.generate_report()
    
    report_file = "ultimate_audit_report_v5.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"🎉 Ultimate audit v5 завершено!")
    print(f"📄 Звіт збережено у файлі: {report_file}")
    print(f"🔍 Знайдено {auditor.stats['total']} проблем")
    print(f"🔴 Критичних: {auditor.stats['critical']}")

if __name__ == "__main__":
    main()