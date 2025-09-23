#!/usr/bin/env python3
"""
Moon Architect Bot - Static UX Analyzer
Comprehensive static analysis of claude-notifer-and-bot without needing Telegram auth
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class UIElement:
    """Represents a UI element (command or button)"""
    type: str  # 'command' or 'button'
    name: str
    description: str
    location: str  # file path where found
    line_number: int
    handler_function: str
    parameters: List[str]
    callback_data: Optional[str] = None
    permissions_required: List[str] = None
    translation_key: Optional[str] = None

    def __post_init__(self):
        if self.permissions_required is None:
            self.permissions_required = []

@dataclass
class UserFlow:
    """Represents a user interaction flow"""
    name: str
    entry_points: List[str]
    steps: List[str]
    exit_points: List[str]
    complexity: str  # 'simple', 'medium', 'complex'
    ui_elements_involved: List[str]

@dataclass
class UXIssue:
    """Represents a UX issue found during analysis"""
    severity: str  # 'critical', 'major', 'minor'
    category: str  # 'usability', 'translation', 'performance', 'bug', 'accessibility'
    description: str
    location: str
    evidence: str
    suggested_fix: str
    estimated_effort: str  # 'low', 'medium', 'high'

@dataclass
class CodeAnalysisResult:
    """Result of code analysis"""
    total_commands: int
    total_buttons: int
    total_handlers: int
    complexity_score: float
    maintainability_score: float
    localization_coverage: float

@dataclass
class UXAnalysisResult:
    """Complete UX analysis result"""
    analysis_timestamp: str
    project_path: str
    ui_elements: List[UIElement]
    user_flows: List[UserFlow]
    issues: List[UXIssue]
    code_analysis: CodeAnalysisResult
    recommendations: List[str]
    improvement_plan: List[Dict[str, Any]]
    summary: str

class StaticUXAnalyzer:
    """Static UX analyzer for claude-notifer-and-bot"""

    def __init__(self, target_project_path: str = "/home/vokov/projects/claude-notifer-and-bot"):
        self.target_path = Path(target_project_path)
        self.src_path = self.target_path / "src"
        self.bot_path = self.src_path / "bot"
        self.handlers_path = self.bot_path / "handlers"

        self.ui_elements: List[UIElement] = []
        self.user_flows: List[UserFlow] = []
        self.issues: List[UXIssue] = []

        # Patterns for code analysis
        self.command_patterns = [
            r'@app\.on_message\(filters\.command\("([^"]+)"\)',
            r'filters\.command\("([^"]+)"\)',
            r'command="([^"]+)"'
        ]

        self.callback_patterns = [
            r'@app\.on_callback_query\(.*data="([^"]+)"',
            r'callback_data="([^"]+)"',
            r'data="([^"]+)"'
        ]

        self.button_patterns = [
            r'InlineKeyboardButton\("([^"]+)",\s*callback_data="([^"]+)"',
            r'button\("([^"]+)",\s*"([^"]+)"'
        ]

    async def analyze_project_structure(self):
        """Analyze the complete project structure"""
        logger.info(f"Starting analysis of {self.target_path}")

        if not self.target_path.exists():
            self.issues.append(UXIssue(
                severity="critical",
                category="bug",
                description="Target project path does not exist",
                location=str(self.target_path),
                evidence=f"Path {self.target_path} not found",
                suggested_fix="Verify project path and ensure project exists",
                estimated_effort="low"
            ))
            return

        # Analyze different components
        await self._analyze_handlers()
        await self._analyze_middleware()
        await self._analyze_features()
        await self._analyze_localization()
        await self._analyze_configuration()
        await self._detect_user_flows()
        await self._perform_quality_analysis()

    async def _analyze_handlers(self):
        """Analyze all handler files for UI elements"""
        logger.info("Analyzing handlers...")

        if not self.handlers_path.exists():
            self.issues.append(UXIssue(
                severity="major",
                category="bug",
                description="Handlers directory not found",
                location=str(self.handlers_path),
                evidence="Missing handlers directory",
                suggested_fix="Verify project structure",
                estimated_effort="low"
            ))
            return

        for handler_file in self.handlers_path.glob("*.py"):
            await self._analyze_handler_file(handler_file)

    async def _analyze_handler_file(self, file_path: Path):
        """Analyze a specific handler file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            logger.info(f"Analyzing {file_path.name}")

            # Find commands
            for line_num, line in enumerate(lines, 1):
                # Check for command patterns
                for pattern in self.command_patterns:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        await self._process_command(match, file_path, line_num, line)

                # Check for callback patterns
                for pattern in self.callback_patterns:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        await self._process_callback(match, file_path, line_num, line)

                # Check for button patterns
                for pattern in self.button_patterns:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        if isinstance(match, tuple) and len(match) == 2:
                            await self._process_button(match[0], match[1], file_path, line_num, line)

        except Exception as e:
            self.issues.append(UXIssue(
                severity="major",
                category="bug",
                description=f"Error analyzing handler file: {e}",
                location=str(file_path),
                evidence=str(e),
                suggested_fix="Fix file encoding or syntax issues",
                estimated_effort="medium"
            ))

    async def _process_command(self, command: str, file_path: Path, line_num: int, line: str):
        """Process a found command"""
        # Extract handler function name (simplified)
        handler_func = "unknown"

        ui_element = UIElement(
            type="command",
            name=f"/{command}",
            description=f"Command: {command}",
            location=f"{file_path.name}:{line_num}",
            line_number=line_num,
            handler_function=handler_func,
            parameters=[]
        )

        self.ui_elements.append(ui_element)

    async def _process_callback(self, callback: str, file_path: Path, line_num: int, line: str):
        """Process a found callback"""
        ui_element = UIElement(
            type="callback",
            name=callback,
            description=f"Callback: {callback}",
            location=f"{file_path.name}:{line_num}",
            line_number=line_num,
            handler_function="callback_handler",
            parameters=[],
            callback_data=callback
        )

        self.ui_elements.append(ui_element)

    async def _process_button(self, button_text: str, callback_data: str, file_path: Path, line_num: int, line: str):
        """Process a found button"""
        ui_element = UIElement(
            type="button",
            name=button_text,
            description=f"Button: {button_text}",
            location=f"{file_path.name}:{line_num}",
            line_number=line_num,
            handler_function="button_handler",
            parameters=[],
            callback_data=callback_data
        )

        self.ui_elements.append(ui_element)

    async def _analyze_middleware(self):
        """Analyze middleware for security and access patterns"""
        middleware_path = self.bot_path / "middleware"

        if middleware_path.exists():
            for middleware_file in middleware_path.glob("*.py"):
                await self._check_security_middleware(middleware_file)

    async def _check_security_middleware(self, file_path: Path):
        """Check security middleware implementation"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for authentication patterns
            if "whitelist" in content.lower() or "allowed_users" in content.lower():
                logger.info(f"Found authentication middleware in {file_path.name}")
            else:
                self.issues.append(UXIssue(
                    severity="major",
                    category="usability",
                    description="No clear authentication pattern found",
                    location=str(file_path),
                    evidence="Missing user authentication checks",
                    suggested_fix="Implement clear user authentication and authorization",
                    estimated_effort="medium"
                ))

        except Exception as e:
            logger.warning(f"Error analyzing middleware {file_path}: {e}")

    async def _analyze_features(self):
        """Analyze feature modules"""
        features_path = self.bot_path / "features"

        if features_path.exists():
            feature_count = len(list(features_path.glob("*.py")))
            logger.info(f"Found {feature_count} feature modules")

            if feature_count > 10:
                self.issues.append(UXIssue(
                    severity="minor",
                    category="usability",
                    description="Large number of features may overwhelm users",
                    location=str(features_path),
                    evidence=f"{feature_count} feature modules found",
                    suggested_fix="Consider grouping features or creating feature categories",
                    estimated_effort="medium"
                ))

    async def _analyze_localization(self):
        """Analyze localization and translation coverage"""
        # Look for translation files
        possible_i18n_paths = [
            self.target_path / "locales",
            self.target_path / "translations",
            self.target_path / "i18n",
            self.src_path / "locales",
            self.src_path / "translations"
        ]

        translation_files_found = False
        for path in possible_i18n_paths:
            if path.exists():
                translation_files_found = True
                logger.info(f"Found translations at {path}")
                break

        if not translation_files_found:
            self.issues.append(UXIssue(
                severity="major",
                category="translation",
                description="No localization system found",
                location=str(self.target_path),
                evidence="No translation directories found",
                suggested_fix="Implement internationalization for Ukrainian/English support",
                estimated_effort="high"
            ))

    async def _analyze_configuration(self):
        """Analyze configuration and settings"""
        config_files = [
            self.target_path / ".env",
            self.target_path / "config.py",
            self.src_path / "config",
            self.target_path / "settings.py"
        ]

        config_found = False
        for config_file in config_files:
            if config_file.exists():
                config_found = True
                await self._check_config_file(config_file)

        if not config_found:
            self.issues.append(UXIssue(
                severity="major",
                category="usability",
                description="No clear configuration system found",
                location=str(self.target_path),
                evidence="Missing configuration files",
                suggested_fix="Create clear configuration documentation",
                estimated_effort="medium"
            ))

    async def _check_config_file(self, file_path: Path):
        """Check configuration file for common issues"""
        try:
            if file_path.suffix == ".env":
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for hardcoded secrets
                if any(keyword in content for keyword in ["password=", "token=", "secret="]):
                    # Check if values are actually set or just placeholders
                    lines = content.split('\n')
                    for line in lines:
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            if any(keyword in key.lower() for keyword in ["password", "token", "secret"]) and value and not value.startswith("your_"):
                                self.issues.append(UXIssue(
                                    severity="critical",
                                    category="bug",
                                    description="Potential hardcoded secrets in config",
                                    location=str(file_path),
                                    evidence=f"Found {key} with apparent real value",
                                    suggested_fix="Use environment variables or secure secret management",
                                    estimated_effort="low"
                                ))

        except Exception as e:
            logger.warning(f"Error checking config file {file_path}: {e}")

    async def _detect_user_flows(self):
        """Detect and analyze user interaction flows"""
        # Define common user flows based on found UI elements
        commands = [elem for elem in self.ui_elements if elem.type == "command"]
        buttons = [elem for elem in self.ui_elements if elem.type == "button"]
        callbacks = [elem for elem in self.ui_elements if elem.type == "callback"]

        # Basic flows
        flows = []

        if any(cmd.name == "/start" for cmd in commands):
            flows.append(UserFlow(
                name="Bot Initialization",
                entry_points=["/start"],
                steps=["Send /start", "Receive welcome message", "See available options"],
                exit_points=["Main menu", "Help command"],
                complexity="simple",
                ui_elements_involved=["/start"]
            ))

        if any(cmd.name == "/help" for cmd in commands):
            flows.append(UserFlow(
                name="Getting Help",
                entry_points=["/help"],
                steps=["Send /help", "Receive command list", "Choose specific command"],
                exit_points=["Return to chat", "Execute command"],
                complexity="simple",
                ui_elements_involved=["/help"]
            ))

        # Detect complex flows based on button patterns
        if len(buttons) > 5:
            flows.append(UserFlow(
                name="Interactive Navigation",
                entry_points=["Any command with buttons"],
                steps=["Execute command", "See inline buttons", "Navigate through options"],
                exit_points=["Complete action", "Cancel operation"],
                complexity="medium",
                ui_elements_involved=[btn.name for btn in buttons[:5]]
            ))

        self.user_flows = flows

    async def _perform_quality_analysis(self):
        """Perform overall quality analysis"""
        # Calculate complexity metrics
        total_commands = len([e for e in self.ui_elements if e.type == "command"])
        total_buttons = len([e for e in self.ui_elements if e.type == "button"])
        total_callbacks = len([e for e in self.ui_elements if e.type == "callback"])

        # Complexity scoring (0-10)
        complexity_score = min(10, (total_commands + total_buttons + total_callbacks) / 5)

        # Maintainability scoring based on issues
        critical_issues = len([i for i in self.issues if i.severity == "critical"])
        major_issues = len([i for i in self.issues if i.severity == "major"])
        maintainability_score = max(0, 10 - (critical_issues * 3 + major_issues * 1))

        # Localization coverage (placeholder)
        localization_coverage = 0.3  # 30% assumed based on analysis

        # Store analysis results
        self.code_analysis = CodeAnalysisResult(
            total_commands=total_commands,
            total_buttons=total_buttons,
            total_handlers=len(list(self.handlers_path.glob("*.py"))) if self.handlers_path.exists() else 0,
            complexity_score=complexity_score,
            maintainability_score=maintainability_score,
            localization_coverage=localization_coverage
        )

    async def generate_comprehensive_report(self) -> UXAnalysisResult:
        """Generate comprehensive UX analysis report"""
        # Generate recommendations
        recommendations = await self._generate_recommendations()

        # Generate improvement plan
        improvement_plan = await self._generate_improvement_plan()

        # Generate summary
        summary = await self._generate_summary()

        # Create final result
        result = UXAnalysisResult(
            analysis_timestamp=datetime.now().isoformat(),
            project_path=str(self.target_path),
            ui_elements=self.ui_elements,
            user_flows=self.user_flows,
            issues=self.issues,
            code_analysis=self.code_analysis,
            recommendations=recommendations,
            improvement_plan=improvement_plan,
            summary=summary
        )

        return result

    async def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Based on issues found
        critical_issues = [i for i in self.issues if i.severity == "critical"]
        if critical_issues:
            recommendations.append("🚨 КРИТИЧНО: Терміново виправити критичні проблеми безпеки та функціональності")

        major_issues = [i for i in self.issues if i.severity == "major"]
        if major_issues:
            recommendations.append("⚠️ ВАЖЛИВО: Розв'язати основні проблеми юзабіліті та надійності")

        # Based on complexity
        if self.code_analysis.complexity_score > 7:
            recommendations.append("📋 Розглянути спрощення інтерфейсу та групування команд")

        # Based on localization
        if self.code_analysis.localization_coverage < 0.5:
            recommendations.append("🌐 Впровадити повноцінну локалізацію українською та англійською")

        # General recommendations
        recommendations.extend([
            "📱 Оптимізувати для мобільних пристроїв Telegram",
            "🎯 Створити інтерактивний онбординг для нових користувачів",
            "📊 Додати аналітику використання для покращення UX",
            "🔄 Впровадити прогрес-індикатори для довгих операцій",
            "💡 Додати контекстну допомогу та підказки",
            "🧪 Створити автоматизовані тести для UI компонентів"
        ])

        return recommendations

    async def _generate_improvement_plan(self) -> List[Dict[str, Any]]:
        """Generate step-by-step improvement plan"""
        plan = []

        # Phase 1: Critical fixes
        critical_issues = [i for i in self.issues if i.severity == "critical"]
        if critical_issues:
            plan.append({
                "phase": 1,
                "title": "Критичні виправлення",
                "description": "Усунення критичних проблем безпеки та функціональності",
                "tasks": [f"Виправити: {issue.description}" for issue in critical_issues],
                "estimated_time": "1-2 дні",
                "priority": "highest"
            })

        # Phase 2: Major improvements
        major_issues = [i for i in self.issues if i.severity == "major"]
        if major_issues:
            plan.append({
                "phase": 2,
                "title": "Основні покращення",
                "description": "Покращення юзабіліті та надійності",
                "tasks": [f"Покращити: {issue.description}" for issue in major_issues],
                "estimated_time": "3-5 днів",
                "priority": "high"
            })

        # Phase 3: UX enhancements
        plan.append({
            "phase": 3,
            "title": "Покращення UX",
            "description": "Оптимізація користувацького досвіду",
            "tasks": [
                "Створити інтуїтивну навігацію",
                "Додати прогрес-індикатори",
                "Впровадити контекстну допомогу",
                "Оптимізувати для мобільних"
            ],
            "estimated_time": "1-2 тижні",
            "priority": "medium"
        })

        # Phase 4: Advanced features
        plan.append({
            "phase": 4,
            "title": "Розширений функціонал",
            "description": "Додання нових можливостей та покращень",
            "tasks": [
                "Впровадити повну локалізацію",
                "Додати аналітику використання",
                "Створити персоналізацію",
                "Додати голосові команди"
            ],
            "estimated_time": "2-3 тижні",
            "priority": "low"
        })

        return plan

    async def _generate_summary(self) -> str:
        """Generate analysis summary"""
        total_elements = len(self.ui_elements)
        critical_issues = len([i for i in self.issues if i.severity == "critical"])
        major_issues = len([i for i in self.issues if i.severity == "major"])
        minor_issues = len([i for i in self.issues if i.severity == "minor"])

        overall_rating = "Відмінно"
        if critical_issues > 0:
            overall_rating = "Потребує негайного втручання"
        elif major_issues > 3:
            overall_rating = "Потребує значних покращень"
        elif major_issues > 0:
            overall_rating = "Потребує покращень"
        elif minor_issues > 5:
            overall_rating = "Задовільно"

        return (
            f"Проаналізовано {total_elements} UI елементів у проекті claude-notifer-and-bot. "
            f"Виявлено {critical_issues} критичних, {major_issues} важливих та {minor_issues} незначних проблем. "
            f"Складність проекту: {self.code_analysis.complexity_score:.1f}/10. "
            f"Рівень підтримуваності: {self.code_analysis.maintainability_score:.1f}/10. "
            f"Загальна оцінка: {overall_rating}."
        )

    async def save_report(self, result: UXAnalysisResult):
        """Save analysis report to files"""
        # Save JSON report
        json_path = Path("ux_analysis_detailed.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, ensure_ascii=False)

        # Save markdown report
        md_path = Path("ux_analysis_report.md")
        markdown_content = await self._generate_markdown_report(result)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        logger.info(f"Reports saved: {json_path}, {md_path}")
        return json_path, md_path

    async def _generate_markdown_report(self, result: UXAnalysisResult) -> str:
        """Generate markdown report"""
        report = f"""# 🔍 Comprehensive UX Analysis Report
