#!/usr/bin/env python3
"""Test script for Git command functionality."""

import asyncio
import sys
import os
sys.path.insert(0, '/home/vokov/projects/claude-notifer-and-bot/src')

from unittest.mock import Mock, AsyncMock
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

async def test_git_command():
    """Test the git command handler."""

    # Import after adding to path
    from src.bot.handlers.command import git_command
    from src.localization.util import t

    # Create mock objects
    user = User(id=123456789, first_name="Test", is_bot=False, username="testuser")
    chat = Chat(id=123456789, type="private")
    message = Mock()
    message.reply_text = AsyncMock()

    update = Mock()
    update.effective_user = user
    update.effective_message = message

    # Mock context
    context = Mock()
    context.bot_data = {
        "localization": Mock(),
        "user_language_storage": Mock()
    }

    # Mock localization function
    async def mock_t(ctx, user_id, key, **kwargs):
        translations = {
            "git.title": "🔧 **Git Управління**",
            "git.description": "Основні Git операції для вашого проекту:",
            "git.buttons.status": "📊 Статус",
            "git.buttons.add": "➕ Додати",
            "git.buttons.commit": "💾 Зберегти",
            "git.buttons.push": "⬆️ Надіслати",
            "git.buttons.pull": "⬇️ Оновити",
            "git.buttons.log": "📜 Історія",
            "git.buttons.diff": "🔍 Зміни",
            "git.buttons.branch": "🌿 Гілки",
            "git.buttons.help": "❓ Довідка",
        }
        return translations.get(key, f"[{key}]")

    # Replace the t function
    import src.bot.handlers.command
    src.bot.handlers.command.t = mock_t

    try:
        # Call the git command
        await git_command(update, context)

        # Check if reply_text was called
        if message.reply_text.called:
            call_args = message.reply_text.call_args
            print("✅ Git command executed successfully!")
            print(f"Called with: {call_args}")

            # Check for InlineKeyboardMarkup
            if len(call_args) > 1 and 'reply_markup' in call_args[1]:
                print("✅ InlineKeyboardMarkup was included!")
            else:
                print("❌ No InlineKeyboardMarkup found")
        else:
            print("❌ reply_text was not called")

    except Exception as e:
        print(f"❌ Error testing git command: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_git_command())