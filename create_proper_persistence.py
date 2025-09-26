#!/usr/bin/env python3
"""
Create proper telegram_persistence.pickle file with correct structure
"""

import pickle
from pathlib import Path

def create_proper_persistence():
    """Create proper persistence file with all required fields."""

    persistence_path = Path("/home/vokov/projects/claude-notifer-and-bot/data/telegram_persistence.pickle")

    # Ensure directory exists
    persistence_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing corrupted file
    if persistence_path.exists():
        persistence_path.unlink()
        print(f"🗑️ Removed corrupted persistence file")

    # Create proper persistence structure based on telegram library requirements
    persistence_data = {
        'user_data': {},
        'chat_data': {},
        'bot_data': {},
        'callback_data': {},
        'conversations': {},
        'update_id': 0
    }

    try:
        with open(persistence_path, 'wb') as f:
            pickle.dump(persistence_data, f)

        print(f"✅ Created proper persistence file: {persistence_path}")

        # Verify the file can be loaded
        with open(persistence_path, 'rb') as f:
            data = pickle.load(f)
            print(f"✅ Verified persistence structure: {list(data.keys())}")

        return True

    except Exception as e:
        print(f"❌ Failed to create persistence file: {e}")
        return False

if __name__ == "__main__":
    create_proper_persistence()