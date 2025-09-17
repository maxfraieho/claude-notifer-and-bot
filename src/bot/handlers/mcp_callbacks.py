"""MCP Callback Handlers for Telegram Bot Inline Keyboards.

Handles all MCP-related callback queries from inline keyboards.
"""

import json
from typing import Any, Dict, Optional

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.localization.util import t, get_user_id
from src.mcp.context_handler import MCPContextHandler
from src.mcp.exceptions import MCPError, MCPServerNotFoundError, MCPValidationError
from src.mcp.manager import MCPManager, MCPServerConfig
from src.mcp.server_configs import server_config_registry

logger = structlog.get_logger()


async def handle_mcp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route MCP callback queries to appropriate handlers."""
    query = update.callback_query
    await query.answer()

    user_id = get_user_id(update)
    if not user_id:
        return

    callback_data = query.data

    try:
        if callback_data.startswith("mcp_add_"):
            await _handle_add_callbacks(update, context, callback_data)
        elif callback_data.startswith("mcp_manage:"):
            await _handle_manage_callbacks(update, context, callback_data)
        elif callback_data.startswith("mcp_set_context:"):
            await _handle_context_callbacks(update, context, callback_data)
        elif callback_data.startswith("mcp_confirm_remove:"):
            await _handle_remove_callbacks(update, context, callback_data)
        elif callback_data in ["mcp_list", "mcp_refresh_all", "mcp_system_status", 
                             "mcp_select_context", "mcp_clear_context", "mcp_cancel"]:
            await _handle_general_callbacks(update, context, callback_data)
        else:
            logger.warning("Unknown MCP callback", callback_data=callback_data, user_id=user_id)

    except Exception as e:
        logger.error("Error handling MCP callback", 
                    callback_data=callback_data, user_id=user_id, error=str(e))
        await query.edit_message_text(
            await t(context, user_id, "mcp.errors.callback_failed", error=str(e))
        )


async def _handle_add_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle server addition callbacks."""
    query = update.callback_query
    user_id = get_user_id(update)

    mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
    if not mcp_manager:
        await query.edit_message_text(await t(context, user_id, "mcp.errors.system_not_available"))
        return

    if callback_data == "mcp_add_wizard":
        # Show server type selection
        await _show_server_type_selection(update, context)

    elif callback_data.startswith("mcp_add_type:"):
        # Start server configuration wizard
        server_type = callback_data.split(":", 1)[1]
        await _start_server_wizard(update, context, server_type)


async def _handle_manage_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle server management callbacks."""
    query = update.callback_query
    user_id = get_user_id(update)

    server_name = callback_data.split(":", 1)[1]

    mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
    if not mcp_manager:
        await query.edit_message_text(await t(context, user_id, "mcp.errors.system_not_available"))
        return

    # Get server info
    servers = await mcp_manager.get_user_servers(user_id)
    server = next((s for s in servers if s['server_name'] == server_name), None)

    if not server:
        await query.edit_message_text(
            await t(context, user_id, "mcp.errors.server_not_found", server_name=server_name)
        )
        return

    # Build management menu
    await _show_server_management_menu(update, context, server, mcp_manager)


async def _handle_context_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle context selection callbacks."""
    query = update.callback_query
    user_id = get_user_id(update)

    server_name = callback_data.split(":", 1)[1]

    mcp_context_handler: MCPContextHandler = context.bot_data.get("mcp_context_handler")
    if not mcp_context_handler:
        await query.edit_message_text(await t(context, user_id, "mcp.errors.system_not_available"))
        return

    try:
        await mcp_context_handler.set_active_context(user_id, server_name)
        await query.edit_message_text(
            await t(context, user_id, "mcp.select.success", server_name=server_name)
        )
    except (MCPServerNotFoundError, MCPError) as e:
        await query.edit_message_text(
            await t(context, user_id, "mcp.select.failed", error=str(e))
        )


