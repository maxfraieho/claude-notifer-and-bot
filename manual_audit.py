#!/usr/bin/env python3
"""
Manual Security and Performance Audit for Claude Telegram Bot
Focus on critical issues without complex imports
"""

import ast
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class CriticalIssue:
    severity: str
    category: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str
    fix_recommendation: str

class ManualBotAuditor:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues: List[CriticalIssue] = []

    def run_audit(self):
        """Run comprehensive manual audit"""
        print("🔍 Starting manual security and performance audit...")

        # 1. Security vulnerabilities
        self.check_security_issues()

        # 2. Performance bottlenecks
        self.check_performance_issues()

        # 3. Stability problems
        self.check_stability_issues()

        # 4. Architecture problems
        self.check_architecture_issues()

        return self.generate_report()

    def check_security_issues(self):
        """Check for security vulnerabilities"""
        print("🔒 Checking security vulnerabilities...")

        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                # Check for various security issues
                self._check_sql_injection(file_path, content, lines)
                self._check_path_traversal(file_path, content, lines)
                self._check_command_injection(file_path, content, lines)
                self._check_hardcoded_secrets(file_path, content, lines)
                self._check_unsafe_deserialization(file_path, content, lines)
                self._check_authentication_bypass(file_path, content, lines)

            except Exception as e:
                self.issues.append(CriticalIssue(
                    severity="HIGH",
                    category="PARSING_ERROR",
                    description=f"Cannot parse file for security analysis: {e}",
                    file_path=str(file_path),
                    line_number=0,
                    code_snippet="",
                    fix_recommendation="Fix syntax errors in file"
                ))

    def check_performance_issues(self):
        """Check for performance bottlenecks"""
        print("⚡ Checking performance issues...")

        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                self._check_blocking_operations(file_path, content, lines)
                self._check_memory_leaks(file_path, content, lines)
                self._check_inefficient_loops(file_path, content, lines)
                self._check_database_n_plus_one(file_path, content, lines)

            except Exception as e:
                pass  # Skip parsing errors for performance check

    def check_stability_issues(self):
        """Check for stability problems"""
        print("🛡️ Checking stability issues...")

        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                self._check_exception_handling(file_path, content, lines)
                self._check_resource_management(file_path, content, lines)
                self._check_callback_errors(file_path, content, lines)
                self._check_async_await_issues(file_path, content, lines)

            except Exception as e:
                pass

    def check_architecture_issues(self):
        """Check for architecture problems"""
        print("🏗️ Checking architecture issues...")

        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                self._check_circular_imports(file_path, content, lines)
                self._check_god_objects(file_path, content, lines)
                self._check_dependency_injection(file_path, content, lines)

            except Exception as e:
                pass

    def _check_sql_injection(self, file_path: Path, content: str, lines: List[str]):
        """Check for SQL injection vulnerabilities"""
        # Look for string formatting in SQL queries
        sql_patterns = [
            r'execute\s*\(\s*["\'][^"\']*%[sd][^"\']*["\']',
            r'execute\s*\(\s*f["\'][^"\']*\{[^}]*\}[^"\']*["\']',
            r'\.format\s*\([^)]*\).*execute',
            r'query\s*\(\s*["\'][^"\']*%[sd][^"\']*["\']'
        ]

        for i, line in enumerate(lines, 1):
            for pattern in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(CriticalIssue(
                        severity="CRITICAL",
                        category="SQL_INJECTION",
                        description="Potential SQL injection through string formatting",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Use parameterized queries with placeholders (?)"
                    ))

    def _check_path_traversal(self, file_path: Path, content: str, lines: List[str]):
        """Check for path traversal vulnerabilities"""
        dangerous_patterns = [
            r'open\s*\([^)]*user[^)]*\)',
            r'Path\s*\([^)]*user[^)]*\)',
            r'os\.path\.join\s*\([^)]*user[^)]*\)',
            r'file_path.*input',
            r'filename.*get',
        ]

        for i, line in enumerate(lines, 1):
            for pattern in dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if '..' not in line:  # Skip if already checking for traversal
                        continue
                    self.issues.append(CriticalIssue(
                        severity="CRITICAL",
                        category="PATH_TRAVERSAL",
                        description="Potential path traversal vulnerability with user input",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Validate and sanitize file paths, use os.path.abspath and check within allowed directory"
                    ))

    def _check_command_injection(self, file_path: Path, content: str, lines: List[str]):
        """Check for command injection vulnerabilities"""
        dangerous_patterns = [
            r'subprocess\.(run|call|Popen)\s*\([^)]*user[^)]*shell\s*=\s*True',
            r'os\.system\s*\([^)]*user[^)]*\)',
            r'os\.popen\s*\([^)]*user[^)]*\)',
            r'shell=True.*user',
        ]

        for i, line in enumerate(lines, 1):
            for pattern in dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(CriticalIssue(
                        severity="CRITICAL",
                        category="COMMAND_INJECTION",
                        description="Potential command injection with user input and shell=True",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Use shell=False and validate input, or use shlex.split() for command parsing"
                    ))

    def _check_hardcoded_secrets(self, file_path: Path, content: str, lines: List[str]):
        """Check for hardcoded secrets"""
        secret_patterns = [
            r'token\s*=\s*["\'][A-Za-z0-9+/]{20,}["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][A-Za-z0-9+/]{20,}["\']',
            r'secret\s*=\s*["\'][A-Za-z0-9+/]{20,}["\']',
        ]

        for i, line in enumerate(lines, 1):
            for pattern in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip test files and examples
                    if 'test' in str(file_path).lower() or 'example' in line.lower():
                        continue
                    self.issues.append(CriticalIssue(
                        severity="HIGH",
                        category="HARDCODED_SECRET",
                        description="Hardcoded secret/token/password found",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip()[:50] + "...",
                        fix_recommendation="Move secrets to environment variables or secure configuration"
                    ))

    def _check_unsafe_deserialization(self, file_path: Path, content: str, lines: List[str]):
        """Check for unsafe deserialization"""
        dangerous_patterns = [
            r'pickle\.loads?\s*\([^)]*user[^)]*\)',
            r'eval\s*\([^)]*user[^)]*\)',
            r'exec\s*\([^)]*user[^)]*\)',
            r'yaml\.load\s*\([^)]*\)',  # Without safe_load
        ]

        for i, line in enumerate(lines, 1):
            for pattern in dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(CriticalIssue(
                        severity="CRITICAL",
                        category="UNSAFE_DESERIALIZATION",
                        description="Unsafe deserialization that could lead to code execution",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Use safe deserialization methods like json.loads or yaml.safe_load"
                    ))

    def _check_blocking_operations(self, file_path: Path, content: str, lines: List[str]):
        """Check for blocking operations in async context"""
        blocking_patterns = [
            r'requests\.(get|post|put|delete)',
            r'urllib\.request',
            r'time\.sleep',
            r'input\s*\(',
            r'open\s*\([^)]*\)(?!.*async)',
        ]

        # Check if we're in an async function
        in_async_func = False
        for i, line in enumerate(lines, 1):
            if re.search(r'async\s+def', line):
                in_async_func = True
            elif re.search(r'^def\s+', line.strip()):
                in_async_func = False
            elif re.search(r'^class\s+', line.strip()):
                in_async_func = False

            if in_async_func:
                for pattern in blocking_patterns:
                    if re.search(pattern, line):
                        self.issues.append(CriticalIssue(
                            severity="HIGH",
                            category="BLOCKING_OPERATION",
                            description="Blocking operation in async function - can cause performance issues",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip(),
                            fix_recommendation="Use async alternatives like aiohttp, asyncio.sleep, aiofiles"
                        ))

    def _check_exception_handling(self, file_path: Path, content: str, lines: List[str]):
        """Check for poor exception handling"""
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Bare except
            if line_stripped == "except:":
                self.issues.append(CriticalIssue(
                    severity="HIGH",
                    category="BARE_EXCEPT",
                    description="Bare except clause - catches all exceptions including system exits",
                    file_path=str(file_path),
                    line_number=i,
                    code_snippet=line.strip(),
                    fix_recommendation="Catch specific exceptions: except Exception: or except SpecificError:"
                ))

            # Exception pass
            if "except" in line and i < len(lines) - 1:
                next_line = lines[i].strip()
                if next_line == "pass":
                    self.issues.append(CriticalIssue(
                        severity="MEDIUM",
                        category="SILENT_EXCEPTION",
                        description="Exception silently ignored with pass",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=f"{line.strip()}\\n{next_line}",
                        fix_recommendation="Log the exception or handle it appropriately"
                    ))

    def _check_callback_errors(self, file_path: Path, content: str, lines: List[str]):
        """Check for Telegram callback handler issues"""
        if "callback" not in content.lower():
            return

        for i, line in enumerate(lines, 1):
            # Callback handler without query.answer()
            if "def " in line and "callback" in line:
                # Look ahead for query.answer()
                answer_found = False
                for j in range(i, min(i + 20, len(lines))):
                    if "query.answer" in lines[j]:
                        answer_found = True
                        break

                if not answer_found:
                    self.issues.append(CriticalIssue(
                        severity="MEDIUM",
                        category="CALLBACK_NO_ANSWER",
                        description="Callback handler without query.answer() - may cause timeout errors",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Add await query.answer() at the beginning of callback handler"
                    ))

    def _check_authentication_bypass(self, file_path: Path, content: str, lines: List[str]):
        """Check for authentication bypass issues"""
        auth_patterns = [
            r'if.*user.*==.*admin',
            r'if.*user.*==.*["\'][^"\']+["\']',
            r'AUTH.*=.*True',
            r'authenticated.*=.*True'
        ]

        for i, line in enumerate(lines, 1):
            for pattern in auth_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check for hardcoded auth values
                    if any(dangerous in line.lower() for dangerous in ['admin', 'root', 'password']):
                        self.issues.append(CriticalIssue(
                            severity="CRITICAL",
                            category="AUTH_BYPASS",
                            description="Hardcoded authentication logic that could be bypassed",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip(),
                            fix_recommendation="Use proper authentication mechanisms with secure user verification"
                        ))

    def _check_memory_leaks(self, file_path: Path, content: str, lines: List[str]):
        """Check for potential memory leaks"""
        leak_patterns = [
            r'while\s+True:(?!.*break)',
            r'for.*in.*range\(\d{4,}\)',  # Very large loops
            r'\.append\([^)]*\)(?!.*clear)',  # List growth without clearing
        ]

        for i, line in enumerate(lines, 1):
            for pattern in leak_patterns:
                if re.search(pattern, line):
                    self.issues.append(CriticalIssue(
                        severity="MEDIUM",
                        category="MEMORY_LEAK",
                        description="Potential memory leak from unbounded loop or list growth",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Add proper loop termination or memory cleanup"
                    ))

    def _check_inefficient_loops(self, file_path: Path, content: str, lines: List[str]):
        """Check for inefficient loop patterns"""
        inefficient_patterns = [
            r'for.*in.*\.keys\(\):.*\[',  # for key in dict.keys(): dict[key]
            r'if.*in.*:.*for.*in.*',      # nested if-in and for-in (potentially O(n²))
        ]

        for i, line in enumerate(lines, 1):
            for pattern in inefficient_patterns:
                if re.search(pattern, line):
                    self.issues.append(CriticalIssue(
                        severity="MEDIUM",
                        category="INEFFICIENT_LOOP",
                        description="Inefficient loop pattern detected",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Use dict.items() instead of dict.keys(), or optimize nested loops"
                    ))

    def _check_database_n_plus_one(self, file_path: Path, content: str, lines: List[str]):
        """Check for N+1 query problems"""
        if "for " not in content or "execute" not in content:
            return

        for i, line in enumerate(lines, 1):
            if "for " in line:
                # Look ahead for database queries
                for j in range(i, min(i + 10, len(lines))):
                    if "execute" in lines[j] or "query" in lines[j]:
                        self.issues.append(CriticalIssue(
                            severity="HIGH",
                            category="N_PLUS_ONE_QUERY",
                            description="Potential N+1 query problem - database query inside loop",
                            file_path=str(file_path),
                            line_number=j + 1,
                            code_snippet=f"{line.strip()} ... {lines[j].strip()}",
                            fix_recommendation="Use batch queries, JOIN operations, or query optimization"
                        ))
                        break

    def _check_resource_management(self, file_path: Path, content: str, lines: List[str]):
        """Check for resource management issues"""
        resource_patterns = [
            r'open\s*\([^)]*\)(?!.*with)',  # File opened without context manager
            r'socket\.[^)]*\)(?!.*with)',   # Socket without proper closing
        ]

        for i, line in enumerate(lines, 1):
            for pattern in resource_patterns:
                if re.search(pattern, line):
                    # Check if it's part of a with statement in next few lines
                    with_context = False
                    for j in range(max(0, i-3), min(len(lines), i+3)):
                        if "with " in lines[j]:
                            with_context = True
                            break

                    if not with_context:
                        self.issues.append(CriticalIssue(
                            severity="MEDIUM",
                            category="RESOURCE_LEAK",
                            description="Resource opened without proper context manager (with statement)",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip(),
                            fix_recommendation="Use 'with' statement for automatic resource cleanup"
                        ))

    def _check_async_await_issues(self, file_path: Path, content: str, lines: List[str]):
        """Check for async/await issues"""
        for i, line in enumerate(lines, 1):
            # Calling async function without await
            if "def " in line and "async" not in line:
                # Look for calls to potentially async functions
                for j in range(i, min(i + 20, len(lines))):
                    current_line = lines[j]
                    if any(async_func in current_line for async_func in ['run_command', 'send_message', 'get_updates']):
                        if "await " not in current_line and "async" not in current_line:
                            self.issues.append(CriticalIssue(
                                severity="HIGH",
                                category="MISSING_AWAIT",
                                description="Async function called without await - will not execute properly",
                                file_path=str(file_path),
                                line_number=j + 1,
                                code_snippet=current_line.strip(),
                                fix_recommendation="Add 'await' before async function calls"
                            ))

    def _check_circular_imports(self, file_path: Path, content: str, lines: List[str]):
        """Check for potential circular import issues"""
        # Look for relative imports that might cause circles
        for i, line in enumerate(lines, 1):
            if "from ." in line and "import" in line:
                # Detect complex relative import patterns
                if line.count("..") > 2:
                    self.issues.append(CriticalIssue(
                        severity="MEDIUM",
                        category="CIRCULAR_IMPORT",
                        description="Complex relative import that may cause circular dependency",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Refactor to use dependency injection or move shared code to common module"
                    ))

    def _check_god_objects(self, file_path: Path, content: str, lines: List[str]):
        """Check for god objects (classes with too many responsibilities)"""
        class_methods = {}
        current_class = None

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("class "):
                class_match = re.match(r'class\s+(\w+)', line.strip())
                if class_match:
                    current_class = class_match.group(1)
                    class_methods[current_class] = 0
            elif line.strip().startswith("def ") and current_class:
                class_methods[current_class] += 1

        for class_name, method_count in class_methods.items():
            if method_count > 20:  # Threshold for too many methods
                self.issues.append(CriticalIssue(
                    severity="MEDIUM",
                    category="GOD_OBJECT",
                    description=f"Class {class_name} has {method_count} methods - too many responsibilities",
                    file_path=str(file_path),
                    line_number=0,
                    code_snippet=f"class {class_name} with {method_count} methods",
                    fix_recommendation="Split class into smaller, focused classes following Single Responsibility Principle"
                ))

    def _check_dependency_injection(self, file_path: Path, content: str, lines: List[str]):
        """Check for dependency injection issues"""
        # Look for hard-coded instantiations in constructors
        in_init = False
        for i, line in enumerate(lines, 1):
            if "def __init__" in line:
                in_init = True
                continue
            elif line.strip().startswith("def ") or line.strip().startswith("class "):
                in_init = False

            if in_init and "= " in line:
                # Look for direct instantiations of complex objects
                if any(pattern in line for pattern in ["Database(", "Client(", "Manager(", "Handler("]):
                    self.issues.append(CriticalIssue(
                        severity="MEDIUM",
                        category="HARD_DEPENDENCY",
                        description="Hard-coded dependency instantiation in constructor",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        fix_recommendation="Use dependency injection pattern - pass dependencies as parameters"
                    ))

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = ["venv", "__pycache__", ".git", "node_modules", ".pytest_cache", "test"]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def generate_report(self) -> str:
        """Generate final audit report"""
        if not self.issues:
            return "🎉 No critical issues found in the codebase!"

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        self.issues.sort(key=lambda x: (severity_order.get(x.severity, 999), x.category))

        # Group by severity
        critical = [i for i in self.issues if i.severity == "CRITICAL"]
        high = [i for i in self.issues if i.severity == "HIGH"]
        medium = [i for i in self.issues if i.severity == "MEDIUM"]
        low = [i for i in self.issues if i.severity == "LOW"]

        report = []
        report.append("🚨 CLAUDE TELEGRAM BOT - CRITICAL SECURITY & PERFORMANCE AUDIT")
        report.append("=" * 80)
        report.append(f"Total Issues Found: {len(self.issues)}")
        report.append(f"Critical: {len(critical)} | High: {len(high)} | Medium: {len(medium)} | Low: {len(low)}")
        report.append("")

        def add_issues_to_report(issues, title):
            if not issues:
                return

            report.append(f"\n🔴 {title} ({len(issues)} issues)")
            report.append("-" * 60)

            for i, issue in enumerate(issues, 1):
                report.append(f"\n{i}. [{issue.category}] {issue.description}")
                report.append(f"   📁 File: {issue.file_path}:{issue.line_number}")
                if issue.code_snippet:
                    report.append(f"   💻 Code: {issue.code_snippet[:100]}...")
                report.append(f"   🔧 Fix: {issue.fix_recommendation}")

        add_issues_to_report(critical, "CRITICAL ISSUES - IMMEDIATE ATTENTION REQUIRED")
        add_issues_to_report(high, "HIGH PRIORITY ISSUES")
        add_issues_to_report(medium, "MEDIUM PRIORITY ISSUES")
        add_issues_to_report(low, "LOW PRIORITY ISSUES")

        # Recommendations
        report.append(f"\n\n💡 PRIORITY RECOMMENDATIONS:")
        if critical:
            report.append("1. 🚨 IMMEDIATELY fix all CRITICAL security issues")
        if high:
            report.append("2. ⚡ Address HIGH priority performance bottlenecks")
        if medium:
            report.append("3. 🛡️ Improve stability with better exception handling")

        return "\n".join(report)

def main():
    project_root = Path("/home/vokov/projects/claude-notifer-and-bot")
    auditor = ManualBotAuditor(project_root)
    report = auditor.run_audit()
    print(report)

    # Save report to file
    with open("critical_audit_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 Report saved to: critical_audit_report.txt")

    return len([i for i in auditor.issues if i.severity in ["CRITICAL", "HIGH"]])

if __name__ == "__main__":
    critical_count = main()