**Claude Notifier Bot - Detailed Analysis**

## 📊 Executive Summary
{result.summary}

**Analysis Date:** {result.analysis_timestamp}
**Project Path:** {result.project_path}

## 📈 Key Metrics
- **Total UI Elements:** {len(result.ui_elements)}
- **Commands:** {result.code_analysis.total_commands}
- **Buttons:** {result.code_analysis.total_buttons}
- **Handlers:** {result.code_analysis.total_handlers}
- **Complexity Score:** {result.code_analysis.complexity_score:.1f}/10
- **Maintainability:** {result.code_analysis.maintainability_score:.1f}/10
- **Localization Coverage:** {result.code_analysis.localization_coverage:.1%}

## 🎯 UI Elements Inventory

### Commands ({result.code_analysis.total_commands})
"""

        commands = [e for e in result.ui_elements if e.type == "command"]
        for cmd in commands:
            report += f"- `{cmd.name}` - *{cmd.location}*\n"

        buttons = [e for e in result.ui_elements if e.type == "button"]
        if buttons:
            report += f"\n### Buttons ({len(buttons)})\n"
            for btn in buttons:
                report += f"- `{btn.name}` → `{btn.callback_data}` - *{btn.location}*\n"

        callbacks = [e for e in result.ui_elements if e.type == "callback"]
        if callbacks:
            report += f"\n### Callbacks ({len(callbacks)})\n"
            for cb in callbacks:
                report += f"- `{cb.callback_data}` - *{cb.location}*\n"

        if result.user_flows:
            report += "\n## 🔄 User Interaction Flows\n"
            for flow in result.user_flows:
                report += f"\n### {flow.name} ({flow.complexity.title()})\n"
                report += f"**Entry Points:** {', '.join(flow.entry_points)}\n"
                report += f"**Steps:**\n"
                for step in flow.steps:
                    report += f"1. {step}\n"
                report += f"**Exit Points:** {', '.join(flow.exit_points)}\n"

        if result.issues:
            report += "\n## ⚠️ Issues Analysis\n"

            critical = [i for i in result.issues if i.severity == "critical"]
            major = [i for i in result.issues if i.severity == "major"]
            minor = [i for i in result.issues if i.severity == "minor"]

            if critical:
                report += "\n### 🚨 Critical Issues\n"
                for issue in critical:
                    report += f"\n**{issue.description}**\n"
                    report += f"- **Location:** {issue.location}\n"
                    report += f"- **Evidence:** {issue.evidence}\n"
                    report += f"- **Fix:** {issue.suggested_fix}\n"
                    report += f"- **Effort:** {issue.estimated_effort}\n"

            if major:
                report += "\n### ⚠️ Major Issues\n"
                for issue in major:
                    report += f"\n**{issue.description}**\n"
                    report += f"- **Location:** {issue.location}\n"
                    report += f"- **Fix:** {issue.suggested_fix}\n"

            if minor:
                report += f"\n### ℹ️ Minor Issues ({len(minor)})\n"
                for issue in minor[:5]:  # Show first 5 minor issues
                    report += f"- {issue.description}\n"
                if len(minor) > 5:
                    report += f"- ... and {len(minor) - 5} more minor issues\n"

        report += "\n## 💡 Recommendations\n"
        for rec in result.recommendations:
            report += f"- {rec}\n"

        report += "\n## 📋 Implementation Plan\n"
        for phase in result.improvement_plan:
            report += f"\n### Phase {phase['phase']}: {phase['title']}\n"
            report += f"**Priority:** {phase['priority'].title()}\n"
            report += f"**Timeline:** {phase['estimated_time']}\n"
            report += f"**Description:** {phase['description']}\n"
            report += "**Tasks:**\n"
            for task in phase['tasks']:
                report += f"- [ ] {task}\n"

        report += f"""