async def _handle_remove_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle server removal callbacks."""
    query = update.callback_query
    user_id = get_user_id(update)

    server_name = callback_data.split(":", 1)[1]

    mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
    if not mcp_manager:
        await query.edit_message_text(await t(context, user_id, "mcp.errors.system_not_available"))
        return

    try:
        success = await mcp_manager.remove_server(user_id, server_name)
        if success:
            await query.edit_message_text(
                await t(context, user_id, "mcp.remove.success", server_name=server_name)
            )
        else:
            await query.edit_message_text(
                await t(context, user_id, "mcp.remove.failed", error="Unknown error")
            )
    except Exception as e:
        await query.edit_message_text(
            await t(context, user_id, "mcp.remove.failed", error=str(e))
        )


async def _handle_general_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """Handle general MCP callbacks."""
    query = update.callback_query
    user_id = get_user_id(update)

    if callback_data == "mcp_list":
        # Redirect to list command
        from .mcp_commands import mcplist_command
        await mcplist_command(update, context)

    elif callback_data == "mcp_system_status":
        # Redirect to status command
        from .mcp_commands import mcpstatus_command
        await mcpstatus_command(update, context)

    elif callback_data == "mcp_select_context":
        # Show context selection
        mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
        mcp_context_handler: MCPContextHandler = context.bot_data.get("mcp_context_handler")

        if mcp_manager and mcp_context_handler:
            await _show_context_selection_menu(update, context, mcp_manager, mcp_context_handler)
        else:
            await query.edit_message_text(await t(context, user_id, "mcp.errors.system_not_available"))

    elif callback_data == "mcp_clear_context":
        # Clear active context
        mcp_context_handler: MCPContextHandler = context.bot_data.get("mcp_context_handler")

        if mcp_context_handler:
            await mcp_context_handler.clear_active_context(user_id)
            await query.edit_message_text(await t(context, user_id, "mcp.select.context_cleared"))
        else:
            await query.edit_message_text(await t(context, user_id, "mcp.errors.system_not_available"))

    elif callback_data == "mcp_refresh_all":
        # Refresh all server statuses
        await _refresh_all_servers(update, context)

    elif callback_data == "mcp_cancel":
        # Cancel current operation
        await query.edit_message_text(await t(context, user_id, "mcp.general.cancelled"))


# Helper functions for UI components

async def _show_server_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show server type selection menu."""
    query = update.callback_query
    user_id = get_user_id(update)

    templates = server_config_registry.get_template_list()

    keyboard = []
    for template in templates:
        keyboard.append([
            InlineKeyboardButton(
                template["display_name"],
                callback_data=f"mcp_add_type:{template['server_type']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            await t(context, user_id, "mcp.buttons.cancel"),
            callback_data="mcp_cancel"
        )
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        await t(context, user_id, "mcp.add.select_type"),
        reply_markup=reply_markup
    )


async def _start_server_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE, server_type: str) -> None:
    """Start interactive server configuration wizard."""
    query = update.callback_query
    user_id = get_user_id(update)

    template = server_config_registry.get_template(server_type)
    if not template:
        await query.edit_message_text(
            await t(context, user_id, "mcp.add.invalid_type", server_type=server_type)
        )
        return

    # Initialize wizard state
    wizard_state = {
        "server_type": server_type,
        "template": template,
        "steps": template.get_setup_steps(),
        "current_step": 0,
        "user_inputs": {},
        "message_id": query.message.message_id
    }

    # Store wizard state in user data
    context.user_data["mcp_wizard"] = wizard_state

    # Show first step
    await _show_wizard_step(update, context, wizard_state)


