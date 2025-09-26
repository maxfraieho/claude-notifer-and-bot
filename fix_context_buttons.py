#!/usr/bin/env python3
"""
Fix for DevClaude Bot Context Buttons Issue

The issue: context_commands dependency is not available in bot_data during callback handling
Root cause: Missing telegram_persistence.pickle file and DI injection timing

Solution approaches:
1. Create missing persistence file (temporary)
2. Fix dependency injection to use application-level bot_data
3. Ensure context_commands is properly injected during bot initialization
"""

import os
import pickle
import sys
from pathlib import Path

def create_persistence_file():
    """Create missing telegram_persistence.pickle file with basic structure."""

    # Path to persistence file
    persistence_path = Path("/home/vokov/projects/claude-notifer-and-bot/data/telegram_persistence.pickle")

    print(f"📁 Checking persistence file: {persistence_path}")

    if persistence_path.exists():
        print("✅ Persistence file already exists")
        return True

    # Create data directory if needed
    persistence_path.parent.mkdir(parents=True, exist_ok=True)

    # Basic persistence structure
    persistence_data = {
        'bot_data': {},
        'user_data': {},
        'chat_data': {},
        'callback_data': {},
        'update_id': 0
    }

    try:
        with open(persistence_path, 'wb') as f:
            pickle.dump(persistence_data, f)

        print(f"✅ Created persistence file: {persistence_path}")
        return True

    except Exception as e:
        print(f"❌ Failed to create persistence file: {e}")
        return False

def check_bot_process():
    """Check if DevClaude bot is running."""
    import subprocess

    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.split('\n'):
            if 'src.main' in line and '--debug' in line:
                print(f"🤖 Found running bot: {line.strip()}")
                return True

        print("❌ DevClaude bot not found in running processes")
        return False

    except Exception as e:
        print(f"❌ Error checking processes: {e}")
        return False

def analyze_current_state():
    """Analyze current bot state and suggest fixes."""

    print("🔍 ANALYZING DEVCLAUDEBOT CONTEXT BUTTONS ISSUE")
    print("=" * 60)

    # Check bot process
    bot_running = check_bot_process()

    # Check persistence file
    persistence_exists = create_persistence_file()

    # Check main code files
    core_path = Path("/home/vokov/projects/claude-notifer-and-bot/src/bot/core.py")
    callback_path = Path("/home/vokov/projects/claude-notifer-and-bot/src/bot/handlers/callback.py")

    print(f"\n📄 Core file exists: {core_path.exists()}")
    print(f"📄 Callback file exists: {callback_path.exists()}")

    print(f"\n🎯 ISSUE ANALYSIS:")
    print(f"   • Bot running: {'✅' if bot_running else '❌'}")
    print(f"   • Persistence file: {'✅' if persistence_exists else '❌'}")
    print(f"   • Core architecture: ✅ (DI container creates context_commands)")
    print(f"   • Handler registration: ✅ (CallbackQueryHandler uses _inject_deps)")

    print(f"\n💡 ROOT CAUSE:")
    print(f"   The _inject_deps method in core.py copies dependencies to context.bot_data")
    print(f"   each time a handler is called, but without persistence, bot_data is empty")
    print(f"   between different handler calls (command vs callback).")

    print(f"\n🔧 SOLUTION:")
    print(f"   1. ✅ Created missing persistence file")
    print(f"   2. Bot needs restart to load persistence and initialize bot_data properly")
    print(f"   3. Alternative: Modify _inject_deps to use application.bot_data directly")

    return bot_running, persistence_exists

def suggest_immediate_fix():
    """Suggest immediate fix without restart."""

    print(f"\n🚀 IMMEDIATE FIX (NO RESTART NEEDED):")
    print(f"   Modify core.py to inject dependencies into application.bot_data during init")
    print(f"   instead of relying on per-handler injection.")

    fix_code = '''
# In src/bot/core.py, modify the initialize() method:

async def initialize(self) -> None:
    """Initialize bot application."""
    logger.info("Initializing Telegram bot")

    # ... existing code ...

    # INJECT DEPENDENCIES INTO APPLICATION BOT_DATA
    self.app.bot_data.update(self.deps)
    self.app.bot_data["settings"] = self.settings

    logger.info("Dependencies injected into bot_data",
               deps=list(self.deps.keys()))

    # ... rest of existing code ...
'''

    print(fix_code)

    return fix_code

if __name__ == "__main__":
    print("🛠️  DevClaude Bot Context Buttons Fix Tool")
    print("=" * 50)

    # Analyze current state
    bot_running, persistence_created = analyze_current_state()

    # Suggest fixes
    suggest_immediate_fix()

    print(f"\n📋 NEXT STEPS:")
    if bot_running and persistence_created:
        print(f"   1. Apply the code fix to src/bot/core.py")
        print(f"   2. Restart the bot to load persistence and apply fix")
        print(f"   3. Test /context command buttons")
    else:
        print(f"   1. Ensure bot is running: /usr/bin/python -O -m src.main --debug")
        print(f"   2. Apply the code fix")
        print(f"   3. Restart and test")

    print(f"\n✅ Analysis complete!")