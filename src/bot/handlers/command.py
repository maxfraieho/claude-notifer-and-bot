"""Command handlers for bot operations."""

import structlog
import asyncio
import re
import pexpect
import time
from datetime import datetime, timedelta
from typing import cast, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ...claude.facade import ClaudeIntegration
from ...config.settings import Settings
from ...security.audit import AuditLogger
from ...security.validators import SecurityValidator
from ...localization.util import t, get_user_id, get_effective_message
from ..utils.error_handler import safe_user_error, safe_critical_error
from datetime import datetime
from pathlib import Path
import uuid

logger = structlog.get_logger()


# Pexpect functions for Claude CLI authentication
async def claude_auth_with_pexpect(timeout: int = 30) -> Tuple[bool, str, Optional[pexpect.spawn]]:
    """
    Захоплює URL авторизації з команди claude login використовуючи pexpect.
    
    Args:
        timeout: Максимальний час очікування в секундах
        
    Returns:
        Tuple з (успіх, URL_або_помилка, процес_pexpect)
    """
    try:
        logger.info("Starting claude login with pexpect")
        
        # Запускаємо процес claude login з підтримкою UTF-8
        child = pexpect.spawn('claude login', encoding='utf-8', timeout=timeout)
        
        # Патерни для пошуку в виводі команди
        patterns = [
            r'https://claude\.ai/[^\s]*',      # Claude.ai URL
            r'https://[^\s]*anthropic[^\s]*', # Anthropic URL
            r'https://[^\s]+',                # Будь-який HTTPS URL
            r'Please visit:?\s*(https://[^\s]+)',  # "Please visit: URL"
            r'Go to:?\s*(https://[^\s]+)',    # "Go to: URL"
            pexpect.TIMEOUT,
            pexpect.EOF
        ]
        
        url = None
        output_buffer = ""
        start_time = time.time()
        
        logger.info("Waiting for authentication URL...")
        
        while time.time() - start_time < timeout:
            try:
                # Очікуємо на один з патернів
                index = child.expect(patterns, timeout=5)
                
                # Збираємо вивід
                if child.before:
                    output_buffer += child.before
                if child.after and index < 5:
                    output_buffer += child.after
                
                logger.debug("Pattern matched", index=index, output_snippet=output_buffer[-200:])
                
                if index < 5:  # Знайдено URL патерн
                    # Витягуємо всі URL з накопиченого виводу
                    url_matches = re.findall(r'https://[^\s]+', output_buffer)
                    
                    if url_matches:
                        # Пріоритет: Claude.ai > Anthropic > інші HTTPS
                        for match in url_matches:
                            if 'claude.ai' in match and ('auth' in match or 'login' in match):
                                url = match
                                break
                        if not url:
                            for match in url_matches:
                                if 'anthropic' in match:
                                    url = match
                                    break
                        if not url:
                            url = url_matches[0]  # Перший HTTPS URL
                        
                        # Очищуємо URL від зайвих символів
                        url = url.rstrip('.,;)')
                        
                        logger.info("Authentication URL captured", url=url)
                        return True, url, child
                        
                elif index == 5:  # TIMEOUT
                    logger.debug("Timeout waiting for pattern, continuing...")
                    continue
                    
                elif index == 6:  # EOF
                    logger.warning("Process ended unexpectedly", output=output_buffer)
                    break
                    
            except pexpect.TIMEOUT:
                # Спробуємо прочитати доступний вивід
                try:
                    available = child.read_nonblocking(size=1024, timeout=0.1)
                    if available:
                        output_buffer += available
                        logger.debug("Read additional output", content=available[:100])
                except:
                    pass
                continue
                
        # Якщо дійшли сюди - не знайшли URL
        logger.error("No authentication URL found", output=output_buffer)
        return False, f"No authentication URL found in output: {output_buffer}", child
        
    except Exception as e:
        logger.error("Error starting claude login", error=str(e))
        return False, f"Error starting claude login: {str(e)}", None


