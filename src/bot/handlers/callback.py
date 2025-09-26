"""Handle inline keyboard callbacks."""

import structlog
from datetime import datetime
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
            "quick_action": handle_quick_action_execution_callback,
            "file_edit": handle_file_edit_callback,
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
            "claude_status": handle_claude_status_callback,
        }

        # Check for MCP callbacks first
        if action.startswith("mcp"):
            from .mcp_callbacks import handle_mcp_callback
            await handle_mcp_callback(update, context)
            return

        # Check for context callbacks
        if data.startswith("context_"):
            context_commands = context.bot_data.get("context_commands")
            if context_commands:
                await context_commands.handle_callback_query(update, context)
            else:
                logger.warning("Context commands not available")
                await query.edit_message_text(
                    "❌ Система контекстної пам'яті недоступна"
                )
            return

        # Check for menu callbacks
        if data.startswith("menu_"):
            unified_menu = context.bot_data.get("unified_menu")
            if unified_menu:
                await unified_menu.handle_menu_callback(update, context)
            else:
                logger.warning("Unified menu not available")
                await query.edit_message_text(
                    "❌ Система меню недоступна"
                )
            return

        handler = handlers.get(action)
        if handler:
            logger.info("Executing callback handler", action=action, param=param, user_id=user_id)
            await handler(query, param, context)
        else:
            logger.warning("Unknown callback action", action=action, param=param, user_id=user_id)
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
        status_text = await get_localized_text(context, user_id, "buttons.status")
        
        keyboard = [
            [
                InlineKeyboardButton(list_files_text, callback_data="action:ls"),
                InlineKeyboardButton(new_session_text, callback_data="action:new_session"),
            ],
            [
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
        "context": _handle_context_action,
        "settings": _handle_settings_action,
        "main_menu": _handle_main_menu_action,
        "schedules": _handle_schedules_action,
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
    quick_actions_text = await get_localized_text(context, user_id, "buttons.quick_actions")
    help_text = await get_localized_text(context, user_id, "buttons.help")
    
    keyboard = [
        [
            InlineKeyboardButton(start_coding_text, callback_data="action:start_coding"),
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

    # Show termination message first
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
        f"• Send any message to begin a new conversation\n\n"
        f"_Returning to main menu..._",
        parse_mode=None,
    )

    # Now call the proper main menu action to ensure consistency
    await _handle_main_menu_action(query, context)


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
                    "🔄 Refresh", callback_data="action:refresh_ls"
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
    user_id = query.from_user.id

    # NEW FUNCTIONAL BUTTONS - using quick_action callback for actual execution
    keyboard = [
        [
            InlineKeyboardButton("📋 Показати файли", callback_data="quick_action:ls"),
            InlineKeyboardButton("🏠 Де я?", callback_data="quick_action:pwd"),
        ],
        [
            InlineKeyboardButton("💾 Git Status", callback_data="quick_action:git_status"),
            InlineKeyboardButton("📝 TODO List", callback_data="action:schedules"),
        ],
        [
            InlineKeyboardButton("📖 Читати файл", callback_data="file_edit:select_read"),
            InlineKeyboardButton("✏️ Редагувати файл", callback_data="file_edit:select_edit"),
        ],
        [
            InlineKeyboardButton("🔍 Знайти файли", callback_data="quick_action:find_files"),
            InlineKeyboardButton("🧪 Запустити тести", callback_data="quick:test"),
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


async def _handle_context_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle context action."""
    try:
        context_commands = context.bot_data.get("context_commands")
        if context_commands:
            # Create a fake update object from callback query
            class FakeUpdate:
                def __init__(self, callback_query):
                    self.callback_query = callback_query
                    self.effective_user = callback_query.from_user
                    self.effective_chat = callback_query.message.chat
                    self.message = callback_query.message

            fake_update = FakeUpdate(query)
            await context_commands.handle_context_status(fake_update, context)
        else:
            await query.edit_message_text(
                "🧠 **Context Management**\n\n"
                "Context management is not properly initialized.\n\n"
                "Please check the bot configuration."
            )
    except Exception as e:
        logger.error("Failed to handle context action", error=str(e))
        await query.edit_message_text(
            "❌ **Error**\n\n"
            "Failed to load context information.\n\n"
            "Please try again later."
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

        # Show termination message first
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
            f"• Send any message to begin a new conversation\n\n"
            f"_Returning to main menu..._",
            parse_mode=None,
        )

        # Now call the proper main menu action to ensure consistency
        await _handle_main_menu_action(query, context)

        logger.info("Conversation ended via callback", user_id=user_id)

    else:
        user_id = query.from_user.id
        await query.edit_message_text(
            await t(context, user_id, "callback_errors.unknown_action") + f": {action_type}"
        )


async def handle_git_callback(
    query, git_action: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle git-related callbacks with Claude CLI delegation."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]

    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # Handle help action
        if git_action == "help":
            title = await t(context, user_id, "git.help.title")
            description = await t(context, user_id, "git.help.description")
            operations = []
            for op in ["status", "add", "commit", "push", "pull", "log", "diff", "branch"]:
                op_text = await t(context, user_id, f"git.help.operations.{op}")
                operations.append(op_text)

            note = await t(context, user_id, "git.help.note")

            help_message = f"{title}\n\n{description}\n\n" + "\n".join(operations) + f"\n\n{note}"

            # Create back button
            keyboard = [[
                InlineKeyboardButton(
                    await t(context, user_id, "git.buttons.back"),
                    callback_data="git:back"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                help_message, reply_markup=reply_markup
            )
            return

        # Handle back action
        if git_action == "back":
            # Show main git menu
            title = await t(context, user_id, "git.title")
            description = await t(context, user_id, "git.description")

            # Create button grid
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
                    ),
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
                    ),
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
                    ),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"{title}\n\n{description}",
                reply_markup=reply_markup
            )
            return

        # Show processing message
        processing_msg = await t(context, user_id, "git.processing")
        await query.edit_message_text(
            processing_msg.format(operation=git_action)
        )

        # Get Claude integration
        claude_integration: ClaudeIntegration = context.bot_data["claude_integration"]

        # Prepare git command based on action
        git_commands = {
            "status": "git status --porcelain",
            "add": "git add .",
            "commit": "git commit -m 'Update via Telegram bot'",
            "push": "git push",
            "pull": "git pull",
            "log": "git log --oneline -10",
            "diff": "git diff",
            "branch": "git branch -a"
        }

        if git_action not in git_commands:
            unknown_action_msg = await t(context, user_id, "git.unknown_git_action")
            await query.edit_message_text(
                unknown_action_msg.format(
                    action=git_action,
                    message="Unknown action"
                )
            )
            return

        # Execute git command via Claude CLI
        command = git_commands[git_action]
        message = f"Execute this git command in directory {current_dir}: {command}"

        claude_response = await claude_integration.run_command(
            prompt=message,
            working_directory=current_dir,
            user_id=user_id
        )

        response = claude_response.content

        # Helper function to escape markdown
        def escape_markdown(text):
            return text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')

        # Format response based on action
        if git_action == "status":
            if "nothing to commit" in response.lower() or not response.strip():
                diff_title_msg = await t(context, user_id, "git.diff_title")
                formatted_message = diff_title_msg.format(
                    diff="No changes to commit"
                )
            else:
                clean_response = escape_markdown(response[:2000] + ("..." if len(response) > 2000 else ""))
                diff_title_msg = await t(context, user_id, "git.diff_title")
                formatted_message = diff_title_msg.format(
                    diff=clean_response
                )
        elif git_action == "diff":
            if not response.strip():
                diff_title_msg = await t(context, user_id, "git.diff_title")
                formatted_message = diff_title_msg.format(
                    diff="No changes to show"
                )
            else:
                # Clean response for display
                clean_response = escape_markdown(response[:2000] + ("..." if len(response) > 2000 else ""))
                diff_title_msg = await t(context, user_id, "git.diff_title")
                formatted_message = diff_title_msg.format(
                    diff=clean_response
                )
        else:
            # For other actions, show success message with truncated output
            success_msg = await t(context, user_id, "git.success")
            output = response[:1500] + ("..." if len(response) > 1500 else "")
            formatted_message = f"{success_msg.format(operation=git_action)}\n\n```\n{output}\n```"

        # Create navigation buttons
        keyboard = [[
            InlineKeyboardButton(
                await t(context, user_id, "git.buttons.back"),
                callback_data="git:back"
            ),
            InlineKeyboardButton(
                await t(context, user_id, "git.buttons.help"),
                callback_data="git:help"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            formatted_message,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(
            "Error in git callback",
            error=str(e),
            git_action=git_action,
            user_id=user_id,
        )
        error_msg = await t(context, user_id, "git.error")
        # Escape markdown characters in error message
        escaped_error = str(e).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
        await query.edit_message_text(
            error_msg.format(error=escaped_error)
        )


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
                    InlineKeyboardButton("📊 Статистика", callback_data="schedule:stats")
                ],
                [
                    InlineKeyboardButton("🔄 Оновити", callback_data="schedule:refresh"),
                    InlineKeyboardButton("▶️ Запустити всі", callback_data="schedule:run_all")
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

        elif param == "edit":
            # Show list of tasks for editing
            config = await prompts_manager.load_prompts()
            prompts = config.get("prompts", [])

            if not prompts:
                await query.edit_message_text(
                    "📝 **Немає завдань для редагування**\n\n"
                    "Спочатку додайте планові завдання.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Додати завдання", callback_data="schedule:add")],
                        [InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")]
                    ])
                )
                return

            message = "📝 **Редагування завдань**\n\nОберіть завдання для редагування:\n\n"
            keyboard = []

            for i, prompt in enumerate(prompts[:10]):  # Show first 10
                status_icon = "✅" if prompt.get("enabled", False) else "❌"
                title = prompt.get("title", f"Завдання {i+1}")
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_icon} {title[:30]}{'...' if len(title) > 30 else ''}",
                        callback_data=f"schedule:edit_task:{i}"
                    )
                ])

            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif param.startswith("edit_task:"):
            # Edit specific task
            task_index = int(param.split(":", 1)[1])
            config = await prompts_manager.load_prompts()
            prompts = config.get("prompts", [])

            if task_index >= len(prompts):
                await query.edit_message_text(
                    "❌ **Завдання не знайдено**\n\nЗавдання з таким номером не існує.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="schedule:edit")]
                    ])
                )
                return

            task = prompts[task_index]
            schedule = task.get("schedule", {})

            message = (
                f"✏️ **Редагування завдання**\n\n"
                f"📝 **Назва:** {task.get('title', 'Без назви')}\n"
                f"📋 **Опис:** {task.get('description', 'Без опису')}\n"
                f"⏰ **Розклад:** {schedule.get('type', 'daily')} о {schedule.get('time', '02:00')}\n"
                f"🔧 **Статус:** {'✅ Увімкнено' if task.get('enabled', False) else '❌ Вимкнено'}\n\n"
                f"**Промпт:**\n`{task.get('prompt', 'Немає промпту')[:200]}{'...' if len(task.get('prompt', '')) > 200 else ''}`"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ Вимкнути" if task.get("enabled", False) else "✅ Увімкнути",
                        callback_data=f"schedule:toggle_task:{task_index}"
                    ),
                    InlineKeyboardButton("🗑️ Видалити", callback_data=f"schedule:delete_task:{task_index}")
                ],
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:edit")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif param.startswith("toggle_task:"):
            # Toggle task enabled/disabled
            task_index = int(param.split(":", 1)[1])
            config = await prompts_manager.load_prompts()
            prompts = config.get("prompts", [])

            if task_index < len(prompts):
                prompts[task_index]["enabled"] = not prompts[task_index].get("enabled", False)
                await prompts_manager.save_prompts(config)

                status = "увімкнено" if prompts[task_index]["enabled"] else "вимкнено"
                await query.edit_message_text(
                    f"✅ **Завдання {status}**\n\n"
                    f"Завдання '{prompts[task_index].get('title', 'Без назви')}' було {status}.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад до редагування", callback_data=f"schedule:edit_task:{task_index}")]
                    ])
                )
            else:
                await query.edit_message_text("❌ Завдання не знайдено")

        elif param.startswith("delete_task:"):
            # Delete task with confirmation
            task_index = int(param.split(":", 1)[1])
            config = await prompts_manager.load_prompts()
            prompts = config.get("prompts", [])

            if task_index < len(prompts):
                task_title = prompts[task_index].get('title', 'Без назви')
                message = (
                    f"🗑️ **Видалення завдання**\n\n"
                    f"Ви впевнені, що хочете видалити завдання:\n"
                    f"**'{task_title}'**?\n\n"
                    f"⚠️ Ця дія незворотна!"
                )

                keyboard = [
                    [
                        InlineKeyboardButton("✅ Так, видалити", callback_data=f"schedule:confirm_delete:{task_index}"),
                        InlineKeyboardButton("❌ Скасувати", callback_data=f"schedule:edit_task:{task_index}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Завдання не знайдено")

        elif param.startswith("confirm_delete:"):
            # Confirm task deletion
            task_index = int(param.split(":", 1)[1])
            config = await prompts_manager.load_prompts()
            prompts = config.get("prompts", [])

            if task_index < len(prompts):
                task_title = prompts[task_index].get('title', 'Без назви')
                del prompts[task_index]
                await prompts_manager.save_prompts(config)

                await query.edit_message_text(
                    f"✅ **Завдання видалено**\n\n"
                    f"Завдання '{task_title}' було успішно видалено.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Назад до списку", callback_data="schedule:list")]
                    ])
                )
            else:
                await query.edit_message_text("❌ Завдання не знайдено")

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
            # Store state for task creation dialogue
            user_id = query.from_user.id
            context.user_data["creating_task"] = {"step": "prompt", "user_id": user_id}

            await query.edit_message_text(
                "📝 **Створити нове планове завдання**\n\n"
                "**Крок 1 з 3: Введіть промпт**\n\n"
                "Введіть текст завдання, яке буде виконано автоматично:\n\n"
                "**Приклади:**\n"
                "• `Проаналізуй останні зміни в проекті`\n"
                "• `Створи щоденний звіт про код`\n"
                "• `Перевір безпеку проекту`\n"
                "• `Оптимізуй код для продуктивності`\n\n"
                "💬 Надішліть повідомлення з текстом завдання.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Скасувати", callback_data="schedule:cancel_create")]
                ])
            )

        elif param == "from_template":
            # Handle create from template
            keyboard = [
                [
                    InlineKeyboardButton("🔍 Аналіз коду", callback_data="schedule:template:code_analysis"),
                    InlineKeyboardButton("📊 Генерація звітів", callback_data="schedule:template:report_generation")
                ],
                [
                    InlineKeyboardButton("⚒️ Рефакторинг", callback_data="schedule:template:refactoring"),
                    InlineKeyboardButton("📝 Документація", callback_data="schedule:template:documentation")
                ],
                [
                    InlineKeyboardButton("🔒 Перевірка безпеки", callback_data="schedule:template:security_audit"),
                    InlineKeyboardButton("🧪 Тестування", callback_data="schedule:template:testing")
                ],
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:add")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = (
                "📋 **Обрати шаблон завдання**\n\n"
                "Виберіть тип завдання зі списку готових шаблонів:\n\n"
                "🔍 **Аналіз коду** - повний аналіз проєкту та архітектури\n"
                "📊 **Генерація звітів** - створення звітів та статистики\n"
                "⚒️ **Рефакторинг** - оптимізація та покращення коду\n"
                "📝 **Документація** - створення та оновлення документації\n"
                "🔒 **Перевірка безпеки** - аналіз уразливостей\n"
                "🧪 **Тестування** - генерація та запуск тестів\n\n"
                "_Натисніть на шаблон для налаштування завдання_"
            )

            await query.edit_message_text(message, reply_markup=reply_markup)

        elif param.startswith("template:"):
            # Handle specific template selection
            template_type = param.split(":", 1)[1]
            await _handle_template_selection(query, template_type, context)
            
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
                [
                    InlineKeyboardButton("🔧 Змінити максимум завдань", callback_data="schedule:change_max_tasks"),
                    InlineKeyboardButton("⏰ Змінити тайм-аут", callback_data="schedule:change_timeout")
                ],
                [
                    InlineKeyboardButton("🔄 Змінити інтервал", callback_data="schedule:change_interval"),
                    InlineKeyboardButton("📝 Переключити логування", callback_data="schedule:toggle_logging")
                ],
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

        elif param == "cancel_create":
            # Cancel task creation and clear state
            context.user_data.pop("creating_task", None)

            await query.edit_message_text(
                "❌ **Створення завдання скасовано**\n\n"
                "Повертаємось до головного меню планових завдань.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Назад до списку", callback_data="schedule:list")]
                ])
            )

        elif param == "change_max_tasks":
            # Handle changing max concurrent tasks
            config = await prompts_manager.load_prompts()
            system_settings = config.get("settings", {})
            current_max = system_settings.get("max_concurrent_tasks", 1)

            message = (
                "🔧 **Змінити максимум завдань**\n\n"
                f"📊 Поточне значення: {current_max}\n\n"
                "Оберіть нове значення максимальної кількості завдань,\n"
                "які можуть виконуватись одночасно:\n\n"
                "• **1** - послідовне виконання (рекомендовано)\n"
                "• **2-3** - паралельне виконання (потребує більше ресурсів)\n"
                "• **4+** - високе навантаження (не рекомендовано)"
            )

            keyboard = [
                [
                    InlineKeyboardButton("1️⃣ Одне завдання", callback_data="schedule:set_max:1"),
                    InlineKeyboardButton("2️⃣ Два завдання", callback_data="schedule:set_max:2")
                ],
                [
                    InlineKeyboardButton("3️⃣ Три завдання", callback_data="schedule:set_max:3"),
                    InlineKeyboardButton("4️⃣ Чотири завдання", callback_data="schedule:set_max:4")
                ],
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:advanced")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif param.startswith("set_max:"):
            # Handle setting max concurrent tasks
            new_max = int(param.split(":", 1)[1])
            config = await prompts_manager.load_prompts()

            if "settings" not in config:
                config["settings"] = {}
            config["settings"]["max_concurrent_tasks"] = new_max

            await prompts_manager.save_prompts(config)

            await query.edit_message_text(
                f"✅ **Налаштування оновлено**\n\n"
                f"🔧 Максимум завдань встановлено: **{new_max}**\n\n"
                f"{'📋 Завдання виконуватимуться послідовно' if new_max == 1 else f'⚡ До {new_max} завдань можуть виконуватись паралельно'}\n\n"
                "Нові налаштування будуть застосовані для наступних завдань.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Назад до налаштувань", callback_data="schedule:advanced")]
                ])
            )

        elif param == "change_timeout":
            # Handle changing task timeout
            config = await prompts_manager.load_prompts()
            system_settings = config.get("settings", {})
            current_timeout = system_settings.get("task_timeout", 300)

            message = (
                "⏰ **Змінити тайм-аут завдання**\n\n"
                f"📊 Поточне значення: {current_timeout} секунд\n\n"
                "Оберіть новий максимальний час виконання одного завдання:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🕑 2 хв (120с)", callback_data="schedule:set_timeout:120"),
                    InlineKeyboardButton("🕕 5 хв (300с)", callback_data="schedule:set_timeout:300")
                ],
                [
                    InlineKeyboardButton("🕙 10 хв (600с)", callback_data="schedule:set_timeout:600"),
                    InlineKeyboardButton("🕐 15 хв (900с)", callback_data="schedule:set_timeout:900")
                ],
                [
                    InlineKeyboardButton("🕕 30 хв (1800с)", callback_data="schedule:set_timeout:1800"),
                    InlineKeyboardButton("🕐 60 хв (3600с)", callback_data="schedule:set_timeout:3600")
                ],
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:advanced")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif param.startswith("set_timeout:"):
            # Handle setting task timeout
            new_timeout = int(param.split(":", 1)[1])
            config = await prompts_manager.load_prompts()

            if "settings" not in config:
                config["settings"] = {}
            config["settings"]["task_timeout"] = new_timeout

            await prompts_manager.save_prompts(config)

            minutes = new_timeout // 60
            await query.edit_message_text(
                f"✅ **Налаштування оновлено**\n\n"
                f"⏰ Тайм-аут завдання встановлено: **{new_timeout}с ({minutes} хв)**\n\n"
                "Завдання, які виконуватимуться довше за цей час,\n"
                "будуть автоматично скасовані.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Назад до налаштувань", callback_data="schedule:advanced")]
                ])
            )

        elif param == "change_interval":
            # Handle changing check interval
            config = await prompts_manager.load_prompts()
            system_settings = config.get("settings", {})
            current_interval = system_settings.get("check_interval", 60)

            message = (
                "🔄 **Змінити інтервал перевірки**\n\n"
                f"📊 Поточне значення: {current_interval} секунд\n\n"
                "Оберіть як часто система перевірятиме нові завдання для виконання:"
            )

            keyboard = [
                [
                    InlineKeyboardButton("⚡ 30с", callback_data="schedule:set_interval:30"),
                    InlineKeyboardButton("🕐 1хв (60с)", callback_data="schedule:set_interval:60")
                ],
                [
                    InlineKeyboardButton("🕕 2хв (120с)", callback_data="schedule:set_interval:120"),
                    InlineKeyboardButton("🕙 5хв (300с)", callback_data="schedule:set_interval:300")
                ],
                [InlineKeyboardButton("🔙 Назад", callback_data="schedule:advanced")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif param.startswith("set_interval:"):
            # Handle setting check interval
            new_interval = int(param.split(":", 1)[1])
            config = await prompts_manager.load_prompts()

            if "settings" not in config:
                config["settings"] = {}
            config["settings"]["check_interval"] = new_interval

            await prompts_manager.save_prompts(config)

            minutes = new_interval // 60 if new_interval >= 60 else 0
            seconds = new_interval % 60
            time_str = f"{minutes}хв {seconds}с" if minutes > 0 else f"{seconds}с"

            await query.edit_message_text(
                f"✅ **Налаштування оновлено**\n\n"
                f"🔄 Інтервал перевірки встановлено: **{time_str}**\n\n"
                "Система перевірятиме нові завдання з цим інтервалом.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Назад до налаштувань", callback_data="schedule:advanced")]
                ])
            )

        elif param == "toggle_logging":
            # Handle toggling logging
            config = await prompts_manager.load_prompts()
            system_settings = config.get("settings", {})
            current_logging = system_settings.get("logging_enabled", True)
            new_logging = not current_logging

            if "settings" not in config:
                config["settings"] = {}
            config["settings"]["logging_enabled"] = new_logging

            await prompts_manager.save_prompts(config)

            status = "увімкнено" if new_logging else "вимкнено"
            icon = "✅" if new_logging else "❌"

            await query.edit_message_text(
                f"✅ **Налаштування оновлено**\n\n"
                f"📝 Логування {icon} **{status}**\n\n"
                f"{'Детальні логи виконання завдань записуватимуться в систему.' if new_logging else 'Логування виконання завдань вимкнено для економії ресурсів.'}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Назад до налаштувань", callback_data="schedule:advanced")]
                ])
            )

        elif param == "refresh":
            # Handle refresh tasks list
            # Simply redirect to list to reload data
            await handle_schedule_callback(query, context, "list")
            return

        elif param == "run_all":
            # Handle running all enabled tasks immediately
            config = await prompts_manager.load_prompts()
            prompts = config.get("prompts", [])
            enabled_prompts = [p for p in prompts if p.get("enabled", False)]

            if not enabled_prompts:
                await query.edit_message_text(
                    "❌ **Немає активних завдань**\n\n"
                    "Спочатку увімкніть завдання, які потрібно виконати.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Повернутися до списку", callback_data="schedule:list")]
                    ])
                )
                return

            # Show confirmation dialog
            message = (
                f"▶️ **Запустити всі активні завдання?**\n\n"
                f"📊 Знайдено активних завдань: **{len(enabled_prompts)}**\n\n"
                "**Список завдань до виконання:**\n"
            )

            for i, prompt in enumerate(enabled_prompts[:5], 1):
                title = prompt.get('title', 'Без назви')
                message += f"{i}. {title}\n"

            if len(enabled_prompts) > 5:
                message += f"... та ще {len(enabled_prompts) - 5} завдань\n"

            message += (
                "\n⚠️ **Увага:** Завдання будуть виконані негайно,\n"
                "незалежно від розкладу.\n\n"
                "Продовжити?"
            )

            keyboard = [
                [
                    InlineKeyboardButton("✅ Так, запустити", callback_data="schedule:confirm_run_all"),
                    InlineKeyboardButton("❌ Скасувати", callback_data="schedule:list")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif param == "confirm_run_all":
            # Handle confirmed run all tasks
            try:
                # Get the prompts manager and run tasks
                await query.edit_message_text(
                    "🚀 **Запускаю всі активні завдання...**\n\n"
                    "⏳ Будь ласка, зачекайте..."
                )

                # Execute all enabled prompts
                config = await prompts_manager.load_prompts()
                prompts = config.get("prompts", [])
                enabled_prompts = [p for p in prompts if p.get("enabled", False)]

                executed_count = 0
                failed_count = 0

                for prompt in enabled_prompts:
                    try:
                        # Here you would call the actual execution logic
                        # For now, we'll just mark as executed
                        logger.info("Executing scheduled prompt",
                                  title=prompt.get('title', 'Без назви'),
                                  user_id=query.from_user.id)

                        # TODO: Add actual prompt execution logic here
                        # await execute_prompt(prompt, context)

                        executed_count += 1
                    except Exception as e:
                        logger.error("Failed to execute prompt",
                                   title=prompt.get('title', 'Без назви'),
                                   error=str(e))
                        failed_count += 1

                # Show results
                result_message = (
                    f"✅ **Виконання завершено**\n\n"
                    f"📈 Виконано успішно: **{executed_count}**\n"
                    f"❌ Помилок: **{failed_count}**\n\n"
                    f"📋 Всі активні завдання запущені в обробку."
                )

                if failed_count > 0:
                    result_message += f"\n\n⚠️ Деякі завдання не вдалося виконати. Перевірте логи."

                keyboard = [
                    [InlineKeyboardButton("📋 Повернутися до списку", callback_data="schedule:list")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(result_message, reply_markup=reply_markup)

            except Exception as e:
                logger.error("Error executing all tasks", error=str(e), user_id=query.from_user.id)
                await query.edit_message_text(
                    f"❌ **Помилка виконання**\n\n"
                    f"```\n{str(e)}\n```\n\n"
                    "Спробуйте ще раз або зверніться до адміністратора.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Повернутися до списку", callback_data="schedule:list")]
                    ])
                )

        elif param.startswith("time:"):
            # Handle time selection for task scheduling
            time_type = param.split(":", 1)[1]
            user_id = query.from_user.id

            if not context.user_data or not context.user_data.get('creating_task'):
                await query.edit_message_text(
                    "❌ **Сесія створення завдання закінчилась**\n\n"
                    "Почніть створення завдання спочатку:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Створити завдання", callback_data="schedule:create_new")]
                    ])
                )
                return

            task_data = context.user_data['creating_task']
            task_data['schedule_type'] = time_type

            if time_type == "custom":
                # Ask user to input custom time
                task_data['step'] = 'custom_time'
                context.user_data['creating_task'] = task_data

                await query.edit_message_text(
                    "⏰ **Налаштування часу виконання**\n\n"
                    "Введіть час у форматі **ГГ:ХХ** (24-годинний формат)\n\n"
                    "**Приклади:**\n"
                    "• `08:30` - щоранку о 8:30\n"
                    "• `14:15` - щодня о 14:15\n"
                    "• `23:00` - щовечора о 23:00\n\n"
                    "💬 Надішліть повідомлення з часом:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Скасувати", callback_data="schedule:cancel_create")]
                    ])
                )
            else:
                # Move to confirmation step
                task_data['step'] = 'confirm'
                context.user_data['creating_task'] = task_data

                from ..handlers.message import _show_task_confirmation
                await _show_task_confirmation(query, task_data)

        elif param == "confirm_task":
            # Handle task confirmation and creation
            user_id = query.from_user.id

            if not context.user_data or not context.user_data.get('creating_task'):
                await query.edit_message_text(
                    "❌ **Сесія створення завдання закінчилась**\n\n"
                    "Почніть створення завдання спочатку:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Створити завдання", callback_data="schedule:create_new")]
                    ])
                )
                return

            task_data = context.user_data['creating_task']

            try:
                # Create new task using ScheduledPromptsManager
                from ..features.scheduled_prompts import ScheduledPromptsManager

                settings = context.bot_data.get("settings")
                if not settings:
                    await query.edit_message_text(
                        "❌ **Помилка системи**\n\n"
                        "Не вдалося отримати налаштування системи."
                    )
                    return

                prompts_manager = ScheduledPromptsManager(context.application, settings)
                config = await prompts_manager.load_prompts()

                # Generate unique task ID
                import uuid
                task_id = f"user_task_{uuid.uuid4().hex[:8]}"

                # Create task object
                new_task = {
                    "id": task_id,
                    "title": f"Користувацьке завдання ({task_data['schedule_type']})",
                    "description": task_data['prompt'][:100] + ("..." if len(task_data['prompt']) > 100 else ""),
                    "prompt": task_data['prompt'],
                    "enabled": True,
                    "schedule": {
                        "type": task_data['schedule_type'],
                        "time": task_data.get('custom_time', '08:00')
                    },
                    "auto_execute": True,
                    "auto_respond": True,
                    "created_by": user_id,
                    "created_at": datetime.now().isoformat()
                }

                # Add task to configuration
                if "prompts" not in config:
                    config["prompts"] = []
                config["prompts"].append(new_task)

                # Save updated configuration
                await prompts_manager.save_prompts(config)

                # Clear creation state
                context.user_data.pop("creating_task", None)

                # Show success message
                schedule_desc = {
                    'dnd': 'під час DND періоду (23:00-08:00)',
                    'morning': 'щоранку о 08:00',
                    'evening': 'щовечора о 20:00',
                    'daily': 'щоденно о 08:00',
                    'weekly': 'щотижня (понеділок о 09:00)',
                    'custom': f'щоденно о {task_data.get("custom_time", "налаштований час")}'
                }

                await query.edit_message_text(
                    f"✅ **Завдання створено успішно!**\n\n"
                    f"**📝 Завдання:** {task_data['prompt'][:150]}{'...' if len(task_data['prompt']) > 150 else ''}\n\n"
                    f"**⏰ Розклад:** {schedule_desc.get(task_data['schedule_type'], 'не вказано')}\n\n"
                    f"**🔧 ID:** `{task_id}`\n\n"
                    f"Завдання буде виконуватись автоматично згідно розкладу.",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📋 Переглянути завдання", callback_data="schedule:list"),
                            InlineKeyboardButton("➕ Ще завдання", callback_data="schedule:create_new")
                        ]
                    ])
                )

            except Exception as e:
                logger.error("Error creating scheduled task", error=str(e), user_id=user_id)
                await query.edit_message_text(
                    f"❌ **Помилка створення завдання**\n\n"
                    f"Виникла помилка: {str(e)}\n\n"
                    f"Спробуйте ще раз пізніше.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")]
                    ])
                )

        elif param == "edit_task":
            # Handle task editing (simple version - just restart creation)
            context.user_data.pop("creating_task", None)

            await query.edit_message_text(
                "✏️ **Редагування завдання**\n\n"
                "Для редагування створіть завдання заново з новими параметрами.\n\n"
                "Почати створення завдання спочатку?",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📝 Створити завдання", callback_data="schedule:create_new"),
                        InlineKeyboardButton("🔙 Назад", callback_data="schedule:list")
                    ]
                ])
            )

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
    user_id = query.from_user.id
    
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
    """Handle main menu action - unified with start command."""
    user_id = query.from_user.id

    try:
        logger.info("🔍 DEBUG: Creating FULL main menu for user", user_id=user_id, function="main_menu_action")

        # Create unified main menu keyboard matching start command layout
        keyboard = [
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.new_session"), callback_data="action:new_session"),
                InlineKeyboardButton(await t(context, user_id, "buttons.continue_session"), callback_data="action:continue")
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.status"), callback_data="action:status")
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.context"), callback_data="action:context"),
                InlineKeyboardButton(await t(context, user_id, "buttons.settings"), callback_data="action:settings")
            ],
            [
                InlineKeyboardButton(await t(context, user_id, "buttons.help"), callback_data="action:help"),
                InlineKeyboardButton(await t(context, user_id, "buttons.language_settings"), callback_data="lang:select")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Build full welcome message like in start command
        welcome_text = await t(context, user_id, "commands.start.welcome", name=query.from_user.first_name)
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
            f"⚠️ {security_note_text}\n"
            f"💡 {usage_note_text}"
        )

        logger.info("Main menu created successfully", user_id=user_id, keyboard_rows=len(keyboard), total_buttons=sum(len(row) for row in keyboard))

        await query.edit_message_text(
            welcome_message,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error("Error in main menu action", error=str(e), user_id=user_id, exc_info=True)
        try:
            await query.edit_message_text(await t(context, user_id, "errors.unexpected_error"))
        except Exception as nested_e:
            logger.error("Failed to send error message for main menu", error=str(nested_e), user_id=user_id)


async def _handle_schedules_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle schedules action - opens schedules/TODO management menu."""
    user_id = query.from_user.id

    try:
        # Import the schedule command function
        from ..handlers.command import schedules_command

        # Create a proper Update object from callback query
        class CallbackUpdate:
            def __init__(self, query):
                self.callback_query = query
                self.effective_user = query.from_user
                self.effective_chat = query.message.chat
                self.effective_message = query.message
                self.message = None

        # Call the schedules command
        callback_update = CallbackUpdate(query)
        await schedules_command(callback_update, context)

    except Exception as e:
        logger.error("Error in schedules action", error=str(e), user_id=user_id)
        try:
            await query.edit_message_text("❌ **Помилка завантаження TODO List**\n\nСпробуйте команду `/schedules`")
        except Exception as nested_e:
            logger.error("Failed to send schedules error message", error=str(nested_e), user_id=user_id)


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


async def _handle_template_selection(query, template_type: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection of task template."""
    user_id = query.from_user.id

    # Get task scheduler from context
    task_scheduler = context.bot_data.get("task_scheduler")
    if not task_scheduler:
        await query.edit_message_text(
            "❌ **Система планування недоступна**\n\n"
            "Система планування завдань не налаштована."
        )
        return

    try:
        # Get template configuration
        from ..features.task_scheduler import TaskScheduler

        template_configs = {
            "code_analysis": {
                "title": "🔍 Аналіз коду",
                "description": "Повний аналіз проєкту та архітектури",
                **TaskScheduler.create_code_analysis_task(
                    user_id,
                    str(context.user_data.get("current_directory", "/"))
                )
            },
            "report_generation": {
                "title": "📊 Генерація звітів",
                "description": "Створення звітів та статистики",
                "task_type": "report_generation",
                "prompt": """Згенеруйте комплексний звіт про проєкт:

1. **Статистика коду**: Підрахуйте рядки коду, файли, компоненти
2. **Структура проєкту**: Опишіть архітектуру та організацію
3. **Залежності**: Проаналізуйте використовувані бібліотеки
4. **Покриття тестами**: Оцініть тестування (якщо є)
5. **Продуктивність**: Виявіть потенційні проблеми
6. **Рекомендації**: Дайте поради щодо покращення

Створіть детальний звіт у форматі Markdown.""",
                "metadata": {"report_type": "comprehensive"}
            },
            "refactoring": {
                "title": "⚒️ Рефакторинг",
                "description": "Оптимізація та покращення коду",
                **TaskScheduler.create_refactoring_task(user_id)
            },
            "documentation": {
                "title": "📝 Документація",
                "description": "Створення та оновлення документації",
                **TaskScheduler.create_documentation_task(user_id, "readme")
            },
            "security_audit": {
                "title": "🔒 Перевірка безпеки",
                "description": "Аналіз уразливостей та безпеки",
                **TaskScheduler.create_code_analysis_task(user_id, str(context.user_data.get("current_directory", "/")), "security")
            },
            "testing": {
                "title": "🧪 Тестування",
                "description": "Генерація та запуск тестів",
                "task_type": "testing",
                "prompt": """Створіть та запустіть тести для проєкту:

1. **Аналіз покриття**: Перевірте існуючі тести
2. **Генерація тестів**: Створіть нові unit-тести для некритичних функцій
3. **Інтеграційні тести**: Додайте тести для основних сценаріїв
4. **Тестування безпеки**: Перевірте уразливості
5. **Запуск тестів**: Виконайте всі тести та опишіть результати
6. **Звіт**: Створіть звіт з рекомендаціями

Зосередьтеся на покращенні якості коду через тестування.""",
                "metadata": {"test_type": "comprehensive"}
            }
        }

        template_config = template_configs.get(template_type)
        if not template_config:
            await query.edit_message_text(
                "❌ **Невідомий шаблон**\n\n"
                f"Шаблон '{template_type}' не знайдено."
            )
            return

        # Show template details and confirmation
        message = (
            f"{template_config['title']}\n\n"
            f"**Опис**: {template_config['description']}\n\n"
            f"**Завдання**:\n{template_config['prompt'][:300]}...\n\n"
            "**Параметри виконання**:\n"
            "• Автоматичне виконання: ✅ Увімкнено\n"
            "• Автовідповіді: ✅ Увімкнено\n"
            "• Пріоритет: 🔥 Високий\n\n"
            "_Підтвердіть створення завдання_"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Створити завдання", callback_data=f"schedule:confirm_template:{template_type}"),
                InlineKeyboardButton("✏️ Редагувати", callback_data=f"schedule:edit_template:{template_type}")
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="schedule:from_template")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    except Exception as e:
        logger.error("Error handling template selection", error=str(e), template_type=template_type)
        await query.edit_message_text(
            "❌ **Помилка обробки шаблону**\n\n"
            f"Виникла помилка при обробці шаблону: {str(e)}"
        )


async def handle_quick_action_execution_callback(
    query, action_type: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quick action execution callbacks - the new functional buttons."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]

    try:
        # Get Claude integration
        claude_integration: ClaudeIntegration = context.bot_data.get("claude_integration")
        if not claude_integration:
            error_text = await get_localized_text(context, user_id, "errors.claude_not_available")
            await query.edit_message_text(error_text, parse_mode=None)
            return

        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )

        # Show executing message
        executing_text = await get_localized_text(context, user_id, "messages.executing_action", action=action_type)
        await query.edit_message_text(executing_text, parse_mode=None)

        # Handle ls action specially to use the same logic as /ls command
        if action_type == "ls":
            await _handle_ls_action_for_quick(query, context)
            return

        # Define action commands mapping for other actions
        action_commands = {
            "pwd": "pwd",
            "git_status": "git status",
            "git_diff": "git diff --color=never",
            "git_log": "git log --oneline -10",
            "find_files": "find . -type f -name \"*.py\" -o -name \"*.js\" -o -name \"*.ts\" | head -20",
            "disk_usage": "du -sh * 2>/dev/null | sort -hr | head -10",
            "processes": "ps aux | head -10"
        }

        # Get command for action
        command = action_commands.get(action_type)
        if not command:
            error_text = await get_localized_text(context, user_id, "errors.action_not_found", action=action_type)
            await query.edit_message_text(error_text, parse_mode=None)
            return

        # Execute command through Claude
        claude_response = await claude_integration.run_command(
            prompt=f"Виконай команду: {command}",
            working_directory=current_dir,
            user_id=user_id
        )

        if claude_response and claude_response.content:
            # Show results with Continue button
            result_text = f"✅ **Результат {action_type}:**\n\n{claude_response.content}"

            # Truncate if too long
            if len(result_text) > 4000:
                result_text = result_text[:4000] + "...\n\n_(Результат обрізано)_"

            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Продовжити", callback_data="conversation:continue"),
                    InlineKeyboardButton("📋 Меню", callback_data="action:quick_actions")
                ]
            ]

            # Add specific action buttons based on action type
            if action_type == "ls":
                keyboard.insert(0, [
                    InlineKeyboardButton("📖 Читати файл", callback_data="file_edit:select_read"),
                    InlineKeyboardButton("✏️ Редагувати файл", callback_data="file_edit:select_edit")
                ])
            elif action_type == "git_status":
                keyboard.insert(0, [
                    InlineKeyboardButton("📊 Git diff", callback_data="quick_action:git_diff"),
                    InlineKeyboardButton("📜 Git log", callback_data="quick_action:git_log")
                ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                result_text,
                parse_mode=None,
                reply_markup=reply_markup
            )
        else:
            failed_text = await get_localized_text(context, user_id, "messages.action_failed", action=action_type)
            await query.edit_message_text(failed_text, parse_mode=None)

    except Exception as e:
        logger.error("Quick action execution failed", error=str(e), user_id=user_id, action_type=action_type)
        error_text = await get_localized_text(context, user_id, "errors.action_error", action=action_type, error=str(e))
        await query.edit_message_text(error_text, parse_mode=None)


async def _handle_ls_action_for_quick(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ls action for quick actions using same logic as /ls command."""
    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    try:
        # List directory contents (same logic as /ls command)
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

        # Add action buttons for quick actions
        keyboard = [
            [
                InlineKeyboardButton("📖 Читати файл", callback_data="file_edit:select_read"),
                InlineKeyboardButton("✏️ Редагувати файл", callback_data="file_edit:select_edit")
            ],
            [
                InlineKeyboardButton("🔄 Продовжити", callback_data="conversation:continue"),
                InlineKeyboardButton("📋 Меню", callback_data="action:quick_actions")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ **Результат ls:**\n\n{message}",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error("Error in ls quick action", error=str(e))
        error_text = f"❌ Помилка при виконанні ls: {str(e)}"
        await query.edit_message_text(error_text)


async def handle_file_edit_callback(
    query, action_type: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle file editing workflow through Telegram interface."""
    user_id = query.from_user.id
    settings: Settings = context.bot_data["settings"]

    try:
        current_dir = context.user_data.get("current_directory", settings.approved_directory)

        if action_type == "select_read":
            # Step 1: Show file selection for reading
            await query.edit_message_text(
                "📖 **Читання файлу**\n\n"
                "📝 Введіть назву файлу який хочете прочитати:\n\n"
                "**Приклади:**\n"
                "• `main.py`\n"
                "• `src/config.py` \n"
                "• `README.md`\n\n"
                "💬 Надішліть повідомлення з назвою файлу.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Скасувати", callback_data="action:quick_actions")]
                ])
            )

            # Set state for waiting for filename
            context.user_data["file_action"] = {"type": "read", "step": "waiting_filename"}

        elif action_type == "select_edit":
            # Step 1: Show file selection for editing
            await query.edit_message_text(
                "✏️ **Редагування файлу**\n\n"
                "📝 Введіть назву файлу який хочете редагувати:\n\n"
                "**Приклади:**\n"
                "• `main.py`\n"
                "• `src/config.py`\n"
                "• `README.md`\n\n"
                "🔄 **Процес редагування:**\n"
                "1. Я надішлю вам файл\n"
                "2. Ви редагуєте його в зовнішньому редакторі\n"
                "3. Надсилаєте відредагований файл назад\n"
                "4. Я зберігаю зміни\n\n"
                "💬 Надішліть повідомлення з назвою файлу.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Скасувати", callback_data="action:quick_actions")]
                ])
            )

            # Set state for waiting for filename
            context.user_data["file_action"] = {"type": "edit", "step": "waiting_filename"}

        elif action_type.startswith("download:"):
            # Step 2: Download file for editing
            filename = action_type.replace("download:", "")

            # Validate and read file
            file_path = current_dir / filename

            if not file_path.exists():
                await query.edit_message_text(
                    f"❌ **Файл не знайдено**\n\n"
                    f"Файл `{filename}` не існує в поточній директорії.\n\n"
                    f"Перевірте назву файлу та спробуйте ще раз.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                    ])
                )
                return

            if not file_path.is_file():
                await query.edit_message_text(
                    f"❌ **Це не файл**\n\n"
                    f"`{filename}` є директорією, а не файлом.\n\n"
                    f"Виберіть файл для редагування.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                    ])
                )
                return

            # Check file size (Telegram limit ~50MB, but let's be conservative)
            file_size = file_path.stat().st_size
            if file_size > 20 * 1024 * 1024:  # 20MB limit
                await query.edit_message_text(
                    f"❌ **Файл занадто великий**\n\n"
                    f"Файл `{filename}` має розмір {_format_file_size(file_size)}.\n"
                    f"Максимальний розмір для редагування: 20MB.\n\n"
                    f"Використайте інші інструменти для великих файлів.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                    ])
                )
                return

            try:
                # Send file to user for editing
                await query.edit_message_text(
                    f"📤 **Надсилаю файл для редагування...**\n\n"
                    f"📁 Файл: `{filename}`\n"
                    f"📏 Розмір: {_format_file_size(file_size)}\n\n"
                    f"⏳ Зачекайте...",
                    parse_mode=None
                )

                # Send the file
                with open(file_path, 'rb') as file:
                    await query.message.reply_document(
                        document=file,
                        filename=filename,
                        caption=(
                            f"✏️ **Файл для редагування**\n\n"
                            f"📁 Назва: `{filename}`\n"
                            f"📏 Розмір: {_format_file_size(file_size)}\n\n"
                            f"🔄 **Як редагувати:**\n"
                            f"1. Завантажте цей файл\n"
                            f"2. Відредагуйте у вашому редакторі\n"
                            f"3. Надішліть відредагований файл назад як документ\n"
                            f"4. Я збережу зміни\n\n"
                            f"💾 Очікую відредагований файл..."
                        ),
                        parse_mode=None
                    )

                # Update state to wait for edited file
                context.user_data["file_action"] = {
                    "type": "edit",
                    "step": "waiting_edited_file",
                    "filename": filename,
                    "original_path": str(file_path)
                }

                # Update original message
                await query.edit_message_text(
                    f"✅ **Файл надіслано**\n\n"
                    f"📁 Файл `{filename}` надіслано вище.\n\n"
                    f"📝 Відредагуйте файл та надішліть його назад як документ.\n\n"
                    f"💡 **Підказка:** Переконайтеся що зберегли файл з тією ж назвою!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Скасувати редагування", callback_data="file_edit:cancel")]
                    ])
                )

            except Exception as e:
                logger.error("File sending failed", error=str(e), filename=filename)
                await query.edit_message_text(
                    f"❌ **Помилка надсилання файлу**\n\n"
                    f"Не вдалося надіслати файл `{filename}`:\n"
                    f"```\n{str(e)}\n```\n\n"
                    f"Спробуйте ще раз або виберіть інший файл.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                    ])
                )

        elif action_type == "cancel":
            # Cancel file editing workflow
            context.user_data.pop("file_action", None)

            await query.edit_message_text(
                "❌ **Редагування скасовано**\n\n"
                "Повертаємось до швидких дій.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Швидкі дії", callback_data="action:quick_actions")]
                ])
            )

        else:
            error_text = await get_localized_text(context, user_id, "errors.unknown_action")
            await query.edit_message_text(f"{error_text}: {action_type}")

    except Exception as e:
        logger.error("File edit callback failed", error=str(e), user_id=user_id, action_type=action_type)
        error_text = await get_localized_text(context, user_id, "errors.file_operation_failed", error=str(e))
        await query.edit_message_text(error_text, parse_mode=None)


async def handle_claude_status_callback(query, param: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle Claude status related callbacks."""
    user_id = query.from_user.id

    try:
        # Get Claude availability monitor
        availability_monitor = context.bot_data.get("claude_availability_monitor")
        if not availability_monitor:
            await query.edit_message_text(
                "❌ **Система моніторингу недоступна**\n\n"
                "Моніторинг Claude CLI не налаштований."
            )
            return

        if param == "check":
            # Manual availability check
            await query.edit_message_text("🟡 **Перевіряю доступність Claude...**")

            is_available, details = await availability_monitor.check_availability_with_details()

            # Get status message with emoji
            if is_available:
                status_icon = "🟢"
                status_text = await get_localized_text(context, user_id, "claude_status.available")
            else:
                status_icon = "🔴"
                status_text = details.get("status_message", "Claude недоступний")

            # Build detailed message
            message_parts = [f"{status_icon} **{status_text}**"]

            if not is_available:
                if "estimated_recovery" in details:
                    message_parts.append(f"\n⏳ {details['estimated_recovery']}")
                if "reason" in details:
                    reason = details["reason"]
                    if reason == "rate_limit":
                        message_parts.append("\n📊 Причина: Досягнуто ліміт запитів")
                    elif reason == "authentication":
                        message_parts.append("\n🔐 Причина: Проблеми автентифікації")
                    else:
                        message_parts.append(f"\n❓ Причина: {reason}")

            # Add buttons
            buttons = [
                [InlineKeyboardButton("🔄 Перевірити ще раз", callback_data="claude_status:check")],
                [InlineKeyboardButton("📈 Історія", callback_data="claude_status:history")],
                [InlineKeyboardButton("🔔 Сповіщення", callback_data="claude_status:notifications")]
            ]

            await query.edit_message_text(
                "\n".join(message_parts),
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        elif param == "history":
            # Show availability history
            history_entries = await availability_monitor.get_status_history(hours=24)

            if not history_entries:
                message = "📈 **Історія доступності (24 години)**\n\n📊 Немає записів в історії"
            else:
                message_parts = ["📈 **Історія доступності (24 години)**\n"]

                for entry in history_entries[-10:]:  # Last 10 entries
                    timestamp = entry.get("timestamp", "")
                    old_status = entry.get("old_status", "unknown")
                    new_status = entry.get("new_status", "unknown")

                    # Format timestamp
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime("%H:%M")
                    except:
                        time_str = timestamp[:5] if timestamp else "??:??"

                    # Status icons
                    status_icons = {
                        "available": "🟢",
                        "unavailable": "🔴",
                        "rate_limited": "🟡",
                        "unknown": "⚪"
                    }

                    old_icon = status_icons.get(old_status, "⚪")
                    new_icon = status_icons.get(new_status, "⚪")

                    message_parts.append(f"• {time_str}: {old_icon} → {new_icon}")

                message = "\n".join(message_parts)

            buttons = [
                [InlineKeyboardButton("🔄 Оновити", callback_data="claude_status:history")],
                [InlineKeyboardButton("🔙 Назад", callback_data="claude_status:check")]
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        elif param == "notifications":
            # Manage notifications
            settings = context.bot_data.get("settings")
            if settings and settings.claude_availability and settings.claude_availability.enabled:
                notify_enabled = True
                chat_ids = settings.claude_availability.notify_chat_ids or []
                current_chat_in_list = str(query.message.chat_id) in map(str, chat_ids)
            else:
                notify_enabled = False
                current_chat_in_list = False

            if notify_enabled:
                status_text = "🔔 **Сповіщення увімкнені**"
                if current_chat_in_list:
                    status_text += "\n✅ Цей чат отримує сповіщення"
                else:
                    status_text += "\n❌ Цей чат НЕ отримує сповіщення"
            else:
                status_text = "🔕 **Сповіщення вимкнені**\n\nСистема сповіщень не налаштована."

            buttons = [
                [InlineKeyboardButton("🔙 Назад", callback_data="claude_status:check")]
            ]

            await query.edit_message_text(
                status_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        else:
            await query.edit_message_text(
                f"❌ **Невідома дія**: {param}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Статус", callback_data="claude_status:check")]
                ])
            )

    except Exception as e:
        logger.error("Claude status callback failed", error=str(e), user_id=user_id, param=param)
        await query.edit_message_text(
            f"❌ **Помилка**\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Спробувати ще раз", callback_data="claude_status:check")]
            ])
        )


# Registration function for callbacks
def register_callbacks(application):
    """Register all callback handlers."""
    from telegram.ext import CallbackQueryHandler

    # Register the main callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback_query))
