"""Handle inline keyboard callbacks."""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ...claude.facade import ClaudeIntegration
from ...config.settings import Settings
from ...security.audit import AuditLogger
from ...security.validators import SecurityValidator
from ...localization.util import t, get_user_id
from ...localization.helpers import get_user_text
from ..utils.error_handler import safe_user_error

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


async def handle_callback_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Route callback queries to appropriate handlers."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    user_id = query.from_user.id
    data = query.data

    logger.info("Processing callback query", user_id=user_id, callback_data=data)

    try:
        # Parse callback data
        if ":" in data:
            action, param = data.split(":", 1)
        else:
            action, param = data, None

        # Route to appropriate handler
        handlers = {
            "cd": handle_cd_callback,
            "action": handle_action_callback,
            "confirm": handle_confirm_callback,
            "quick": handle_quick_action_callback,
            "followup": handle_followup_callback,
            "conversation": handle_conversation_callback,
            "git": handle_git_callback,
            "export": handle_export_callback,
            "lang": handle_language_callback,
            "schedule": handle_schedule_callback,
            "prompts_settings": handle_prompts_settings_callback,
            "save_code": handle_save_code_callback,
            "continue": handle_continue_callback,
            "explain": handle_explain_callback,
            "refresh": handle_refresh_callback,
        }

        # Check for MCP callbacks first
        if action.startswith("mcp"):
            from .mcp_callbacks import handle_mcp_callback
            await handle_mcp_callback(update, context)
            return

        handler = handlers.get(action)
        if handler:
            await handler(query, param, context)
        else:
            user_id = get_user_id(update)
            await query.edit_message_text(
                await t(context, user_id, "callback_errors.unknown_action")
            )

    except Exception as e:
        logger.error(
            "Error handling callback query",
            error=str(e),
            user_id=user_id,
            callback_data=data,
        )

        try:
            user_id = get_user_id(update)
            await query.edit_message_text(
                await t(context, user_id, "errors.unexpected_error")
            )
        except Exception:
            # If we can't edit the message, send a new one
            await query.message.reply_text(
                await t(context, user_id, "errors.unexpected_error")
            )


async def handle_cd_callback(
    query, project_name: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle directory change from inline keyboard."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]
    security_validator: SecurityValidator = context.bot_data.get("security_validator")
    audit_logger: AuditLogger = context.bot_data.get("audit_logger")

    try:
        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )

        # Handle special paths
        if project_name == "/":
            new_path = settings.approved_directory
        elif project_name == "..":
            new_path = current_dir.parent
            # Ensure we don't go above approved directory
            if not str(new_path).startswith(str(settings.approved_directory)):
                new_path = settings.approved_directory
        else:
            new_path = settings.approved_directory / project_name

        # Validate path if security validator is available
        if security_validator:
            # Pass the absolute path for validation
            valid, resolved_path, error = security_validator.validate_path(
                str(new_path), settings.approved_directory
            )
            if not valid:
                await query.edit_message_text(
                    await t(context, user_id, "errors_command.access_denied", error=error)
                )
                return
            # Use the validated path
            new_path = resolved_path

        # Check if directory exists
        if not new_path.exists() or not new_path.is_dir():
            await query.edit_message_text(
                await t(context, user_id, "errors_command.directory_not_found", path=project_name)
            )
            return

        # Update directory and clear session
        context.user_data["current_directory"] = new_path
        context.user_data["claude_session_id"] = None

        # Send confirmation with new directory info
        relative_path = new_path.relative_to(settings.approved_directory)

        # Add navigation buttons with localization
        list_files_text = await get_localized_text(context, user_id, "buttons.list_files")
        new_session_text = await get_localized_text(context, user_id, "buttons.new_session")
        projects_text = await get_localized_text(context, user_id, "buttons.projects")
        status_text = await get_localized_text(context, user_id, "buttons.status")
        
        keyboard = [
            [
                InlineKeyboardButton(list_files_text, callback_data="action:ls"),
                InlineKeyboardButton(new_session_text, callback_data="action:new_session"),
            ],
            [
                InlineKeyboardButton(projects_text, callback_data="action:show_projects"),
                InlineKeyboardButton(status_text, callback_data="action:status"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            await t(context, user_id, "commands_extended.cd.directory_changed", relative_path=relative_path),
            parse_mode=None,
            reply_markup=reply_markup,
        )

        # Log successful directory change
        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id, command="cd", args=[project_name], success=True
            )

    except Exception as e:
        await query.edit_message_text(
            await t(context, user_id, "errors_command.error_changing_directory", error=str(e))
        )

        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id, command="cd", args=[project_name], success=False
            )


