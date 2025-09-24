"""
Additional Command Handlers for DevClaude_bot
Commands identified as missing during comprehensive testing
"""

import os
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
import structlog

from ..utils.message import get_user_id, get_effective_message
from ..utils.error_handler import safe_user_error

logger = structlog.get_logger(__name__)


async def projects_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available projects."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    try:
        # Show available projects in current and parent directories
        current_path = Path.cwd()
        projects = []

        # Look for common project indicators
        common_project_files = ['.git', 'pyproject.toml', 'package.json', 'Cargo.toml', 'go.mod', '.env', 'requirements.txt']

        # Check current directory
        for indicator in common_project_files:
            if (current_path / indicator).exists():
                projects.append(f"📁 **Current Project**: `{current_path.name}`")
                break

        # Check subdirectories
        try:
            for item in current_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    for indicator in common_project_files:
                        if (item / indicator).exists():
                            projects.append(f"📂 `{item.name}` - {indicator} detected")
                            break
                    if len(projects) > 10:  # Limit results
                        break
        except PermissionError:
            pass

        if not projects:
            projects.append("No projects detected in current directory")
            projects.append("Use `/ls` to see available directories")

        project_text = "🏗️ **Available Projects**\n\n" + "\n".join(projects[:10])
        project_text += f"\n\n📍 Current location: `{current_path}`"
        project_text += f"\n💡 Use `/cd <project-name>` to navigate"

        await message.reply_text(project_text, parse_mode='Markdown')
        logger.info("Projects command executed", user_id=user_id)
    except Exception as e:
        await safe_user_error(update, context, "errors.projects_failed", e)


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigate back to previous directory."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    try:
        current_path = Path.cwd()
        parent_path = current_path.parent

        if current_path != parent_path:  # Not at root
            os.chdir(parent_path)
            back_text = f"⬅️ **Navigated Back**\n\n📁 From: `{current_path.name}`\n📍 To: `{parent_path}`"

            # Add quick ls view
            try:
                items = []
                for item in parent_path.iterdir():
                    if len(items) < 5:  # Show first 5 items
                        icon = "📁" if item.is_dir() else "📄"
                        items.append(f"{icon} `{item.name}`")
                if items:
                    back_text += f"\n\n**Contents:**\n" + "\n".join(items)
                    if len(list(parent_path.iterdir())) > 5:
                        back_text += f"\n... and {len(list(parent_path.iterdir())) - 5} more items"
            except PermissionError:
                pass

        else:
            back_text = "⚠️ Already at root directory, cannot go back further."

        await message.reply_text(back_text, parse_mode='Markdown')
        logger.info("Back command executed", user_id=user_id,
                   old_path=str(current_path), new_path=str(Path.cwd()))
    except Exception as e:
        await safe_user_error(update, context, "errors.back_failed", e)


async def run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run scripts and commands."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    try:
        # Show available run options based on current directory
        current_path = Path.cwd()
        run_options = []

        # Check for common executable files and commands
        executable_patterns = {
            'package.json': "📦 `npm run start` or `npm run dev`",
            'pyproject.toml': "🐍 `poetry run python -m module` or `python script.py`",
            'requirements.txt': "🐍 `python script.py` or `pip install -r requirements.txt`",
            'Cargo.toml': "🦀 `cargo run` or `cargo build`",
            'Makefile': "🔧 `make` or `make build`",
            'docker-compose.yml': "🐳 `docker-compose up`",
            '.env': "⚙️ Environment configured - check main scripts"
        }

        for file, command in executable_patterns.items():
            if (current_path / file).exists():
                run_options.append(command)

        # Look for executable files
        try:
            for item in current_path.iterdir():
                if item.is_file() and item.suffix in ['.py', '.sh', '.js', '.ts']:
                    if len(run_options) < 8:
                        icon = "🐍" if item.suffix == '.py' else "📜"
                        run_options.append(f"{icon} `{item.name}`")
        except PermissionError:
            pass

        if not run_options:
            run_text = """⚡ **Run Commands**

No executable files detected in current directory.

**Generic Commands:**
🐍 `python script.py` - Run Python scripts
📜 `bash script.sh` - Run shell scripts
📦 `npm run <command>` - Run npm scripts
🔧 `make <target>` - Run make targets

💡 Navigate to a project directory first using `/projects` and `/cd`"""
        else:
            run_text = f"""⚡ **Run Commands**

**Available in current directory:**
{chr(10).join(run_options[:8])}

📍 Location: `{current_path.name}`
💡 Send message like: "run python script.py" to execute"""

        await message.reply_text(run_text, parse_mode='Markdown')
        logger.info("Run command executed", user_id=user_id)
    except Exception as e:
        await safe_user_error(update, context, "errors.run_failed", e)


async def edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick file editing."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    try:
        # Show editable files in current directory
        current_path = Path.cwd()
        editable_files = []

        # Common editable file extensions
        editable_extensions = {'.py', '.js', '.ts', '.json', '.md', '.txt', '.yml', '.yaml',
                              '.toml', '.cfg', '.ini', '.env', '.sh', '.css', '.html'}

        try:
            for item in current_path.iterdir():
                if item.is_file() and item.suffix.lower() in editable_extensions:
                    if len(editable_files) < 10:
                        size = item.stat().st_size
                        size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                        icon = "🐍" if item.suffix == '.py' else "📝"
                        editable_files.append(f"{icon} `{item.name}` ({size_str})")
        except PermissionError:
            pass

        if editable_files:
            edit_text = f"""📝 **Quick File Editing**

**Editable files in current directory:**
{chr(10).join(editable_files)}

📍 Location: `{current_path.name}`
💡 Send message like: "edit filename.py" to open file for editing"""
        else:
            edit_text = """📝 **Quick File Editing**

No editable files found in current directory.

**Supported formats:**
🐍 Python (.py), 📜 JavaScript (.js), 📄 JSON (.json)
📝 Markdown (.md), ⚙️ Config files (.yml, .toml, .env)
🌐 Web files (.html, .css), 📋 Text files (.txt)

💡 Navigate to project directory using `/projects` and `/cd`"""

        await message.reply_text(edit_text, parse_mode='Markdown')
        logger.info("Edit command executed", user_id=user_id)
    except Exception as e:
        await safe_user_error(update, context, "errors.edit_failed", e)


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for files and content in project."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    try:
        current_path = Path.cwd()

        # Quick search preview - show directory structure
        search_info = []
        file_count = 0
        dir_count = 0

        try:
            for item in current_path.rglob('*'):
                if item.is_file():
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1

                # Stop counting after reasonable limit
                if file_count + dir_count > 100:
                    break
        except PermissionError:
            pass

        # Show project structure overview
        search_text = f"""🔍 **Search & Discovery**

📊 **Current Project Overview:**
📁 Directories: ~{dir_count}
📄 Files: ~{file_count}
📍 Location: `{current_path.name}`

**🔍 Search Examples:**
• "find Python files" - Locate .py files
• "search for TODO" - Find TODO comments
• "find config files" - Locate configuration files
• "search imports" - Find import statements

**📁 Quick Navigation:**
• Use `/ls` to browse current directory
• Use `/projects` to find project directories
• Use `/cd <directory>` to navigate

💡 Send a message starting with "search" or "find" to begin searching"""

        await message.reply_text(search_text, parse_mode='Markdown')
        logger.info("Search command executed", user_id=user_id)
    except Exception as e:
        await safe_user_error(update, context, "errors.search_failed", e)