## 🎯 Next Steps

1. **Immediate Actions** (1-2 days)
   - [ ] Fix all critical issues
   - [ ] Address security vulnerabilities
   - [ ] Ensure basic functionality works

2. **Short Term** (1 week)
   - [ ] Resolve major usability issues
   - [ ] Improve error handling
   - [ ] Add basic localization

3. **Medium Term** (2-3 weeks)
   - [ ] Implement comprehensive UX improvements
   - [ ] Add advanced features
   - [ ] Optimize performance

4. **Long Term** (1+ month)
   - [ ] Full feature expansion
   - [ ] Advanced analytics
   - [ ] Community features

---
*Analysis generated by Moon Architect Bot*
*Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return report

async def main():
    """Main analysis function"""
    analyzer = StaticUXAnalyzer()

    try:
        logger.info("🚀 Starting comprehensive UX analysis...")

        # Perform analysis
        await analyzer.analyze_project_structure()

        # Generate report
        result = await analyzer.generate_comprehensive_report()

        # Save reports
        json_path, md_path = await analyzer.save_report(result)

        # Print summary
        print("\n" + "="*60)
        print("🎉 UX ANALYSIS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"📊 Analysis Summary:")
        print(f"   • UI Elements Found: {len(result.ui_elements)}")
        print(f"   • Issues Identified: {len(result.issues)}")
        print(f"   • Recommendations: {len(result.recommendations)}")
        print(f"   • Improvement Phases: {len(result.improvement_plan)}")
        print("\n📁 Reports Generated:")
        print(f"   • Detailed JSON: {json_path}")
        print(f"   • Human-readable: {md_path}")
        print("\n📋 Summary:")
        print(f"   {result.summary}")
        print("="*60)

        return result

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())