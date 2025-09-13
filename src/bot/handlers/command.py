"""Command handlers for bot operations."""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ...claude.facade import ClaudeIntegration
from ...config.settings import Settings
from ...security.audit import AuditLogger
from ...security.validators import SecurityValidator
from ...localization.helpers import get_user_text

logger = structlog.get_logger()


async def get_localized_text(context, user_id, key, **kwargs):
    """Helper to get localized text with fallback."""
    localization = context.bot_data.get("localization")
    user_language_storage = context.bot_data.get("user_language_storage")
    
    if localization and user_language_storage:
        return await get_user_text(localization, user_language_storage, user_id, key, **kwargs)
    elif localization:
        return localization.get(key, language=None, **kwargs) or f"[{key}]"
    else:
        return f"[{key}]"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    
    # Get localization components from bot data
    localization = context.bot_data.get("localization")
    user_language_storage = context.bot_data.get("user_language_storage")
    
    if localization and user_language_storage:
        # Build localized welcome message
        welcome_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.welcome", name=user.first_name)
        description_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.description")
        available_commands_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.available_commands")
        
        help_cmd_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.help_cmd")
        new_cmd_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.new_cmd")
        ls_cmd_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.ls_cmd")
        cd_cmd_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.cd_cmd")
        projects_cmd_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.projects_cmd")
        status_cmd_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.status_cmd")
        actions_cmd_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.actions_cmd")
        git_cmd_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.git_cmd")
        
        quick_start_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.quick_start")
        quick_start_1_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.quick_start_1")
        quick_start_2_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.quick_start_2")
        quick_start_3_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.quick_start_3")
        
        security_note_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.security_note")
        usage_note_text = await get_user_text(localization, user_language_storage, user.id, "commands.start.usage_note")
        
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
        show_projects_text = await get_user_text(localization, user_language_storage, user.id, "buttons.show_projects")
        get_help_text = await get_user_text(localization, user_language_storage, user.id, "buttons.get_help")
        new_session_text = await get_user_text(localization, user_language_storage, user.id, "buttons.new_session")
        check_status_text = await get_user_text(localization, user_language_storage, user.id, "buttons.check_status")
        language_settings_text = await get_user_text(localization, user_language_storage, user.id, "buttons.language_settings")
        
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
            f"👋 Welcome to Claude Code Telegram Bot, {user.first_name}!\n\n"
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

    await update.message.reply_text(
        welcome_message, parse_mode=None, reply_markup=reply_markup
    )

    # Log command
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")
    if audit_logger:
        await audit_logger.log_command(
            user_id=user.id, command="start", args=[], success=True
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with localization."""
    user_id = update.effective_user.id
    
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
            help_text = await get_localized_text(context, user_id, "commands.help.title")
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

    await update.message.reply_text(help_text, parse_mode=None)


async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command."""
    settings: Settings = context.bot_data["settings"]

    # For now, we'll use a simple session concept
    # This will be enhanced when we implement proper session management

    # Get current directory (default to approved directory)
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Clear any existing session data
    context.user_data["claude_session_id"] = None
    context.user_data["session_started"] = True

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 Start Coding", callback_data="action:start_coding"
            ),
            InlineKeyboardButton(
                "📁 Change Project", callback_data="action:show_projects"
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 Quick Actions", callback_data="action:quick_actions"
            ),
            InlineKeyboardButton("❓ Help", callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🆕 **New Claude Code Session**\n\n"
        f"📂 Working directory: `{relative_path}/`\n\n"
        f"Ready to help you code! Send me a message to get started, or use the buttons below:",
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def continue_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /continue command with optional prompt."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Parse optional prompt from command arguments
    prompt = " ".join(context.args) if context.args else None

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        if not claude_integration:
            await update.message.reply_text(
                "❌ **Claude Integration Not Available**\n\n"
                "Claude integration is not properly configured."
            )
            return

        # Check if there's an existing session in user context
        claude_session_id = context.user_data.get("claude_session_id")

        if claude_session_id:
            # We have a session in context, continue it directly
            status_msg = await update.message.reply_text(
                f"🔄 **Continuing Session**\n\n"
                f"Session ID: `{claude_session_id[:8]}...`\n"
                f"Directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
                f"{'Processing your message...' if prompt else 'Continuing where you left off...'}",
                parse_mode=None,
            )

            # Continue with the existing session
            claude_response = await claude_integration.run_command(
                prompt=prompt or "",
                working_directory=current_dir,
                user_id=user_id,
                session_id=claude_session_id,
            )
        else:
            # No session in context, try to find the most recent session
            status_msg = await update.message.reply_text(
                "🔍 **Looking for Recent Session**\n\n"
                "Searching for your most recent session in this directory...",
                parse_mode=None,
            )

            claude_response = await claude_integration.continue_session(
                user_id=user_id,
                working_directory=current_dir,
                prompt=prompt,
            )

        if claude_response:
            # Update session ID in context
            context.user_data["claude_session_id"] = claude_response.session_id

            # Delete status message and send response
            await status_msg.delete()

            # Format and send Claude's response
            from ..utils.formatting import ResponseFormatter

            formatter = ResponseFormatter()
            formatted_messages = formatter.format_claude_response(claude_response)

            for msg in formatted_messages:
                await update.message.reply_text(
                    msg.content,
                    parse_mode=None,
                    reply_markup=msg.reply_markup,
                )

            # Log successful continue
            if audit_logger:
                await audit_logger.log_command(
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
                f"Directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
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
            if "status_msg" in locals():
                await status_msg.delete()
        except Exception:
            pass

        # Send error response
        await update.message.reply_text(
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
            await audit_logger.log_command(
                user_id=user_id,
                command="continue",
                args=context.args or [],
                success=False,
            )


async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ls command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

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
        relative_path = current_dir.relative_to(settings.approved_directory)
        if not items:
            message = f"📂 `{relative_path}/`\n\n_(empty directory)_"
        else:
            message = f"📂 `{relative_path}/`\n\n"

            # Limit items shown to prevent message being too long
            max_items = 50
            if len(items) > max_items:
                shown_items = items[:max_items]
                message += "\n".join(shown_items)
                message += f"\n\n_... and {len(items) - max_items} more items_"
            else:
                message += "\n".join(items)

        # Add navigation buttons if not at root
        keyboard = []
        if current_dir != settings.approved_directory:
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

        await update.message.reply_text(
            message, parse_mode=None, reply_markup=reply_markup
        )

        # Log successful command
        if audit_logger:
            await audit_logger.log_command(user_id, "ls", [], True)

    except Exception as e:
        error_msg = f"❌ Error listing directory: {str(e)}"
        await update.message.reply_text(error_msg)

        # Log failed command
        if audit_logger:
            await audit_logger.log_command(user_id, "ls", [], False)

        logger.error("Error in list_files command", error=str(e), user_id=user_id)


async def change_directory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cd command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    security_validator: SecurityValidator = context.bot_data.get("security_validator")
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    # Parse arguments
    if not context.args:
        await update.message.reply_text(
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
        "current_directory", settings.approved_directory
    )

    try:
        # Validate path using security validator
        if security_validator:
            valid, resolved_path, error = security_validator.validate_path(
                target_path, current_dir
            )

            if not valid:
                await update.message.reply_text(f"❌ **Access Denied**\n\n{error}")

                # Log security violation
                if audit_logger:
                    await audit_logger.log_security_violation(
                        user_id=user_id,
                        violation_type="path_traversal_attempt",
                        details=f"Attempted path: {target_path}",
                        severity="medium",
                    )
                return
        else:
            # Fallback validation without security validator
            if target_path == "/":
                resolved_path = settings.approved_directory
            elif target_path == "..":
                resolved_path = current_dir.parent
                if not str(resolved_path).startswith(str(settings.approved_directory)):
                    resolved_path = settings.approved_directory
            else:
                resolved_path = current_dir / target_path
                resolved_path = resolved_path.resolve()

        # Check if directory exists and is actually a directory
        if not resolved_path.exists():
            await update.message.reply_text(
                f"❌ **Directory Not Found**\n\n`{target_path}` does not exist."
            )
            return

        if not resolved_path.is_dir():
            await update.message.reply_text(
                f"❌ **Not a Directory**\n\n`{target_path}` is not a directory."
            )
            return

        # Update current directory in user data
        context.user_data["current_directory"] = resolved_path

        # Clear Claude session on directory change
        context.user_data["claude_session_id"] = None

        # Send confirmation
        relative_path = resolved_path.relative_to(settings.approved_directory)
        await update.message.reply_text(
            f"✅ **Directory Changed**\n\n"
            f"📂 Current directory: `{relative_path}/`\n\n"
            f"🔄 Claude session cleared. Send a message to start coding in this directory.",
            parse_mode=None,
        )

        # Log successful command
        if audit_logger:
            await audit_logger.log_command(user_id, "cd", [target_path], True)

    except Exception as e:
        error_msg = f"❌ **Error changing directory**\n\n{str(e)}"
        await update.message.reply_text(error_msg, parse_mode=None)

        # Log failed command
        if audit_logger:
            await audit_logger.log_command(user_id, "cd", [target_path], False)

        logger.error("Error in change_directory command", error=str(e), user_id=user_id)


async def print_working_directory(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /pwd command."""
    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    relative_path = current_dir.relative_to(settings.approved_directory)
    absolute_path = str(current_dir)

    # Add quick navigation buttons
    keyboard = [
        [
            InlineKeyboardButton("📁 List Files", callback_data="action:ls"),
            InlineKeyboardButton("📋 Projects", callback_data="action:show_projects"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📍 **Current Directory**\n\n"
        f"Relative: `{relative_path}/`\n"
        f"Absolute: `{absolute_path}`",
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def show_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /projects command."""
    settings: Settings = context.bot_data["settings"]

    try:
        # Get directories in approved directory (these are "projects")
        projects = []
        for item in sorted(settings.approved_directory.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                projects.append(item.name)

        if not projects:
            await update.message.reply_text(
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

        await update.message.reply_text(
            f"📁 **Available Projects**\n\n"
            f"{project_list}\n\n"
            f"Click a project below to navigate to it:",
            parse_mode=None,
            reply_markup=reply_markup,
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error loading projects: {str(e)}")
        logger.error("Error in show_projects command", error=str(e))


async def session_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    # Get session info
    claude_session_id = context.user_data.get("claude_session_id")
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Get rate limiter info if available
    rate_limiter = context.bot_data.get("rate_limiter")
    usage_info = ""
    if rate_limiter:
        try:
            user_status = rate_limiter.get_user_status(user_id)
            cost_usage = user_status.get("cost_usage", {})
            current_cost = cost_usage.get("current", 0.0)
            cost_limit = cost_usage.get("limit", settings.claude_max_cost_per_user)
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
        f"🕐 Last Update: {update.message.date.strftime('%H:%M:%S UTC')}",
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

    await update.message.reply_text(
        "\n".join(status_lines), parse_mode=None, reply_markup=reply_markup
    )


async def export_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command."""
    user_id = update.effective_user.id
    features = context.bot_data.get("features")

    # Check if session export is available
    session_exporter = features.get_session_export() if features else None

    if not session_exporter:
        await update.message.reply_text(
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
    claude_session_id = context.user_data.get("claude_session_id")

    if not claude_session_id:
        await update.message.reply_text(
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

    await update.message.reply_text(
        "📤 **Export Session**\n\n"
        f"Ready to export session: `{claude_session_id[:8]}...`\n\n"
        "**Choose export format:**",
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def end_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /end command to terminate the current session."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    # Check if there's an active session
    claude_session_id = context.user_data.get("claude_session_id")

    if not claude_session_id:
        await update.message.reply_text(
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
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Clear session data
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

    await update.message.reply_text(
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
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("quick_actions"):
        await update.message.reply_text(
            "❌ **Quick Actions Disabled**\n\n"
            "Quick actions feature is not enabled.\n"
            "Contact your administrator to enable this feature."
        )
        return

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        quick_action_manager = features.get_quick_actions()
        if not quick_action_manager:
            await update.message.reply_text(
                "❌ **Quick Actions Unavailable**\n\n"
                "Quick actions service is not available."
            )
            return

        # Get context-aware actions
        actions = await quick_action_manager.get_suggestions(
            session_data={"working_directory": str(current_dir), "user_id": user_id}
        )

        if not actions:
            await update.message.reply_text(
                "🤖 **No Actions Available**\n\n"
                "No quick actions are available for the current context.\n\n"
                "**Try:**\n"
                "• Navigating to a project directory with `/cd`\n"
                "• Creating some code files\n"
                "• Starting a Claude session with `/new`"
            )
            return

        # Create inline keyboard with localization
        user_id = update.effective_user.id
        localization = context.bot_data.get("localization")
        user_language_storage = context.bot_data.get("user_language_storage")
        user_lang = None
        
        if user_language_storage:
            try:
                user_lang = await user_language_storage.get_user_language(user_id)
            except:
                pass
        
        keyboard = quick_action_manager.create_inline_keyboard(
            actions, columns=2, localization=localization, user_lang=user_lang
        )

        # Get localized title for quick actions
        title_text = await get_localized_text(context, user_id, "quick_actions.title")
        
        relative_path = current_dir.relative_to(settings.approved_directory)
        message_text = f"{title_text}\n\n📂 Context: `{relative_path}/`"
        
        await update.message.reply_text(
            message_text,
            parse_mode=None,
            reply_markup=keyboard,
        )

    except Exception as e:
        error_text = await get_localized_text(context, user_id, "errors.quick_actions_unavailable")
        await update.message.reply_text(error_text, parse_mode=None)
        logger.error("Error in quick_actions command", error=str(e), user_id=user_id)


async def git_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /git command to show git repository information."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("git"):
        await update.message.reply_text(
            "❌ **Git Integration Disabled**\n\n"
            "Git integration feature is not enabled.\n"
            "Contact your administrator to enable this feature."
        )
        return

    # Get current directory
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        git_integration = features.get_git_integration()
        if not git_integration:
            await update.message.reply_text(
                "❌ **Git Integration Unavailable**\n\n"
                "Git integration service is not available."
            )
            return

        # Check if current directory is a git repository
        if not (current_dir / ".git").exists():
            await update.message.reply_text(
                f"📂 **Not a Git Repository**\n\n"
                f"Current directory `{current_dir.relative_to(settings.approved_directory)}/` is not a git repository.\n\n"
                f"**Options:**\n"
                f"• Navigate to a git repository with `/cd`\n"
                f"• Initialize a new repository (ask Claude to help)\n"
                f"• Clone an existing repository (ask Claude to help)"
            )
            return

        # Get git status
        git_status = await git_integration.get_status(current_dir)

        # Format status message
        relative_path = current_dir.relative_to(settings.approved_directory)
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

        await update.message.reply_text(
            status_message, parse_mode=None, reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(f"❌ **Git Error**\n\n{str(e)}")
        logger.error("Error in git_command", error=str(e), user_id=user_id)


def _format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}B"
        size /= 1024
    return f"{size:.1f}TB"
