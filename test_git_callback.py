#!/usr/bin/env python3
"""Test script for Git callback functionality."""

import asyncio
import sys
import os
sys.path.insert(0, '/home/vokov/projects/claude-notifer-and-bot/src')

from unittest.mock import Mock, AsyncMock

async def test_git_callback():
    """Test the git callback handler."""

    # Import after adding to path
    from src.bot.handlers.callback import handle_git_callback
    from src.localization.util import t
    from src.config.settings import Settings

    # Create mock objects
    query = Mock()
    query.from_user.id = 123456789
    query.edit_message_text = AsyncMock()
    query.answer = AsyncMock()

    # Mock context with all required components
    context = Mock()
    context.bot_data = {
        "settings": Settings(),
        "claude_integration": Mock(),
        "localization": Mock(),
        "user_language_storage": Mock()
    }
    context.user_data = {
        "current_directory": "/home/vokov/projects/claude-notifer-and-bot"
    }

    # Mock claude integration
    claude_integration = context.bot_data["claude_integration"]
    claude_integration.create_session = AsyncMock(return_value="test_session_123")
    claude_integration.send_message = AsyncMock(return_value="Git operation completed successfully")

    # Mock localization function
    async def mock_t(ctx, user_id, key, **kwargs):
        translations = {
            "git.processing": "🔄 Executing Git operation: **{operation}**...",
            "git.success": "✅ Git operation **{operation}** completed successfully",
            "git.diff_title": "📊 **Git Diff**\n\n```\n{diff}\n```",
            "git.unknown_git_action": "❌ **Unknown Git action: {action}**\n\n{message}",
            "git.error": "❌ Git operation error: {error}",
            "git.buttons.back": "⬅️ Back",
            "git.buttons.help": "❓ Help"
        }
        return translations.get(key, f"[{key}]")

    # Replace the t function
    import src.bot.handlers.callback
    src.bot.handlers.callback.t = mock_t

    try:
        # Test different git actions
        test_actions = ["status", "help", "back", "add", "commit"]

        for action in test_actions:
            print(f"\n🧪 Testing Git action: {action}")

            # Reset the mock
            query.edit_message_text.reset_mock()

            # Call the git callback handler
            await handle_git_callback(query, action, context)

            # Check if edit_message_text was called
            if query.edit_message_text.called:
                call_args = query.edit_message_text.call_args
                print(f"✅ Git callback executed successfully for {action}")
                print(f"Message: {call_args[0][0][:100]}...")  # First 100 chars of message
            else:
                print(f"❌ edit_message_text was not called for {action}")

    except Exception as e:
        print(f"❌ Error testing git callback: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_git_callback())