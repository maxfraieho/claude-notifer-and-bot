#!/usr/bin/env python3
"""Validate translation keys between base and target locales."""
import json
import sys
from pathlib import Path

def deep_keys(d, parent_key=''):
    keys = []
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        keys.append(new_key)
        if isinstance(v, dict):
            keys.extend(deep_keys(v, new_key))
    return set(keys)

def main():
    if len(sys.argv) != 5 or sys.argv[1] != '--base' or sys.argv[3] != '--target':
        print("Usage: check_i18n.py --base en.json --target uk.json")
        sys.exit(1)

    base_path = Path(sys.argv[2])
    target_path = Path(sys.argv[4])

    with open(base_path) as f:
        base = json.load(f)
    with open(target_path) as f:
        target = json.load(f)

    base_keys = deep_keys(base)
    target_keys = deep_keys(target)

    missing_in_target = base_keys - target_keys
    extra_in_target = target_keys - base_keys

    if missing_in_target:
        print("❌ Missing keys in target:", sorted(missing_in_target))
    if extra_in_target:
        print("⚠️  Extra keys in target (not in base):", sorted(extra_in_target))

    if missing_in_target or extra_in_target:
        sys.exit(1)
    else:
        print("✅ All keys synchronized")

if __name__ == '__main__':
    main()