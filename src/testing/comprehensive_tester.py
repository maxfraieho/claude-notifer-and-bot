#!/usr/bin/env python3
"""
Comprehensive Bot Testing Framework for DevClaude_bot

Advanced testing system implementing recommendations from Enhanced Architect Bot analysis.
Features intelligent validation, performance monitoring, and detailed reporting.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict

from pyrogram import Client
from pyrogram.errors import FloodWait

from .response_validator import validate_bot_response, ValidationResult


@dataclass
class TestCommand:
    """Structure for test command configuration"""
    command: str
    expected_response_time: float = 5.0
    requires_context: bool = False
    context_setup: Optional[str] = None
    expected_features: List[str] = None
    min_response_length: int = 10
    category: str = "general"


@dataclass
class TestResult:
    """Comprehensive test result structure"""
    command: str
    status: str
    response_text: str
    response_time: float
    response_length: int
    has_keyboard: bool
    validation_score: int
    issues: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]
    timestamp: str


@dataclass
class TestSuiteReport:
    """Complete test suite report"""
    target_bot: str
    test_timestamp: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    warning_tests: int
    success_rate: float
    average_score: float
    total_runtime: float
    test_results: List[TestResult]
    performance_metrics: Dict[str, Any]
    recommendations: List[str]
    summary: Dict[str, Any]


class ComprehensiveBotTester:
    """
    Advanced bot testing framework with comprehensive validation and reporting
    """

    def __init__(self, session_string: Optional[str] = None):
        self.api_id = 28605494
        self.api_hash = "3ff0adf3dd08d70a5dc3f1bea8e9285f"
        self.session_string = session_string or self._load_session()

        self.client = Client(
            "comprehensive_tester",
            api_id=self.api_id,
            api_hash=self.api_hash,
            session_string=self.session_string
        )

        self.test_commands = self._init_test_commands()

    def _load_session(self) -> Optional[str]:
        """Load session string from file"""
        try:
            session_path = Path("/home/vokov/projects/arhitector/WORKING_SESSION.txt")
            if session_path.exists():
                return session_path.read_text().strip()
        except Exception as e:
            print(f"⚠️ Could not load session: {e}")
        return None

    def _init_test_commands(self) -> List[TestCommand]:
        """Initialize comprehensive test command suite"""
        return [
            # Basic Commands
            TestCommand("start", category="basic", min_response_length=200,
                       expected_features=["welcome", "help", "commands"]),
            TestCommand("/help", category="basic", min_response_length=300,
                       expected_features=["commands", "usage", "navigation"]),
            TestCommand("/version", category="basic", min_response_length=200,
                       expected_features=["version", "release", "features"]),
            TestCommand("/status", category="basic", min_response_length=30,
                       expected_features=["session", "directory"]),

            # Navigation Commands
            TestCommand("/pwd", category="navigation", min_response_length=15,
                       expected_features=["directory", "current"]),
            TestCommand("/ls", category="navigation", min_response_length=50,
                       expected_features=["files", "directories"]),
            TestCommand("/projects", category="navigation", min_response_length=50,
                       expected_features=["projects", "directory"]),
            TestCommand("/cd", category="navigation", min_response_length=50,
                       expected_features=["usage", "directory"]),
            TestCommand("/back", category="navigation", min_response_length=30,
                       expected_features=["navigated", "directory"]),

            # Interactive Commands
            TestCommand("/actions", category="interactive", min_response_length=50,
                       expected_features=["actions", "buttons"]),
            TestCommand("/git", category="interactive", min_response_length=30,
                       expected_features=["git", "repository"]),
            TestCommand("/search", category="interactive", min_response_length=30,
                       expected_features=["search", "files"]),
            TestCommand("/run", category="interactive", min_response_length=30,
                       expected_features=["run", "script"]),
            TestCommand("/edit", category="interactive", min_response_length=30,
                       expected_features=["edit", "file"]),

            # Session Management
            TestCommand("/new", category="session", min_response_length=10,
                       expected_features=["session", "new"]),
            TestCommand("/continue", category="session", min_response_length=20,
                       expected_features=["continue", "session"]),
            TestCommand("/end", category="session", min_response_length=10,
                       expected_features=["end", "session"]),

            # Advanced Features
            TestCommand("/language", category="advanced", min_response_length=50,
                       expected_features=["language", "settings"]),
            TestCommand("/settings", category="advanced", min_response_length=50,
                       expected_features=["settings", "configuration"]),
        ]

    async def run_comprehensive_tests(self, target_bot: str = "@DevClaude_bot",
                                     test_categories: Optional[Set[str]] = None) -> TestSuiteReport:
        """
        Execute comprehensive test suite with detailed analysis

        Args:
            target_bot: Target bot username
            test_categories: Optional set of categories to test (if None, test all)

        Returns:
            TestSuiteReport: Comprehensive test results
        """
        print(f"🚀 Starting comprehensive testing of {target_bot}")
        start_time = time.time()

        # Filter commands by categories if specified
        commands_to_test = self.test_commands
        if test_categories:
            commands_to_test = [cmd for cmd in self.test_commands if cmd.category in test_categories]

        test_results = []
        performance_metrics = {
            "response_times": [],
            "response_lengths": [],
            "validation_scores": [],
            "commands_with_keyboards": 0,
            "category_performance": {}
        }

        try:
            await self.client.start()
            print(f"✅ Connected to Telegram successfully")
            print(f"🧪 Testing {len(commands_to_test)} commands across categories: {set(cmd.category for cmd in commands_to_test)}")

            for i, test_cmd in enumerate(commands_to_test, 1):
                print(f"🔍 [{i}/{len(commands_to_test)}] Testing: {test_cmd.command}")

                try:
                    result = await self._execute_single_test(target_bot, test_cmd)
                    test_results.append(result)

                    # Update performance metrics
                    self._update_performance_metrics(performance_metrics, result, test_cmd.category)

                    # Progress indicator
                    self._print_test_progress(result, i, len(commands_to_test))

                except FloodWait as e:
                    print(f"⏰ FloodWait: waiting {e.value} seconds")
                    await asyncio.sleep(e.value)
                    # Retry the command
                    try:
                        result = await self._execute_single_test(target_bot, test_cmd)
                        test_results.append(result)
                        self._update_performance_metrics(performance_metrics, result, test_cmd.category)
                    except Exception as retry_e:
                        print(f"❌ Retry failed for {test_cmd.command}: {retry_e}")
                        # Add failed test result
                        test_results.append(self._create_failed_result(test_cmd, str(retry_e)))

                except Exception as e:
                    print(f"❌ Error testing {test_cmd.command}: {e}")
                    test_results.append(self._create_failed_result(test_cmd, str(e)))

        except Exception as e:
            print(f"💥 Testing failed: {e}")
        finally:
            await self.client.stop()

        # Calculate final metrics
        total_runtime = time.time() - start_time
        return self._generate_comprehensive_report(
            target_bot, test_results, performance_metrics, total_runtime
        )

    async def _execute_single_test(self, target_bot: str, test_cmd: TestCommand) -> TestResult:
        """Execute a single test command with comprehensive analysis"""
        start_time = time.time()

        # Setup context if needed
        if test_cmd.context_setup:
            await self.client.send_message(target_bot, test_cmd.context_setup)
            await asyncio.sleep(1)

        # Send test command
        await self.client.send_message(target_bot, test_cmd.command)
        await asyncio.sleep(test_cmd.expected_response_time)

        # Get response
        messages = []
        async for msg in self.client.get_chat_history(target_bot, limit=5):
            if msg.from_user and msg.from_user.username and "DevClaude" in msg.from_user.username:
                messages.append(msg)
                break

        response_time = time.time() - start_time

        if not messages:
            return TestResult(
                command=test_cmd.command,
                status="no_response",
                response_text="",
                response_time=response_time,
                response_length=0,
                has_keyboard=False,
                validation_score=0,
                issues=["No response received"],
                recommendations=["Check bot availability and command handling"],
                metadata={"category": test_cmd.category},
                timestamp=datetime.now().isoformat()
            )

        response = messages[0]
        response_text = response.text or ""

        # Comprehensive validation
        validation_report = validate_bot_response(test_cmd.command, response_text)

        # Additional analysis
        has_keyboard = bool(response.reply_markup)
        feature_analysis = self._analyze_expected_features(response_text, test_cmd.expected_features or [])

        return TestResult(
            command=test_cmd.command,
            status=validation_report.overall_status.value,
            response_text=response_text,
            response_time=response_time,
            response_length=len(response_text),
            has_keyboard=has_keyboard,
            validation_score=validation_report.score,
            issues=[issue.message for issue in validation_report.issues] + feature_analysis["missing_features"],
            recommendations=validation_report.recommendations,
            metadata={
                "category": test_cmd.category,
                "expected_features": test_cmd.expected_features or [],
                "found_features": feature_analysis["found_features"],
                "feature_score": feature_analysis["score"]
            },
            timestamp=datetime.now().isoformat()
        )

    def _analyze_expected_features(self, response_text: str, expected_features: List[str]) -> Dict[str, Any]:
        """Analyze if response contains expected features"""
        text_lower = response_text.lower()
        found_features = []
        missing_features = []

        for feature in expected_features:
            if feature.lower() in text_lower:
                found_features.append(feature)
            else:
                missing_features.append(f"Missing expected feature: {feature}")

        feature_score = (len(found_features) / len(expected_features)) * 100 if expected_features else 100

        return {
            "found_features": found_features,
            "missing_features": missing_features,
            "score": feature_score
        }

    def _create_failed_result(self, test_cmd: TestCommand, error: str) -> TestResult:
        """Create a failed test result"""
        return TestResult(
            command=test_cmd.command,
            status="failed",
            response_text="",
            response_time=0.0,
            response_length=0,
            has_keyboard=False,
            validation_score=0,
            issues=[f"Test execution failed: {error}"],
            recommendations=["Check bot availability and network connection"],
            metadata={"category": test_cmd.category, "error": error},
            timestamp=datetime.now().isoformat()
        )

    def _update_performance_metrics(self, metrics: Dict[str, Any], result: TestResult, category: str):
        """Update performance metrics with test result"""
        metrics["response_times"].append(result.response_time)
        metrics["response_lengths"].append(result.response_length)
        metrics["validation_scores"].append(result.validation_score)

        if result.has_keyboard:
            metrics["commands_with_keyboards"] += 1

        if category not in metrics["category_performance"]:
            metrics["category_performance"][category] = {
                "total_tests": 0,
                "successful_tests": 0,
                "avg_score": 0,
                "scores": []
            }

        cat_metrics = metrics["category_performance"][category]
        cat_metrics["total_tests"] += 1
        cat_metrics["scores"].append(result.validation_score)

        if result.status in ["success", "warning"]:
            cat_metrics["successful_tests"] += 1

        cat_metrics["avg_score"] = sum(cat_metrics["scores"]) / len(cat_metrics["scores"])

    def _print_test_progress(self, result: TestResult, current: int, total: int):
        """Print progress indicator for current test"""
        status_emoji = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨",
            "no_response": "❓",
            "failed": "💥"
        }.get(result.status, "❓")

        print(f"  {status_emoji} {result.status.upper()} (Score: {result.validation_score}/100, "
              f"Time: {result.response_time:.2f}s, Length: {result.response_length})")

        if result.issues:
            for issue in result.issues[:2]:  # Show first 2 issues
                print(f"    📝 {issue}")

    def _generate_comprehensive_report(self, target_bot: str, test_results: List[TestResult],
                                     performance_metrics: Dict[str, Any], total_runtime: float) -> TestSuiteReport:
        """Generate comprehensive test suite report"""

        # Calculate summary statistics
        total_tests = len(test_results)
        successful_tests = sum(1 for r in test_results if r.status in ["success", "warning"])
        failed_tests = sum(1 for r in test_results if r.status in ["error", "critical", "failed", "no_response"])
        warning_tests = sum(1 for r in test_results if r.status == "warning")
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        # Calculate average score
        scores = [r.validation_score for r in test_results]
        average_score = sum(scores) / len(scores) if scores else 0

        # Performance analysis
        response_times = performance_metrics["response_times"]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        response_lengths = performance_metrics["response_lengths"]
        avg_response_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0

        # Generate recommendations
        recommendations = self._generate_suite_recommendations(test_results, performance_metrics)

        return TestSuiteReport(
            target_bot=target_bot,
            test_timestamp=datetime.now().isoformat(),
            total_tests=total_tests,
            successful_tests=successful_tests,
            failed_tests=failed_tests,
            warning_tests=warning_tests,
            success_rate=success_rate,
            average_score=average_score,
            total_runtime=total_runtime,
            test_results=test_results,
            performance_metrics={
                **performance_metrics,
                "avg_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "avg_response_length": avg_response_length,
                "keyboard_usage_rate": (performance_metrics["commands_with_keyboards"] / total_tests * 100) if total_tests > 0 else 0
            },
            recommendations=recommendations,
            summary={
                "overall_status": "EXCELLENT" if success_rate >= 95 else "GOOD" if success_rate >= 85 else "NEEDS_IMPROVEMENT",
                "top_issues": self._get_top_issues(test_results),
                "best_performing_category": self._get_best_category(performance_metrics),
                "needs_attention": [r.command for r in test_results if r.status in ["error", "critical", "failed"]]
            }
        )

    def _generate_suite_recommendations(self, test_results: List[TestResult],
                                      performance_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations for the entire test suite"""
        recommendations = []

        # Success rate analysis
        success_rate = sum(1 for r in test_results if r.status in ["success", "warning"]) / len(test_results) * 100
        if success_rate < 85:
            recommendations.append("Overall success rate is below 85% - prioritize fixing critical command failures")

        # Response time analysis
        avg_response_time = sum(performance_metrics["response_times"]) / len(performance_metrics["response_times"])
        if avg_response_time > 5.0:
            recommendations.append("Average response time exceeds 5 seconds - consider performance optimization")

        # Feature analysis
        failed_commands = [r for r in test_results if r.status in ["error", "critical", "failed"]]
        if failed_commands:
            categories_with_issues = set(r.metadata.get("category", "unknown") for r in failed_commands)
            recommendations.append(f"Focus on fixing issues in categories: {', '.join(categories_with_issues)}")

        # Keyboard usage
        keyboard_rate = performance_metrics["commands_with_keyboards"] / len(test_results) * 100
        if keyboard_rate < 30:
            recommendations.append("Consider adding more interactive keyboard elements to improve UX")

        return recommendations

    def _get_top_issues(self, test_results: List[TestResult]) -> List[str]:
        """Get most common issues across all tests"""
        all_issues = []
        for result in test_results:
            all_issues.extend(result.issues)

        # Count issue frequency
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Return top 3 most common issues
        return sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    def _get_best_category(self, performance_metrics: Dict[str, Any]) -> str:
        """Get the best performing category"""
        category_performance = performance_metrics["category_performance"]
        if not category_performance:
            return "none"

        best_category = max(category_performance.items(), key=lambda x: x[1]["avg_score"])
        return best_category[0]

    def save_report(self, report: TestSuiteReport, filename: Optional[str] = None) -> Path:
        """Save comprehensive test report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_report_{timestamp}.json"

        report_path = Path(filename)

        # Convert dataclass to dict for JSON serialization
        report_dict = asdict(report)

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        print(f"📊 Comprehensive test report saved to: {report_path}")
        return report_path

    def print_executive_summary(self, report: TestSuiteReport):
        """Print executive summary of test results"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE BOT TESTING - EXECUTIVE SUMMARY")
        print("="*80)
        print(f"🤖 Target Bot: {report.target_bot}")
        print(f"⏰ Test Duration: {report.total_runtime:.2f} seconds")
        print(f"🧪 Total Tests: {report.total_tests}")
        print(f"✅ Success Rate: {report.success_rate:.1f}%")
        print(f"📊 Average Score: {report.average_score:.1f}/100")
        print(f"⚡ Avg Response Time: {report.performance_metrics['avg_response_time']:.2f}s")
        print(f"🎮 Keyboard Usage: {report.performance_metrics['keyboard_usage_rate']:.1f}%")

        print(f"\n🎯 OVERALL STATUS: {report.summary['overall_status']}")

        if report.summary["needs_attention"]:
            print(f"\n⚠️ COMMANDS NEEDING ATTENTION:")
            for cmd in report.summary["needs_attention"]:
                print(f"   • {cmd}")

        if report.recommendations:
            print(f"\n💡 TOP RECOMMENDATIONS:")
            for i, rec in enumerate(report.recommendations[:3], 1):
                print(f"   {i}. {rec}")

        print("\n" + "="*80)


async def main():
    """Main execution function for comprehensive testing"""
    print("🚀 Starting Comprehensive Bot Testing Framework")
    print("Enhanced with intelligent validation and performance monitoring\n")

    tester = ComprehensiveBotTester()

    # Run comprehensive tests
    report = await tester.run_comprehensive_tests("@DevClaude_bot")

    # Print executive summary
    tester.print_executive_summary(report)

    # Save detailed report
    report_file = tester.save_report(report)

    print(f"\n✅ Comprehensive testing completed!")
    print(f"📊 Detailed report available at: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())