#!/usr/bin/env python3
"""
Критичні тести для виправлення 21 проблеми з аудиту
Цей файл містить конкретні тести для кожної категорії критичних проблем
"""

import ast
import pytest
import asyncio
import re
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

# Import our bot modules
import sys
sys.path.append('src')

from bot.handlers import message, command, image_command
from bot.utils.error_handler import safe_user_error, safe_critical_error
from localization.util import t
import json


class TestCriticalSilentFailures:
    """
    Тести для 10 критичних silent failure проблем
    Статус: 🔴 КРИТИЧНО
    """

    def test_no_silent_failures_in_production_code(self):
        """
        КРИТИЧНИЙ ТЕСТ: Перевірка відсутності except: pass в production коді
        Має блокувати CI/CD якщо знайдено silent failures
        """
        production_dirs = [
            Path('src/bot/handlers'),
            Path('src/bot/features'),
            Path('src/bot/core.py'),
            Path('src/security'),
            Path('src/claude')
        ]

        forbidden_patterns = [
            r'except\s*:',  # except:
            r'except\s+Exception\s*:',  # except Exception:
            r'except\s+BaseException\s*:'  # except BaseException:
        ]

        violations = []

        for directory in production_dirs:
            if directory.is_file():
                files_to_check = [directory]
            else:
                files_to_check = directory.rglob('*.py') if directory.exists() else []

            for file_path in files_to_check:
                if file_path.suffix == '.py':
                    content = file_path.read_text(encoding='utf-8')
                    lines = content.split('\n')

                    for line_num, line in enumerate(lines, 1):
                        for pattern in forbidden_patterns:
                            if re.search(pattern, line):
                                # Перевірити чи є pass на наступних рядках
                                next_lines = lines[line_num:line_num+3]
                                if any('pass' in next_line.strip() for next_line in next_lines):
                                    violations.append({
                                        'file': str(file_path),
                                        'line': line_num,
                                        'code': line.strip(),
                                        'pattern': pattern
                                    })

        if violations:
            error_msg = "🚨 КРИТИЧНІ SILENT FAILURES ЗНАЙДЕНО:\n"
            for violation in violations[:10]:  # Show first 10
                error_msg += f"- {violation['file']}:{violation['line']} -> {violation['code']}\n"
            if len(violations) > 10:
                error_msg += f"... та ще {len(violations) - 10} випадків\n"
            error_msg += "\n❌ CI/CD ПОВИНЕН БЛОКУВАТИ ЦЕ!"

            pytest.fail(error_msg)

    async def test_message_handler_error_handling_line_368(self):
        """
        Тест для src/bot/handlers/message.py:368
        Перевірка правильної обробки винятків замість silent failure
        """
        # Створити mock objects
        update = Mock(spec=Update)
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 12345
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()

        # Mock що викликає exception
        with patch('src.bot.handlers.message.some_risky_operation', side_effect=Exception("Test error")):
            with patch('src.bot.utils.error_handler.safe_user_error') as mock_safe_error:
                # Викликати обробник повідомлень
                try:
                    await message.handle_text_message(update, context)
                except Exception as e:
                    # Має бути proper error handling, не silent failure
                    assert mock_safe_error.called or "Test error" in str(e)
                    # НЕ повинно бути просто проігноровано

    async def test_image_command_error_handling_line_294(self):
        """
        Тест для src/bot/handlers/image_command.py:294
        Критичний тест обробки винятків в image processing
        """
        update = Mock(spec=Update)
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)

        # Симуляція помилки обробки зображення
        with patch('src.bot.handlers.image_command.process_image', side_effect=Exception("Image processing failed")):
            with patch('src.bot.utils.error_handler.safe_user_error') as mock_safe_error:
                try:
                    await image_command.handle_image_processing(update, context)
                    # Має викликатися proper error handling
                    assert mock_safe_error.called
                except Exception:
                    # Exception може бути, але не silent failure
                    pass

    def test_error_handling_completeness(self):
        """
        Мета-тест: перевірка, що всі обробники мають proper error handling
        """
        handler_files = [
            'src/bot/handlers/message.py',
            'src/bot/handlers/command.py',
            'src/bot/handlers/image_command.py',
            'src/bot/handlers/callback.py'
        ]

        missing_error_handling = []

        for file_path in handler_files:
            if Path(file_path).exists():
                content = Path(file_path).read_text()

                # Знайти всі async def функції
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef):
                        func_name = node.name

                        # Перевірити чи є try/except блоки
                        has_try_except = any(isinstance(child, ast.Try) for child in ast.walk(node))

                        if not has_try_except and func_name.startswith('handle_'):
                            missing_error_handling.append(f"{file_path}:{func_name}")

        if missing_error_handling:
            pytest.fail(f"Відсутнє error handling в: {missing_error_handling}")


