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


def safe_terminate_process(process: Optional[pexpect.spawn]) -> None:
    """Безпечно завершує процес pexpect."""
    if not process:
        return
    try:
        if process.isalive():
            process.terminate(force=True)
    except Exception as e:
        logger.debug("Error terminating process", error=str(e))
        try:
            process.close()
        except:
            pass


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
        get_help_text = await t(context, user_id, "buttons.get_help")
        new_session_text = await t(context, user_id, "buttons.new_session")
        check_status_text = await t(context, user_id, "buttons.check_status")
        language_settings_text = await t(context, user_id, "buttons.language_settings")
        
        # Enhanced unified menu with all essential functions
        continue_session_text = await t(context, user_id, "buttons.continue_session")
        export_session_text = await t(context, user_id, "buttons.export")
        settings_text = await t(context, user_id, "buttons.settings")

        keyboard = [
            [
                InlineKeyboardButton(new_session_text, callback_data="action:new_session"),
                InlineKeyboardButton(continue_session_text, callback_data="action:continue"),
            ],
            [
                InlineKeyboardButton(check_status_text, callback_data="action:status"),
            ],
            [
                InlineKeyboardButton(export_session_text, callback_data="action:export"),
                InlineKeyboardButton(settings_text, callback_data="action:settings"),
            ],
            [
                InlineKeyboardButton(get_help_text, callback_data="action:help"),
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
            f"• `/status` - Show session status\n"
            f"• `/actions` - Show quick actions\n"
            f"• `/git` - Git repository commands\n\n"
            f"**Quick Start:**\n"
            f"1. Use `/ls` to see available directories\n"
            f"2. Use `/cd <dir>` to navigate to a directory\n"
            f"3. Send any message to start coding with Claude!\n\n"
            f"🔒 Your access is secured and all actions are logged.\n"
            f"📊 Use `/status` to check your usage limits."
        )
        
        keyboard = [
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.new_session"), callback_data="action:new_session"),
                InlineKeyboardButton(await t(context, user_id, "buttons.continue"), callback_data="action:continue"),
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.check_status"), callback_data="action:status"),
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.export"), callback_data="action:export"),
                InlineKeyboardButton(await t(context, user_id, "buttons.settings"), callback_data="action:settings"),
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.get_help"), callback_data="action:help"),
                InlineKeyboardButton(await t(context, user_id, "buttons.language_settings"), callback_data="lang:select"),
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
                    f"• {help_data.get('usage_cd', 'cd mydir - Enter directory')}",
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
        quick_actions_btn = await t(context, user_id, "commands_extended.new_session.button_quick_actions")
        help_btn = await t(context, user_id, "commands_extended.new_session.button_help")
    else:
        start_coding_btn = "📝 Start Coding"
        quick_actions_btn = "📋 Quick Actions"
        help_btn = "❓ Help"
    
    keyboard = [
        [
            InlineKeyboardButton(
                start_coding_btn, callback_data="action:start_coding"
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
                    msg.text,
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
                    InlineKeyboardButton(await t(context, user_id, "buttons.go_up"), callback_data="cd:.."),
                    InlineKeyboardButton(await t(context, user_id, "buttons.root"), callback_data="cd:/"),
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.refresh"), callback_data="action:refresh_ls"),
                InlineKeyboardButton(
                    await t(context, user_id, "buttons.refresh"), callback_data="action:refresh_ls"
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
            "• `/cd mydir` - Enter subdirectory\n"
            "• `/cd ..` - Go up one level\n"
            "• `/cd /` - Go to root of approved directory\n\n"
            "**Tips:**\n"
            "• Use `/ls` to see available directories\n"
            "• Use `/ls` to see all subdirectories",
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
            InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_pwd"),
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

    # Create full main menu keyboard (8 buttons in 4 rows)
    keyboard = [
        [
            InlineKeyboardButton(await t(context, user_id, "buttons.new_session"), callback_data="action:new_session"),
            InlineKeyboardButton(await t(context, user_id, "buttons.continue_session"), callback_data="action:continue")
        ],
        [
            InlineKeyboardButton(await t(context, user_id, "buttons.status"), callback_data="action:status")
        ],
        [
            InlineKeyboardButton(await t(context, user_id, "buttons.export"), callback_data="action:export"),
            InlineKeyboardButton(await t(context, user_id, "buttons.settings"), callback_data="action:settings")
        ],
        [
            InlineKeyboardButton(await t(context, user_id, "buttons.help"), callback_data="action:help"),
            InlineKeyboardButton(await t(context, user_id, "buttons.language_settings"), callback_data="lang:select")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        "✅ **Session Ended**\n\n"
        f"Your Claude session has been terminated.\n\n"
        f"**Current Status:**\n"
        f"• Directory: `{relative_path}/`\n"
        f"• Session: None\n"
        f"• Ready for new commands\n\n"
        f"**Main Menu:**\n"
        f"Choose your next action from the full menu below, or send any message to begin a new conversation.",
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

        # Create a mock session for quick actions context
        from ...storage.models import SessionModel
        from datetime import datetime
        mock_session = SessionModel(
            session_id="quick_actions_mock",
            user_id=user_id,
            project_path=str(current_dir),
            created_at=datetime.now(),
            last_used=datetime.now()
        )

        # Get context-aware actions
        actions = await quick_action_manager.get_suggestions(mock_session)

        if not actions:
            await message.reply_text(
                "🤖 **No Actions Available**\n\n"
                "No quick actions are available for the current context.\n\n"
                "**Try:**\n"
                "• Navigating to directories with `/cd`\n"
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
            ],
            [
                InlineKeyboardButton("🔄 Оновити", callback_data="schedule:refresh"),
                InlineKeyboardButton("▶️ Запустити всі", callback_data="schedule:run_all")
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
    """Show available quick actions with interactive buttons."""
    # Delegate to the existing quick actions implementation
    await quick_actions(update, context)

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



async def git_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /git command with simple button interface."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    settings = context.bot_data.get("settings")
    if not settings:
        await message.reply_text(await t(context, user_id, "errors.settings_not_available"))
        return
    settings_typed = cast(Settings, settings)

    # Get current directory for context
    current_dir = context.user_data.get(
        "current_directory", settings_typed.approved_directory
    ) if context.user_data else settings_typed.approved_directory

    relative_path = current_dir.relative_to(settings_typed.approved_directory)

    try:
        # Get localized texts
        title = await t(context, user_id, "git.title")
        description = await t(context, user_id, "git.description")

        # Create message
        current_dir_text = await t(context, user_id, "commands.pwd.current_directory")
        message_text = f"{title}\n\n{description}\n\n📂 {current_dir_text}: {relative_path}/"

        # Create button grid with localized labels
        keyboard = [
            [
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.status"),
                    callback_data="git:status"
                ),
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.add"),
                    callback_data="git:add"
                ),
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.commit"),
                    callback_data="git:commit"
                )
            ],
            [
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.push"),
                    callback_data="git:push"
                ),
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.pull"),
                    callback_data="git:pull"
                ),
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.log"),
                    callback_data="git:log"
                )
            ],
            [
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.diff"),
                    callback_data="git:diff"
                ),
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.branch"),
                    callback_data="git:branch"
                ),
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.help"),
                    callback_data="git:help"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(
            message_text, reply_markup=reply_markup
        )

    except Exception as e:
        error_msg = await t(context, user_id, "git.error")
        await message.reply_text(error_msg.format(error=str(e)))
        logger.error("Error in git_handler", error=str(e), user_id=user_id)


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


# New Claude login helper functions
async def extract_auth_url_from_claude_login() -> Tuple[bool, str, Optional[pexpect.spawn]]:
    """Запускає `claude login` та витягує URL для авторизації."""
    try:
        logger.info("Starting claude login to extract auth URL")

        # Запускаємо процес claude login
        child = pexpect.spawn('claude login', encoding='utf-8', timeout=30)

        # Паттерни для пошуку URL
        url_patterns = [
            r'https://claude\.ai/login\?[^\s]*',  # Claude login URL
            r'https://[^\s]*anthropic[^\s]*',     # Anthropic URL
            r'https://[^\s]+',                    # Будь-який HTTPS URL
            pexpect.TIMEOUT,
            pexpect.EOF
        ]

        output_buffer = ""
        start_time = time.time()

        while time.time() - start_time < 30:  # 30 секунд timeout
            try:
                index = child.expect(url_patterns, timeout=5)

                # Збираємо весь вивід
                if child.before:
                    output_buffer += child.before
                if child.after and index < 3:  # URL знайдено
                    output_buffer += child.after

                logger.debug("Claude login output", index=index, output=output_buffer[-200:])

                if index < 3:  # URL знайдено
                    # Витягуємо URL з output_buffer
                    url_match = re.search(r'https://[^\s]+', output_buffer)
                    if url_match:
                        auth_url = url_match.group(0)
                        logger.info("Auth URL extracted successfully", url=auth_url[:50] + "...")
                        return True, auth_url, child

                elif index == 3:  # TIMEOUT
                    continue

                elif index == 4:  # EOF
                    break

            except pexpect.TIMEOUT:
                continue

        # Якщо URL не знайдено, перевіримо весь output
        url_match = re.search(r'https://[^\s]+', output_buffer)
        if url_match:
            auth_url = url_match.group(0)
            logger.info("Auth URL found in buffer", url=auth_url[:50] + "...")
            return True, auth_url, child

        logger.error("No auth URL found in claude login output", output=output_buffer)
        try:
            if child and child.isalive():
                child.terminate(force=True)
        except:
            pass
        return False, f"No authentication URL found. Output: {output_buffer}", None

    except Exception as e:
        logger.error("Error extracting auth URL", error=str(e))
        try:
            if 'child' in locals() and child and child.isalive():
                child.terminate(force=True)
        except:
            pass
        return False, f"Error starting claude login: {str(e)}", None


async def submit_auth_code_to_claude(child: pexpect.spawn, auth_code: str) -> Tuple[bool, str]:
    """Надсилає код авторизації до процесу claude login."""
    try:
        logger.info("Submitting auth code to claude login")

        # Надсилаємо код
        child.sendline(auth_code)

        # Паттерни для очікування результату
        result_patterns = [
            r'(?i)success',           # Успіх
            r'(?i)authenticated',     # Автентифіковано
            r'(?i)logged.*in',        # Залогінено
            r'(?i)invalid.*code',     # Невірний код
            r'(?i)expired.*code',     # Код просрочений
            r'(?i)error',             # Помилка
            r'(?i)failed',            # Невдача
            pexpect.TIMEOUT,
            pexpect.EOF
        ]

        output_buffer = ""
        start_time = time.time()

        while time.time() - start_time < 60:  # 60 секунд на авторизацію
            try:
                index = child.expect(result_patterns, timeout=10)

                # Збираємо вивід
                if child.before:
                    output_buffer += child.before
                if child.after and index < 7:
                    output_buffer += child.after

                logger.debug("Auth code response", index=index, output=output_buffer[-200:])

                if index in [0, 1, 2]:  # Успіх
                    logger.info("Authentication successful")
                    safe_terminate_process(child)
                    return True, "Authentication successful"

                elif index in [3, 4, 5, 6]:  # Помилка
                    logger.warning("Authentication failed", output=output_buffer)
                    safe_terminate_process(child)
                    return False, f"Authentication failed: {output_buffer}"

                elif index == 7:  # TIMEOUT
                    continue

                elif index == 8:  # EOF
                    # Перевіряємо exit code
                    if child.exitstatus == 0:
                        logger.info("Process exited successfully")
                        return True, "Authentication completed successfully"
                    else:
                        logger.warning("Process exited with error", exit_code=child.exitstatus)
                        return False, f"Process failed with exit code {child.exitstatus}: {output_buffer}"

            except pexpect.TIMEOUT:
                logger.debug("Waiting for auth response...")
                continue

        # Timeout
        logger.error("Authentication timeout", output=output_buffer)
        safe_terminate_process(child)
        return False, f"Authentication timed out: {output_buffer}"

    except Exception as e:
        logger.error("Error submitting auth code", error=str(e))
        safe_terminate_process(child)
        return False, f"Error during authentication: {str(e)}"


async def check_claude_auth_status() -> Tuple[bool, str]:
    """Перевіряє поточний статус авторизації Claude CLI."""
    try:
        logger.info("Checking Claude CLI auth status")

        # Перевіряємо файл з креденшиалами
        credentials_path = Path.home() / ".claude" / ".credentials.json"

        if not credentials_path.exists():
            return False, "Файл креденшиалів не знайдено"

        # Перевіряємо термін дії токену
        import json
        try:
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
                oauth_data = creds.get("claudeAiOauth", {})
                expires_at = oauth_data.get("expiresAt", 0)
                current_time = time.time() * 1000

                if expires_at == 0:
                    return False, "Некоректні креденшиали (немає expiresAt)"

                if current_time >= expires_at:
                    return False, f"Токен просрочений"

                # Якщо токен валідний по часу, припускаємо що авторизація працює
                hours_remaining = (expires_at - current_time) / (1000 * 3600)
                return True, f"Авторизований (залишилось {hours_remaining:.1f} годин)"

        except (json.JSONDecodeError, KeyError) as e:
            return False, f"Помилка читання креденшиалів: {str(e)}"

    except Exception as e:
        logger.error("Error checking auth status", error=str(e))
        return False, f"Помилка перевірки: {str(e)}"


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє команду /login для авторизації Claude CLI."""
    user_id = update.effective_user.id
    message = update.effective_message

    if not user_id or not message:
        return

    try:
        # Перевіряємо чи не очікуємо вже код авторизації
        if context.user_data.get('claude_auth_waiting'):
            await message.reply_text(
                "⏳ **Вже очікую код авторизації**\n\n"
                "Надішліть код авторизації з браузера або використайте /cancel для скасування."
            )
            return

        # Перевіряємо поточний статус авторизації
        await message.reply_text("🔍 **Перевіряю поточний статус авторизації...**")

        is_auth, status_msg = await check_claude_auth_status()

        if is_auth:
            await message.reply_text(
                f"✅ **Claude CLI вже авторизований**\n\n"
                f"📊 Статус: {status_msg}\n\n"
                f"Авторизація не потрібна!"
            )
            return

        # Починаємо процес авторизації
        await message.reply_text(
            f"❌ **Claude CLI не авторизований**\n\n"
            f"📊 Статус: {status_msg}\n\n"
            f"🚀 Починаю процес авторизації..."
        )

        # Витягуємо URL авторизації
        success, result, child = await extract_auth_url_from_claude_login()

        if not success:
            await message.reply_text(
                f"❌ **Помилка запуску авторизації**\n\n"
                f"```\n{result}\n```\n\n"
                f"Спробуйте ще раз або зверніться до адміністратора."
            )
            return

        # Зберігаємо процес для подальшого використання
        context.user_data['claude_auth_waiting'] = True
        context.user_data['claude_auth_process'] = child
        context.user_data['claude_auth_url'] = result

        # Надсилаємо інструкції користувачу
        auth_url = result
        instructions = (
            f"🔐 **Авторизація Claude CLI**\n\n"
            f"**Крок 1:** Відкрийте це посилання у браузері:\n"
            f"👆 {auth_url}\n\n"
            f"**Крок 2:** Увійдіть у свій акаунт Claude\n\n"
            f"**Крок 3:** Скопіюйте код авторизації\n\n"
            f"**Крок 4:** Надішліть код у це повідомлення\n\n"
            f"⏳ **Очікую код авторизації...**\n\n"
            f"💡 Використайте /cancel для скасування"
        )

        await message.reply_text(instructions)

        logger.info("Claude login process started", user_id=user_id, url_length=len(auth_url))

    except Exception as e:
        logger.error("Error in login command", error=str(e), user_id=user_id, exc_info=True)

        # Очищуємо стан в разі помилки
        context.user_data.pop('claude_auth_waiting', None)
        if 'claude_auth_process' in context.user_data:
            try:
                context.user_data['claude_auth_process'].close()
            except:
                pass
            context.user_data.pop('claude_auth_process', None)

        await message.reply_text(
            f"❌ **Помилка виконання команди**\n\n"
            f"```\n{str(e)}\n```\n\n"
            f"Спробуйте ще раз."
        )


# Alias for backward compatibility
async def claude_auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated: Use /login instead. Redirects to login_command."""
    await login_command(update, context)


async def handle_claude_auth_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Обробляє повідомлення з кодом авторизації.
    Returns: True якщо повідомлення оброблено як код авторизації, False інакше
    """
    user_id = update.effective_user.id
    message = update.effective_message

    if not user_id or not message or not message.text:
        return False

    # Перевіряємо чи очікуємо код авторизації
    if not context.user_data.get('claude_auth_waiting'):
        return False

    auth_code = message.text.strip()

    # Перевіряємо формат коду (зазвичай це довгий рядок)
    if len(auth_code) < 10:
        await message.reply_text(
            "🤔 **Код занадто короткий**\n\n"
            "Код авторизації зазвичай довгий рядок.\n"
            "Перевірте та надішліть правильний код.\n\n"
            "💡 Використайте /cancel для скасування"
        )
        return True

    try:
        await message.reply_text("🔄 **Обробляю код авторизації...**")

        # Отримуємо збережений процес
        child = context.user_data.get('claude_auth_process')
        if not child or not child.isalive():
            await message.reply_text(
                "❌ **Сесія авторизації втрачена**\n\n"
                "Процес авторизації більше не активний.\n"
                "Виконайте /login знову."
            )
            # Очищуємо стан
            context.user_data.pop('claude_auth_waiting', None)
            context.user_data.pop('claude_auth_process', None)
            return True

        # Надсилаємо код до Claude CLI
        success, result = await submit_auth_code_to_claude(child, auth_code)

        # Очищуємо стан авторизації
        context.user_data.pop('claude_auth_waiting', None)
        context.user_data.pop('claude_auth_process', None)
        context.user_data.pop('claude_auth_url', None)

        if success:
            await message.reply_text(
                f"✅ **Авторизація успішна!**\n\n"
                f"🎉 Claude CLI тепер авторизований\n"
                f"📊 Результат: {result}\n\n"
                f"Тепер ви можете користуватися всіма функціями бота!"
            )
            logger.info("Claude CLI authentication successful", user_id=user_id)
        else:
            await message.reply_text(
                f"❌ **Помилка авторизації**\n\n"
                f"```\n{result}\n```\n\n"
                f"Спробуйте /login знову з новим кодом."
            )
            logger.warning("Claude CLI authentication failed", user_id=user_id, error=result)

        return True

    except Exception as e:
        logger.error("Error processing auth code", error=str(e), user_id=user_id, exc_info=True)

        # Очищуємо стан
        context.user_data.pop('claude_auth_waiting', None)
        if 'claude_auth_process' in context.user_data:
            try:
                context.user_data['claude_auth_process'].close()
            except:
                pass
            context.user_data.pop('claude_auth_process', None)

        await message.reply_text(
            f"❌ **Помилка обробки коду**\n\n"
            f"```\n{str(e)}\n```\n\n"
            f"Спробуйте /login знову."
        )
        return True


async def cancel_auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Скасовує поточний процес авторизації."""
    user_id = update.effective_user.id
    message = update.effective_message

    if not user_id or not message:
        return

    if not context.user_data.get('claude_auth_waiting'):
        await message.reply_text(
            "ℹ️ **Немає активного процесу авторизації**\n\n"
            "Немає що скасовувати."
        )
        return

    try:
        # Закриваємо процес якщо він є
        if 'claude_auth_process' in context.user_data:
            process = context.user_data['claude_auth_process']
            safe_terminate_process(process)
            context.user_data.pop('claude_auth_process', None)

        # Очищуємо стан
        context.user_data.pop('claude_auth_waiting', None)
        context.user_data.pop('claude_auth_url', None)

        await message.reply_text(
            "✅ **Авторизація скасована**\n\n"
            "Процес авторизації Claude CLI скасовано.\n"
            "Використайте /login для нової спроби."
        )

        logger.info("Claude CLI authentication cancelled", user_id=user_id)

    except Exception as e:
        logger.error("Error cancelling auth", error=str(e), user_id=user_id)
        await message.reply_text(
            f"❌ **Помилка скасування**\n\n"
            f"```\n{str(e)}\n```"
        )


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


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /restart command to restart the bot."""
    import subprocess
    import os

    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    try:
        # Check if user has admin privileges or is authorized
        auth_manager = context.bot_data.get("auth_manager")
        if auth_manager and not auth_manager.is_authenticated(user_id):
            access_denied_text = await t(context, user_id, "commands.restart.access_denied")
            await message.reply_text(access_denied_text)
            return

        # Send confirmation message
        restarting_text = await t(context, user_id, "commands.restart.restarting")
        status_msg = await message.reply_text(restarting_text)

        # Run the restart script
        script_path = "/home/vokov/claude-notifer-and-bot/restart-bot.sh"
        if os.path.exists(script_path):
            # Execute restart script in background
            subprocess.Popen([script_path], cwd="/home/vokov/claude-notifer-and-bot")

            # The current process will be killed by the script, so this might not send
            initiated_text = await t(context, user_id, "commands.restart.initiated")
            await status_msg.edit_text(initiated_text)
        else:
            script_not_found_text = await t(context, user_id, "commands.restart.script_not_found")
            await status_msg.edit_text(script_not_found_text)

    except Exception as e:
        logger.error("Error in restart command", error=str(e), user_id=user_id)
        failed_text = await t(context, user_id, "commands.restart.failed")
        await message.reply_text(f"{failed_text}\n\nError: {str(e)}")


async def audit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запустити інтелектуальний аудит бота"""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not user_id or not message:
        return

    logger.info("Starting intelligent bot audit", user_id=user_id)

    try:
        # Перевірити права доступу (тільки адміністратори)
        auth_manager = context.bot_data.get("auth_manager")
        if not auth_manager or not auth_manager.is_authenticated(user_id):
            await message.reply_text("❌ Доступ заборонено. Аудит доступний тільки адміністраторам.")
            return

        # Парсинг аргументів команди
        message_text = message.text or ""
        parts = message_text.split()

        focus_area = None
        if len(parts) > 1:
            focus_area = parts[1].lower()
            if focus_area not in ["callbacks", "localization", "security", "architecture", "quick"]:
                await message.reply_text(
                    "❌ Невідома область аудиту.\n\n"
                    "Доступні опції:\n"
                    "• `/audit` - повний аудит\n"
                    "• `/audit quick` - швидкий аналіз\n"
                    "• `/audit callbacks` - аналіз callback handlers\n"
                    "• `/audit localization` - аналіз перекладів\n"
                    "• `/audit security` - аналіз безпеки\n"
                    "• `/audit architecture` - аналіз архітектури"
                )
                return

        # Показати повідомлення про початок аудиту
        if focus_area == "quick":
            status_text = "🔍 **Швидкий аудит коду...**\n\nЗапускаю базовий аналіз..."
        elif focus_area:
            status_text = f"🔍 **Фокусований аудит: {focus_area}**\n\nАналізую {focus_area}..."
        else:
            status_text = "🔍 **Повний інтелектуальний аудит**\n\nАналізую код, архітектуру та логіку..."

        status_msg = await message.reply_text(status_text)

        # Отримати Claude інтеграцію
        claude_integration = context.bot_data.get("claude_integration")
        settings = context.bot_data.get("settings")

        if not settings:
            await status_msg.edit_text("❌ Конфігурація бота недоступна")
            return

        # Запустити аудитор
        from ..features.intelligent_auditor import IntelligentTelegramBotAuditor, format_audit_report

        auditor = IntelligentTelegramBotAuditor(
            project_root=str(settings.approved_directory),
            claude_integration=claude_integration if focus_area != "quick" else None
        )

        # Налаштування для швидкого аудиту
        if focus_area == "quick":
            auditor.analysis_config["enable_claude_analysis"] = False
            auditor.analysis_config["group_similar_issues"] = False

        await status_msg.edit_text(f"{status_text}\n\n⏳ Виконую аналіз коду...")

        # Запустити аудит
        result = await auditor.run_audit(focus_area)

        # Згенерувати звіт
        report = format_audit_report(result)

        # Відправити звіт
        if len(report) > 4096:
            # Розбити на частини для Telegram
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]

            await status_msg.edit_text(f"✅ **Аудит завершено!**\n\nЗнайдено {result.total_issues} проблем.\nВідправляю звіт...")

            for i, chunk in enumerate(chunks):
                if i == 0:
                    await message.reply_text(chunk, parse_mode=None)
                else:
                    await message.reply_text(f"**Частина {i+1}:**\n\n{chunk}", parse_mode=None)

                if i < len(chunks) - 1:
                    await asyncio.sleep(1)  # Уникнути rate limit
        else:
            await status_msg.edit_text(report, parse_mode=None)

        # Додатковий аналіз для критичних проблем
        critical_issues = [i for i in result.issues if i.severity == "CRITICAL"]
        if critical_issues and focus_area != "quick":
            await message.reply_text(
                f"🚨 **УВАГА!** Знайдено {len(critical_issues)} критичних проблем.\n\n"
                f"Рекомендую негайно виправити ці проблеми, оскільки вони можуть впливати на роботу бота."
            )

        logger.info("Audit completed",
                   user_id=user_id,
                   total_issues=result.total_issues,
                   critical=result.critical_count,
                   focus_area=focus_area)

    except Exception as e:
        logger.error("Error in audit command", error=str(e), user_id=user_id, exc_info=True)
        error_msg = f"❌ **Помилка під час аудиту**\n\n`{str(e)}`"

        try:
            await status_msg.edit_text(error_msg)
        except:
            await message.reply_text(error_msg)


async def dracon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """DRACON-YAML bot logic modeling command."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not message:
        logger.warning("No message in dracon command", user_id=user_id)
        return

    logger.info("DRACON command invoked", user_id=user_id)

    try:
        from ..features.dracon_yaml import DraconYamlProcessor, EXAMPLE_MENU_SCHEMA
        from ..features.dracon_storage import DraconStorageManager

        # Parse command arguments
        args = context.args if context.args else []
        command_text = " ".join(args) if args else ""

        # Initialize storage manager
        settings = context.bot_data.get("settings")
        if not settings:
            await message.reply_text("❌ Налаштування бота недоступні")
            return

        storage = DraconStorageManager(str(settings.approved_directory))

        # Show help if no arguments
        if not command_text or command_text.lower() in ["help", "допомога"]:
            help_text = """🔧 **Enhanced DRACON-YAML Bot Logic Modeling**

DRACON (Дружелюбные Русские Алгоритмы, Которые Обеспечивают Надежность) - професійна система моделирования логіки бота з візуальними діаграмами.

**Основні команди:**
• `/dracon help` - Ця довідка
• `/dracon example` - Показати приклад схеми
• `/dracon analyze <yaml>` - Аналізувати YAML-схему
• `/dracon generate <yaml>` - Згенерувати компоненти
• `/dracon validate <yaml>` - Перевірити схему
• `/dracon diagram <category> <filename>` - 🎨 Візуальна діаграма

**Файлові операції:**
• `/dracon list [category]` - Список збережених схем
• `/dracon load <category> <filename>` - Завантажити схему
• `/dracon save <category> <name>` - Зберегти схему
• `/dracon copy <from_cat> <filename> <to_cat>` - Копіювати схему
• `/dracon delete <category> <filename>` - Видалити схему
• `/dracon stats` - Статистика зберігання

**Категорії схем:**
📁 `reverse` - Схеми з реверс-інжинірингу
📁 `build` - Базові схеми для розбудови
📁 `audit` - Схеми для тестування
📁 `library` - Бібліотека компонентів
📁 `active` - Активні схеми
📁 `archive` - Архівні версії

**Приклад:**
```
/dracon save reverse my_bot_schema
/dracon list reverse
/dracon load reverse my_bot_schema_20241219_143022.yaml
```"""

            await message.reply_text(help_text, parse_mode="Markdown")
            return

        # Handle visual diagram generation
        if command_text.lower().startswith("diagram"):
            parts = command_text.split()
            if len(parts) < 3:
                await message.reply_text("❌ Використання: `/dracon diagram <category> <filename>`")
                return

            category = parts[1]
            filename = parts[2]

            try:
                # Load schema
                schema_content = storage.load_schema(category, filename)
                if not schema_content:
                    await message.reply_text(f"❌ Схема `{filename}` не знайдена в категорії `{category}`")
                    return

                # Process with enhanced processor
                from ..features.dracon_enhanced import EnhancedDraconProcessor
                processor = EnhancedDraconProcessor()

                # Create temporary file for processing
                temp_file = storage.temp_dir / f"temp_{filename}"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(schema_content)

                # Process schema
                result = await processor.process_schema_file(temp_file)

                if not result["success"]:
                    error_msg = "❌ Помилка обробки схеми:\n" + "\n".join(result.get("errors", []))
                    await message.reply_text(error_msg)
                    return

                # Send visual diagram if available
                if result.get("svg_diagram"):
                    try:
                        # Convert SVG to PNG for Telegram
                        import io
                        from PIL import Image
                        import cairosvg

                        png_data = cairosvg.svg2png(bytestring=result["svg_diagram"].encode('utf-8'))

                        await message.reply_photo(
                            photo=io.BytesIO(png_data),
                            caption=f"📊 **Візуальна схема:** {result['metadata']['name']}\n"
                                   f"🔧 Вузлів: {result['metadata']['node_count']}\n"
                                   f"➡️ З'єднань: {result['metadata']['edge_count']}\n"
                                   f"⚡ Складність: {result['metadata']['complexity']}"
                        )
                    except Exception as e:
                        logger.warning("Failed to convert SVG to PNG", error=str(e))
                        # Fallback to text description
                        await message.reply_text(
                            f"📊 **Схема проаналізована:** {result['metadata']['name']}\n"
                            f"🔧 Вузлів: {result['metadata']['node_count']}\n"
                            f"➡️ З'єднань: {result['metadata']['edge_count']}\n"
                            f"⚡ Складність: {result['metadata']['complexity']}\n\n"
                            f"*Візуалізація недоступна (потрібен cairosvg)*"
                        )

                # Cleanup
                temp_file.unlink(missing_ok=True)

            except Exception as e:
                logger.error("Diagram generation failed", error=str(e))
                await message.reply_text(f"❌ Помилка генерації діаграми: {str(e)}")
            return

        # Handle file operations first
        if command_text.lower().startswith("list"):
            parts = command_text.split()
            category = parts[1] if len(parts) > 1 else None

            try:
                schemas = storage.list_schemas(category)

                if not any(schemas.values()):
                    await message.reply_text("📁 **Немає збережених схем**\n\nВикористайте команди для створення та збереження схем.")
                    return

                report = "📋 **Збережені DRACON Схеми**\n\n"

                for cat, schema_list in schemas.items():
                    if not schema_list:
                        continue

                    report += f"📁 **{cat}** ({len(schema_list)} схем):\n"
                    for schema in schema_list[:5]:  # Show first 5
                        report += f"• `{schema['filename']}`\n"
                        if 'metadata' in schema and 'description' in schema['metadata']:
                            report += f"  📝 {schema['metadata']['description'][:50]}...\n"
                        report += f"  📅 {schema['created'][:10]}\n"

                    if len(schema_list) > 5:
                        report += f"  ... та ще {len(schema_list) - 5} схем\n"
                    report += "\n"

                await message.reply_text(report)

            except Exception as e:
                await message.reply_text(f"❌ **Помилка отримання списку:**\n\n`{str(e)}`")
            return

        elif command_text.lower().startswith("load"):
            parts = command_text.split()
            if len(parts) < 3:
                await message.reply_text("❌ **Використання:** `/dracon load <category> <filename>`")
                return

            category, filename = parts[1], parts[2]

            try:
                schema_yaml, metadata = storage.load_schema(category, filename)

                # Show schema info
                info = f"✅ **Схема завантажена:** `{filename}`\n"
                info += f"📁 Категорія: `{category}`\n"

                if metadata:
                    if 'description' in metadata:
                        info += f"📝 Опис: {metadata['description']}\n"
                    if 'saved_at' in metadata:
                        info += f"📅 Збережено: {metadata['saved_at'][:10]}\n"

                await message.reply_text(info)

                # Send schema content
                await message.reply_text(f"📋 **Вміст схеми:**\n\n```yaml\n{schema_yaml}\n```", parse_mode="Markdown")

            except Exception as e:
                await message.reply_text(f"❌ **Помилка завантаження:**\n\n`{str(e)}`")
            return

        elif command_text.lower().startswith("stats"):
            try:
                stats = storage.get_storage_stats()

                report = f"📊 **Статистика DRACON Сховища**\n\n"
                report += f"**Загальна інформація:**\n"
                report += f"• Всього схем: {stats['total_schemas']}\n"
                report += f"• Загальний розмір: {stats['total_size'] / 1024:.1f} KB\n\n"

                report += f"**По категоріях:**\n"
                for category, info in stats['categories'].items():
                    report += f"📁 {category}: {info['count']} схем ({info['size'] / 1024:.1f} KB)\n"

                if stats['newest_schema']:
                    from pathlib import Path
                    report += f"\n🆕 Найновіша: `{Path(stats['newest_schema']).name}`\n"
                if stats['oldest_schema']:
                    report += f"📜 Найстаріша: `{Path(stats['oldest_schema']).name}`"

                await message.reply_text(report)

            except Exception as e:
                await message.reply_text(f"❌ **Помилка статистики:**\n\n`{str(e)}`")
            return

        elif command_text.lower().startswith("copy"):
            parts = command_text.split()
            if len(parts) < 4:
                await message.reply_text("❌ **Використання:** `/dracon copy <source_category> <filename> <target_category>`")
                return

            source_cat, filename, target_cat = parts[1], parts[2], parts[3]

            try:
                new_path = storage.copy_schema(source_cat, filename, target_cat)
                await message.reply_text(f"✅ **Схему скопійовано!**\n\n📂 З: `{source_cat}/{filename}`\n📁 До: `{target_cat}/{Path(new_path).name}`")

            except Exception as e:
                await message.reply_text(f"❌ **Помилка копіювання:**\n\n`{str(e)}`")
            return

        elif command_text.lower().startswith("delete"):
            parts = command_text.split()
            if len(parts) < 3:
                await message.reply_text("❌ **Використання:** `/dracon delete <category> <filename>`")
                return

            category, filename = parts[1], parts[2]

            try:
                storage.delete_schema(category, filename, archive_first=True)
                await message.reply_text(f"✅ **Схему видалено!**\n\n📁 Категорія: `{category}`\n📄 Файл: `{filename}`\n💾 Збережено в архіві")

            except Exception as e:
                await message.reply_text(f"❌ **Помилка видалення:**\n\n`{str(e)}`")
            return

        elif command_text.lower().startswith("save"):
            parts = command_text.split()
            if len(parts) < 3:
                await message.reply_text("❌ **Використання:** `/dracon save <category> <name> [yaml_content]`\n\nАбо надішліть YAML схему після команди.")
                return

            category, name = parts[1], parts[2]

            # Check if YAML content is provided in same message
            remaining_text = " ".join(parts[3:]) if len(parts) > 3 else ""

            if "version:" in remaining_text and ("nodes:" in remaining_text or "edges:" in remaining_text):
                yaml_content = remaining_text
            else:
                await message.reply_text(f"📝 **Надішліть YAML схему для збереження в категорію `{category}` з ім'ям `{name}`:**")
                # Store pending save operation in user context
                if not hasattr(context, 'user_data'):
                    context.user_data = {}
                context.user_data['pending_save'] = {'category': category, 'name': name}
                return

            try:
                # Create metadata
                metadata = {
                    'name': name,
                    'description': f"DRACON schema saved via bot interface",
                    'created_by': user_id,
                    'source': 'bot_interface'
                }

                file_path, filename = storage.save_schema(yaml_content, category, name, metadata)
                await message.reply_text(f"✅ **Схему збережено!**\n\n📁 Категорія: `{category}`\n📄 Файл: `{filename}`\n💾 Шлях: `{file_path}`")

            except Exception as e:
                await message.reply_text(f"❌ **Помилка збереження:**\n\n`{str(e)}`")
            return

        # Handle different subcommands
        if command_text.lower().startswith("example"):
            await message.reply_text(
                "📋 **Приклад DRACON схеми:**\n\n```yaml\n" +
                EXAMPLE_MENU_SCHEMA +
                "\n```",
                parse_mode="Markdown"
            )
            return

        # Process YAML content from user message
        yaml_content = None

        # Check if user sent YAML in the same message
        if "version:" in command_text and ("nodes:" in command_text or "edges:" in command_text):
            yaml_content = command_text
        else:
            # Ask user to send YAML content
            await message.reply_text(
                "📝 **Надішліть YAML-схему DRACON для аналізу:**\n\n"
                "Використовуйте `/dracon example` для перегляду прикладу схеми."
            )
            return

        # Initialize processor
        processor = DraconYamlProcessor()

        # Determine action
        action = "analyze"  # default
        if command_text.lower().startswith("generate"):
            action = "generate"
            yaml_content = command_text[8:].strip()  # Remove "generate"
        elif command_text.lower().startswith("validate"):
            action = "validate"
            yaml_content = command_text[8:].strip()  # Remove "validate"
        elif command_text.lower().startswith("analyze"):
            yaml_content = command_text[7:].strip()  # Remove "analyze"

        # Show processing status
        status_msg = await message.reply_text("🔄 **Обробляю DRACON схему...**\n\nЗавантажую та перевіряю YAML...")

        # Process based on action
        if action == "validate":
            try:
                schema = processor.load_schema(yaml_content)
                await status_msg.edit_text(
                    f"✅ **Схема валідна!**\n\n"
                    f"📋 Назва: {schema.name}\n"
                    f"📝 Опис: {schema.description or 'Не вказано'}\n"
                    f"🔗 Вузлів: {len(schema.nodes)}\n"
                    f"➡️ Зв'язків: {len(schema.edges)}"
                )
            except Exception as e:
                await status_msg.edit_text(f"❌ **Помилка валідації:**\n\n`{str(e)}`")
            return

        elif action == "generate":
            await status_msg.edit_text("🔄 **Генерую компоненти...**\n\nАналізую схему та створюю код...")

            components = await processor.generate_components(yaml_content)

            if not components:
                await status_msg.edit_text("❌ **Не вдалося згенерувати компоненти**")
                return

            # Show generated components
            report = f"✅ **Згенеровано {len(components)} компонентів:**\n\n"

            for comp in components[:5]:  # Show first 5 components
                report += f"🔧 **{comp.type}**: `{comp.name}`\n"
                if comp.properties.get('description'):
                    report += f"   📝 {comp.properties['description']}\n"
                report += "\n"

            if len(components) > 5:
                report += f"... та ще {len(components) - 5} компонентів\n\n"

            report += "💾 Код компонентів готовий до інтеграції!"

            await status_msg.edit_text(report)

            # Send code examples for first few components
            for i, comp in enumerate(components[:3]):
                await message.reply_text(
                    f"**{comp.type}: {comp.name}**\n\n```python\n{comp.code}\n```",
                    parse_mode="Markdown"
                )
                if i < 2:
                    await asyncio.sleep(1)  # Avoid rate limit

            return

        # Default: analyze
        await status_msg.edit_text("🔄 **Аналізую граф...**\n\nПеревіряю топологію та логічну цілісність...")

        # Perform analysis
        result = await processor.analyze_graph(yaml_content)

        # Generate analysis report
        report = f"📊 **Аналіз DRACON схеми**\n\n"

        if result.is_valid:
            report += "✅ **Схема валідна та готова до використання!**\n\n"
        else:
            report += "⚠️ **Знайдено проблеми в схемі:**\n\n"

        # Status indicators
        report += f"🔒 Замкнений граф: {'✅' if result.is_closed else '❌'}\n"
        report += f"🎯 Досяжність: {'✅' if result.is_reachable else '❌'}\n\n"

        # Issues
        if result.issues:
            report += "🔴 **Проблеми:**\n"
            for issue in result.issues[:5]:
                report += f"• {issue}\n"
            if len(result.issues) > 5:
                report += f"... та ще {len(result.issues) - 5} проблем\n"
            report += "\n"

        # Warnings
        if result.warnings:
            report += "🟡 **Попередження:**\n"
            for warning in result.warnings[:3]:
                report += f"• {warning}\n"
            report += "\n"

        # Suggestions
        if result.suggestions:
            report += "💡 **Рекомендації:**\n"
            for suggestion in result.suggestions[:3]:
                report += f"• {suggestion}\n"
            report += "\n"

        # Components summary
        total_components = sum(len(comps) for comps in result.components.values())
        if total_components > 0:
            report += f"🔧 **Компоненти:** {total_components} елементів готові до генерації\n"
            for comp_type, items in result.components.items():
                if items:
                    report += f"   • {comp_type}: {len(items)}\n"

        await status_msg.edit_text(report)

        # Send Claude analysis if available
        if result.claude_analysis and len(result.claude_analysis) > 100:
            claude_report = f"🤖 **Аналіз Claude:**\n\n{result.claude_analysis}"

            if len(claude_report) > 4096:
                # Split into chunks
                chunks = [claude_report[i:i+4000] for i in range(0, len(claude_report), 4000)]
                for i, chunk in enumerate(chunks):
                    await message.reply_text(chunk)
                    if i < len(chunks) - 1:
                        await asyncio.sleep(1)
            else:
                await message.reply_text(claude_report)

        logger.info("DRACON analysis completed",
                   user_id=user_id,
                   is_valid=result.is_valid,
                   issues_count=len(result.issues),
                   components_count=total_components)

    except Exception as e:
        logger.error("Error in DRACON command", error=str(e), user_id=user_id, exc_info=True)
        error_msg = f"❌ **Помилка DRACON:**\n\n`{str(e)}`"

        try:
            await message.reply_text(error_msg)
        except:
            # Fallback if message fails
            pass


async def refactor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reverse engineer bot code into DRACON schemas for refactoring."""
    user_id = get_user_id(update)
    message = get_effective_message(update)

    if not message:
        logger.warning("No message in refactor command", user_id=user_id)
        return

    logger.info("Refactor command invoked", user_id=user_id)

    try:
        # Check admin access
        auth_manager = context.bot_data.get("auth_manager")
        if not auth_manager or not auth_manager.is_authenticated(user_id):
            await message.reply_text("❌ Доступ заборонено. Рефакторинг доступний тільки адміністраторам.")
            return

        from ..features.dracon_reverse_engineer import DraconReverseEngineer
        from ..features.dracon_storage import DraconStorageManager

        # Parse command arguments
        args = context.args if context.args else []
        command_text = " ".join(args) if args else ""

        # Show help if no arguments
        if not command_text or command_text.lower() in ["help", "допомога"]:
            help_text = """🔄 **DRACON Рефакторинг Системи**

Зворотний інжиніринг існуючого коду бота в DRACON схеми для модернізації та аналізу.

**Команди:**
• `/refactor help` - Ця довідка
• `/refactor analyze` - Аналізувати архітектуру бота
• `/refactor generate` - Створити DRACON схему з коду
• `/refactor suggest` - Рекомендації з рефакторингу
• `/refactor handlers` - Аналіз тільки handlers
• `/refactor flows` - Аналіз логічних потоків

**Процес:**
1. 📖 Парсинг всіх Python файлів з handlers
2. 🔍 Виявлення логічних зв'язків між функціями
3. 🧠 Інтелектуальний аналіз з Claude
4. 📊 Генерація DRACON схеми
5. 💡 Рекомендації з покращення

**Що аналізується:**
• Command handlers та callback handlers
• Логічні потоки між функціями
• Складність коду та помилки
• Паттерни навігації та стани
• Можливості модернізації"""

            await message.reply_text(help_text, parse_mode="Markdown")
            return

        # Get settings for project root
        settings = context.bot_data.get("settings")
        if not settings:
            await message.reply_text("❌ Налаштування бота недоступні")
            return

        # Show processing status
        status_msg = await message.reply_text("🔄 **Аналізую архітектуру бота...**\n\nПарсинг Python файлів та виявлення handlers...")

        # Initialize reverse engineer and storage
        claude_integration = context.bot_data.get("claude_integration")
        engineer = DraconReverseEngineer(str(settings.approved_directory), claude_integration)
        storage = DraconStorageManager(str(settings.approved_directory))

        # Determine analysis type
        if command_text.lower().startswith("handlers"):
            await status_msg.edit_text("🔄 **Аналізую handlers...**\n\nВиявляю command та callback handlers...")

            # Focus only on handlers analysis
            architecture = await engineer.analyze_bot_architecture(focus_path="src/bot/handlers")

            # Generate handlers report
            report = f"📋 **Аналіз Handlers**\n\n"
            report += f"**Загальна статистика:**\n"
            report += f"• Handlers: {len(architecture.handlers)}\n"
            report += f"• Логічних зв'язків: {len(architecture.flows)}\n"
            report += f"• Точок входу: {len(architecture.entry_points)}\n"
            report += f"• Відокремлених handlers: {len(architecture.orphaned_handlers)}\n\n"

            # Show complexity distribution
            complexity = architecture.complexity_metrics['complexity_distribution']
            report += f"**Розподіл складності:**\n"
            report += f"• Прості: {complexity['simple']}\n"
            report += f"• Середні: {complexity['medium']}\n"
            report += f"• Складні: {complexity['complex']}\n\n"

            # Show handler types
            handler_types = architecture.complexity_metrics['handler_types']
            report += f"**Типи handlers:**\n"
            for htype, count in handler_types.items():
                report += f"• {htype}: {count}\n"

            await status_msg.edit_text(report)

        elif command_text.lower().startswith("flows"):
            await status_msg.edit_text("🔄 **Аналізую логічні потоки...**\n\nВідстежую зв'язки між handlers...")

            architecture = await engineer.analyze_bot_architecture()

            # Generate flows report
            report = f"🔗 **Аналіз Логічних Потоків**\n\n"
            report += f"**Загальна статистика:**\n"
            report += f"• Всього потоків: {len(architecture.flows)}\n"
            report += f"• Handlers: {len(architecture.handlers)}\n"
            report += f"• Точки входу: {len(architecture.entry_points)}\n\n"

            if architecture.flows:
                report += f"**Приклади потоків:**\n"
                for flow in architecture.flows[:5]:
                    report += f"• {flow.from_handler} → {flow.to_handler}\n"
                    if flow.trigger_value:
                        report += f"  Trigger: {flow.trigger_value}\n"

                if len(architecture.flows) > 5:
                    report += f"... та ще {len(architecture.flows) - 5} потоків\n"
            else:
                report += "❌ **Логічних потоків не виявлено**\n"
                report += "Рекомендується додати більше інтерактивності між handlers."

            await status_msg.edit_text(report)

        elif command_text.lower().startswith("suggest"):
            await status_msg.edit_text("🔄 **Генерую рекомендації...**\n\nАналізую можливості покращення...")

            architecture = await engineer.analyze_bot_architecture()
            suggestions = await engineer.suggest_refactoring(architecture)

            # Save suggestions to audit directory
            try:
                suggestions_metadata = {
                    'name': 'refactoring_suggestions',
                    'description': f"Refactoring suggestions for bot with {len(architecture.handlers)} handlers",
                    'created_by': user_id,
                    'source': 'refactoring_analysis',
                    'suggestions': suggestions,
                    'handlers_analyzed': len(architecture.handlers),
                    'flows_analyzed': len(architecture.flows)
                }

                import json
                suggestions_yaml = f"""# Refactoring Suggestions Report
# Generated: {datetime.now().isoformat()}
# User: {user_id}

suggestions:
{json.dumps(suggestions, indent=2, ensure_ascii=False)}

architecture_summary:
  handlers: {len(architecture.handlers)}
  flows: {len(architecture.flows)}
  complexity_metrics: {architecture.complexity_metrics}
"""

                storage.save_schema(suggestions_yaml, 'audit', 'refactoring_suggestions', suggestions_metadata)

            except Exception as e:
                logger.warning("Failed to save refactoring suggestions", error=str(e))

            # Generate suggestions report
            report = f"💡 **Рекомендації з Рефакторингу**\n\n"

            # Complexity issues
            if suggestions['complexity_issues']:
                report += f"🔴 **Проблеми складності ({len(suggestions['complexity_issues'])}):**\n"
                for issue in suggestions['complexity_issues'][:3]:
                    report += f"• {issue['handler']}: {issue['issue']}\n"
                    report += f"  💡 {issue['recommendation']}\n"
                report += "\n"

            # Flow improvements
            if suggestions['flow_improvements']:
                report += f"🔗 **Покращення потоків:**\n"
                for improvement in suggestions['flow_improvements']:
                    report += f"• {improvement['issue']}\n"
                    report += f"  💡 {improvement['recommendation']}\n"
                report += "\n"

            # Modernization opportunities
            if suggestions['modernization_opportunities']:
                report += f"🚀 **Можливості модернізації:**\n"
                for opportunity in suggestions['modernization_opportunities']:
                    report += f"• {opportunity['opportunity']}\n"
                    report += f"  💡 {opportunity['recommendation']}\n"
                report += "\n"

            if not any(suggestions.values()):
                report += "🎉 **Чудово!** Архітектура бота виглядає добре організованою."

            await status_msg.edit_text(report)

        elif command_text.lower().startswith("generate"):
            await status_msg.edit_text("🔄 **Генерую DRACON схему...**\n\nЗворотний інжиніринг коду в YAML...")

            architecture = await engineer.analyze_bot_architecture()
            schema_yaml = await engineer.generate_dracon_schema(architecture, "Reverse Engineered Bot")

            # Automatically save to reverse directory
            try:
                metadata = {
                    'name': 'reverse_engineered_bot',
                    'description': f"Reverse engineered DRACON schema with {len(architecture.handlers)} handlers and {len(architecture.flows)} flows",
                    'created_by': user_id,
                    'source': 'reverse_engineering',
                    'handlers_count': len(architecture.handlers),
                    'flows_count': len(architecture.flows),
                    'complexity_metrics': architecture.complexity_metrics
                }

                file_path, filename = storage.save_schema(schema_yaml, 'reverse', 'bot_architecture', metadata)

                # Also save analysis metadata
                analysis_metadata = {
                    'analysis_type': 'full_reverse_engineering',
                    'handlers': [{'name': h.name, 'type': h.handler_type, 'complexity': h.complexity_score} for h in architecture.handlers],
                    'flows': [{'from': f.from_handler, 'to': f.to_handler, 'type': f.trigger_type} for f in architecture.flows],
                    'suggestions_count': len((await engineer.suggest_refactoring(architecture))['complexity_issues']),
                    'created_by': user_id,
                    'timestamp': datetime.now().isoformat()
                }

                analysis_path = file_path.replace('.yaml', '_analysis.json')
                with open(analysis_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(analysis_metadata, f, indent=2, ensure_ascii=False)

                # Send schema with save confirmation
                await status_msg.edit_text(f"✅ **DRACON схема згенерована та збережена!**\n\n"
                                         f"📊 Вузлів: {len(architecture.handlers) + 2}\n"
                                         f"🔗 Зв'язків: {len(architecture.flows)}\n"
                                         f"💾 Збережено: `drn/reverse/{filename}`\n"
                                         f"📋 Готова для аналізу та модернізації")

            except Exception as e:
                logger.error("Failed to save reverse engineered schema", error=str(e))
                await status_msg.edit_text(f"✅ **DRACON схема згенерована!**\n\n"
                                         f"📊 Вузлів: {len(architecture.handlers) + 2}\n"
                                         f"🔗 Зв'язків: {len(architecture.flows)}\n"
                                         f"⚠️ Помилка збереження: {str(e)}")

            # Send YAML content
            await message.reply_text(
                f"📋 **Згенерована DRACON схема:**\n\n```yaml\n{schema_yaml}\n```",
                parse_mode="Markdown"
            )

            # Suggest next steps with file operations
            await message.reply_text(
                "🔧 **Наступні кроки:**\n\n"
                "• `/dracon list reverse` - Переглянути збережені схеми\n"
                f"• `/dracon load reverse {filename}` - Завантажити схему\n"
                "• `/dracon analyze` - Аналізувати завантажену схему\n"
                "• `/dracon save build my_framework` - Зберегти як фреймворк\n"
                "• `/refactor suggest` - Отримати рекомендації з покращення"
            )

        else:
            # Default: comprehensive analysis
            await status_msg.edit_text("🔄 **Повний аналіз архітектури...**\n\nПарсинг файлів, аналіз логіки, Claude аналіз...")

            architecture = await engineer.analyze_bot_architecture()

            # Generate comprehensive report
            report = f"📊 **Аналіз Архітектури Бота**\n\n"

            # Basic stats
            report += f"**Основна статистика:**\n"
            report += f"• Handlers: {len(architecture.handlers)}\n"
            report += f"• Логічних потоків: {len(architecture.flows)}\n"
            report += f"• Точок входу: {len(architecture.entry_points)}\n"
            report += f"• Середня складність: {architecture.complexity_metrics['average_complexity']}\n\n"

            # Architecture quality
            quality_score = "Добра" if len(architecture.orphaned_handlers) < 3 else "Потребує покращення"
            report += f"**Якість архітектури:** {quality_score}\n\n"

            # Issues summary
            error_handling_ratio = architecture.complexity_metrics['has_error_handling'] / len(architecture.handlers)
            if error_handling_ratio < 0.5:
                report += f"⚠️ **Попередження:** Низький рівень обробки помилок ({error_handling_ratio:.0%})\n"

            if architecture.orphaned_handlers:
                report += f"⚠️ **Попередження:** {len(architecture.orphaned_handlers)} відокремлених handlers\n"

            report += f"\n💡 **Рекомендації:**\n"
            report += f"• Використайте `/refactor generate` для створення DRACON схеми\n"
            report += f"• Використайте `/refactor suggest` для детальних рекомендацій\n"
            report += f"• Розгляньте модернізацію складних handlers"

            await status_msg.edit_text(report)

            # Send Claude analysis if available
            if architecture.claude_analysis and len(architecture.claude_analysis) > 100:
                claude_report = f"🤖 **Аналіз Claude:**\n\n{architecture.claude_analysis}"

                if len(claude_report) > 4096:
                    chunks = [claude_report[i:i+4000] for i in range(0, len(claude_report), 4000)]
                    for i, chunk in enumerate(chunks):
                        await message.reply_text(chunk)
                        if i < len(chunks) - 1:
                            await asyncio.sleep(1)
                else:
                    await message.reply_text(claude_report)

        logger.info("Refactor analysis completed",
                   user_id=user_id,
                   handlers_count=len(architecture.handlers),
                   flows_count=len(architecture.flows))

    except Exception as e:
        logger.error("Error in refactor command", error=str(e), user_id=user_id, exc_info=True)
        error_msg = f"❌ **Помилка рефакторинга:**\n\n`{str(e)}`"

        try:
            await message.reply_text(error_msg)
        except:
            # Fallback if message fails
            pass



async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias for schedules_command - manage scheduled tasks."""
    await schedules_command(update, context)


async def claude_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /claude_status - показати поточний статус Claude CLI."""
    user_id = update.effective_user.id
    message = get_effective_message(update)

    logger.info("Claude status command started", user_id=user_id)

    try:
        # Отримати availability monitor
        availability_monitor = context.bot_data.get("claude_availability_monitor")
        if not availability_monitor:
            await message.reply_text(
                "❌ **Моніторинг Claude недоступний**\n\n"
                "Система моніторингу не налаштована.",
                parse_mode=None
            )
            return

        # Показати статус "перевіряємо"
        status_msg = await message.reply_text(
            await t(context, user_id, "claude_status.checking"),
            parse_mode=None
        )

        # Виконати детальну перевірку
        is_available, details = await availability_monitor.check_availability_with_details()

        # Побудувати детальне повідомлення
        status_lines = []
        status_lines.append(await t(context, user_id, "claude_status.title"))
        status_lines.append("")

        # Поточний статус
        current_status = await t(context, user_id, "claude_status.current_status")
        status_message = details.get("status_message", "❓ Невідомо")
        status_lines.append(f"**{current_status}** {status_message}")

        # Остання перевірка
        last_check = await t(context, user_id, "claude_status.last_check")
        check_time = details.get("last_check")
        if check_time:
            from zoneinfo import ZoneInfo
            kyiv_time = check_time.astimezone(ZoneInfo("Europe/Kyiv"))
            status_lines.append(f"**{last_check}** {kyiv_time.strftime('%H:%M:%S')}")

        # Прогноз відновлення
        if "estimated_recovery" in details:
            recovery_text = await t(context, user_id, "claude_status.recovery_prediction")
            status_lines.append(f"**{recovery_text}** {details['estimated_recovery']}")

        status_lines.append("")
        status_lines.append(await t(context, user_id, "claude_status.check_again"))

        # Створити кнопки
        keyboard = [
            [
                InlineKeyboardButton("🔄 Оновити", callback_data="claude_status:refresh"),
                InlineKeyboardButton("📊 Історія", callback_data="claude_status:history")
            ],
            [
                InlineKeyboardButton("🔔 Сповіщення", callback_data="claude_status:notifications"),
                InlineKeyboardButton("⚙️ Налаштування", callback_data="claude_status:settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        full_message = "\n".join(status_lines)

        await status_msg.edit_text(full_message, reply_markup=reply_markup, parse_mode=None)

        logger.info("Claude status displayed", user_id=user_id, is_available=is_available)

    except Exception as e:
        logger.error("Error in claude_status command", error=str(e), user_id=user_id, exc_info=True)
        await safe_critical_error(message, context, e, "claude_status")


async def claude_notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /claude_notifications - керування сповіщеннями про статус."""
    user_id = update.effective_user.id
    message = get_effective_message(update)

    logger.info("Claude notifications command started", user_id=user_id)

    try:
        settings: Settings = context.bot_data["settings"]

        # Перевірити поточні налаштування
        notifications_enabled = settings.claude_availability.enabled
        notify_chats = settings.claude_availability.notify_chat_ids
        check_interval = settings.claude_availability.check_interval_seconds

        # Побудувати повідомлення
        status_lines = []
        status_lines.append("⚙️ **Налаштування сповіщень Claude**")
        status_lines.append("")

        if notifications_enabled:
            status_lines.append("🔔 **Статус:** ✅ Увімкнено")
        else:
            status_lines.append("🔔 **Статус:** ❌ Вимкнено")

        if notify_chats:
            chat_count = len(notify_chats)
            status_lines.append(f"📢 **Групи сповіщень:** {chat_count} налаштовано")
        else:
            status_lines.append("📢 **Групи сповіщень:** Не налаштовано")

        status_lines.append(f"⏰ **Інтервал перевірки:** {check_interval // 60} хвилин")
        status_lines.append("")

        # Додати інформацію про можливості
        status_lines.append("💡 **Можливості сповіщень:**")
        status_lines.append("• Автоматичні повідомлення про недоступність")
        status_lines.append("• Сповіщення про відновлення роботи")
        status_lines.append("• Прогноз часу відновлення")
        status_lines.append("• Режим DND (без сповіщень вночі)")

        # Створити кнопки
        keyboard = []

        if notifications_enabled:
            keyboard.append([InlineKeyboardButton("❌ Вимкнути сповіщення", callback_data="claude_notifications:disable")])
        else:
            keyboard.append([InlineKeyboardButton("✅ Увімкнути сповіщення", callback_data="claude_notifications:enable")])

        keyboard.extend([
            [
                InlineKeyboardButton("📊 Історія", callback_data="claude_notifications:history"),
                InlineKeyboardButton("🔄 Статус", callback_data="claude_status:refresh")
            ],
            [InlineKeyboardButton("⬅️ Назад", callback_data="claude_status:main")]
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        full_message = "\n".join(status_lines)

        await message.reply_text(full_message, reply_markup=reply_markup, parse_mode=None)

        logger.info("Claude notifications settings displayed", user_id=user_id, enabled=notifications_enabled)

    except Exception as e:
        logger.error("Error in claude_notifications command", error=str(e), user_id=user_id, exc_info=True)
        await safe_critical_error(message, context, e, "claude_notifications")


async def claude_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /claude_history - історія доступності за 24 години."""
    user_id = update.effective_user.id
    message = get_effective_message(update)

    logger.info("Claude history command started", user_id=user_id)

    try:
        # Показати повідомлення "завантаження"
        status_msg = await message.reply_text("📊 Завантажую історію доступності...", parse_mode=None)

        # Читати файл transitions.jsonl
        from pathlib import Path
        import json
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        transitions_file = Path("./data/transitions.jsonl")

        if not transitions_file.exists():
            await status_msg.edit_text(
                "📊 **Історія доступності Claude**\n\n"
                "❌ Файл історії не знайдено.\n"
                "Моніторинг буде створювати історію з наступних перевірок.",
                parse_mode=None
            )
            return

        # Читати останні 24 години
        now = datetime.now(ZoneInfo("UTC"))
        cutoff_time = now - timedelta(hours=24)

        transitions = []
        try:
            with open(transitions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        record_time = datetime.fromisoformat(record['timestamp'])
                        if record_time >= cutoff_time:
                            transitions.append(record)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as e:
            logger.error(f"Error reading transitions file: {e}")

        # Побудувати звіт
        report_lines = []
        report_lines.append("📊 **Історія доступності Claude за 24 години**")
        report_lines.append("")

        if not transitions:
            report_lines.append("ℹ️ Змін статусу за останні 24 години не було.")
        else:
            report_lines.append(f"📈 **Всього змін статусу:** {len(transitions)}")
            report_lines.append("")

            # Показати останні 5 переходів
            recent_transitions = sorted(transitions, key=lambda x: x['timestamp'], reverse=True)[:5]

            report_lines.append("🕒 **Останні зміни:**")
            for i, trans in enumerate(recent_transitions):
                try:
                    trans_time = datetime.fromisoformat(trans['timestamp'])
                    kyiv_time = trans_time.astimezone(ZoneInfo("Europe/Kyiv"))

                    from_state = trans.get('from', 'unknown')
                    to_state = trans.get('to', 'unknown')

                    # Перекласти статуси
                    state_translations = {
                        'available': '🟢 доступний',
                        'limited': '⏳ обмежений',
                        'unavailable': '🔴 недоступний',
                        'auth_error': '🔑 помилка авторизації'
                    }

                    from_emoji = state_translations.get(from_state, f"❓ {from_state}")
                    to_emoji = state_translations.get(to_state, f"❓ {to_state}")

                    time_str = kyiv_time.strftime('%H:%M')
                    report_lines.append(f"{i+1}. **{time_str}** {from_emoji} → {to_emoji}")

                    # Додати тривалість якщо є
                    if 'duration_unavailable' in trans and trans['duration_unavailable']:
                        duration_minutes = int(trans['duration_unavailable'] / 60)
                        if duration_minutes > 0:
                            report_lines.append(f"   ⏱️ _Недоступність: {duration_minutes} хв_")

                except (ValueError, KeyError) as e:
                    logger.warning(f"Error processing transition: {e}")
                    continue

        report_lines.append("")
        report_lines.append("🔄 Використайте /claude_status для поточного статусу")

        # Створити кнопки
        keyboard = [
            [
                InlineKeyboardButton("🔄 Оновити", callback_data="claude_status:history"),
                InlineKeyboardButton("📊 Статус", callback_data="claude_status:refresh")
            ],
            [InlineKeyboardButton("⬅️ Назад", callback_data="claude_status:main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        full_report = "\n".join(report_lines)

        await status_msg.edit_text(full_report, reply_markup=reply_markup, parse_mode=None)

        logger.info("Claude history displayed", user_id=user_id, transitions_count=len(transitions))

    except Exception as e:
        logger.error("Error in claude_history command", error=str(e), user_id=user_id, exc_info=True)
        await safe_critical_error(message, context, e, "claude_history")