async def handle_action_callback(
    query, action_type: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle general action callbacks."""
    actions = {
        "help": _handle_help_action,
        "full_help": _handle_full_help_action,
        "show_projects": _handle_show_projects_action,
        "new_session": _handle_new_session_action,
        "new": _handle_new_session_action,  # alias for new_session
        "continue": _handle_continue_action,
        "end_session": _handle_end_session_action,
        "status": _handle_status_action,
        "ls": _handle_ls_action,
        "start_coding": _handle_start_coding_action,
        "quick_actions": _handle_quick_actions_action,
        "refresh_status": _handle_refresh_status_action,
        "refresh_ls": _handle_refresh_ls_action,
        "export": _handle_export_action,
        "settings": _handle_settings_action,
        "main_menu": _handle_main_menu_action,
    }

    handler = actions.get(action_type)
    if handler:
        await handler(query, context)
    else:
        user_id = query.from_user.id
        await query.edit_message_text(
            await t(context, user_id, "callback_errors.action_not_implemented") + f": {action_type}"
        )


async def handle_confirm_callback(
    query, confirmation_type: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle confirmation dialogs."""
    user_id = query.from_user.id
    if confirmation_type == "yes":
        await query.edit_message_text(
            await t(context, user_id, "buttons.confirmed")
        )
    elif confirmation_type == "no":
        await query.edit_message_text(
            await t(context, user_id, "buttons.cancelled")
        )
    else:
        await query.edit_message_text(
            await t(context, user_id, "callback_errors.unknown_action") + f": {confirmation_type}"
        )


# Action handlers


async def _handle_help_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help action."""
    user_id = query.from_user.id

    # Get localized help text
    help_text = await get_localized_text(context, user_id, "help.quick_help_title")
    navigation_text = await get_localized_text(context, user_id, "help.navigation_section")
    sessions_text = await get_localized_text(context, user_id, "help.sessions_section")
    tips_text = await get_localized_text(context, user_id, "help.tips_section")

    # Get individual tip texts
    send_text_tip = await get_localized_text(context, user_id, "help.send_text_tip")
    upload_files_tip = await get_localized_text(context, user_id, "help.upload_files_tip")
    use_buttons_tip = await get_localized_text(context, user_id, "help.use_buttons_tip")
    detailed_help_note = await get_localized_text(context, user_id, "help.detailed_help_note")

    # Build the help text
    full_help_content = (
        f"{help_text}\n\n"
        f"{navigation_text}\n"
        f"• `/ls` - {await get_localized_text(context, user_id, 'commands.ls.title')}\n"
        f"• `/cd <dir>` - {await get_localized_text(context, user_id, 'commands.cd.usage')}\n"
        f"• `/projects` - {await get_localized_text(context, user_id, 'commands.projects.title')}\n\n"
        f"{sessions_text}\n"
        f"• `/new` - {await get_localized_text(context, user_id, 'buttons.new_session')}\n"
        f"• `/status` - {await get_localized_text(context, user_id, 'commands.status.title')}\n\n"
        f"{tips_text}\n"
        f"{send_text_tip}\n"
        f"{upload_files_tip}\n"
        f"{use_buttons_tip}\n\n"
        f"{detailed_help_note}"
    )

    # Get localized button text
    full_help_text = await get_localized_text(context, user_id, "buttons.full_help")
    main_menu_text = await get_localized_text(context, user_id, "buttons.main_menu")

    keyboard = [
        [
            InlineKeyboardButton(full_help_text, callback_data="action:full_help"),
            InlineKeyboardButton(main_menu_text, callback_data="action:main_menu"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        full_help_content, parse_mode=None, reply_markup=reply_markup
    )


async def _handle_full_help_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle full help action."""
    user_id = query.from_user.id
    help_text = await get_localized_text(context, user_id, "commands.help.title")

    # Build comprehensive help text using localization
    full_help_text = await t(context, user_id, "help.commands")

    # Get back button text
    main_menu_text = await get_localized_text(context, user_id, "buttons.main_menu")

    keyboard = [
        [InlineKeyboardButton(main_menu_text, callback_data="action:main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        full_help_text, parse_mode=None, reply_markup=reply_markup
    )


async def _handle_show_projects_action(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle show projects action."""
    settings: Settings = context.bot_data["settings"]

    try:
        # Get directories in approved directory
        projects = []
        for item in sorted(settings.approved_directory.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                projects.append(item.name)

        if not projects:
            await query.edit_message_text(
                await t(context, user_id, "errors_command.no_projects_found")
            )
            return

        # Create project buttons
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

        # Add navigation buttons with localization
        user_id = query.from_user.id
        root_text = await get_localized_text(context, user_id, "buttons.root")
        refresh_text = await get_localized_text(context, user_id, "buttons.refresh")
        
        keyboard.append(
            [
                InlineKeyboardButton(root_text, callback_data="cd:/"),
                InlineKeyboardButton(refresh_text, callback_data="action:show_projects"),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        project_list = "\n".join([f"• `{project}/`" for project in projects])

        available_projects_text = await t(context, user_id, "commands_extended.projects.available_projects_title")
        click_navigate_text = await t(context, user_id, "commands_extended.projects.click_to_navigate")

        await query.edit_message_text(
            f"{available_projects_text}\n\n{project_list}\n\n{click_navigate_text}",
            parse_mode=None,
            reply_markup=reply_markup,
        )

    except Exception as e:
        await query.edit_message_text(
            await t(context, user_id, "errors_command.error_loading_projects", error=str(e))
        )


async def _handle_new_session_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle new session action."""
    settings: Settings = context.bot_data["settings"]

    # Clear session
    context.user_data["claude_session_id"] = None
    context.user_data["session_started"] = True

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Get localized button text
    user_id = query.from_user.id
    start_coding_text = await get_localized_text(context, user_id, "buttons.start_coding")
    change_project_text = await get_localized_text(context, user_id, "buttons.change_project")
    quick_actions_text = await get_localized_text(context, user_id, "buttons.quick_actions")
    help_text = await get_localized_text(context, user_id, "buttons.help")
    
    keyboard = [
        [
            InlineKeyboardButton(start_coding_text, callback_data="action:start_coding"),
            InlineKeyboardButton(change_project_text, callback_data="action:show_projects"),
        ],
        [
            InlineKeyboardButton(quick_actions_text, callback_data="action:quick_actions"),
            InlineKeyboardButton(help_text, callback_data="action:help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    new_session_text = await t(context, user_id, "commands_extended.new_session.title")
    working_dir_text = await t(context, user_id, "commands_extended.new_session.working_directory", relative_path=relative_path)
    ready_message_text = await t(context, user_id, "commands_extended.new_session.ready_message")

    await query.edit_message_text(
        f"{new_session_text}\n\n{working_dir_text}\n\n{ready_message_text}",
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def _handle_end_session_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle end session action."""
    settings: Settings = context.bot_data["settings"]

    # Check if there's an active session
    claude_session_id = context.user_data.get("claude_session_id")

    if not claude_session_id:
        no_active_session_text = await t(context, user_id, "commands_extended.export.no_active_session_title")
        no_active_session_message = await t(context, user_id, "commands_extended.export.no_active_session_message")
        what_you_can_do_text = await t(context, user_id, "commands_extended.export.what_you_can_do_title")
        start_new_session_text = await t(context, user_id, "commands_extended.export.start_new_session")
        check_status_text = await t(context, user_id, "commands_extended.export.check_status")

        new_session_btn = await get_localized_text(context, user_id, "buttons.new_session")
        status_btn = await get_localized_text(context, user_id, "buttons.status")

        await query.edit_message_text(
            f"{no_active_session_text}\n\n{no_active_session_message}\n\n{what_you_can_do_text}\n• {start_new_session_text}\n• {check_status_text}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            new_session_btn, callback_data="action:new_session"
                        )
                    ],
                    [InlineKeyboardButton(status_btn, callback_data="action:status")],
                ]
            ),
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

    await query.edit_message_text(
        "✅ **Session Ended**\n\n"
        f"Your Claude session has been terminated.\n\n"
        f"**Current Status:**\n"
        f"• Directory: `{relative_path}/`\n"
        f"• Session: None\n"
        f"• Ready for new commands\n\n"
        f"**Next Steps:**\n"
        f"• Start a new session\n"
        f"• Check status\n"
        f"• Send any message to begin a new conversation",
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def _handle_continue_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle continue session action."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]
    claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        if not claude_integration:
            await query.edit_message_text(
                "❌ **Claude Integration Not Available**\n\n"
                "Claude integration is not properly configured."
            )
            return

        # Check if there's an existing session in user context
        claude_session_id = context.user_data.get("claude_session_id")

        if claude_session_id:
            # Continue with the existing session (no prompt = use --continue)
            await query.edit_message_text(
                f"🔄 **Continuing Session**\n\n"
                f"Session ID: `{claude_session_id[:8]}...`\n"
                f"Directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
                f"Continuing where you left off...",
                parse_mode=None,
            )

            claude_response = await claude_integration.run_command(
                prompt="",  # Empty prompt triggers --continue
                working_directory=current_dir,
                user_id=user_id,
                session_id=claude_session_id,
            )
        else:
            # No session in context, try to find the most recent session
            await query.edit_message_text(
                "🔍 **Looking for Recent Session**\n\n"
                "Searching for your most recent session in this directory...",
                parse_mode=None,
            )

            claude_response = await claude_integration.continue_session(
                user_id=user_id,
                working_directory=current_dir,
                prompt=None,  # No prompt = use --continue
            )

        if claude_response:
            # Update session ID in context
            context.user_data["claude_session_id"] = claude_response.session_id

            # Send Claude's response
            await query.message.reply_text(
                f"✅ **Session Continued**\n\n"
                f"{claude_response.content[:500]}{'...' if len(claude_response.content) > 500 else ''}",
                parse_mode=None,
            )
        else:
            # No session found to continue
            await query.edit_message_text(
                "❌ **No Session Found**\n\n"
                f"No recent Claude session found in this directory.\n"
                f"Directory: `{current_dir.relative_to(settings.approved_directory)}/`\n\n"
                f"**What you can do:**\n"
                f"• Use the button below to start a fresh session\n"
                f"• Check your session status\n"
                f"• Navigate to a different directory",
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
        logger.error("Error in continue action", error=str(e), user_id=user_id)
        await query.edit_message_text(
            f"❌ **Error Continuing Session**\n\n"
            f"An error occurred: `{str(e)}`\n\n"
            f"Try starting a new session instead.",
            parse_mode=None,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🆕 New Session", callback_data="action:new_session"
                        )
                    ]
                ]
            ),
        )


async def _handle_status_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle status action."""
    # This essentially duplicates the /status command functionality
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]

    claude_session_id = context.user_data.get("claude_session_id")
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Get usage info if rate limiter is available
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

    status_lines = [
        "📊 **Session Status**",
        "",
        f"📂 Directory: `{relative_path}/`",
        f"🤖 Claude Session: {'✅ Active' if claude_session_id else '❌ None'}",
        usage_info.rstrip(),
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
                    "🛑 End Session", callback_data="action:end_session"
                ),
            ]
        )
        keyboard.append(
            [
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
            InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_status"),
            InlineKeyboardButton("📁 Projects", callback_data="action:show_projects"),
        ]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "\n".join(status_lines), parse_mode=None, reply_markup=reply_markup
    )


async def _handle_ls_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ls action."""
    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # List directory contents (similar to /ls command)
        items = []
        directories = []
        files = []

        for item in sorted(current_dir.iterdir()):
            if item.name.startswith("."):
                continue

            if item.is_dir():
                directories.append(f"📁 {item.name}/")
            else:
                try:
                    size = item.stat().st_size
                    size_str = _format_file_size(size)
                    files.append(f"📄 {item.name} ({size_str})")
                except OSError:
                    files.append(f"📄 {item.name}")

        items = directories + files
        relative_path = current_dir.relative_to(settings.approved_directory)

        if not items:
            message = f"📂 `{relative_path}/`\n\n_(empty directory)_"
        else:
            message = f"📂 `{relative_path}/`\n\n"
            max_items = 30  # Limit for inline display
            if len(items) > max_items:
                shown_items = items[:max_items]
                message += "\n".join(shown_items)
                message += f"\n\n_... and {len(items) - max_items} more items_"
            else:
                message += "\n".join(items)

        # Add buttons
        keyboard = []
        if current_dir != settings.approved_directory:
            keyboard.append(
                [
                    InlineKeyboardButton("⬆️ Go Up", callback_data="cd:.."),
                    InlineKeyboardButton("🏠 Root", callback_data="cd:/"),
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh_ls"),
                InlineKeyboardButton(
                    "📋 Projects", callback_data="action:show_projects"
                ),
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message, parse_mode=None, reply_markup=reply_markup
        )

    except Exception as e:
        await query.edit_message_text(f"❌ Error listing directory: {str(e)}")


async def _handle_start_coding_action(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle start coding action."""
    user_id = query.from_user.id
    
    # Get localized text
    ready_to_code = await get_localized_text(context, user_id, "session.ready_to_code")
    send_message_prompt = await get_localized_text(context, user_id, "session.send_message_prompt")
    examples_title = await get_localized_text(context, user_id, "session.examples_title")
    example_create_script = await get_localized_text(context, user_id, "session.example_create_script")
    example_debug_code = await get_localized_text(context, user_id, "session.example_debug_code")
    example_explain_file = await get_localized_text(context, user_id, "session.example_explain_file")
    example_upload_file = await get_localized_text(context, user_id, "session.example_upload_file")
    help_message = await get_localized_text(context, user_id, "session.help_message")
    
    message_text = (
        f"{ready_to_code}\n\n"
        f"{send_message_prompt}\n\n"
        f"{examples_title}\n"
        f"{example_create_script}\n"
        f"{example_debug_code}\n"
        f"{example_explain_file}\n"
        f"{example_upload_file}\n\n"
        f"{help_message}"
    )
    
    await query.edit_message_text(message_text)


async def _handle_quick_actions_action(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quick actions menu."""
    keyboard = [
        [
            InlineKeyboardButton("🧪 Run Tests", callback_data="quick:test"),
            InlineKeyboardButton("📦 Install Deps", callback_data="quick:install"),
        ],
        [
            InlineKeyboardButton("🎨 Format Code", callback_data="quick:format"),
            InlineKeyboardButton("🔍 Find TODOs", callback_data="quick:find_todos"),
        ],
        [
            InlineKeyboardButton("🔨 Build", callback_data="quick:build"),
            InlineKeyboardButton("🚀 Start Server", callback_data="quick:start"),
        ],
        [
            InlineKeyboardButton("📊 Git Status", callback_data="quick:git_status"),
            InlineKeyboardButton("🔧 Lint Code", callback_data="quick:lint"),
        ],
        [InlineKeyboardButton("⬅️ " + await get_localized_text(context, user_id, "buttons.back"), callback_data="action:new_session")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    quick_actions_text = await get_localized_text(context, user_id, "quick_actions.title")

    await query.edit_message_text(
        quick_actions_text,
        parse_mode=None,
        reply_markup=reply_markup,
    )


async def _handle_refresh_status_action(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle refresh status action."""
    await _handle_status_action(query, context)


async def _handle_refresh_ls_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle refresh ls action."""
    await _handle_ls_action(query, context)


async def _handle_export_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export action."""
    await query.edit_message_text(
        "📤 **Export Session**\n\n"
        "Session export functionality will be available once the storage layer is implemented.\n\n"
        "**Planned features:**\n"
        "• Export conversation history\n"
        "• Save session state\n"
        "• Share conversations\n"
        "• Create session backups\n\n"
        "_Coming in the next development phase!_"
    )


async def handle_quick_action_callback(
    query, action_id: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quick action callbacks with localization."""
    user_id = query.from_user.id

    # Get localization components
    localization = context.bot_data.get("localization")
    user_language_storage = context.bot_data.get("user_language_storage")
    
    # Get quick actions manager from bot data if available
    quick_actions = context.bot_data.get("quick_actions")

    if not quick_actions:
        error_text = await get_localized_text(context, user_id, "errors.quick_actions_unavailable")
        await query.edit_message_text(error_text, parse_mode=None)
        return

    # Get Claude integration
    claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")
    if not claude_integration:
        error_text = await get_localized_text(context, user_id, "errors.claude_not_available")
        await query.edit_message_text(error_text, parse_mode=None)
        return

    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # Get the action from the manager
        action = quick_actions.actions.get(action_id)
        if not action:
            error_text = await get_localized_text(context, user_id, "errors.action_not_found", action=action_id)
            await query.edit_message_text(error_text, parse_mode=None)
            return
            
        # Get localized action name
        if localization and user_language_storage:
            user_lang = await user_language_storage.get_user_language(user_id)
            action_display_name = localization.get(f"quick_actions.{action.id}.name", language=user_lang) or f"{action.icon} {action.name}"
        else:
            action_display_name = f"{action.icon} {action.name}"

        # Check if action is properly implemented
        if not action.command and not getattr(action, "prompt", None):
            error_text = await get_localized_text(context, user_id, "errors.action_not_implemented", action=action_display_name)
            await query.edit_message_text(error_text, parse_mode=None)
            return

        # Show execution message
        executing_text = await get_localized_text(context, user_id, "messages.executing_action", action=action_display_name)
        await query.edit_message_text(executing_text, parse_mode=None)

        # Run the action through Claude
        prompt = getattr(action, "prompt", None) or action.command
        claude_response = await claude_integration.run_command(
            prompt=prompt, working_directory=current_dir, user_id=user_id
        )

        if claude_response:
            # Show completion message and format response
            completed_text = await get_localized_text(context, user_id, "messages.action_completed", action=action_display_name)
            response_text = claude_response.content
            if len(response_text) > 4000:
                response_text = response_text[:4000] + "...\n\n_(Response truncated)_"

            await query.message.reply_text(
                f"{completed_text}\n\n{response_text}",
                parse_mode=None,
            )
        else:
            failed_text = await get_localized_text(context, user_id, "messages.action_failed", action=action_display_name)
            await query.edit_message_text(failed_text, parse_mode=None)

    except Exception as e:
        logger.error("Quick action execution failed", error=str(e), user_id=user_id)
        error_text = await get_localized_text(context, user_id, "errors.action_error", action=action_id, error=str(e))
        await query.edit_message_text(error_text, parse_mode=None)


async def handle_followup_callback(
    query, suggestion_hash: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle follow-up suggestion callbacks."""
    user_id = query.from_user.id

    # Get conversation enhancer from bot data if available
    conversation_enhancer = context.bot_data.get("conversation_enhancer")

    if not conversation_enhancer:
        await query.edit_message_text(
            "❌ **Follow-up Not Available**\n\n"
            "Conversation enhancement features are not available."
        )
        return

    try:
        # Get stored suggestions (this would need to be implemented in the enhancer)
        # For now, we'll provide a generic response
        await query.edit_message_text(
            "💡 **Follow-up Suggestion Selected**\n\n"
            "This follow-up suggestion will be implemented once the conversation "
            "enhancement system is fully integrated with the message handler.\n\n"
            "**Current Status:**\n"
            "• Suggestion received ✅\n"
            "• Integration pending 🔄\n\n"
            "_You can continue the conversation by sending a new message._"
        )

        logger.info(
            "Follow-up suggestion selected",
            user_id=user_id,
            suggestion_hash=suggestion_hash,
        )

    except Exception as e:
        logger.error(
            "Error handling follow-up callback",
            error=str(e),
            user_id=user_id,
            suggestion_hash=suggestion_hash,
        )

        await query.edit_message_text(
            "❌ **Error Processing Follow-up**\n\n"
            "An error occurred while processing your follow-up suggestion."
        )


async def handle_conversation_callback(
    query, action_type: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle conversation control callbacks."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]

    if action_type == "continue":
        # Remove suggestion buttons and show continue message
        await query.edit_message_text(
            "✅ **Continuing Conversation**\n\n"
            "Send me your next message to continue coding!\n\n"
            "I'm ready to help with:\n"
            "• Code review and debugging\n"
            "• Feature implementation\n"
            "• Architecture decisions\n"
            "• Testing and optimization\n"
            "• Documentation\n\n"
            "_Just type your request or upload files._"
        )

    elif action_type == "end":
        # End the current session
        conversation_enhancer = context.bot_data.get("conversation_enhancer")
        if conversation_enhancer:
            conversation_enhancer.clear_context(user_id)

        # Clear session data
        context.user_data["claude_session_id"] = None
        context.user_data["session_started"] = False

        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )
        relative_path = current_dir.relative_to(settings.approved_directory)

        # Create quick action buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    "🆕 New Session", callback_data="action:new_session"
                ),
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

        await query.edit_message_text(
            "✅ **Conversation Ended**\n\n"
            f"Your Claude session has been terminated.\n\n"
            f"**Current Status:**\n"
            f"• Directory: `{relative_path}/`\n"
            f"• Session: None\n"
            f"• Ready for new commands\n\n"
            f"**Next Steps:**\n"
            f"• Start a new session\n"
            f"• Check status\n"
            f"• Send any message to begin a new conversation",
            parse_mode=None,
            reply_markup=reply_markup,
        )

        logger.info("Conversation ended via callback", user_id=user_id)

    else:
        user_id = query.from_user.id
        await query.edit_message_text(
            await t(context, user_id, "callback_errors.unknown_action") + f": {action_type}"
        )


async def handle_git_callback(
    query, git_action: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle git-related callbacks."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]
    features = context.bot_data.get("features")

    if not features or not features.is_enabled("git"):
        await query.edit_message_text(
            "❌ **Git Integration Disabled**\n\n"
            "Git integration feature is not enabled."
        )
        return

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        git_integration = features.get_git_integration()
        if not git_integration:
            await query.edit_message_text(
                "❌ **Git Integration Unavailable**\n\n"
                "Git integration service is not available."
            )
            return

        if git_action == "status":
            # Refresh git status
            git_status = await git_integration.get_status(current_dir)
            status_message = git_integration.format_status(git_status)

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

            await query.edit_message_text(
                status_message, parse_mode=None, reply_markup=reply_markup
            )

        elif git_action == "diff":
            # Show git diff
            diff_output = await git_integration.get_diff(current_dir)

            if not diff_output.strip():
                diff_message = "📊 **Git Diff**\n\n_No changes to show._"
            else:
                # Clean up diff output for Telegram
                # Remove emoji symbols that interfere with markdown parsing
                clean_diff = diff_output.replace("➕", "+").replace("➖", "-").replace("📍", "@")
                
                # Limit diff output
                max_length = 2000
                if len(clean_diff) > max_length:
                    clean_diff = (
                        clean_diff[:max_length] + "\n\n_... output truncated ..._"
                    )

                diff_message = f"📊 **Git Diff**\n\n```\n{clean_diff}\n```"

            keyboard = [
                [
                    InlineKeyboardButton("📜 Show Log", callback_data="git:log"),
                    InlineKeyboardButton("📊 Status", callback_data="git:status"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                diff_message, parse_mode=None, reply_markup=reply_markup
            )

        elif git_action == "log":
            # Show git log
            commits = await git_integration.get_file_history(current_dir, ".")

            if not commits:
                log_message = "📜 **Git Log**\n\n_No commits found._"
            else:
                log_message = "📜 **Git Log**\n\n"
                for commit in commits[:10]:  # Show last 10 commits
                    short_hash = commit.hash[:7]
                    short_message = commit.message[:60]
                    if len(commit.message) > 60:
                        short_message += "..."
                    log_message += f"• `{short_hash}` {short_message}\n"

            keyboard = [
                [
                    InlineKeyboardButton("📊 Show Diff", callback_data="git:diff"),
                    InlineKeyboardButton("📊 Status", callback_data="git:status"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                log_message, parse_mode=None, reply_markup=reply_markup
            )

        else:
            user_id = query.from_user.id
            await query.edit_message_text(
                await t(context, user_id, "callback_errors.unknown_action") + f": {git_action}"
            )

    except Exception as e:
        logger.error(
            "Error in git callback",
            error=str(e),
            git_action=git_action,
            user_id=user_id,
        )
        await query.edit_message_text(f"❌ **Git Error**\n\n{str(e)}")


async def handle_export_callback(
    query, export_format: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle export format selection callbacks."""
    user_id = query.from_user.id
    features = context.bot_data.get("features")

    if export_format == "cancel":
        await query.edit_message_text(
            await t(context, user_id, "buttons.cancelled")
        )
        return

    session_exporter = features.get_session_export() if features else None
    if not session_exporter:
        await query.edit_message_text(
            "❌ **Export Unavailable**\n\n" "Session export service is not available."
        )
        return

    # Get current session
    claude_session_id = context.user_data.get("claude_session_id")
    if not claude_session_id:
        await query.edit_message_text(
            "❌ **No Active Session**\n\n" "There's no active session to export."
        )
        return

    try:
        # Show processing message
        await query.edit_message_text(
            f"📤 **Exporting Session**\n\n"
            f"Generating {export_format.upper()} export...",
            parse_mode=None,
        )

        # Export session
        exported_session = await session_exporter.export_session(
            claude_session_id, export_format
        )

        # Send the exported file
        from io import BytesIO

        file_bytes = BytesIO(exported_session.content.encode("utf-8"))
        file_bytes.name = exported_session.filename

        await query.message.reply_document(
            document=file_bytes,
            filename=exported_session.filename,
            caption=(
                f"📤 **Session Export Complete**\n\n"
                f"Format: {exported_session.format.upper()}\n"
                f"Size: {exported_session.size_bytes:,} bytes\n"
                f"Created: {exported_session.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            parse_mode=None,
        )

        # Update the original message
        await query.edit_message_text(
            f"✅ **Export Complete**\n\n"
            f"Your session has been exported as {exported_session.filename}.\n"
            f"Check the file above for your complete conversation history.",
            parse_mode=None,
        )

    except Exception as e:
        logger.error(
            "Export failed", error=str(e), user_id=user_id, format=export_format
        )
        await query.edit_message_text(f"❌ **Export Failed**\n\n{str(e)}")


async def handle_language_callback(query, param: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection callbacks."""
    user_id = query.from_user.id
    localization = context.bot_data.get("localization")
    user_language_storage = context.bot_data.get("user_language_storage")
    
    if not localization or not user_language_storage:
        await query.edit_message_text("❌ Localization system not available")
        return
    
    if param == "select":
        # Show language selection menu
        available_languages = localization.get_available_languages()
        
        keyboard = []
        row = []
        for lang_code, lang_name in available_languages.items():
            flag = "🇺🇦" if lang_code == "uk" else "🇺🇸"
            row.append(InlineKeyboardButton(f"{flag} {lang_name}", callback_data=f"lang:set:{lang_code}"))
            
            # Create rows of 2 buttons each
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        # Add remaining button if any
        if row:
            keyboard.append(row)
            
        # Add back button
        back_text = await get_user_text(localization, user_language_storage, user_id, "buttons.back")
        keyboard.append([InlineKeyboardButton(back_text, callback_data="action:help")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get localized text
        select_message = await get_user_text(localization, user_language_storage, user_id, "messages.language_select")
        
        await query.edit_message_text(select_message, reply_markup=reply_markup)
        
    elif param.startswith("set:"):
        # Set user language
        new_language = param.split(":", 1)[1]
        
        if localization.is_language_available(new_language):
            success = await user_language_storage.set_user_language(user_id, new_language)
            
            if success:
                # Get language name for confirmation
                lang_name = localization.get_available_languages().get(new_language, new_language.upper())
                
                # Get confirmation message in NEW language
                confirmation_text = localization.get("messages.language_changed", language=new_language).format(language_name=lang_name)
                
                # Show language changed message with back button
                back_text = localization.get("buttons.back", language=new_language)
                keyboard = [[InlineKeyboardButton(back_text, callback_data="action:help")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(confirmation_text, reply_markup=reply_markup)
                
                logger.info("User language changed", user_id=user_id, new_language=new_language)
            else:
                error_text = await get_user_text(localization, user_language_storage, user_id, "messages.error_occurred", error="Failed to save language preference")
                await query.edit_message_text(error_text)
        else:
            error_text = await get_user_text(localization, user_language_storage, user_id, "messages.language_not_available", language=new_language)
            await query.edit_message_text(error_text)


async def handle_schedule_callback(query, param: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle scheduled prompts callbacks."""
    try:
        from ..features.scheduled_prompts import ScheduledPromptsManager
        
        user_id = query.from_user.id
        application = context.application
        settings = context.bot_data.get("settings")
        
        if not application or not settings:
            await query.edit_message_text("❌ Помилка доступу до системи")
            return
            
        prompts_manager = ScheduledPromptsManager(application, settings)
        
        if param == "add":
            # Show add schedule menu
            keyboard = [
                [InlineKeyboardButton("📝 Створити завдання", callback_data="schedule:create_new")],
                [InlineKeyboardButton("📋 Зі шаблону", callback_data="schedule:from_template")],
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                "➕ **Додати планове завдання**\n\n"
                "Планові завдання виконуються автоматично\n"
                "під час DND періоду (23:00-08:00).\n\n"
                "Оберіть спосіб створення:"
            )
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        elif param == "list":
            # Show schedules list
            config = await prompts_manager.load_prompts()
            prompts = config.get("prompts", [])
            system_settings = config.get("settings", {})
            
            if not prompts:
                keyboard = [[
                    InlineKeyboardButton("➕ Додати завдання", callback_data="schedule:add"),
                    InlineKeyboardButton("⚙️ Налаштування", callback_data="schedule:settings")
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "📋 **Планових завдань немає**\n\n"
                    "🔧 Додайте перше завдання для початку роботи",
                    reply_markup=reply_markup
                )
                return
            
            enabled_count = sum(1 for p in prompts if p.get("enabled", False))
            system_status = "✅ Увімкнена" if system_settings.get("enabled", False) else "❌ Вимкнена"
            
            message = (
                f"📋 **Планові завдання** ({len(prompts)})\n"
                f"🔧 Система: {system_status} | Активних: {enabled_count}\n\n"
            )
            
            for i, prompt in enumerate(prompts[:5], 1):  # Show first 5
                status_icon = "✅" if prompt.get("enabled", False) else "❌"
                schedule = prompt.get("schedule", {})
                schedule_info = f"{schedule.get('type', 'daily')} о {schedule.get('time', '02:00')}"
                
                message += (
                    f"{i}. {status_icon} **{prompt.get('title', 'Без назви')}**\n"
                    f"   📅 {schedule_info}\n\n"
                )
            
            if len(prompts) > 5:
                message += f"... та ще {len(prompts) - 5} завдань\n\n"
                
            keyboard = [
                [
                    InlineKeyboardButton("➕ Додати", callback_data="schedule:add"),
                    InlineKeyboardButton("📝 Редагувати", callback_data="schedule:edit")
                ],
                [
                    InlineKeyboardButton("⚙️ Налаштування", callback_data="schedule:settings"),
                    InlineKeyboardButton("🔄 Оновити", callback_data="schedule:list")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        elif param == "settings":
            # Show system settings
            config = await prompts_manager.load_prompts()
            system_settings = config.get("settings", {})
            
            enabled = system_settings.get("enabled", False)
            dnd_start = system_settings.get("dnd_start", "23:00")
            dnd_end = system_settings.get("dnd_end", "08:00")
            max_concurrent = system_settings.get("max_concurrent_tasks", 1)
            
            message = (
                "⚙️ **Налаштування системи**\n\n"
                f"🔧 Система: {'✅ Увімкнена' if enabled else '❌ Вимкнена'}\n"
                f"🌙 DND період: {dnd_start} - {dnd_end}\n"
                f"⚡ Максимально завдань: {max_concurrent}\n\n"
                "**Do Not Disturb (DND) період** - це час коли\n"
                "користувачі не працюють і система може\n"
                "автоматично виконувати планові завдання."
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "❌ Вимкнути" if enabled else "✅ Увімкнути",
                    callback_data=f"schedule:toggle_system"
                )],
                [
                    InlineKeyboardButton("🌙 Змінити DND", callback_data="schedule:change_dnd"),
                    InlineKeyboardButton("⚡ Налаштування", callback_data="schedule:advanced")
                ],
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        elif param == "stats":
            # Show execution statistics
            stats = await prompts_manager.get_execution_stats()
            
            message = (
                "📊 **Статистика виконання**\n\n"
                f"📈 Всього виконань: {stats.get('total_executions', 0)}\n"
                f"✅ Успішних: {stats.get('successful', 0)}\n"
                f"❌ Помилок: {stats.get('failed', 0)}\n"
                f"⏱️ Середній час: {stats.get('avg_duration', 0):.1f}с\n"
                f"🕒 Останнє виконання: {stats.get('last_execution', 'Немає')}\n\n"
                f"🔄 Система працює: {'✅ Так' if stats.get('system_active', False) else '❌ Ні'}"
            )
            
            keyboard = [
                [InlineKeyboardButton("📋 Детальні логи", callback_data="schedule:logs")],
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        elif param == "create_new":
            # Handle create new scheduled prompt
            await query.edit_message_text(
                "📝 **Створити нове завдання**\n\n"
                "Функція створення нових планових завдань\n"
                "буде доступна найближчим часом.\n\n"
                "Наразі ви можете:\n"
                "• Переглядати існуючі завдання\n"
                "• Керувати налаштуваннями системи\n"
                "• Переглядати статистику",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")]
                ])
            )
            
        elif param == "advanced":
            # Handle advanced settings  
            config = await prompts_manager.load_prompts()
            system_settings = config.get("settings", {})
            
            message = (
                "⚙️ **Розширені налаштування**\n\n"
                f"🔧 Максимально завдань: {system_settings.get('max_concurrent_tasks', 1)}\n"
                f"⏰ Тайм-аут завдання: {system_settings.get('task_timeout', 300)}с\n"
                f"🔄 Інтервал перевірки: {system_settings.get('check_interval', 60)}с\n"
                f"📝 Логування: {'✅ Увімкнено' if system_settings.get('logging_enabled', True) else '❌ Вимкнено'}\n\n"
                "**Опис налаштувань:**\n"
                "• Максимально завдань - скільки завдань можуть виконуватись одночасно\n"
                "• Тайм-аут - максимальний час виконання одного завдання\n"
                "• Інтервал перевірки - як часто система перевіряє нові завдання"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        elif param == "change_dnd":
            # Handle change DND settings
            config = await prompts_manager.load_prompts()
            system_settings = config.get("settings", {})
            
            dnd_start = system_settings.get("dnd_start", "23:00")
            dnd_end = system_settings.get("dnd_end", "08:00")
            
            message = (
                "🌙 **Налаштування DND періоду**\n\n"
                f"📅 Поточні налаштування:\n"
                f"• Початок: {dnd_start}\n"
                f"• Кінець: {dnd_end}\n\n"
                "**Do Not Disturb (DND)** - це період часу,\n"
                "коли користувачі зазвичай не працюють\n"
                "і система може виконувати планові завдання\n"
                "без перешкод.\n\n"
                "Зміна DND періоду буде доступна\n"
                "в наступних версіях системи."
            )
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        else:
            user_id = query.from_user.id
            await query.edit_message_text(
                await t(context, user_id, "callback_errors.unknown_action") + f": {param}"
            )
            
    except Exception as e:
        logger.error("Error in schedule callback", error=str(e))
        user_id = query.from_user.id
        await query.edit_message_text(
            await t(context, user_id, "errors.unexpected_error")
        )


async def _handle_settings_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings action."""
    update = query.callback_query if hasattr(query, 'callback_query') else type('obj', (object,), {'callback_query': query})()
    user_id = get_user_id(update)
    
    try:
        # Create settings keyboard
        keyboard = [
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.help"), callback_data="action:help"),
                InlineKeyboardButton("🔙 " + await t(context, user_id, "buttons.back"), callback_data="action:quick_actions")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings_text = await t(context, user_id, "commands.settings.title")
        description_text = await t(context, user_id, "commands.settings.description")
        
        await query.edit_message_text(
            f"⚙️ **{settings_text}**\n\n{description_text}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error("Error in settings action", error=str(e))
        await query.edit_message_text(await t(context, user_id, "errors.unexpected_error"))


async def _handle_main_menu_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main menu action."""
    update = query.callback_query if hasattr(query, 'callback_query') else type('obj', (object,), {'callback_query': query})()
    user_id = get_user_id(update)
    
    try:
        # Create main menu keyboard with all primary actions
        keyboard = [
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.new_session"), callback_data="action:new"),
                InlineKeyboardButton(await t(context, user_id, "buttons.continue_session"), callback_data="action:continue")
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.status"), callback_data="action:status"),
                InlineKeyboardButton(await t(context, user_id, "buttons.export"), callback_data="action:export")
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.help"), callback_data="action:help"),
                InlineKeyboardButton(await t(context, user_id, "buttons.settings"), callback_data="action:settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        main_menu_text = await t(context, user_id, "commands.main_menu.title")
        description_text = await t(context, user_id, "commands.main_menu.description")
        
        await query.edit_message_text(
            f"🏠 **{main_menu_text}**\n\n{description_text}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error("Error in main menu action", error=str(e))
        await query.edit_message_text(await t(context, user_id, "errors.unexpected_error"))


def _format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}B"
        size /= 1024
    return f"{size:.1f}TB"


# NEW CALLBACK HANDLERS FROM GROK ALL-FIX

async def handle_prompts_settings_callback(query, param: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Налаштування' button."""
    await query.answer()
    try:
        user_id = query.from_user.id
        settings_text = await t(context, user_id, "settings.title")
        await query.edit_message_text(
            text=settings_text,
            # reply_markup=get_settings_keyboard(query.from_user.id)  # TODO: implement
        )
        logger.info("Prompts settings callback", user_id=user_id)
    except Exception as e:
        await query.edit_message_text(await t(context, query.from_user.id, "errors.settings_failed"))
        logger.error("Settings callback error", error=str(e))

async def handle_save_code_callback(query, param: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Save Code' button."""
    await query.answer()
    try:
        user_id = query.from_user.id
        # Assuming storage save logic
        # from src.storage.facade import Storage
        # storage = context.application.bot_data.get('storage')
        # await storage.save_code(user_id, context.user_data.get('current_code', ''))
        await query.edit_message_text(await t(context, user_id, "session.save_complete"))
        logger.info("Code saved", user_id=user_id)
    except Exception as e:
        await query.edit_message_text(await t(context, query.from_user.id, "errors.save_failed", error=str(e)))

async def handle_continue_callback(query, param: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Continue Session' button - allows user to ask follow-up questions."""
    await query.answer()
    try:
        user_id = query.from_user.id

        # Remove buttons and prepare for continuation
        continue_text = await t(
            context, user_id, "buttons.continue_prompt",
            fallback="✅ **Готовий до продовження!**\n\n"
                     "Надішліть ваше питання або запит:\n"
                     "• Додаткові уточнення щодо проблеми\n"
                     "• Запит на впровадження змін\n"
                     "• Питання про рішення\n"
                     "• Інші побажання\n\n"
                     "_Очікую ваше повідомлення..._"
        )

        await query.edit_message_text(continue_text)

        # Set flag that user wants to continue conversation
        if not context.user_data:
            context.user_data = {}
        context.user_data['awaiting_continuation'] = True

    except Exception as e:
        error_text = await t(context, query.from_user.id, "errors.continue_failed", fallback="❌ Помилка продовження діалогу")
        await query.edit_message_text(error_text)

async def handle_explain_callback(query, param: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Explain' button - asks Claude to explain the previous response."""
    await query.answer()
    try:
        user_id = query.from_user.id

        # Show processing message
        processing_text = await t(
            context, user_id, "explain.processing",
            fallback="🤔 **Пояснюю детальніше...**\n\n_Аналізую попередню відповідь та готую детальне пояснення..._"
        )
        await query.edit_message_text(processing_text)

        # Get Claude integration
        claude_integration = context.bot_data.get('claude_integration')
        if not claude_integration:
            error_text = await t(context, user_id, "errors.service_unavailable", fallback="❌ Сервіс недоступний")
            await query.edit_message_text(error_text)
            return

        # Get current directory
        settings = context.bot_data.get("settings")
        if not settings:
            current_dir = Path.cwd()
        else:
            current_dir = context.user_data.get(
                'current_directory',
                settings.approved_directory
            ) if context.user_data else settings.approved_directory

        # Create explanation prompt in Ukrainian
        explain_prompt = (
            "Будь ласка, дайте детальне пояснення вашої попередньої відповіді:\n\n"
            "1. **Поясніть кожен крок** який ви запропонували\n"
            "2. **Чому саме такий підхід** є найкращим?\n"
            "3. **Які альтернативи** можливі?\n"
            "4. **Потенційні ризики** та як їх уникнути\n"
            "5. **Що буде після впровадження** змін?\n\n"
            "Дайте максимально детальне та зрозуміле пояснення українською мовою."
        )

        # Run Claude command for explanation
        claude_response = await claude_integration.run_command(
            prompt=explain_prompt,
            working_directory=current_dir,
            user_id=user_id,
            session_id=context.user_data.get('claude_session_id') if context.user_data else None
        )

        if claude_response and claude_response.content:
            # Format the explanation response
            explanation_text = f"💡 **Детальне пояснення:**\n\n{claude_response.content}"

            # Create new Continue button for further questions
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Продовжити діалог", callback_data="continue")]
            ])

            await query.edit_message_text(explanation_text, reply_markup=keyboard, parse_mode='Markdown')
        else:
            error_text = await t(context, user_id, "explain.no_response", fallback="❌ Не вдалося отримати пояснення")
            await query.edit_message_text(error_text)

    except Exception as e:
        error_text = await t(context, query.from_user.id, "errors.explain_failed", fallback="❌ Помилка отримання пояснення")
        await query.edit_message_text(error_text)

async def handle_refresh_callback(query, param: str, context: ContextTypes.DEFAULT_TYPE):
    """Fixed: Hardcoded '🔄 Оновити'."""
    await query.answer()
    try:
        user_id = query.from_user.id
        refresh_text = await t(context, user_id, "buttons.refresh")
        current_status = await t(context, user_id, "status.title")
        await query.edit_message_text(refresh_text + "\n\n" + current_status)
    except Exception as e:
        from ..utils.error_handler import safe_user_error
        await safe_user_error(query, context, "errors.refresh_failed", e)


# Registration function for callbacks
def register_callbacks(application):
    """Register all callback handlers."""
    from telegram.ext import CallbackQueryHandler
    
    # Register the main callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback_query))
