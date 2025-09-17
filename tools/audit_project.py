#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit script for Claude Telegram Bot
- Localization gaps
- Unfinished functionality
- Technical debt
Generates Markdown report
"""

import re
import json
from pathlib import Path
from datetime import datetime

# === PATTERNS ===
HARDCODED_PATTERNS = [
    r'reply_text\(["\']([^"\']{10,})["\']',
    r'send_message\(["\']([^"\']{10,})["\']',
    r'raise \w+Error\(["\']([^"\']+)["\']',
    r'print\(["\']([^"\']{10,})["\']',
    r'logger\.\w+\(["\']([^"\']{10,})["\']',
    r'["\']([^"\']*(?:Error|Message|Warning|Success|Failed)[^"\']*)["\']',
]

INCOMPLETE_PATTERNS = [
    r'TODO[:|\s]([^\n]+)',
    r'FIXME[:|\s]([^\n]+)',
    r'XXX[:|\s]([^\n]+)',
    r'raise NotImplementedError',
    r'pass\s*#.*(?:todo|implement|fixme)',
    r'def \w+\([^)]*\):\s*pass',
]

# === SCANNING ===
def scan_codebase(root_dir="src"):
    findings = {"hardcoded": [], "incomplete": []}
    
    for py_file in Path(root_dir).rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except:
            continue
            
        # Search hardcoded patterns
        for pattern in HARDCODED_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                findings["hardcoded"].append({
                    "file": str(py_file),
                    "pattern": pattern,
                    "match": match.group(0)[:100]
                })
        
        # Search incomplete patterns
        for pattern in INCOMPLETE_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
                findings["incomplete"].append({
                    "file": str(py_file),
                    "pattern": pattern,
                    "match": match.group(0)[:100]
                })
    
    return findings

def check_translations():
    try:
        with open("src/localization/translations/en.json", "r", encoding="utf-8") as f:
            en = json.load(f)
        with open("src/localization/translations/uk.json", "r", encoding="utf-8") as f:
            uk = json.load(f)
    except FileNotFoundError:
        return []
    
    def flatten_dict(d, parent_key="", sep="."):
        items = []
        for k, v in d.items():
            if k.startswith("_"):  # Skip meta keys
                continue
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    en_flat = flatten_dict(en)
    uk_flat = flatten_dict(uk)
    
    missing_in_uk = [k for k in en_flat if k not in uk_flat]
    missing_in_en = [k for k in uk_flat if k not in en_flat]
    
    return {"missing_in_uk": missing_in_uk, "missing_in_en": missing_in_en}

# === REPORT ===
def generate_report(findings, missing_keys, out="audit_report.md"):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    total_hardcoded = len(findings['hardcoded'])
    total_incomplete = len(findings['incomplete'])
    total_missing_uk = len(missing_keys.get('missing_in_uk', []))
    total_missing_en = len(missing_keys.get('missing_in_en', []))
    
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# 🔍 Audit Report — Claude Bot\n\n")
        f.write(f"**Generated:** {now}\n\n")
        
        f.write("## 📊 SUMMARY\n")
        f.write(f"- **Hardcoded strings**: {total_hardcoded}\n")
        f.write(f"- **Incomplete features**: {total_incomplete}\n")
        f.write(f"- **Missing UK translations**: {total_missing_uk}\n")
        f.write(f"- **Missing EN translations**: {total_missing_en}\n\n")
        
        # Severity assessment
        critical_issues = total_hardcoded + total_incomplete
        f.write("## 🚦 SEVERITY BREAKDOWN\n")
        if critical_issues > 50:
            f.write("- 🔴 **Critical**: High number of issues detected\n")
        elif critical_issues > 20:
            f.write("- 🟠 **High**: Moderate number of issues\n")
        elif critical_issues > 0:
            f.write("- 🟡 **Medium**: Some issues found\n")
        else:
            f.write("- 🟢 **Low**: Minimal issues detected\n")
        f.write("\n")

        f.write("## 🌐 Localization Issues\n\n")
        
        f.write("### Missing Ukrainian Translations\n")
        if missing_keys.get('missing_in_uk'):
            for k in missing_keys['missing_in_uk'][:20]:
                f.write(f"- [ ] Missing key: `{k}`\n")
            if len(missing_keys['missing_in_uk']) > 20:
                f.write(f"- ... and {len(missing_keys['missing_in_uk']) - 20} more\n")
        else:
            f.write("✅ No missing Ukrainian translation keys detected.\n")
        f.write("\n")
        
        f.write("### Missing English Translations\n")
        if missing_keys.get('missing_in_en'):
            for k in missing_keys['missing_in_en'][:20]:
                f.write(f"- [ ] Missing key: `{k}`\n")
            if len(missing_keys['missing_in_en']) > 20:
                f.write(f"- ... and {len(missing_keys['missing_in_en']) - 20} more\n")
        else:
            f.write("✅ No missing English translation keys detected.\n")
        f.write("\n")

        f.write("## ⚙️ Functionality Gaps\n\n")
        if findings["incomplete"]:
            for i, item in enumerate(findings["incomplete"][:25], 1):
                f.write(f"- [ ] **F{i:03d}** `{item['file']}`: {item['match']}\n")
            if len(findings["incomplete"]) > 25:
                f.write(f"- ... and {len(findings['incomplete']) - 25} more issues\n")
        else:
            f.write("✅ No unfinished functionality found.\n")
        f.write("\n")

        f.write("## 🔧 Technical Debt (Hardcoded Strings)\n\n")
        if findings["hardcoded"]:
            for i, item in enumerate(findings["hardcoded"][:25], 1):
                f.write(f"- [ ] **L{i:03d}** `{item['file']}`: {item['match']}\n")
            if len(findings["hardcoded"]) > 25:
                f.write(f"- ... and {len(findings['hardcoded']) - 25} more issues\n")
        else:
            f.write("✅ No hardcoded user-facing strings detected.\n")
        f.write("\n")
        
        # Add recommendations section
        f.write("## 🚀 Recommended Action Plan\n\n")
        
        if total_hardcoded > 0:
            f.write("### Priority 1: Localization\n")
            f.write("1. Extract hardcoded strings to translation files\n")
            f.write("2. Add missing translation keys\n")
            f.write("3. Update code to use `t()` localization function\n\n")
        
        if total_incomplete > 0:
            f.write("### Priority 2: Complete Functionality\n")
            f.write("1. Implement TODO items\n")
            f.write("2. Replace NotImplementedError with proper functionality\n")
            f.write("3. Add proper error handling\n\n")
        
        f.write("### Priority 3: Quality Assurance\n")
        f.write("1. Test all localized messages\n")
        f.write("2. Verify Ukrainian translation quality\n")
        f.write("3. Ensure consistent terminology\n\n")

    return out

# === MAIN ===
if __name__ == "__main__":
    print("🔍 Starting Claude Bot audit...")
    findings = scan_codebase("src")
    missing = check_translations()
    report_file = generate_report(findings, missing)
    print(f"✅ Audit completed. Report saved to {report_file}")
    
    # Print quick summary
    total_issues = len(findings['hardcoded']) + len(findings['incomplete'])
    missing_count = len(missing.get('missing_in_uk', [])) + len(missing.get('missing_in_en', []))
    
    print(f"\n📊 Quick Summary:")
    print(f"   🔧 Technical issues: {total_issues}")
    print(f"   🌐 Translation gaps: {missing_count}")
    print(f"   📄 Report: {report_file}")