#!/usr/bin/env python3
"""
Runner script for the Intelligent Telegram Bot Auditor
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bot.features.intelligent_auditor import IntelligentTelegramBotAuditor, format_audit_report

async def run_audit():
    """Run the intelligent audit system"""
    project_root = Path(__file__).parent

    # Initialize auditor without Claude integration for now
    auditor = IntelligentTelegramBotAuditor(
        project_root=str(project_root),
        claude_integration=None  # We'll run static analysis only
    )

    print("🔍 Starting intelligent audit of Claude Telegram Bot...")
    print(f"📂 Project root: {project_root}")

    # Run audit focusing on critical areas
    result = await auditor.run_audit()

    # Print detailed results
    print("\n" + "="*80)
    print("📋 DETAILED AUDIT RESULTS")
    print("="*80)

    # Group issues by severity
    critical_issues = [i for i in result.issues if i.severity == "CRITICAL"]
    high_issues = [i for i in result.issues if i.severity == "HIGH"]
    medium_issues = [i for i in result.issues if i.severity == "MEDIUM"]
    low_issues = [i for i in result.issues if i.severity == "LOW"]

    def print_issues(issues, title):
        if not issues:
            return

        print(f"\n🚨 {title} ({len(issues)} issues):")
        print("-" * 50)

        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. [{issue.category}] {issue.description}")
            print(f"   📁 File: {issue.file_path}:{issue.line_number}")
            if issue.code_snippet:
                print(f"   💻 Code: {issue.code_snippet}")
            if issue.fix_suggestion:
                print(f"   🔧 Fix: {issue.fix_suggestion}")
            if issue.group:
                print(f"   🏷️  Group: {issue.group}")

    # Print issues by severity
    print_issues(critical_issues, "CRITICAL ISSUES")
    print_issues(high_issues, "HIGH PRIORITY ISSUES")
    print_issues(medium_issues, "MEDIUM PRIORITY ISSUES")
    print_issues(low_issues, "LOW PRIORITY ISSUES")

    # Summary
    print(f"\n📊 AUDIT SUMMARY:")
    print(f"   Total issues found: {result.total_issues}")
    print(f"   Critical: {result.critical_count}")
    print(f"   High: {result.high_count}")
    print(f"   Medium: {result.medium_count}")
    print(f"   Low: {result.low_count}")

    if result.recommendations:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in result.recommendations:
            print(f"   • {rec}")

    # Save detailed results to JSON
    output_file = project_root / f"audit_results_{result.total_issues}_issues.json"

    # Convert to serializable format
    issues_data = []
    for issue in result.issues:
        issues_data.append({
            "category": issue.category,
            "severity": issue.severity,
            "file_path": issue.file_path,
            "line_number": issue.line_number,
            "description": issue.description,
            "code_snippet": issue.code_snippet,
            "fix_suggestion": issue.fix_suggestion,
            "group": issue.group
        })

    audit_data = {
        "summary": {
            "total_issues": result.total_issues,
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "medium_count": result.medium_count,
            "low_count": result.low_count
        },
        "issues": issues_data,
        "recommendations": result.recommendations
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Detailed results saved to: {output_file}")

    return result

if __name__ == "__main__":
    try:
        result = asyncio.run(run_audit())

        # Exit with non-zero code if critical issues found
        if result.critical_count > 0:
            sys.exit(1)

    except Exception as e:
        print(f"❌ Audit failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)