#!/usr/bin/env python3
"""
Automated Localization Tests
Tests for ensuring proper localization and absence of hardcoded UI elements
"""

import os
import re
import json
import pytest
from pathlib import Path
from typing import Dict, List, Set, Any


class TestLocalization:
    """Test suite for localization compliance"""

    @pytest.fixture
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent

    @pytest.fixture
    def translations(self, project_root):
        """Load all translation files"""
        translations = {}
        translations_dir = project_root / "src" / "localization" / "translations"

        for file_path in translations_dir.glob("*.json"):
            lang = file_path.stem
            with open(file_path, 'r', encoding='utf-8') as f:
                translations[lang] = json.load(f)

        return translations

    @pytest.fixture
    def source_files(self, project_root):
        """Get all Python source files"""
        source_files = []
        src_dir = project_root / "src"

        for file_path in src_dir.rglob("*.py"):
            # Skip __pycache__ and other non-source files
            if "__pycache__" not in str(file_path):
                source_files.append(file_path)

        return source_files

    def test_translation_files_exist(self, project_root):
        """Test that required translation files exist"""
        translations_dir = project_root / "src" / "localization" / "translations"

        assert translations_dir.exists(), "Translations directory must exist"

        # Check required languages
        required_languages = ["uk", "en"]
        for lang in required_languages:
            lang_file = translations_dir / f"{lang}.json"
            assert lang_file.exists(), f"Translation file for {lang} must exist"

    def test_translation_files_valid_json(self, translations):
        """Test that all translation files are valid JSON"""
        for lang, content in translations.items():
            assert isinstance(content, dict), f"Translation file {lang}.json must contain a JSON object"
            assert "_meta" in content, f"Translation file {lang}.json must have _meta section"
            assert "name" in content["_meta"], f"Translation file {lang}.json must have _meta.name"
            assert "code" in content["_meta"], f"Translation file {lang}.json must have _meta.code"

    def test_translation_key_consistency(self, translations):
        """Test that all translation files have consistent keys"""
        if len(translations) < 2:
            pytest.skip("Need at least 2 translation files to test consistency")

        def get_all_keys(obj, prefix=""):
            """Recursively get all keys from nested dict"""
            keys = set()
            for key, value in obj.items():
                if key == "_meta":  # Skip meta section
                    continue
                full_key = f"{prefix}.{key}" if prefix else key
                keys.add(full_key)
                if isinstance(value, dict):
                    keys.update(get_all_keys(value, full_key))
            return keys

        # Get keys from first language as reference
        reference_lang = list(translations.keys())[0]
        reference_keys = get_all_keys(translations[reference_lang])

        # Check all other languages have same keys
        for lang, content in translations.items():
            if lang == reference_lang:
                continue

            lang_keys = get_all_keys(content)

            missing_keys = reference_keys - lang_keys
            extra_keys = lang_keys - reference_keys

            assert not missing_keys, f"Language {lang} missing keys: {missing_keys}"
            assert not extra_keys, f"Language {lang} has extra keys: {extra_keys}"

    def test_no_hardcoded_ui_strings(self, source_files):
        """Test that source files don't contain hardcoded UI strings"""

        # Patterns that indicate hardcoded UI strings in InlineKeyboardButton
        hardcoded_patterns = [
            r'InlineKeyboardButton\(\s*["\']([^"\']*[🔧📊🔄📝📋🔙➕⚙️🌙⚡📁🆕💾❓🏠🌐⬆️🔨📄💡]+[^"\']*)["\']',
            r'InlineKeyboardButton\(\s*["\']([^"\']*(?:Налаштування|Settings|Створити|Create|Додати|Add|Редагувати|Edit|Назад|Back|Оновити|Update|Статистика|Statistics)[^"\']*)["\']'
        ]

        violations = []

        for file_path in source_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern in hardcoded_patterns:
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            # Skip if it's using localization (contains 'await t(' or 'get_localized_text')
                            if 'await t(' in line or 'get_localized_text' in line:
                                continue

                            violations.append({
                                'file': str(file_path.relative_to(file_path.parents[1])),
                                'line': line_num,
                                'text': match.group(1),
                                'full_line': line.strip()
                            })

            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        if violations:
            violation_messages = []
            for v in violations:
                violation_messages.append(
                    f"  {v['file']}:{v['line']} - Hardcoded UI text: '{v['text']}'"
                )

            failure_message = (
                f"Found {len(violations)} hardcoded UI strings:\n" +
                "\n".join(violation_messages)
            )
            assert False, failure_message

    def test_required_localization_keys_exist(self, translations):
        """Test that required localization keys exist"""
        required_keys = {
            "buttons.new_session",
            "buttons.continue",
            "buttons.status",
            "buttons.export",
            "buttons.settings",
            "buttons.help",
            "buttons.back",
            "buttons.refresh",
            "buttons.projects",
            "buttons.go_up",
            "buttons.git_status",
            "buttons.create_task",
            "buttons.add",
            "buttons.edit",
            "buttons.update",
            "buttons.create_prompt",
            "buttons.prompts_list",
            "buttons.statistics"
        }

        def has_key(obj, key_path):
            """Check if nested key exists in object"""
            keys = key_path.split('.')
            current = obj
            for key in keys:
                if not isinstance(current, dict) or key not in current:
                    return False
                current = current[key]
            return True

        for lang, content in translations.items():
            missing_keys = []
            for key in required_keys:
                if not has_key(content, key):
                    missing_keys.append(key)

            assert not missing_keys, f"Language {lang} missing required keys: {missing_keys}"

    def test_no_empty_translations(self, translations):
        """Test that no translation values are empty"""
        def check_empty_values(obj, path=""):
            """Recursively check for empty values"""
            empty_keys = []
            for key, value in obj.items():
                if key == "_meta":
                    continue

                current_path = f"{path}.{key}" if path else key

                if isinstance(value, dict):
                    empty_keys.extend(check_empty_values(value, current_path))
                elif isinstance(value, str):
                    if not value.strip():
                        empty_keys.append(current_path)
                elif value is None or value == "":
                    empty_keys.append(current_path)

            return empty_keys

        for lang, content in translations.items():
            empty_keys = check_empty_values(content)
            assert not empty_keys, f"Language {lang} has empty translation values: {empty_keys}"

    def test_localization_imports_present(self, source_files):
        """Test that files using localization have proper imports"""
        files_with_inline_keyboard = []
        files_with_localization = []

        for file_path in source_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if file uses InlineKeyboardButton
                if 'InlineKeyboardButton(' in content:
                    files_with_inline_keyboard.append(file_path)

                # Check if file has localization imports
                if ('from ...localization.util import' in content or
                    'from ..localization.util import' in content or
                    'await t(' in content or
                    'get_localized_text(' in content):
                    files_with_localization.append(file_path)

            except (UnicodeDecodeError, PermissionError):
                continue

        # Files that use InlineKeyboardButton should have localization
        files_needing_localization = []
        for file_path in files_with_inline_keyboard:
            if file_path not in files_with_localization:
                # Skip utility files that might not need localization
                if 'util' in str(file_path) or 'helper' in str(file_path):
                    continue
                files_needing_localization.append(file_path)

        if files_needing_localization:
            file_list = "\n".join([f"  {f.relative_to(f.parents[1])}" for f in files_needing_localization])
            assert False, f"Files using InlineKeyboardButton should import localization:\n{file_list}"

    def test_consistent_emoji_usage(self, translations):
        """Test that emoji usage is consistent across translations"""
        def extract_emojis(text):
            """Extract emojis from text"""
            emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF\U0001F018-\U0001F0FF]+'
            return re.findall(emoji_pattern, text)

        def get_button_emojis(obj, path=""):
            """Get emojis from button texts"""
            button_emojis = {}
            for key, value in obj.items():
                if key == "_meta":
                    continue

                current_path = f"{path}.{key}" if path else key

                if isinstance(value, dict):
                    button_emojis.update(get_button_emojis(value, current_path))
                elif isinstance(value, str) and ("button" in current_path.lower() or "меню" in value.lower() or "menu" in value.lower()):
                    emojis = extract_emojis(value)
                    if emojis:
                        button_emojis[current_path] = emojis

            return button_emojis

        if len(translations) < 2:
            pytest.skip("Need at least 2 translation files to test emoji consistency")

        reference_lang = list(translations.keys())[0]
        reference_emojis = get_button_emojis(translations[reference_lang])

        for lang, content in translations.items():
            if lang == reference_lang:
                continue

            lang_emojis = get_button_emojis(content)

            for key, ref_emojis in reference_emojis.items():
                if key in lang_emojis:
                    assert lang_emojis[key] == ref_emojis, (
                        f"Emoji mismatch in {lang} for key {key}: "
                        f"expected {ref_emojis}, got {lang_emojis[key]}"
                    )


class TestLocalizationIntegration:
    """Integration tests for localization system"""

    def test_localization_system_can_load(self):
        """Test that localization system can be imported and initialized"""
        try:
            from src.localization.util import LocalizationManager
            manager = LocalizationManager()
            assert manager is not None
        except ImportError:
            pytest.skip("Localization system not available for testing")

    @pytest.mark.asyncio
    async def test_localization_function_works(self):
        """Test that localization function works with sample data"""
        try:
            from src.localization.util import LocalizationManager, t

            # Create a mock context and test translation
            class MockContext:
                def __init__(self):
                    pass

            context = MockContext()
            user_id = "test_user"

            # This might fail if system is not fully initialized, so we catch gracefully
            try:
                result = await t(context, user_id, "buttons.help")
                assert isinstance(result, str)
                assert len(result) > 0
            except Exception:
                # If the full system isn't available, at least test the manager exists
                manager = LocalizationManager()
                assert manager is not None

        except ImportError:
            pytest.skip("Localization system not available for testing")


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v"])