async def _show_wizard_step(update: Update, context: ContextTypes.DEFAULT_TYPE, wizard_state: Dict[str, Any]) -> None:
    """Show current wizard step."""
    query = update.callback_query
    user_id = get_user_id(update)

    current_step = wizard_state["current_step"]
    steps = wizard_state["steps"]

    if current_step >= len(steps):
        # Wizard complete - build and add server
        await _complete_server_wizard(update, context, wizard_state)
        return

    step = steps[current_step]

    # Build step message
    title = await t(context, user_id, "mcp.add.wizard.title", 
                   server_type=wizard_state["template"].display_name)
    step_info = await t(context, user_id, "mcp.add.wizard.step", 
                       current=current_step + 1, total=len(steps))

    text_lines = [title, "", step_info, "", f"**{step['title']}**", step['description']]

    if step.get('help_text'):
        text_lines.extend(["", step['help_text']])

    # Create keyboard for input or show input prompt
    keyboard = []

    if step.get('default'):
        keyboard.append([
            InlineKeyboardButton(
                f"✅ {step['default']}",
                callback_data=f"mcp_wizard_input:{step['default']}"
            )
        ])

    keyboard.extend([
        [InlineKeyboardButton(
            await t(context, user_id, "mcp.buttons.cancel"),
            callback_data="mcp_cancel"
        )]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Update message
    await query.edit_message_text(
        "\n".join(text_lines),
        reply_markup=reply_markup,
        parse_mode=None
    )

    # Set waiting for input flag
    wizard_state["waiting_for_input"] = True
    wizard_state["current_step_data"] = step


async def _complete_server_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE, wizard_state: Dict[str, Any]) -> None:
    """Complete server configuration wizard."""
    query = update.callback_query
    user_id = get_user_id(update)

    template = wizard_state["template"]
    user_inputs = wizard_state["user_inputs"]

    try:
        # Validate configuration
        is_valid, error_msg = template.validate_config(user_inputs)
        if not is_valid:
            await query.edit_message_text(
                await t(context, user_id, "mcp.add.wizard.failed", error=error_msg)
            )
            return

        # Build server configuration
        server_config_dict = template.build_server_config(user_inputs)
        server_config = MCPServerConfig(**server_config_dict)

        # Add server via manager
        mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
        if not mcp_manager:
            await query.edit_message_text(await t(context, user_id, "mcp.errors.system_not_available"))
            return

        success = await mcp_manager.add_server(user_id, server_config)

        if success:
            await query.edit_message_text(
                await t(context, user_id, "mcp.add.wizard.success", server_name=server_config.name)
            )
        else:
            await query.edit_message_text(
                await t(context, user_id, "mcp.add.wizard.failed", error="Unknown error")
            )

    except (MCPValidationError, MCPError) as e:
        await query.edit_message_text(
            await t(context, user_id, "mcp.add.wizard.failed", error=str(e))
        )
    finally:
        # Clear wizard state
        if context.user_data and "mcp_wizard" in context.user_data:
            del context.user_data["mcp_wizard"]


async def _show_server_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     server: Dict[str, Any], mcp_manager: MCPManager) -> None:
    """Show server management menu."""
    query = update.callback_query
    user_id = get_user_id(update)

    server_name = server['server_name']
    server_type = server['server_type']
    display_name = server.get('display_name', server_type)
    status = server['status']
    is_enabled = server['is_enabled']

    # Build info text
    title = await t(context, user_id, "mcp.manage.title", server_name=server_name)
    info = await t(context, user_id, "mcp.manage.server_info", 
                  server_type=display_name, status=status, enabled="✅" if is_enabled else "❌")

    text_lines = [title, "", info]

    if server.get('last_status_check'):
        last_check = server['last_status_check'].strftime('%d.%m %H:%M')
        text_lines.append(await t(context, user_id, "mcp.manage.last_check", time=last_check))

    if server.get('error_message'):
        error_msg = server['error_message'][:100]
        text_lines.append(await t(context, user_id, "mcp.manage.error_details", error=error_msg))

    # Build keyboard
    keyboard = []

    if is_enabled:
        keyboard.append([
            InlineKeyboardButton(
                await t(context, user_id, "mcp.buttons.disable_server"),
                callback_data=f"mcp_disable:{server_name}"
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                await t(context, user_id, "mcp.buttons.enable_server"),
                callback_data=f"mcp_enable:{server_name}"
            )
        ])

    keyboard.extend([
        [
            InlineKeyboardButton(
                await t(context, user_id, "mcp.buttons.test_connection"),
                callback_data=f"mcp_test:{server_name}"
            ),
            InlineKeyboardButton(
                await t(context, user_id, "mcp.buttons.refresh_status"),
                callback_data=f"mcp_refresh:{server_name}"
            )
        ],
        [
            InlineKeyboardButton(
                await t(context, user_id, "mcp.buttons.remove_server"),
                callback_data=f"mcp_confirm_remove:{server_name}"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ " + await t(context, user_id, "mcp.buttons.back_to_list"),
                callback_data="mcp_list"
            )
        ]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "\n".join(text_lines),
        reply_markup=reply_markup,
        parse_mode=None
    )


async def _show_context_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     mcp_manager: MCPManager, mcp_context_handler: MCPContextHandler) -> None:
    """Show context selection menu."""
    query = update.callback_query
    user_id = get_user_id(update)

    # Get enabled servers
    servers = await mcp_manager.get_user_servers(user_id)
    enabled_servers = [s for s in servers if s['is_enabled']]

    if not enabled_servers:
        await query.edit_message_text(await t(context, user_id, "mcp.select.no_enabled_servers"))
        return

    # Get current active context
    active_context = await mcp_context_handler.get_active_context(user_id)
    active_server = active_context.get('selected_server') if active_context else None

    keyboard = []
    for server in enabled_servers:
        server_name = server['server_name']
        display_name = server.get('display_name', server['server_type'])

        # Mark active server
        text = f"🎯 {display_name}" if server_name == active_server else display_name

        keyboard.append([
            InlineKeyboardButton(
                text,
                callback_data=f"mcp_set_context:{server_name}"
            )
        ])

    # Add clear context option if there is an active context
    if active_context:
        keyboard.append([
            InlineKeyboardButton(
                await t(context, user_id, "mcp.buttons.clear_context"),
                callback_data="mcp_clear_context"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        await t(context, user_id, "mcp.select.choose_context"),
        reply_markup=reply_markup
    )


async def _refresh_all_servers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh status of all servers."""
    query = update.callback_query
    user_id = get_user_id(update)

    mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
    if not mcp_manager:
        await query.edit_message_text(await t(context, user_id, "mcp.errors.system_not_available"))
        return

    # Show loading message
    await query.edit_message_text(await t(context, user_id, "mcp.status.checking"))

    try:
        # Get all user servers
        servers = await mcp_manager.get_user_servers(user_id)

        # Refresh status for each enabled server
        refresh_count = 0
        for server in servers:
            if server['is_enabled']:
                try:
                    await mcp_manager.get_server_status(user_id, server['server_name'])
                    refresh_count += 1
                except Exception as e:
                    logger.error("Failed to refresh server status", 
                               server_name=server['server_name'], error=str(e))

        # Redirect back to list
        from .mcp_commands import mcplist_command
        await mcplist_command(update, context)

    except Exception as e:
        await query.edit_message_text(
            await t(context, user_id, "mcp.errors.refresh_failed", error=str(e))
        )
