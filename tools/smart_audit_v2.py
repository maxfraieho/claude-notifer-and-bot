#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Bot Audit v2.0 - Deep Logic Tree Analysis
Finds REAL problems that users experience, not just code patterns
"""

import re
import json
import ast
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Any
import inspect

class BotLogicAuditor:
    def __init__(self, src_dir="src"):
        self.src_dir = Path(src_dir)
        self.translations = {}
        self.handlers = {}
        self.command_flows = {}
        self.callback_flows = {}
        self.real_issues = []
        
    def load_translations(self):
        """Load and analyze translation files"""
        try:
            with open("src/localization/translations/en.json", "r", encoding="utf-8") as f:
                self.translations['en'] = json.load(f)
            with open("src/localization/translations/uk.json", "r", encoding="utf-8") as f:  
                self.translations['uk'] = json.load(f)
        except Exception as e:
            self.real_issues.append({
                'type': 'CRITICAL',
                'category': 'System',
                'issue': f'Cannot load translation files: {e}',
                'impact': 'Bot cannot start or localize messages',
                'user_experience': 'Complete failure for Ukrainian users'
            })

    def analyze_command_handlers(self):
        """Deep analysis of command handler implementations"""
        handler_files = list(self.src_dir.rglob("*handler*.py"))
        
        for file_path in handler_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                self._analyze_handler_file(file_path, content)
            except Exception as e:
                self.real_issues.append({
                    'type': 'ERROR',
                    'category': 'Handler Analysis',
                    'file': str(file_path),
                    'issue': f'Cannot analyze handler: {e}',
                    'impact': 'Unknown handler issues',
                    'user_experience': 'Potential command failures'
                })

    def _analyze_handler_file(self, file_path: Path, content: str):
        """Analyze individual handler file for real issues"""
        
        # Find direct reply_text with hardcoded strings
        hardcoded_replies = re.findall(r'reply_text\((["\'])(.*?)\1', content, re.DOTALL)
        for quote, text in hardcoded_replies:
            if len(text) > 10 and not text.startswith('await t('):
                self.real_issues.append({
                    'type': 'HIGH',
                    'category': 'Localization',
                    'file': str(file_path),
                    'issue': f'Hardcoded reply: {text[:50]}...',
                    'impact': 'Ukrainian users see English/mixed text',
                    'user_experience': 'Confusing mixed language interface',
                    'fix': 'Replace with await t(update, "translation.key")'
                })
        
        # Find error responses without localization
        error_patterns = [
            r'return.*["\']([^"\']*(?:[Ee]rror|[Ff]ailed|[Nn]ot found)[^"\']*)["\']',
            r'send_message.*["\']([^"\']*❌[^"\']*)["\']',
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if not self._is_localized(match):
                    self.real_issues.append({
                        'type': 'HIGH',
                        'category': 'User Experience',
                        'file': str(file_path),
                        'issue': f'Non-localized error: {match}',
                        'impact': 'Users get technical English errors',
                        'user_experience': 'Frustrating error messages',
                        'fix': 'Use localized error messages from translations'
                    })

        # Find incomplete command implementations
        incomplete_patterns = [
            r'async def (\w+)_handler.*?:\s*pass',
            r'async def (\w+)_handler.*?raise NotImplementedError',
            r'❌.*недоступні',  # Ukrainian "unavailable" messages
            r'❌.*недоступна'   # Ukrainian "unavailable" messages
        ]
        
        for pattern in incomplete_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                self.real_issues.append({
                    'type': 'CRITICAL',
                    'category': 'Functionality',
                    'file': str(file_path),
                    'issue': f'Incomplete handler: {match}',
                    'impact': 'Command advertised but does not work',
                    'user_experience': 'User tries feature → gets error/nothing happens',
                    'fix': 'Implement functionality or remove from menus'
                })

    def _is_localized(self, text: str) -> bool:
        """Check if text appears to be properly localized"""
        # Simple heuristics for localization
        if 'await t(' in text or 't_sync(' in text:
            return True
        if text in str(self.translations.get('en', {})):
            return True
        if text in str(self.translations.get('uk', {})):
            return True
        return False

    def analyze_callback_handlers(self):
        """Analyze button callback handlers for real UX issues"""
        callback_files = list(self.src_dir.rglob("*callback*.py"))
        
        for file_path in callback_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Find callbacks that might fail silently
                callback_patterns = [
                    r'async def (\w+_callback).*?pass',
                    r'callback_data\s*==\s*["\'](\w+)["\'].*?pass',
                    r'NotImplementedError.*callback'
                ]
                
                for pattern in callback_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
                    for match in matches:
                        self.real_issues.append({
                            'type': 'HIGH',
                            'category': 'Button Functionality',
                            'file': str(file_path),
                            'issue': f'Incomplete callback: {match}',
                            'impact': 'Button does nothing when pressed',
                            'user_experience': 'User presses button → nothing happens → confusion',
                            'fix': 'Implement callback or remove button'
                        })
                        
            except Exception as e:
                continue

    def analyze_translation_coverage(self):
        """Find translation gaps that cause runtime issues"""
        if not self.translations:
            return
            
        en_keys = self._flatten_dict(self.translations.get('en', {}))
        uk_keys = self._flatten_dict(self.translations.get('uk', {}))
        
        # Find keys missing in Ukrainian that are actually used
        missing_uk = set(en_keys.keys()) - set(uk_keys.keys())
        
        # Find actual usage of these keys in code
        all_py_files = list(self.src_dir.rglob("*.py"))
        for missing_key in missing_uk:
            for py_file in all_py_files:
                try:
                    content = py_file.read_text(encoding="utf-8")
                    if missing_key in content:
                        self.real_issues.append({
                            'type': 'HIGH',
                            'category': 'Runtime Localization',
                            'file': str(py_file),
                            'issue': f'Code uses missing Ukrainian key: {missing_key}',
                            'impact': 'Ukrainian users see key names instead of text',
                            'user_experience': 'Broken interface with technical key names',
                            'fix': f'Add "{missing_key}" to uk.json translations'
                        })
                        break
                except:
                    continue

    def analyze_menu_consistency(self):
        """Check if advertised features actually work"""
        
        # Common bot menu items that should be implemented
        expected_commands = [
            '/new', '/continue', '/help', '/start', '/status', 
            '/projects', '/actions', '/git', '/ls', '/cd'
        ]
        
        # Check if handlers exist for these commands
        handler_files = list(self.src_dir.rglob("*handler*.py"))
        found_handlers = set()
        
        for file_path in handler_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                for cmd in expected_commands:
                    cmd_name = cmd[1:]  # remove /
                    if f"{cmd_name}_handler" in content or f'"{cmd}"' in content:
                        found_handlers.add(cmd)
            except:
                continue
        
        missing_commands = set(expected_commands) - found_handlers
        for cmd in missing_commands:
            self.real_issues.append({
                'type': 'CRITICAL',
                'category': 'Missing Functionality',
                'issue': f'Command {cmd} advertised but no handler found',
                'impact': 'Users expect this command to work',
                'user_experience': f'User types {cmd} → gets error or no response',
                'fix': f'Implement {cmd}_handler or remove from help/menus'
            })

    def analyze_error_handling_quality(self):
        """Find places where errors are not user-friendly"""
        
        error_files = list(self.src_dir.rglob("*.py"))
        
        bad_error_patterns = [
            r'except.*:\s*pass',  # Silent failures
            r'except.*:\s*print\(',  # Console-only errors
            r'raise Exception\(["\']([^"\']+)["\']',  # Generic exceptions
            r'logger\.error\(["\']([^"\']+)["\'].*\n.*reply_text',  # Log + raw reply
        ]
        
        for file_path in error_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                for pattern in bad_error_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        self.real_issues.append({
                            'type': 'MEDIUM',
                            'category': 'Error Handling',
                            'file': str(file_path),
                            'issue': f'Poor error handling: {match[:50] if isinstance(match, str) else "Silent failure"}',
                            'impact': 'Users get confusing or no error messages',
                            'user_experience': 'When something fails, user has no idea why',
                            'fix': 'Add user-friendly localized error messages'
                        })
                        
            except:
                continue

    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for key comparison"""
        items = []
        for k, v in d.items():
            if k.startswith('_'):  # Skip meta keys
                continue
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def generate_smart_report(self, output_file="smart_audit_report.md"):
        """Generate actionable report focused on real user issues"""
        
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Categorize issues by severity and type
        critical = [i for i in self.real_issues if i['type'] == 'CRITICAL']
        high = [i for i in self.real_issues if i['type'] == 'HIGH']
        medium = [i for i in self.real_issues if i['type'] == 'MEDIUM']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 🔍 Smart Bot Audit Report v2.0\n\n")
            f.write(f"**Generated:** {now}\n")
            f.write(f"**Focus:** Real user experience issues\n\n")
            
            # Executive Summary
            f.write("## 📊 EXECUTIVE SUMMARY\n\n")
            f.write(f"**Total Real Issues Found:** {len(self.real_issues)}\n\n")
            f.write(f"- 🔴 **Critical (User Blocking):** {len(critical)}\n")
            f.write(f"- 🟠 **High (Poor UX):** {len(high)}\n")
            f.write(f"- 🟡 **Medium (Polish Needed):** {len(medium)}\n\n")
            
            if len(critical) > 0:
                f.write("### ⚠️ **IMMEDIATE ACTION REQUIRED**\n")
                f.write(f"**{len(critical)} critical issues** are preventing core functionality!\n\n")
            
            # Critical Issues Section
            if critical:
                f.write("## 🔴 CRITICAL ISSUES (Fix Immediately)\n\n")
                for i, issue in enumerate(critical, 1):
                    f.write(f"### C{i:02d}: {issue['category']}\n")
                    f.write(f"**Issue:** {issue['issue']}\n\n")
                    f.write(f"**User Impact:** {issue['user_experience']}\n\n")
                    if 'file' in issue:
                        f.write(f"**Location:** `{issue['file']}`\n\n")
                    if 'fix' in issue:
                        f.write(f"**Fix:** {issue['fix']}\n\n")
                    f.write("---\n\n")
            
            # High Issues Section  
            if high:
                f.write("## 🟠 HIGH PRIORITY ISSUES (Fix This Week)\n\n")
                for i, issue in enumerate(high, 1):
                    f.write(f"### H{i:02d}: {issue['category']}\n")
                    f.write(f"**Issue:** {issue['issue']}\n\n")
                    f.write(f"**User Impact:** {issue['user_experience']}\n\n")
                    if 'file' in issue:
                        f.write(f"**Location:** `{issue['file']}`\n\n")
                    if 'fix' in issue:
                        f.write(f"**Fix:** {issue['fix']}\n\n")
                    f.write("---\n\n")
            
            # Medium Issues Section
            if medium:
                f.write("## 🟡 MEDIUM PRIORITY ISSUES (Polish & Quality)\n\n")
                for i, issue in enumerate(medium, 1):
                    f.write(f"### M{i:02d}: {issue['category']}\n")
                    f.write(f"**Issue:** {issue['issue']}\n\n")
                    f.write(f"**User Impact:** {issue['user_experience']}\n\n")
                    if 'file' in issue:
                        f.write(f"**Location:** `{issue['file']}`\n\n")
                    if 'fix' in issue:
                        f.write(f"**Fix:** {issue['fix']}\n\n")
                    f.write("---\n\n")
            
            # Action Plan
            f.write("## 🚀 PRIORITIZED ACTION PLAN\n\n")
            f.write("### This Week (Critical)\n")
            for issue in critical[:5]:  # Top 5 critical
                f.write(f"- [ ] Fix {issue['category']}: {issue['issue'][:60]}...\n")
            f.write("\n")
            
            f.write("### Next Week (High Priority)\n")  
            for issue in high[:5]:  # Top 5 high
                f.write(f"- [ ] Improve {issue['category']}: {issue['issue'][:60]}...\n")
            f.write("\n")
            
            f.write("### Future (Polish)\n")
            for issue in medium[:3]:  # Top 3 medium
                f.write(f"- [ ] Polish {issue['category']}: {issue['issue'][:60]}...\n")
        
        return output_file

    def run_full_audit(self):
        """Run complete smart audit"""
        print("🔍 Starting Smart Bot Audit v2.0...")
        
        self.load_translations()
        print("📚 Loaded translations")
        
        self.analyze_command_handlers()  
        print("🎮 Analyzed command handlers")
        
        self.analyze_callback_handlers()
        print("🔘 Analyzed button callbacks")
        
        self.analyze_translation_coverage()
        print("🌐 Analyzed translation coverage")
        
        self.analyze_menu_consistency()
        print("📋 Analyzed menu consistency")
        
        self.analyze_error_handling_quality()
        print("⚠️ Analyzed error handling")
        
        report_file = self.generate_smart_report()
        
        critical_count = len([i for i in self.real_issues if i['type'] == 'CRITICAL'])
        high_count = len([i for i in self.real_issues if i['type'] == 'HIGH'])
        
        print(f"\n✅ Smart audit completed!")
        print(f"📊 Found {len(self.real_issues)} real user issues")
        print(f"🔴 Critical: {critical_count}")
        print(f"🟠 High: {high_count}")
        print(f"📄 Report: {report_file}")
        
        return report_file

if __name__ == "__main__":
    auditor = BotLogicAuditor("src")
    auditor.run_full_audit()