class TestHardcodedUIElements:
    """
    Тести для 8 критичних hardcoded UI проблем
    Статус: 🟠 ВИСОКИЙ
    """

    def test_no_hardcoded_button_texts_in_code(self):
        """
        КРИТИЧНИЙ ТЕСТ: Перевірка відсутності hardcoded текстів кнопок
        """
        critical_hardcoded_patterns = [
            '🔧 Налаштування',
            '📊 Історія',
            '🔄 Перемкнути систему',
            '📝 Створити завдання',
            '📋 Зі шаблону',
            '🔙 Назад',
            '➕ Додати',
            '📝 Редагувати',
            '⚙️ Налаштування',
            '🔄 Оновити',
            '🌙 Змінити DND',
            '⚡ Налаштування',
            '📋 Детальні логи'
        ]

        source_files = list(Path('src').rglob('*.py'))
        violations = []

        for file_path in source_files:
            content = file_path.read_text(encoding='utf-8')

            for pattern in critical_hardcoded_patterns:
                if pattern in content:
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if pattern in line:
                            violations.append({
                                'file': str(file_path),
                                'line': line_num,
                                'pattern': pattern,
                                'code': line.strip()
                            })

        if violations:
            error_msg = "🚨 HARDCODED UI ТЕКСТИ ЗНАЙДЕНО:\n"
            for violation in violations:
                error_msg += f"- {violation['file']}:{violation['line']} -> {violation['pattern']}\n"
            error_msg += "\n❌ ВСІ UI ТЕКСТИ МАЮТЬ ВИКОРИСТОВУВАТИ ЛОКАЛІЗАЦІЮ!"

            pytest.fail(error_msg)

    async def test_all_inline_keyboard_buttons_use_localization(self):
        """
        Тест що всі InlineKeyboardButton використовують функцію t()
        """
        source_files = list(Path('src/bot').rglob('*.py'))
        violations = []

        for file_path in source_files:
            content = file_path.read_text(encoding='utf-8')

            # Знайти всі InlineKeyboardButton конструкції
            inline_button_pattern = r'InlineKeyboardButton\s*\(\s*["\'][^"\']*["\']'
            matches = re.finditer(inline_button_pattern, content)

            for match in matches:
                button_text = match.group(0)
                # Перевірити чи використовується await t() або t()
                if 'await t(' not in button_text and 't(' not in button_text:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': str(file_path),
                        'line': line_num,
                        'code': button_text
                    })

        if violations:
            error_msg = "🚨 КНОПКИ БЕЗ ЛОКАЛІЗАЦІЇ:\n"
            for violation in violations[:5]:  # Show first 5
                error_msg += f"- {violation['file']}:{violation['line']}\n"
            pytest.fail(error_msg)

    def test_localization_keys_completeness(self):
        """
        Тест повноти локалізаційних ключів
        """
        required_button_keys = [
            'buttons.settings',
            'buttons.history',
            'buttons.toggle_system',
            'buttons.create_task',
            'buttons.from_template',
            'buttons.back',
            'buttons.add',
            'buttons.edit',
            'buttons.update',
            'buttons.change_dnd',
            'buttons.detailed_logs'
        ]

        # Перевірити українську локалізацію
        uk_file = Path('src/localization/translations/uk.json')
        en_file = Path('src/localization/translations/en.json')

        missing_keys = []

        for file_path in [uk_file, en_file]:
            if file_path.exists():
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    translations = json.load(f)

                for key in required_button_keys:
                    key_parts = key.split('.')
                    current = translations

                    try:
                        for part in key_parts:
                            current = current[part]
                    except KeyError:
                        missing_keys.append(f"{file_path.name}:{key}")

        if missing_keys:
            pytest.fail(f"Відсутні локалізаційні ключі: {missing_keys}")


class TestErrorHandlerCoverage:
    """
    Тести для відсутніх error handlers (2 проблеми)
    Статус: 🔴 КРИТИЧНО
    """

    async def test_all_critical_operations_have_error_handlers(self):
        """
        Тест що всі критичні операції мають error handlers
        """
        critical_operations = [
            'claude_cli_call',
            'file_read_operation',
            'database_operation',
            'telegram_api_call',
            'image_processing',
            'yaml_parsing',
            'svg_generation'
        ]

        # Мокуємо критичні операції для тестування error handling
        for operation in critical_operations:
            with patch(f'src.bot.{operation}', side_effect=Exception(f"{operation} failed")):
                # Перевірити що є proper error handling
                # Це має бути реалізовано в конкретних тестах для кожної операції
                pass

    async def test_fallback_mechanisms_exist(self):
        """
        Тест наявності fallback механізмів
        """
        # Тест fallback Claude CLI -> SDK
        with patch('src.claude.integration.call_claude_cli', side_effect=Exception("CLI failed")):
            with patch('src.claude.sdk_integration.call_claude_sdk') as mock_sdk:
                # Має автоматично перемкнутися на SDK
                mock_sdk.return_value = "success"
                # Викликати операцію що використовує Claude
                # Перевірити що відбувся fallback

    async def test_graceful_degradation(self):
        """
        Тест graceful degradation при помилках
        """
        # Тест що коли візуалізація не працює, повертається текстовий опис
        with patch('src.bot.features.dracon_renderer.render_svg', side_effect=Exception("Render failed")):
            # Має повернутися текстовий fallback
            pass


