#!/usr/bin/env python3
"""
Interactive Bot Tester - Real-time testing of @DevClaude_bot
Tests all commands and functionality in real Telegram environment
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from pyrogram import Client
from pyrogram.errors import FloodWait

class InteractiveBotTester:
    """Real-time bot testing via Telegram API"""

    def __init__(self):
        # Load configuration from .env
        self.api_id = 28605494
        self.api_hash = "3ff0adf3dd08d70a5dc3f1bea8e9285f"
        self.session_string = self._load_session()

        self.client = Client(
            "bot_tester",
            api_id=self.api_id,
            api_hash=self.api_hash,
            session_string=self.session_string
        )

    def _load_session(self):
        """Load session string from file"""
        try:
            session_path = Path("/home/vokov/projects/arhitector/WORKING_SESSION.txt")
            if session_path.exists():
                return session_path.read_text().strip()
        except Exception as e:
            print(f"⚠️ Could not load session: {e}")
        return None

    async def test_bot_commands(self, target_bot: str = "@DevClaude_bot") -> dict:
        """Test bot commands interactively"""
        print(f"🧪 Starting interactive testing of {target_bot}")

        test_results = {
            "target_bot": target_bot,
            "test_timestamp": datetime.now().isoformat(),
            "commands_tested": {},
            "issues_found": [],
            "recommendations": [],
            "overall_status": "pending"
        }

        # Common bot commands to test
        commands_to_test = [
            "/start",
            "/help",
            "/pwd",
            "/status",
            "/settings",
            "/language"
        ]

        try:
            await self.client.start()
            print(f"✅ Connected to Telegram successfully")

            for cmd in commands_to_test:
                try:
                    print(f"🔍 Testing command: {cmd}")

                    # Send command to bot
                    await self.client.send_message(target_bot, cmd)
                    await asyncio.sleep(3)  # Wait for response

                    # Get last messages from bot
                    messages = []
                    async for msg in self.client.get_chat_history(target_bot, limit=1):
                        if msg.from_user and msg.from_user.username and "DevClaude" in msg.from_user.username:
                            messages.append(msg)
                            break

                    if messages:
                        response = messages[0]
                        response_text = response.text or "No text response"

                        # Analyze response
                        cmd_result = await self._analyze_response(cmd, response_text)
                        test_results["commands_tested"][cmd] = cmd_result

                        print(f"  📄 Response: {response_text[:100]}...")

                        # Check for specific issues
                        if self._is_problematic_response(response_text):
                            issue = {
                                "command": cmd,
                                "issue": "Problematic response detected",
                                "response": response_text,
                                "detected_problems": self._detect_problems(response_text)
                            }
                            test_results["issues_found"].append(issue)
                            print(f"  ⚠️ Issue detected: {issue['detected_problems']}")
                    else:
                        print(f"  ❌ No response received for {cmd}")
                        test_results["commands_tested"][cmd] = {
                            "status": "no_response",
                            "response": None,
                            "issues": ["No response received"]
                        }

                except FloodWait as e:
                    print(f"⏰ FloodWait: waiting {e.value} seconds")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    print(f"❌ Error testing {cmd}: {e}")
                    test_results["commands_tested"][cmd] = {
                        "status": "error",
                        "error": str(e)
                    }

            # Calculate overall status
            test_results["overall_status"] = self._calculate_status(test_results)
            test_results["recommendations"] = self._generate_recommendations(test_results)

            print(f"\n🎯 Testing completed!")
            print(f"Commands tested: {len(test_results['commands_tested'])}")
            print(f"Issues found: {len(test_results['issues_found'])}")
            print(f"Overall status: {test_results['overall_status']}")

        except Exception as e:
            print(f"💥 Testing failed: {e}")
            test_results["overall_status"] = "failed"
            test_results["error"] = str(e)
        finally:
            await self.client.stop()

        return test_results

    async def _analyze_response(self, command: str, response_text: str) -> dict:
        """Analyze individual command response"""
        result = {
            "command": command,
            "response": response_text,
            "status": "success",
            "issues": [],
            "score": 100
        }

        # Special analysis for /pwd command
        if command == "/pwd" and "pwd.title" in response_text.lower():
            result["issues"].append("Localization key returned instead of actual directory")
            result["status"] = "issues_found"
            result["score"] = 30

        # Check for other common issues
        if self._is_error_response(response_text):
            result["issues"].append("Error in response")
            result["status"] = "error"
            result["score"] = 20

        # Check for empty or unclear responses
        if len(response_text.strip()) < 10:
            result["issues"].append("Very short response")
            result["score"] -= 20

        return result

    def _is_problematic_response(self, response_text: str) -> bool:
        """Check if response indicates problems"""
        problematic_indicators = [
            ".title", ".description", ".error",  # Localization keys
            "error", "exception", "failed",      # Error indicators
            "undefined", "null", "none",         # Empty values
            "не вдалося", "помилка"              # Ukrainian error messages
        ]

        text_lower = response_text.lower()
        return any(indicator in text_lower for indicator in problematic_indicators)

    def _is_error_response(self, response_text: str) -> bool:
        """Check if response is an error"""
        error_indicators = [
            "error", "exception", "failed", "не вдалося", "помилка"
        ]
        text_lower = response_text.lower()
        return any(indicator in text_lower for indicator in error_indicators)

    def _detect_problems(self, response_text: str) -> list:
        """Detect specific problems in response"""
        problems = []
        text_lower = response_text.lower()

        if ".title" in text_lower:
            problems.append("Localization key instead of actual content")
        if "error" in text_lower:
            problems.append("Contains error message")
        if len(response_text.strip()) < 10:
            problems.append("Very short response")

        return problems

    def _calculate_status(self, test_results: dict) -> str:
        """Calculate overall testing status"""
        total_commands = len(test_results["commands_tested"])
        if total_commands == 0:
            return "no_tests"

        issues_count = len(test_results["issues_found"])

        if issues_count == 0:
            return "healthy"
        elif issues_count < total_commands * 0.3:
            return "minor_issues"
        else:
            return "major_issues"

    def _generate_recommendations(self, test_results: dict) -> list:
        """Generate recommendations based on test results"""
        recommendations = []

        for issue in test_results["issues_found"]:
            if "Localization key" in issue.get("issue", ""):
                recommendations.append("Fix localization system to return actual values instead of keys")
            if "No response" in issue.get("issue", ""):
                recommendations.append("Ensure all commands have proper response handling")

        if len(test_results["issues_found"]) > 0:
            recommendations.append("Perform end-to-end testing of user workflows")
            recommendations.append("Review error handling and user feedback")

        return recommendations

    def save_report(self, test_results: dict, filename: str = None):
        """Save test results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bot_test_report_{timestamp}.json"

        report_path = Path(filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

        print(f"📊 Test report saved to: {report_path}")
        return report_path

    def print_detailed_report(self, test_results: dict):
        """Print detailed test report to console"""
        print("\n" + "="*60)
        print("🤖 INTERACTIVE BOT TESTING REPORT")
        print("="*60)
        print(f"🎯 Target Bot: {test_results['target_bot']}")
        print(f"⏰ Test Time: {test_results['test_timestamp']}")
        print(f"📊 Overall Status: {test_results['overall_status'].upper()}")
        print(f"🧪 Commands Tested: {len(test_results['commands_tested'])}")
        print(f"⚠️ Issues Found: {len(test_results['issues_found'])}")

        print("\n📋 COMMAND TEST RESULTS:")
        print("-" * 40)
        for cmd, result in test_results["commands_tested"].items():
            status_emoji = "✅" if result.get("status") == "success" else "❌"
            print(f"{status_emoji} {cmd}: {result.get('status', 'unknown')}")
            if result.get("issues"):
                for issue in result["issues"]:
                    print(f"    ⚠️ {issue}")

        if test_results["issues_found"]:
            print("\n🚨 CRITICAL ISSUES:")
            print("-" * 40)
            for i, issue in enumerate(test_results["issues_found"], 1):
                print(f"{i}. Command: {issue['command']}")
                print(f"   Issue: {issue['issue']}")
                if issue.get('detected_problems'):
                    print(f"   Problems: {', '.join(issue['detected_problems'])}")
                print()

        if test_results["recommendations"]:
            print("🎯 RECOMMENDATIONS:")
            print("-" * 40)
            for i, rec in enumerate(test_results["recommendations"], 1):
                print(f"{i}. {rec}")

        print("\n" + "="*60)


async def main():
    """Main execution function"""
    print("🚀 Starting Interactive Bot Testing for @DevClaude_bot")
    print("This will test commands and functionality in real-time via Telegram API\n")

    tester = InteractiveBotTester()

    # Run the tests
    results = await tester.test_bot_commands("@DevClaude_bot")

    # Print detailed report
    tester.print_detailed_report(results)

    # Save report to file
    report_file = tester.save_report(results)

    print(f"\n✅ Interactive testing completed!")
    print(f"📊 Detailed report saved to: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())