async def send_auth_code(child: pexpect.spawn, code: str, timeout: int = 30) -> Tuple[bool, str]:
    """
    Відправляє код авторизації в процес claude login.
    
    Args:
        child: Процес pexpect
        code: Код авторизації від користувача
        timeout: Максимальний час очікування
        
    Returns:
        Tuple з (успіх, вивід_або_помилка)
    """
    try:
        logger.info("Sending authentication code")
        
        # Відправляємо код авторизації
        child.sendline(code)
        
        # Патерни для результату авторизації
        patterns = [
            r'(?i)(success|successful|authenticated|complete)',  # Успіх
            r'(?i)(error|failed|invalid|expired|wrong)',        # Помилка
            r'(?i)(rate limit|too many|quota|limit exceeded)',  # Ліміти
            pexpect.TIMEOUT,
            pexpect.EOF
        ]
        
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                index = child.expect(patterns, timeout=5)
                
                # Збираємо вся вивід
                if child.before:
                    output += child.before
                if child.after and index < 3:
                    output += child.after
                
                logger.debug("Auth response pattern", index=index, output_snippet=output[-200:])
                
                if index == 0:  # Успіх
                    logger.info("Authentication successful")
                    child.close()
                    return True, output
                    
                elif index == 1:  # Помилка авторизації
                    logger.warning("Authentication failed", error=output)
                    child.close()
                    return False, output
                    
                elif index == 2:  # Ліміти API
                    logger.warning("Rate limit or quota issue", output=output)
                    child.close()
                    return False, output
                    
                elif index == 3:  # TIMEOUT
                    continue
                    
                elif index == 4:  # EOF
                    child.close()
                    # Перевіряємо exit код
                    if child.exitstatus == 0:
                        logger.info("Process exited successfully")
                        return True, output
                    else:
                        logger.warning("Process exited with error", exit_code=child.exitstatus)
                        return False, f"Process exited with code {child.exitstatus}: {output}"
                        
            except pexpect.TIMEOUT:
                logger.debug("Waiting for auth response...")
                continue
                
        # Timeout досягнуто
        logger.error("Authentication timeout", output=output)
        child.close()
        return False, f"Authentication timed out after {timeout}s: {output}"
        
    except Exception as e:
        logger.error("Error during authentication", error=str(e))
        if child and child.isalive():
            child.close()
        return False, f"Error during authentication: {str(e)}"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message or not update.effective_user:
        return
    
    # Get localization components from bot data
    localization = context.bot_data.get("localization")
    user_language_storage = context.bot_data.get("user_language_storage")
    
    if localization and user_language_storage:
        # Build localized welcome message
        welcome_text = await t(context, user_id, "commands.start.welcome", name=update.effective_user.first_name)
        description_text = await t(context, user_id, "commands.start.description")
        available_commands_text = await t(context, user_id, "commands.start.available_commands")
        
        help_cmd_text = await t(context, user_id, "commands.start.help_cmd")
        new_cmd_text = await t(context, user_id, "commands.start.new_cmd")
        ls_cmd_text = await t(context, user_id, "commands.start.ls_cmd")
        cd_cmd_text = await t(context, user_id, "commands.start.cd_cmd")
        projects_cmd_text = await t(context, user_id, "commands.start.projects_cmd")
        status_cmd_text = await t(context, user_id, "commands.start.status_cmd")
        actions_cmd_text = await t(context, user_id, "commands.start.actions_cmd")
        git_cmd_text = await t(context, user_id, "commands.start.git_cmd")
        
        quick_start_text = await t(context, user_id, "commands.start.quick_start")
        quick_start_1_text = await t(context, user_id, "commands.start.quick_start_1")
        quick_start_2_text = await t(context, user_id, "commands.start.quick_start_2")
        quick_start_3_text = await t(context, user_id, "commands.start.quick_start_3")
        
        security_note_text = await t(context, user_id, "commands.start.security_note")
        usage_note_text = await t(context, user_id, "commands.start.usage_note")
        
        welcome_message = (
            f"{welcome_text}\n\n"
            f"{description_text}\n\n"
            f"{available_commands_text}\n"
            f"• `/help` - {help_cmd_text}\n"
            f"• `/new` - {new_cmd_text}\n"
            f"• `/ls` - {ls_cmd_text}\n"
            f"• `/cd <dir>` - {cd_cmd_text}\n"
            f"• `/projects` - {projects_cmd_text}\n"
            f"• `/status` - {status_cmd_text}\n"
            f"• `/actions` - {actions_cmd_text}\n"
            f"• `/git` - {git_cmd_text}\n\n"
            f"{quick_start_text}\n"
            f"1. {quick_start_1_text}\n"
            f"2. {quick_start_2_text}\n"
            f"3. {quick_start_3_text}\n\n"
            f"{security_note_text}\n"
            f"{usage_note_text}"
        )
        
        # Localized button texts
        show_projects_text = await t(context, user_id, "buttons.show_projects")
        get_help_text = await t(context, user_id, "buttons.get_help")
        new_session_text = await t(context, user_id, "buttons.new_session")
        check_status_text = await t(context, user_id, "buttons.check_status")
        language_settings_text = await t(context, user_id, "buttons.language_settings")
        
        # Add quick action buttons with language switcher
        keyboard = [
            [
                InlineKeyboardButton(show_projects_text, callback_data="action:show_projects"),
                InlineKeyboardButton(get_help_text, callback_data="action:help"),
            ],
            [
                InlineKeyboardButton(new_session_text, callback_data="action:new_session"),
                InlineKeyboardButton(check_status_text, callback_data="action:status"),
            ],
            [
                InlineKeyboardButton(language_settings_text, callback_data="lang:select"),
            ]
        ]
    else:
        # Fallback to English if localization is not available
        welcome_message = (
            f"👋 Welcome to Claude Code Telegram Bot, {update.effective_user.first_name}!\n\n"
            f"🤖 I help you access Claude Code remotely through Telegram.\n\n"
            f"**Available Commands:**\n"
            f"• `/help` - Show detailed help\n"
            f"• `/new` - Start a new Claude session\n"
            f"• `/ls` - List files in current directory\n"
            f"• `/cd <dir>` - Change directory\n"
            f"• `/projects` - Show available projects\n"
            f"• `/status` - Show session status\n"
            f"• `/actions` - Show quick actions\n"
            f"• `/git` - Git repository commands\n\n"
            f"**Quick Start:**\n"
            f"1. Use `/projects` to see available projects\n"
            f"2. Use `/cd <project>` to navigate to a project\n"
            f"3. Send any message to start coding with Claude!\n\n"
            f"🔒 Your access is secured and all actions are logged.\n"
            f"📊 Use `/status` to check your usage limits."
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📁 Show Projects", callback_data="action:show_projects"),
                InlineKeyboardButton("❓ Get Help", callback_data="action:help"),
            ],
            [
                InlineKeyboardButton("🆕 New Session", callback_data="action:new_session"),
                InlineKeyboardButton("📊 Check Status", callback_data="action:status"),
            ],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        welcome_message, parse_mode=None, reply_markup=reply_markup
    )

    # Log command
    audit_logger = context.bot_data.get("audit_logger")
    if audit_logger:
        audit_logger_typed = cast(AuditLogger, audit_logger)
        await audit_logger_typed.log_command(
            user_id=user_id, command="start", args=[], success=True
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with localization."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
    
    # Get localized help text - try to get combined help or build from components
    localization = context.bot_data.get("localization")
    user_language_storage = context.bot_data.get("user_language_storage")
    
    if localization and user_language_storage:
        # Try to get full help text from translations
        user_lang = await user_language_storage.get_user_language(user_id) 
        if not user_lang:
            user_lang = "uk"  # Default to Ukrainian
        help_data = localization.translations.get(user_lang, {}).get("commands", {}).get("help", {})
        
        if help_data:
            # Build help text from individual components
            parts = []
            if "title" in help_data:
                parts.append(help_data["title"])
                parts.append("")
            
            if "navigation_title" in help_data:
                parts.append(help_data["navigation_title"])
                parts.extend([
                    f"• `/ls` - {help_data.get('ls_desc', 'List files and directories')}",
                    f"• `/cd <directory>` - {help_data.get('cd_desc', 'Change to directory')}",
                    f"• `/pwd` - {help_data.get('pwd_desc', 'Show current directory')}",
                    f"• `/projects` - {help_data.get('projects_desc', 'Show available projects')}",
                    ""
                ])
            
            if "session_title" in help_data:
                parts.append(help_data["session_title"])
                parts.extend([
                    f"• `/new` - {help_data.get('new_desc', 'Start new Claude session')}",
                    f"• `/continue [message]` - {help_data.get('continue_desc', 'Continue last session')}",
                    f"• `/end` - {help_data.get('end_desc', 'End current session')}",
                    f"• `/status` - {help_data.get('status_desc', 'Show session and usage status')}",
                    f"• `/export` - {help_data.get('export_desc', 'Export session history')}",
                    f"• `/actions` - {help_data.get('actions_desc', 'Show context-aware quick actions')}",
                    f"• `/git` - {help_data.get('git_desc', 'Git repository information')}",
                    ""
                ])
            
            if "usage_title" in help_data:
                parts.append(help_data["usage_title"])
                parts.extend([
                    f"• {help_data.get('usage_cd', 'cd myproject - Enter project directory')}",
                    f"• {help_data.get('usage_ls', 'ls - See what is in current directory')}",
                    f"• {help_data.get('usage_code', 'Create a simple Python script - Ask Claude to code')}",
                    f"• {help_data.get('usage_file', 'Send a file to have Claude review it')}",
                    ""
                ])
            
            if "tips_title" in help_data:
                parts.append(help_data["tips_title"])
                parts.extend([
                    f"• {help_data.get('tips_specific', 'Use specific, clear requests for best results')}",
                    f"• {help_data.get('tips_status', 'Check `/status` to monitor your usage')}",
                    f"• {help_data.get('tips_buttons', 'Use quick action buttons when available')}",
                ])
            
            help_text = "\n".join(parts)
        else:
            # Fallback to English
            help_text = await t(context, user_id, "commands.help.title")
    else:
        # Ultimate fallback
        help_text = (
            "🤖 **Claude Code Telegram Bot Help**\n\n"
            "• `/new` - Start new Claude session\n"
            "• `/help` - Show this help\n"
            "• `/status` - Show session status\n"
            "• `/ls` - List files\n"
            "• `/cd <dir>` - Change directory"
        )

    await message.reply_text(help_text, parse_mode=None)


async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)

    # For now, we'll use a simple session concept
    # This will be enhanced when we implement proper session management

    # Get current directory (default to approved directory)
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory
    relative_path = current_dir.relative_to(settings_typed.approved_directory)

    # Clear any existing session data
    if context.user_data:
        context.user_data["claude_session_id"] = None
        context.user_data["session_started"] = True

    # Get localized button texts
    localization = context.bot_data.get("localization")
    user_language_storage = context.bot_data.get("user_language_storage")
    
    if localization and user_language_storage:
        start_coding_btn = await t(context, user_id, "commands_extended.new_session.button_start_coding")
        change_project_btn = await t(context, user_id, "commands_extended.new_session.button_change_project")
        quick_actions_btn = await t(context, user_id, "commands_extended.new_session.button_quick_actions")
        help_btn = await t(context, user_id, "commands_extended.new_session.button_help")
    else:
        start_coding_btn = "📝 Start Coding"
        change_project_btn = "📁 Change Project"
        quick_actions_btn = "📋 Quick Actions"
        help_btn = "❓ Help"
    
    keyboard = [
        [
            InlineKeyboardButton(
                start_coding_btn, callback_data="action:start_coding"
            ),
            InlineKeyboardButton(
                change_project_btn, callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton(
                quick_actions_btn, callback_data="action:quick_actions"
            ),
            InlineKeyboardButton(help_btn, callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Get localized text for new session message
    if localization and user_language_storage:
        title = await t(context, user_id, "commands_extended.new_session.title")
        working_dir_msg = await t(context, user_id, "commands_extended.new_session.working_directory", relative_path=str(relative_path))
        ready_msg = await t(context, user_id, "commands_extended.new_session.ready_message")
        
        new_session_message = f"{title}\n\n{working_dir_msg}\n\n{ready_msg}"
    else:
        new_session_message = (
            f"🆕 **New Claude Code Session**\n\n"
            f"📂 Working directory: `{relative_path}/`\n\n"
            f"Ready to help you code! Send me a message to get started, or use the buttons below:"
        )
    
    await message.reply_text(
        new_session_message,
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def continue_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /continue command with optional prompt."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)
    
    claude_integration = context.bot_data.get("claude_integration")
    audit_logger = context.bot_data.get("audit_logger")

    # Parse optional prompt from command arguments
    prompt = " ".join(context.args) if context.args else None

    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory

    status_msg = None
    try:
        if not claude_integration:
            # Get localized error message
            localization = context.bot_data.get("localization")
            user_language_storage = context.bot_data.get("user_language_storage")
            
            if localization and user_language_storage:
                error_msg = await t(context, user_id, "errors.claude_not_available")
            else:
                error_msg = "❌ **Claude Integration Not Available**\n\nClaude integration is not properly configured."
            
            await message.reply_text(error_msg)
            return

        # Check if there's an existing session in user context
        claude_session_id = context.user_data.get("claude_session_id") if context.user_data else None

        if claude_session_id:
            # We have a session in context, continue it directly
            # Get localized continuation messages
            localization = context.bot_data.get("localization")
            user_language_storage = context.bot_data.get("user_language_storage")
            
            if localization and user_language_storage:
                continuing_title = await t(context, user_id, "commands_extended.continue_session.continuing")
                session_id_msg = await t(context, user_id, "commands_extended.continue_session.session_id", session_id=claude_session_id[:8])
                directory_msg = await t(context, user_id, "commands_extended.continue_session.directory", relative_path=str(current_dir.relative_to(settings_typed.approved_directory)))
                
                if prompt:
                    process_msg = await t(context, user_id, "commands_extended.continue_session.processing_message")
                else:
                    process_msg = await t(context, user_id, "commands_extended.continue_session.continuing_message")
                
                status_text = f"{continuing_title}\n\n{session_id_msg}\n{directory_msg}\n\n{process_msg}"
            else:
                status_text = (
                    f"🔄 **Continuing Session**\n\n"
                    f"Session ID: `{claude_session_id[:8]}...`\n"
                    f"Directory: `{current_dir.relative_to(settings_typed.approved_directory)}/`\n\n"
                    f"{'Processing your message...' if prompt else 'Continuing where you left off...'}"
                )
            
            status_msg = await message.reply_text(
                status_text,
                parse_mode=None,
            )

            # Continue with the existing session
            if claude_integration:
                claude_integration_typed = cast(ClaudeIntegration, claude_integration)
                claude_response = await claude_integration_typed.run_command(
                    prompt=prompt or "",
                    working_directory=current_dir,
                    user_id=user_id,
                    session_id=claude_session_id,
                )
            else:
                claude_response = None
        else:
            # No session in context, try to find the most recent session
            # Get localized session search messages
            localization = context.bot_data.get("localization")
            user_language_storage = context.bot_data.get("user_language_storage")
            if localization and user_language_storage:
                looking_title = await t(context, user_id, "commands_extended.continue_session.looking_for_session")
                searching_msg = await t(context, user_id, "commands_extended.continue_session.searching_message")
                search_text = f"{looking_title}\n\n{searching_msg}"
            else:
                search_text = (
                    "🔍 **Looking for Recent Session**\n\n"
                    "Searching for your most recent session in this directory..."
                )
            
            status_msg = await message.reply_text(
                search_text,
                parse_mode=None,
            )

            if claude_integration:
                claude_integration_typed = cast(ClaudeIntegration, claude_integration)
                claude_response = await claude_integration_typed.continue_session(
                    user_id=user_id,
                    working_directory=current_dir,
                    prompt=prompt,
                )
            else:
                claude_response = None

        if claude_response:
            # Update session ID in context
            if context.user_data:
                context.user_data["claude_session_id"] = claude_response.session_id

            # Delete status message and send response
            await status_msg.delete()

            # Format and send Claude's response
            from ..utils.formatting import ResponseFormatter

            formatter = ResponseFormatter(settings_typed)
            formatted_messages = formatter.format_claude_response(str(claude_response))

            for msg in formatted_messages:
                await message.reply_text(
                    str(msg),
                    parse_mode=None,
                )

            # Log successful continue
            if audit_logger:
                audit_logger_typed = cast(AuditLogger, audit_logger)
                await audit_logger_typed.log_command(
                    user_id=user_id,
                    command="continue",
                    args=context.args or [],
                    success=True,
                )

        else:
            # No session found to continue
            await status_msg.edit_text(
                "❌ **No Session Found**\n\n"
                f"No recent Claude session found in this directory.\n"
                f"Directory: `{current_dir.relative_to(settings_typed.approved_directory)}/`\n\n"
                f"**What you can do:**\n"
                f"• Use `/new` to start a fresh session\n"
                f"• Use `/status` to check your sessions\n"
                f"• Navigate to a different directory with `/cd`",
                parse_mode=None,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🆕 New Session", callback_data="action:new_session"
                            ),
                            InlineKeyboardButton(
                                "📊 Status", callback_data="action:status"
                            ),
                        ]
                    ]
                ),
            )

    except Exception as e:
        error_msg = str(e)
        logger.error("Error in continue command", error=error_msg, user_id=user_id)

        # Delete status message if it exists
        try:
            if 'status_msg' in locals() and status_msg:
                await status_msg.delete()
        except Exception as e:
            logger.warning("Failed to delete status message", error=str(e))

        # Send error response
        await message.reply_text(
            f"❌ **Error Continuing Session**\n\n"
            f"An error occurred while trying to continue your session:\n\n"
            f"`{error_msg}`\n\n"
            f"**Suggestions:**\n"
            f"• Try starting a new session with `/new`\n"
            f"• Check your session status with `/status`\n"
            f"• Contact support if the issue persists",
            parse_mode=None,
        )

        # Log failed continue
        if audit_logger:
            audit_logger_typed = cast(AuditLogger, audit_logger)
            await audit_logger_typed.log_command(
                user_id=user_id,
                command="continue",
                args=context.args or [],
                success=False,
            )


async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ls command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)
    
    audit_logger = context.bot_data.get("audit_logger")

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory

    try:
        # List directory contents
        items = []
        directories = []
        files = []

        for item in sorted(current_dir.iterdir()):
            # Skip hidden files (starting with .)
            if item.name.startswith("."):
                continue

            if item.is_dir():
                directories.append(f"📁 {item.name}/")
            else:
                # Get file size
                try:
                    size = item.stat().st_size
                    size_str = _format_file_size(size)
                    files.append(f"📄 {item.name} ({size_str})")
                except OSError:
                    files.append(f"📄 {item.name}")

        # Combine directories first, then files
        items = directories + files

        # Format response
        relative_path = current_dir.relative_to(settings_typed.approved_directory)
        if not items:
            ls_message = f"📂 `{relative_path}/`\n\n_(empty directory)_"
        else:
            ls_message = f"📂 `{relative_path}/`\n\n"

            # Limit items shown to prevent message being too long
            max_items = 50
            if len(items) > max_items:
                shown_items = items[:max_items]
                ls_message += "\n".join(shown_items)
                ls_message += f"\n\n_... and {len(items) - max_items} more items_"
            else:
                ls_message += "\n".join(items)

        # Add navigation buttons if not at root
        keyboard = []
        if current_dir != settings_typed.approved_directory:
            keyboard.append(
                [
                    InlineKeyboardButton("⬆️ Go Up", callback_data="cd:.."),
                    InlineKeyboardButton("🏠 Go to Root", callback_data="cd:/"),
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_ls"),
                InlineKeyboardButton(
                    "📁 Projects", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await message.reply_text(
            ls_message, parse_mode=None, reply_markup=reply_markup
        )

        # Log successful command
        if audit_logger:
            audit_logger_typed = cast(AuditLogger, audit_logger)
            await audit_logger_typed.log_command(user_id, "ls", [], True)

    except Exception as e:
        error_msg = f"❌ Error listing directory: {str(e)}"
        await message.reply_text(error_msg)

        # Log failed command
        if audit_logger:
            audit_logger_typed = cast(AuditLogger, audit_logger)
            await audit_logger_typed.log_command(user_id, "ls", [], False)

        logger.error("Error in list_files command", error=str(e), user_id=user_id)


async def change_directory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cd command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)
    
    security_validator = context.bot_data.get("security_validator")
    audit_logger = context.bot_data.get("audit_logger")

    # Parse arguments
    if not context.args:
        await message.reply_text(
            "**Usage:** `/cd <directory>`\n\n"
            "**Examples:**\n"
            "• `/cd myproject` - Enter subdirectory\n"
            "• `/cd ..` - Go up one level\n"
            "• `/cd /` - Go to root of approved directory\n\n"
            "**Tips:**\n"
            "• Use `/ls` to see available directories\n"
            "• Use `/projects` to see all projects",
            parse_mode=None,
        )
        return

    target_path = " ".join(context.args)
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory

    try:
        # Validate path using security validator
        if security_validator:
            security_validator_typed = cast(SecurityValidator, security_validator)
            valid, resolved_path, error = security_validator_typed.validate_path(
                target_path, current_dir
            )

            if not valid:
                await message.reply_text(f"❌ **Access Denied**\n\n{error}")

                # Log security violation
                if audit_logger:
                    audit_logger_typed = cast(AuditLogger, audit_logger)
                    await audit_logger_typed.log_security_violation(
                        user_id=user_id,
                        violation_type="path_traversal_attempt",
                        details=f"Attempted path: {target_path}",
                        severity="medium",
                    )
                return
        else:
            # Fallback validation without security validator
            if target_path == "/":
                resolved_path = settings_typed.approved_directory
            elif target_path == "..":
                resolved_path = current_dir.parent
                if not str(resolved_path).startswith(str(settings_typed.approved_directory)):
                    resolved_path = settings_typed.approved_directory
            else:
                resolved_path = current_dir / target_path
                resolved_path = resolved_path.resolve()

        # Check if directory exists and is actually a directory
        if not resolved_path or not resolved_path.exists():
            await message.reply_text(
                f"❌ **Directory Not Found**\n\n`{target_path}` does not exist."
            )
            return

        if not resolved_path.is_dir():
            await message.reply_text(
                f"❌ **Not a Directory**\n\n`{target_path}` is not a directory."
            )
            return

        # Update current directory in user data
        if context.user_data:
            context.user_data["current_directory"] = resolved_path
            # Clear Claude session on directory change
            context.user_data["claude_session_id"] = None

        # Send confirmation
        relative_path = resolved_path.relative_to(settings_typed.approved_directory)
        await message.reply_text(
            f"✅ **Directory Changed**\n\n"
            f"📂 Current directory: `{relative_path}/`\n\n"
            f"🔄 Claude session cleared. Send a message to start coding in this directory.",
            parse_mode=None,
        )

        # Log successful command
        if audit_logger:
            audit_logger_typed = cast(AuditLogger, audit_logger)
            await audit_logger_typed.log_command(user_id, "cd", [target_path], True)

    except Exception as e:
        error_msg = f"❌ **Error changing directory**\n\n{str(e)}"
        await message.reply_text(error_msg, parse_mode=None)

        # Log failed command
        if audit_logger:
            audit_logger_typed = cast(AuditLogger, audit_logger)
            await audit_logger_typed.log_command(user_id, "cd", [target_path], False)

        logger.error("Error in change_directory command", error=str(e), user_id=user_id)


async def print_working_directory(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /pwd command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)
    
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory

    relative_path = current_dir.relative_to(settings_typed.approved_directory)
    absolute_path = str(current_dir)

    # Add quick navigation buttons
    keyboard = [
        [
            InlineKeyboardButton("📁 List Files", callback_data="action:ls"),
            InlineKeyboardButton("📋 Projects", callback_data="action:show_projects"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"📍 **Current Directory**\n\n"
        f"Relative: `{relative_path}/`\n"
        f"Absolute: `{absolute_path}`",
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /projects command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)

    try:
        # Get directories in approved directory (these are "projects")
        projects = []
        for item in sorted(settings_typed.approved_directory.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                projects.append(item.name)

        if not projects:
            await message.reply_text(
                "📁 **No Projects Found**\n\n"
                "No subdirectories found in your approved directory.\n"
                "Create some directories to organize your projects!"
            )
            return

        # Create inline keyboard with project buttons
        keyboard = []
        for i in range(0, len(projects), 2):
            row = []
            for j in range(2):
                if i + j < len(projects):
                    project = projects[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"📁 {project}", callback_data=f"cd:{project}"
                        )
                    )
            keyboard.append(row)

        # Add navigation buttons
        keyboard.append(
            [
                InlineKeyboardButton("🏠 Go to Root", callback_data="cd:/"),
                InlineKeyboardButton(
                    "🔄 Refresh", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        project_list = "\n".join([f"• `{project}/`" for project in projects])

        await message.reply_text(
            f"📁 **Available Projects**\n\n"
            f"{project_list}\n\n"
            f"Click a project below to navigate to it:",
            parse_mode=None,
            reply_markup=reply_markup,
        )

    except Exception as e:
        await message.reply_text(f"❌ Error loading projects: {str(e)}")
        logger.error("Error in show_projects command", error=str(e), user_id=user_id)


async def session_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)

    # Get session info
    claude_session_id = context.user_data.get("claude_session_id") if context.user_data else None
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory
    relative_path = current_dir.relative_to(settings_typed.approved_directory)

    # Get rate limiter info if available
    rate_limiter = context.bot_data.get("rate_limiter")
    usage_info = ""
    if rate_limiter:
        try:
            user_status = rate_limiter.get_user_status(user_id)
            cost_usage = user_status.get("cost_usage", {})
            current_cost = cost_usage.get("current", 0.0)
            cost_limit = cost_usage.get("limit", settings_typed.claude_max_cost_per_user)
            cost_percentage = (current_cost / cost_limit) * 100 if cost_limit > 0 else 0

            usage_info = f"💰 Usage: ${current_cost:.2f} / ${cost_limit:.2f} ({cost_percentage:.0f}%)\n"
        except Exception:
            usage_info = "💰 Usage: _Unable to retrieve_\n"

    # Format status message
    status_lines = [
        "📊 **Session Status**",
        "",
        f"📂 Directory: `{relative_path}/`",
        f"🤖 Claude Session: {'✅ Active' if claude_session_id else '❌ None'}",
        usage_info.rstrip(),
        f"🕐 Last Update: {message.date.strftime('%H:%M:%S UTC') if message.date else 'Unknown'}",
    ]

    if claude_session_id:
        status_lines.append(f"🆔 Session ID: `{claude_session_id[:8]}...`")

    # Add action buttons
    keyboard = []
    if claude_session_id:
        keyboard.append(
            [
                InlineKeyboardButton("🔄 Continue", callback_data="action:continue"),
                InlineKeyboardButton(
                    "🆕 New Session", callback_data="action:new_session"
                ),
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🆕 Start Session", callback_data="action:new_session"
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton("📤 Export", callback_data="action:export"),
            InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_status"),
        ]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        "\n".join(status_lines), parse_mode=None, reply_markup=reply_markup
    )


async def export_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    features = context.bot_data.get("features")

    # Check if session export is available
    session_exporter = features.get_session_export() if features else None

    if not session_exporter:
        await message.reply_text(
            "📤 **Export Session**\n\n"
            "Session export functionality is not available.\n\n"
            "**Planned features:**\n"
            "• Export conversation history\n"
            "• Save session state\n"
            "• Share conversations\n"
            "• Create session backups"
        )
        return

    # Get current session
    claude_session_id = context.user_data.get("claude_session_id") if context.user_data else None

    if not claude_session_id:
        await message.reply_text(
            "❌ **No Active Session**\n\n"
            "There's no active Claude session to export.\n\n"
            "**What you can do:**\n"
            "• Start a new session with `/new`\n"
            "• Continue an existing session with `/continue`\n"
            "• Check your status with `/status`"
        )
        return

    # Create export format selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("📝 Markdown", callback_data="export:markdown"),
            InlineKeyboardButton("🌐 HTML", callback_data="export:html"),
        ],
        [
            InlineKeyboardButton("📋 JSON", callback_data="export:json"),
            InlineKeyboardButton("❌ Cancel", callback_data="export:cancel"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        "📤 **Export Session**\n\n"
        f"Ready to export session: `{claude_session_id[:8]}...`\n\n"
        "**Choose export format:**",
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def end_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /end command to terminate the current session."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)

    # Check if there's an active session
    claude_session_id = context.user_data.get("claude_session_id") if context.user_data else None

    if not claude_session_id:
        await message.reply_text(
            "ℹ️ **No Active Session**\n\n"
            "There's no active Claude session to end.\n\n"
            "**What you can do:**\n"
            "• Use `/new` to start a new session\n"
            "• Use `/status` to check your session status\n"
            "• Send any message to start a conversation"
        )
        return

    # Get current directory for display
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory
    relative_path = current_dir.relative_to(settings_typed.approved_directory)

    # Clear session data
    if context.user_data:
        context.user_data["claude_session_id"] = None
        context.user_data["session_started"] = False
        context.user_data["last_message"] = None

    # Create quick action buttons
    keyboard = [
        [
            InlineKeyboardButton("🆕 New Session", callback_data="action:new_session"),
            InlineKeyboardButton(
                "📁 Change Project", callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="action:status"),
            InlineKeyboardButton("❓ Help", callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        "✅ **Session Ended**\n\n"
        f"Your Claude session has been terminated.\n\n"
        f"**Current Status:**\n"
        f"• Directory: `{relative_path}/`\n"
        f"• Session: None\n"
        f"• Ready for new commands\n\n"
        f"**Next Steps:**\n"
        f"• Start a new session with `/new`\n"
        f"• Check status with `/status`\n"
        f"• Send any message to begin a new conversation",
        parse_mode=None,
        reply_markup=reply_markup,
    )

    logger.info("Session ended by user", user_id=user_id, session_id=claude_session_id)


async def quick_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /actions command to show quick actions."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)
    
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("quick_actions"):
        await message.reply_text(
            "❌ **Quick Actions Disabled**\n\n"
            "Quick actions feature is not enabled.\n"
            "Contact your administrator to enable this feature."
        )
        return

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory

    try:
        quick_action_manager = features.get_quick_actions()
        if not quick_action_manager:
            await message.reply_text(
                "❌ **Quick Actions Unavailable**\n\n"
                "Quick actions service is not available."
            )
            return

        # Get context-aware actions
        actions = await quick_action_manager.get_suggestions(
            session_data={"working_directory": str(current_dir), "user_id": user_id}
        )

        if not actions:
            await message.reply_text(
                "🤖 **No Actions Available**\n\n"
                "No quick actions are available for the current context.\n\n"
                "**Try:**\n"
                "• Navigating to a project directory with `/cd`\n"
                "• Creating some code files\n"
                "• Starting a Claude session with `/new`"
            )
            return

        # Create inline keyboard with localization
        # user_id already defined above
        localization = context.bot_data.get("localization")
        user_language_storage = context.bot_data.get("user_language_storage")
        user_lang = None
        
        if user_language_storage:
            try:
                user_lang = await user_language_storage.get_user_language(user_id)
            except Exception as e:
                logger.warning("Failed to get user language", user_id=user_id, error=str(e))
                user_lang = "en"  # fallback to English
        
        keyboard = quick_action_manager.create_inline_keyboard(
            actions, columns=2, localization=localization, user_lang=user_lang
        )

        # Get localized title for quick actions
        title_text = await t(context, user_id, "quick_actions.title")
        
        relative_path = current_dir.relative_to(settings_typed.approved_directory)
        message_text = f"{title_text}\n\n📂 Context: `{relative_path}/`"
        
        await message.reply_text(
            message_text,
            parse_mode=None,
            reply_markup=keyboard,
        )

    except Exception as e:
        error_text = await t(context, user_id, "errors.quick_actions_unavailable")
        await message.reply_text(error_text, parse_mode=None)
        logger.error("Error in quick_actions command", error=str(e), user_id=user_id)


async def git_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /git command to show git repository information."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)
    
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("git"):
        await message.reply_text(
            "❌ **Git Integration Disabled**\n\n"
            "Git integration feature is not enabled.\n"
            "Contact your administrator to enable this feature."
        )
        return

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory

    try:
        git_integration = features.get_git_integration()
        if not git_integration:
            await message.reply_text(
                "❌ **Git Integration Unavailable**\n\n"
                "Git integration service is not available."
            )
            return

        # Check if current directory is a git repository
        if not (current_dir / ".git").exists():
            await message.reply_text(
                f"📂 **Not a Git Repository**\n\n"
                f"Current directory `{current_dir.relative_to(settings_typed.approved_directory)}/` is not a git repository.\n\n"
                f"**Options:**\n"
                f"• Navigate to a git repository with `/cd`\n"
                f"• Initialize a new repository (ask Claude to help)\n"
                f"• Clone an existing repository (ask Claude to help)"
            )
            return

        # Get git status
        git_status = await git_integration.get_status(current_dir)

        # Format status message
        relative_path = current_dir.relative_to(settings_typed.approved_directory)
        status_message = f"🔗 **Git Repository Status**\n\n"
        status_message += f"📂 Directory: `{relative_path}/`\n"
        status_message += f"🌿 Branch: `{git_status.branch}`\n"

        if git_status.ahead > 0:
            status_message += f"⬆️ Ahead: {git_status.ahead} commits\n"
        if git_status.behind > 0:
            status_message += f"⬇️ Behind: {git_status.behind} commits\n"

        # Show file changes
        if not git_status.is_clean:
            status_message += f"\n**Changes:**\n"
            if git_status.modified:
                status_message += f"📝 Modified: {len(git_status.modified)} files\n"
            if git_status.added:
                status_message += f"➕ Added: {len(git_status.added)} files\n"
            if git_status.deleted:
                status_message += f"➖ Deleted: {len(git_status.deleted)} files\n"
            if git_status.untracked:
                status_message += f"❓ Untracked: {len(git_status.untracked)} files\n"
        else:
            status_message += "\n✅ Working directory clean\n"

        # Create action buttons
        keyboard = [
            [
                InlineKeyboardButton("📊 Show Diff", callback_data="git:diff"),
                InlineKeyboardButton("📜 Show Log", callback_data="git:log"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="git:status"),
                InlineKeyboardButton("📁 Files", callback_data="action:ls"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(
            status_message, parse_mode=None, reply_markup=reply_markup
        )

    except Exception as e:
        await message.reply_text(f"❌ **Git Error**\n\n{str(e)}")
        logger.error("Error in git_command", error=str(e), user_id=user_id)


def _format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    size_float = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024:
            return f"{size_float:.1f}{unit}" if unit != "B" else f"{int(size_float)}B"
        size_float /= 1024
    return f"{size_float:.1f}TB"


async def schedules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List and manage scheduled tasks."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    try:
        from ..features.scheduled_prompts import ScheduledPromptsManager
        
        # Get application from context
        application = context.application
        settings = context.bot_data.get("settings")
        
        if not application or not settings:
            await message.reply_text(
                "❌ **Помилка системи**\n"
                "Неможливо отримати доступ до компонентів системи"
            )
            return
            
        prompts_manager = ScheduledPromptsManager(application, settings)
        config = await prompts_manager.load_prompts()
        prompts = config.get("prompts", [])
        system_settings = config.get("settings", {})
        
        if not prompts:
            keyboard = [[
                InlineKeyboardButton("➕ Додати завдання", callback_data="schedule:add"),
                InlineKeyboardButton("⚙️ Налаштування", callback_data="schedule:settings")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(
                "📋 **Планових завдань немає**\n\n"
                "Ця система дозволяє автоматично виконувати завдання\n"
                "під час DND періоду (23:00-08:00).\n\n"
                "🔧 Додайте перше завдання для початку роботи",
                reply_markup=reply_markup
            )
            return
        
        # Build message with prompts list
        enabled_count = sum(1 for p in prompts if p.get("enabled", False))
        system_status = "✅ Увімкнена" if system_settings.get("enabled", False) else "❌ Вимкнена"
        
        message_text = (
            f"📋 **Планові завдання** ({len(prompts)})\n"
            f"🔧 Система: {system_status} | Активних: {enabled_count}\n\n"
        )
        
        for i, prompt in enumerate(prompts[:10], 1):  # Show first 10
            status_icon = "✅" if prompt.get("enabled", False) else "❌"
            schedule = prompt.get("schedule", {})
            schedule_info = f"{schedule.get('type', 'daily')} о {schedule.get('time', '02:00')}"
            
            message_text += (
                f"{i}. {status_icon} **{prompt.get('title', 'Без назви')}**\n"
                f"   📅 {schedule_info}\n"
                f"   📝 {prompt.get('description', 'Без опису')[:50]}{'...' if len(prompt.get('description', '')) > 50 else ''}\n\n"
            )
        
        if len(prompts) > 10:
            message_text += f"... та ще {len(prompts) - 10} завдань\n\n"
            
        # Add control buttons
        keyboard = [
            [
                InlineKeyboardButton("➕ Додати", callback_data="schedule:add"),
                InlineKeyboardButton("📝 Редагувати", callback_data="schedule:edit")
            ],
            [
                InlineKeyboardButton("⚙️ Налаштування", callback_data="schedule:settings"),
                InlineKeyboardButton("📊 Статистика", callback_data="schedule:stats")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(message_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error("Error in schedules command", error=str(e))
        await message.reply_text(
            "❌ **Помилка**\n"
            f"Не вдалося отримати список завдань: {str(e)}"
        )


async def add_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add new scheduled task."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    try:
        # Create inline keyboard for adding new task
        keyboard = [
            [InlineKeyboardButton("📝 Створити завдання", callback_data="schedule:create_new")],
            [InlineKeyboardButton("📋 Зі шаблону", callback_data="schedule:from_template")],
            [InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            "➕ **Додати планове завдання**\n\n"
            "Планові завдання виконуються автоматично\n"
            "під час DND періоду (23:00-08:00)\n"
            "коли Claude CLI доступна та користувачі не працюють.\n\n"
            "**Типи завдань:**\n"
            "• 🔍 Аналіз коду та архітектури\n"
            "• 📊 Генерація звітів\n"
            "• 🧹 Рефакторинг та оптимізація\n"
            "• 📝 Оновлення документації\n"
            "• 🔒 Перевірка безпеки\n\n"
            "Оберіть спосіб створення:"
        )
        
        await message.reply_text(message_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error("Error in add_schedule command", error=str(e))
        await message.reply_text(
            "❌ **Помилка**\n"
            f"Не вдалося відкрити меню додавання: {str(e)}"
        )


# ========== MISSING CRITICAL COMMAND HANDLERS ==========

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot and session status."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
    
    try:
        status_text = await t(context, user_id, "status.title")
        current_dir = await t(context, user_id, "status.directory", directory=str(Path.cwd()))
        claude_active = "🤖 Сесія Claude: ✅ Активна" if context.user_data.get('claude_session_active') else await t(context, user_id, "status.claude_session_inactive")
        
        full_status = f"{status_text}\n\n{current_dir}\n{claude_active}"
        await message.reply_text(full_status)
        logger.info("Status command executed", user_id=user_id)
    except Exception as e:
        await safe_user_error(update, context, "errors.status_failed", e)
        logger.error("Status handler error", error=str(e), user_id=user_id)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
    
    try:
        help_text = await t(context, user_id, "help.title")
        commands_list = await t(context, user_id, "help.commands")
        await message.reply_text(f"{help_text}\n\n{commands_list}")
        logger.info("Help command executed", user_id=user_id)
    except Exception as e:
        await safe_user_error(update, context, "errors.help_failed", e)

async def new_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start new Claude session."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
    
    try:
        await message.reply_text(await t(context, user_id, "session.new_started"))
        # Reset session in context.user_data
        if context.user_data:
            context.user_data['claude_session_id'] = None
            context.user_data['claude_session_active'] = False
        await message.reply_text(await t(context, user_id, "session.cleared"))
        logger.info("New session started", user_id=user_id)
    except Exception as e:
        await safe_user_error(update, context, "errors.session_new_failed", e)

async def actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available quick actions."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
    
    try:
        actions_text = await t(context, user_id, "actions.title")
        await message.reply_text(actions_text)
    except Exception as e:
        await safe_user_error(update, context, "errors.actions_failed", e)

async def pwd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current directory."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
    
    try:
        pwd_text = await t(context, user_id, "pwd.title", directory=str(Path.cwd()))
        await message.reply_text(pwd_text)
    except Exception as e:
        await safe_user_error(update, context, "errors.pwd_failed", e)

async def projects_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show project list."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
    
    try:
        projects_text = await t(context, user_id, "projects.title", count=0)
        await message.reply_text(projects_text)
    except Exception as e:
        await safe_user_error(update, context, "errors.projects_failed", e)


# FIXED: Git command (line ~1241 - mixed language fix)
async def git_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Git operations - fixed error handling."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return
        
    try:
        # Existing git logic...
        git_text = await t(context, user_id, "commands.git.title")
        await message.reply_text(f"🔗 **{git_text}**")
    except Exception as e:
        error_msg = await t(context, user_id, "errors.git_operation_failed", error=str(e))
        await message.reply_text(error_msg)
        logger.error("Git operation failed", error=str(e), user_id=user_id)


def extract_auth_url(output: str) -> str:
    """Extract authentication URL from claude login output."""
    # Look for URLs in the output
    url_pattern = r'https://[^\s]+'
    urls = re.findall(url_pattern, output)
    for url in urls:
        if 'anthropic.com' in url or 'claude.ai' in url:
            return url
    return ""


def extract_reset_time(error_text: str) -> str:
    """Extract reset time from rate limit error."""
    # Look for reset time patterns in error messages
    patterns = [
        r'reset at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',
        r'try again at (\d{2}:\d{2})',
        r'available at (\d+:\d+)',
        r'reset in (\d+) minutes',
        r'after (\d+:\d{2})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "невідомо"


def analyze_claude_error(error_text: str, stderr: str = "") -> tuple[str, dict]:
    """Analyze Claude CLI error and return appropriate message key and format args."""
    full_error = f"{error_text} {stderr}".lower()
    
    # Rate limiting patterns
    rate_limit_patterns = [
        "rate limit", "too many requests", "429", "quota exceeded",
        "requests per", "try again later", "temporary limit"
    ]
    
    # Quota/billing patterns  
    quota_patterns = [
        "usage limit", "billing", "plan limit", "daily limit",
        "monthly usage", "account limit", "subscription"
    ]
    
    # Network patterns
    network_patterns = [
        "network", "connection", "timeout", "dns", "unreachable",
        "connection refused", "connection reset", "no internet"
    ]
    
    # Server error patterns
    server_patterns = [
        "500", "502", "503", "504", "internal server error",
        "bad gateway", "service unavailable", "gateway timeout"
    ]
    
    # Invalid code patterns
    invalid_patterns = [
        "invalid code", "invalid token", "expired token", "wrong code",
        "authentication failed", "invalid authorization"
    ]
    
    if any(pattern in full_error for pattern in rate_limit_patterns):
        reset_time = extract_reset_time(full_error)
        return "commands.claude.error_rate_limit", {"reset_time": reset_time}
    
    elif any(pattern in full_error for pattern in quota_patterns):
        return "commands.claude.error_quota", {}
    
    elif any(pattern in full_error for pattern in network_patterns):
        return "commands.claude.error_network", {}
    
    elif any(pattern in full_error for pattern in server_patterns):
        return "commands.claude.error_server", {}
    
    elif any(pattern in full_error for pattern in invalid_patterns):
        return "commands.claude.error_invalid_code", {}
    
    else:
        return "commands.claude.error_generic", {}


async def claude_auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /claude command for interactive Claude CLI authentication using pexpect."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message:
        return

    try:
        # Check if already waiting for auth code
        if context.user_data.get('claude_auth_waiting'):
            already_waiting_msg = await t(context, user_id, "commands.claude.already_waiting")
            await message.reply_text(already_waiting_msg)
            return
        
        # First check current Claude CLI authentication status
        logger.info("Checking Claude CLI authentication status", user_id=user_id)
        try:
            import json
            credentials_path = Path.home() / ".claude" / ".credentials.json"
            logger.info("Checking credentials file", path=str(credentials_path), exists=credentials_path.exists())
            if credentials_path.exists():
                with open(credentials_path, 'r') as f:
                    creds = json.load(f)
                    oauth_data = creds.get("claudeAiOauth", {})
                    expires_at = oauth_data.get("expiresAt", 0)
                    current_time = time.time() * 1000
                    
                    logger.info("Token status check", current_time=current_time, expires_at=expires_at, 
                               expired=current_time > expires_at)
                    
                    if current_time < expires_at:
                        # Token is not expired, test connectivity
                        logger.info("Token valid, testing Claude CLI connectivity", user_id=user_id)
                        test_result = await asyncio.create_subprocess_exec(
                            "timeout", "10", "claude", "auth", "status",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await test_result.communicate()
                        
                        logger.info("Claude CLI connectivity test result", return_code=test_result.returncode,
                                   stdout=stdout.decode()[:100], stderr=stderr.decode()[:100])
                        
                        if test_result.returncode == 0:
                            # Claude CLI works fine
                            logger.info("Claude CLI verified working", user_id=user_id)
                            verified_msg = await t(context, user_id, "commands.claude.verified")
                            await message.reply_text(verified_msg)
                            return
                        else:
                            # Token exists but CLI doesn't work - connectivity issue
                            hours_remaining = (expires_at - current_time) / (1000 * 3600)
                            logger.info("Claude CLI connectivity issue detected", user_id=user_id, 
                                       hours_remaining=hours_remaining, return_code=test_result.returncode)
                            connectivity_msg = await t(context, user_id, "commands.claude.connectivity_issue", 
                                                     hours=f"{hours_remaining:.1f}")
                            await message.reply_text(connectivity_msg)
                            return
                    else:
                        # Token is expired
                        logger.info("Claude CLI token expired", user_id=user_id, expires_at=expires_at)
                        expired_msg = await t(context, user_id, "commands.claude.token_expired")
                        await message.reply_text(expired_msg)
                        # Continue with authentication process
            else:
                logger.info("No Claude CLI credentials file found", user_id=user_id)
        except Exception as e:
            logger.warning("Could not check Claude CLI status", error=str(e), user_id=user_id)
            # Continue with authentication process anyway
        
        # Start claude login process with pexpect
        logger.info("Starting Claude authentication process with pexpect", user_id=user_id)
        
        starting_msg = await t(context, user_id, "commands.claude.starting")
        await message.reply_text(starting_msg)
        
        # Use pexpect to capture authentication URL
        success, result, child = await claude_auth_with_pexpect(timeout=30)
        
        if not success:
            # Authentication failed
            error_key, format_args = analyze_claude_error(result, "")
            error_msg = await t(context, user_id, error_key, **format_args)
            await message.reply_text(error_msg)
            logger.error("Failed to start Claude authentication with pexpect", 
                        user_id=user_id, error=result)
            return
        
        # Success - we have the authentication URL
        auth_url = result
        
        # Send instructions to user
        title = await t(context, user_id, "commands.claude.title")
        step1 = await t(context, user_id, "commands.claude.step1")
        step2 = await t(context, user_id, "commands.claude.step2") 
        step3 = await t(context, user_id, "commands.claude.step3")
        step4 = await t(context, user_id, "commands.claude.step4")
        waiting = await t(context, user_id, "commands.claude.waiting")
        
        instructions = (
            f"{title}\n\n"
            f"{step1}\n"
            f"🔗 {auth_url}\n\n"
            f"{step2}\n"
            f"{step3}\n"
            f"{step4}\n\n"
            f"{waiting}"
        )
        
        await message.reply_text(instructions)
        
        # Store authentication state with pexpect child process
        context.user_data['claude_auth_process'] = child
        context.user_data['claude_auth_waiting'] = True
        context.user_data['claude_auth_start_time'] = datetime.now()
        
        logger.info("Claude authentication instructions sent with pexpect", 
                   user_id=user_id, auth_url=auth_url)
        
    except Exception as e:
        error_msg = await t(context, user_id, "commands.claude.error_process")
        await message.reply_text(f"{error_msg}\n\n_{str(e)}_")
        logger.error("Failed to start Claude authentication", error=str(e), user_id=user_id)


async def handle_claude_auth_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle authentication code input for Claude CLI using pexpect. Returns True if handled."""
    user_id = get_user_id(update)
    message = get_effective_message(update)
    
    if not user_id or not message or not message.text:
        return False
    
    # Check if user is waiting for auth code
    if not context.user_data.get('claude_auth_waiting'):
        return False
    
    child = context.user_data.get('claude_auth_process')
    start_time = context.user_data.get('claude_auth_start_time')
    
    if not child or not start_time:
        return False
    
    # Check timeout (10 minutes)
    if datetime.now() - start_time > timedelta(minutes=10):
        timeout_msg = await t(context, user_id, "commands.claude.timeout") 
        await message.reply_text(timeout_msg)
        
        # Clean up
        try:
            if child.isalive():
                child.terminate()
        except:
            pass
        
        context.user_data.pop('claude_auth_process', None)
        context.user_data.pop('claude_auth_waiting', None)
        context.user_data.pop('claude_auth_start_time', None)
        return True
    
    # Handle cancel command
    if message.text.lower() in ['/cancel', 'cancel', 'скасувати', 'стоп']:
        cancelled_msg = await t(context, user_id, "commands.claude.cancelled")
        await message.reply_text(cancelled_msg)
        
        try:
            if child.isalive():
                child.terminate()
        except:
            pass
        
        context.user_data.pop('claude_auth_process', None)
        context.user_data.pop('claude_auth_waiting', None) 
        context.user_data.pop('claude_auth_start_time', None)
        return True
    
    # Extract authentication code
    auth_code = message.text.strip()
    
    # Basic validation of auth code format
    if not auth_code or len(auth_code) < 6:
        invalid_msg = await t(context, user_id, "commands.claude.error_invalid_code")
        await message.reply_text(invalid_msg)
        return True
    
    try:
        logger.info("Processing Claude authentication code with pexpect", user_id=user_id)
        
        processing_msg = await t(context, user_id, "commands.claude.processing")
        await message.reply_text(processing_msg)
        
        # Check if pexpect child is still alive
        if not child.isalive():
            session_expired_msg = await t(context, user_id, "commands.claude.session_expired")
            await message.reply_text(session_expired_msg)
            
            # Clean up
            context.user_data.pop('claude_auth_process', None)
            context.user_data.pop('claude_auth_waiting', None)
            context.user_data.pop('claude_auth_start_time', None)
            return True
        
        # Send auth code through pexpect
        success, result = await send_auth_code(child, auth_code, timeout=30)
        
        # Clean up user data first
        context.user_data.pop('claude_auth_process', None)
        context.user_data.pop('claude_auth_waiting', None)
        context.user_data.pop('claude_auth_start_time', None)
        
        if success:
            # Success
            success_msg = await t(context, user_id, "commands.claude.success")
            verified_msg = await t(context, user_id, "commands.claude.verified")
            await message.reply_text(f"{success_msg}\n\n{verified_msg}")
            logger.info("Claude authentication successful with pexpect", user_id=user_id)
        else:
            # Error - analyze and provide detailed feedback
            error_key, format_args = analyze_claude_error(result, "")
            error_msg = await t(context, user_id, error_key, **format_args)
            await message.reply_text(error_msg)
            
            logger.warning("Claude authentication failed with pexpect", 
                         user_id=user_id, 
                         error=result[:500])
        
        return True
        
    except Exception as e:
        # Clean up user data
        context.user_data.pop('claude_auth_process', None)
        context.user_data.pop('claude_auth_waiting', None)
        context.user_data.pop('claude_auth_start_time', None)
        
        # Clean up pexpect process
        try:
            if child and child.isalive():
                child.terminate()
        except:
            pass
        
        error_msg = await t(context, user_id, "commands.claude.error_generic")
        await message.reply_text(f"{error_msg}\n\n_{str(e)}_")
        logger.error("Exception during Claude authentication with pexpect", error=str(e), user_id=user_id)
        return True


# Registration function for handlers
def register_handlers(application):
    """Register all command handlers."""
    from telegram.ext import CommandHandler
    
    # Register all command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("new", new_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("actions", actions_handler))
    application.add_handler(CommandHandler("pwd", pwd_handler))
    application.add_handler(CommandHandler("projects", projects_handler))
    application.add_handler(CommandHandler("ls", list_files))
    application.add_handler(CommandHandler("cd", change_directory))
    application.add_handler(CommandHandler("continue", continue_session))
    application.add_handler(CommandHandler("end", end_session))
    application.add_handler(CommandHandler("export", export_session))
    application.add_handler(CommandHandler("git", git_handler))
    application.add_handler(CommandHandler("claude", claude_auth_command))
    application.add_handler(CommandHandler("schedules", schedules_command))
    application.add_handler(CommandHandler("add_schedule", add_schedule_command))


async def img_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /img command for image processing."""
    # Get the image handler instance from bot data
    image_handler = context.bot_data.get('image_command_handler')
    if image_handler:
        await image_handler.handle_img_command(update, context)
    else:
        # Fallback error message
        user_id = get_user_id(update)
        message = get_effective_message(update)
        if user_id and message:
            error_text = await t(context, user_id, "errors.image_processing_disabled")
            await message.reply_text(error_text)