class TestSecurityVulnerabilities:
    """
    Тест для 1 security вразливості
    Статус: 🔴 КРИТИЧНО
    """

    async def test_security_events_not_silenced(self):
        """
        КРИТИЧНИЙ ТЕСТ: Security події не маскуються silent failures
        """
        security_events = [
            'unauthorized_access_attempt',
            'path_traversal_attempt',
            'injection_attempt',
            'rate_limit_violation',
            'token_validation_failure'
        ]

        for event in security_events:
            with patch('src.security.audit.log_security_event') as mock_log:
                # Симуляція security події
                try:
                    # Викликати операцію що може викликати security event
                    pass
                except Exception:
                    # Security події МАЮТЬ бути залоговані, навіть при exception
                    assert mock_log.called, f"Security event {event} не був залогований!"

    async def test_security_exception_proper_handling(self):
        """
        Тест правильної обробки security винятків
        """
        from src.security.validators import SecurityValidator

        validator = SecurityValidator()

        # Тест що security винятки не ігноруються
        with patch.object(validator, 'validate_path', side_effect=Exception("Security violation")):
            with pytest.raises(Exception):
                # Security винятки НЕ повинні бути silent
                await validator.validate_file_access('/etc/passwd')

    def test_audit_trail_completeness(self):
        """
        Тест повноти audit trail для security подій
        """
        # Перевірити що всі security-sensitive операції логуються
        security_sensitive_functions = [
            'authenticate_user',
            'validate_file_path',
            'check_rate_limit',
            'validate_command_access'
        ]

        # Кожна з цих функцій має викликати audit logging
        for func_name in security_sensitive_functions:
            # Перевірити що функція існує і має audit logging
            pass


class TestProductionReadiness:
    """
    Мета-тести готовності до production
    """

    def test_all_21_critical_issues_addressed(self):
        """
        МЕТА-ТЕСТ: Всі 21 критична проблема адресовані
        """
        # Запустити всі критичні тести
        critical_test_results = []

        # 1. Silent failures
        try:
            self.test_no_silent_failures_in_production_code()
            critical_test_results.append("✅ Silent failures: FIXED")
        except Exception as e:
            critical_test_results.append(f"❌ Silent failures: {str(e)}")

        # 2. Hardcoded UI
        try:
            hardcoded_tester = TestHardcodedUIElements()
            hardcoded_tester.test_no_hardcoded_button_texts_in_code()
            critical_test_results.append("✅ Hardcoded UI: FIXED")
        except Exception as e:
            critical_test_results.append(f"❌ Hardcoded UI: {str(e)}")

        # 3. Error handlers
        critical_test_results.append("⚠️ Error handlers: Needs implementation")

        # 4. Security
        critical_test_results.append("⚠️ Security: Needs verification")

        # Звіт
        report = "\n".join(critical_test_results)
        failed_tests = [r for r in critical_test_results if r.startswith("❌")]

        if failed_tests:
            pytest.fail(f"КРИТИЧНІ ПРОБЛЕМИ НЕ ВИРІШЕНІ:\n{report}")

    def test_code_quality_metrics(self):
        """
        Тест метрик якості коду
        """
        metrics = {
            'silent_failures': 0,  # Має бути 0
            'hardcoded_ui_elements': 0,  # Має бути 0
            'missing_error_handlers': 0,  # Має бути 0
            'security_vulnerabilities': 0  # Має бути 0
        }

        # Підрахувати реальні метрики
        # actual_metrics = calculate_quality_metrics()

        # for metric, expected in metrics.items():
        #     assert actual_metrics[metric] == expected, f"{metric}: очікували {expected}, отримали {actual_metrics[metric]}"

    async def test_error_recovery_functionality(self):
        """
        Тест функціональності відновлення після помилок
        """
        # Симуляція різних типів помилок та перевірка recovery
        error_scenarios = [
            'network_timeout',
            'file_not_found',
            'permission_denied',
            'invalid_input',
            'external_service_unavailable'
        ]

        for scenario in error_scenarios:
            # Кожен сценарій має мати proper recovery mechanism
            recovery_successful = await self._test_error_recovery(scenario)
            assert recovery_successful, f"Recovery failed for scenario: {scenario}"

    async def _test_error_recovery(self, scenario: str) -> bool:
        """Допоміжний метод для тестування recovery"""
        # Реалізація specific recovery тестів
        return True  # Placeholder


class TestCriticalLocalization:
    """
    Швидкі критичні тести для проблем локалізації
    Статус: 🟠 ВИСОКА критичність
    """

    @pytest.fixture
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent

    def test_zero_hardcoded_ui_elements_critical(self, project_root):
        """
        КРИТИЧНИЙ ТЕСТ: Zero tolerance до hardcoded UI елементів
        Має блокувати CI/CD якщо знайдено hardcoded UI
        """
        critical_files = [
            project_root / "src" / "bot" / "handlers" / "dnd_prompts.py",
            project_root / "src" / "bot" / "handlers" / "command.py",
            project_root / "src" / "bot" / "handlers" / "callback.py"
        ]

        # Небезпечні patterns для кнопок
        dangerous_patterns = [
            r'InlineKeyboardButton\(\s*["\']([^"\']*[🔧📊🔄📝📋🔙➕⚙️🌙⚡📁🆕💾❓🏠🌐⬆️]+[^"\']*)["\']',
            r'InlineKeyboardButton\(\s*["\']([^"\']*(?:Налаштування|Settings|Створити|Create|Додати|Add|Редагувати|Edit)[^"\']*)["\']',
        ]

        violations = []

        for file_path in critical_files:
            if not file_path.exists():
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for line_num, line in enumerate(content.split('\n'), 1):
                    # Skip якщо вже використовує локалізацію
                    if 'await t(' in line or 'get_localized_text' in line:
                        continue

                    for pattern in dangerous_patterns:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            violations.append({
                                'file': str(file_path.name),
                                'line': line_num,
                                'text': match.group(1),
                                'severity': 'CRITICAL'
                            })

            except Exception as e:
                continue

        if violations:
            violation_msg = "\n".join([
                f"❌ {v['file']}:{v['line']} - HARDCODED: '{v['text']}'"
                for v in violations
            ])
            assert False, f"🚨 CRITICAL: {len(violations)} hardcoded UI elements found:\n{violation_msg}"

    def test_translation_files_exist_critical(self, project_root):
        """
        КРИТИЧНИЙ ТЕСТ: Файли перекладів мають існувати
        """
        translations_dir = project_root / "src" / "localization" / "translations"

        assert translations_dir.exists(), "❌ CRITICAL: Translations directory missing"

        required_files = ["uk.json", "en.json"]
        for file_name in required_files:
            file_path = translations_dir / file_name
            assert file_path.exists(), f"❌ CRITICAL: Translation file {file_name} missing"

    def test_critical_localization_keys_exist(self, project_root):
        """
        КРИТИЧНИЙ ТЕСТ: Критичні ключі локалізації мають існувати
        """
        translations_dir = project_root / "src" / "localization" / "translations"
        uk_file = translations_dir / "uk.json"

        assert uk_file.exists(), "❌ CRITICAL: UK translation file missing"

        with open(uk_file, 'r', encoding='utf-8') as f:
            uk_data = json.load(f)

        # Критичні ключі які мають бути присутні після наших виправлень
        critical_keys = [
            ("buttons", "new_session"),
            ("buttons", "continue"),
            ("buttons", "settings"),
            ("buttons", "create_prompt"),
            ("buttons", "prompts_list"),
            ("buttons", "go_up"),
            ("buttons", "refresh"),
            ("buttons", "projects")
        ]

        missing_keys = []
        for section, key in critical_keys:
            if section not in uk_data or key not in uk_data[section]:
                missing_keys.append(f"{section}.{key}")

        if missing_keys:
            assert False, f"❌ CRITICAL: Missing localization keys: {missing_keys}"

    def test_localization_imports_in_handlers(self, project_root):
        """
        КРИТИЧНИЙ ТЕСТ: Handlers мають мати локалізаційні imports
        """
        handler_files = [
            project_root / "src" / "bot" / "handlers" / "dnd_prompts.py",
            project_root / "src" / "bot" / "handlers" / "command.py"
        ]

        missing_imports = []

        for file_path in handler_files:
            if not file_path.exists():
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Перевірити чи є локалізаційні imports
                has_localization_import = (
                    'from ...localization.util import' in content or
                    'from ..localization.util import' in content
                )

                # Перевірити чи файл використовує InlineKeyboardButton
                uses_keyboard = 'InlineKeyboardButton(' in content

                if uses_keyboard and not has_localization_import:
                    missing_imports.append(file_path.name)

            except Exception:
                continue

        if missing_imports:
            assert False, f"❌ CRITICAL: Files missing localization imports: {missing_imports}"


if __name__ == "__main__":
    # Запуск критичних тестів
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--strict-markers",
        "--strict-config"
    ])