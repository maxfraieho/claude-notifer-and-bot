"""MCP Command Handlers for Telegram Bot.

Handles all MCP-related commands: /mcpadd, /mcplist, /mcpselect, /mcpask, /mcpremove, /mcpstatus
"""

import asyncio
from typing import Dict, List, Optional

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ...localization.util import t, get_user_id
from ...mcp.context_handler import MCPContextHandler
from ...mcp.exceptions import (
    MCPContextError,
    MCPError,
    MCPServerNotFoundError,
    MCPValidationError,
)
from ...mcp.manager import MCPManager, MCPServerConfig
from ...mcp.server_configs import server_config_registry

logger = structlog.get_logger()


async def mcpadd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mcpadd command - Add new MCP server."""
    user_id = get_user_id(update)
    message = update.effective_message

    if not user_id or not message:
        return

    try:
        mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
        if not mcp_manager:
            await message.reply_text(await t(context, user_id, "mcp.errors.system_not_available"))
            return

        # Check if user provided server type as argument
        args = context.args or []

        if args:
            # Quick add with command line arguments
            await _handle_quick_add(update, context, args[0], mcp_manager)
        else:
            # Interactive wizard
            await _show_server_type_selection(update, context, mcp_manager)

    except Exception as e:
        logger.error("Error in mcpadd command", user_id=user_id, error=str(e))
        await message.reply_text(await t(context, user_id, "mcp.errors.add_failed", error=str(e)))


async def mcplist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mcplist command - List user's MCP servers."""
    user_id = get_user_id(update)
    message = update.effective_message

    if not user_id or not message:
        return

    try:
        mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
        if not mcp_manager:
            await message.reply_text(await t(context, user_id, "mcp.errors.system_not_available"))
            return

        # Get user's servers
        servers = await mcp_manager.get_user_servers(user_id)

        if not servers:
            # No servers configured
            keyboard = [
                [InlineKeyboardButton(
                    await t(context, user_id, "mcp.buttons.add_first_server"), 
                    callback_data="mcp_add_wizard"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(
                await t(context, user_id, "mcp.list.no_servers"),
                reply_markup=reply_markup
            )
            return

        # Build servers list
        text_lines = [await t(context, user_id, "mcp.list.title")]
        text_lines.append("")

        keyboard = []
        for server in servers:
            # Status emoji
            if server['is_enabled']:
                if server['status'] == 'active':
                    status_emoji = "✅"
                elif server['status'] == 'error':
                    status_emoji = "❌"
                else:
                    status_emoji = "🔧"
            else:
                status_emoji = "⚪"

            server_name = server['server_name']
            display_name = server.get('display_name', server['server_type'])

            text_lines.append(f"{status_emoji} **{server_name}** - {display_name}")

            if server['status'] == 'active':
                text_lines.append(f"   {await t(context, user_id, 'mcp.list.status_active')}")
            elif server['status'] == 'error':
                error_msg = server.get('error_message', 'Unknown error')[:50]
                text_lines.append(f"   {await t(context, user_id, 'mcp.list.status_error', error=error_msg)}")
            elif not server['is_enabled']:
                text_lines.append(f"   {await t(context, user_id, 'mcp.list.status_disabled')}")
            else:
                text_lines.append(f"   {await t(context, user_id, 'mcp.list.status_inactive')}")

            if server.get('last_used'):
                last_used = server['last_used'].strftime('%d.%m %H:%M')
                text_lines.append(f"   {await t(context, user_id, 'mcp.list.last_used', time=last_used)}")

            text_lines.append("")

            # Add server control button
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ {server_name}",
                    callback_data=f"mcp_manage:{server_name}"
                )
            ])

        # Add control buttons
        keyboard.extend([
            [
                InlineKeyboardButton(
                    await t(context, user_id, "mcp.buttons.add_server"),
                    callback_data="mcp_add_wizard"
                ),
                InlineKeyboardButton(
                    await t(context, user_id, "mcp.buttons.refresh_status"),
                    callback_data="mcp_refresh_all"
                )
            ],
            [
                InlineKeyboardButton(
                    await t(context, user_id, "mcp.buttons.system_status"),
                    callback_data="mcp_system_status"
                )
            ]
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(
            "\n".join(text_lines),
            reply_markup=reply_markup,
            parse_mode=None
        )

    except Exception as e:
        logger.error("Error in mcplist command", user_id=user_id, error=str(e))
        await message.reply_text(await t(context, user_id, "mcp.errors.list_failed", error=str(e)))


async def mcpselect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mcpselect command - Select active MCP context."""
    user_id = get_user_id(update)
    message = update.effective_message

    if not user_id or not message:
        return

    try:
        mcp_context_handler: MCPContextHandler = context.bot_data.get("mcp_context_handler")
        mcp_manager: MCPManager = context.bot_data.get("mcp_manager")

        if not mcp_context_handler or not mcp_manager:
            await message.reply_text(await t(context, user_id, "mcp.errors.system_not_available"))
            return

        args = context.args or []

        if args:
            # Direct selection
            server_name = args[0]
            try:
                await mcp_context_handler.set_active_context(user_id, server_name)
                await message.reply_text(
                    await t(context, user_id, "mcp.select.success", server_name=server_name)
                )
            except (MCPServerNotFoundError, MCPContextError) as e:
                await message.reply_text(
                    await t(context, user_id, "mcp.select.failed", error=str(e))
                )
        else:
            # Show selection menu
            await _show_context_selection_menu(update, context, mcp_manager, mcp_context_handler)

    except Exception as e:
        logger.error("Error in mcpselect command", user_id=user_id, error=str(e))
        await message.reply_text(await t(context, user_id, "mcp.errors.select_failed", error=str(e)))


async def mcpask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mcpask command - Execute query with MCP context."""
    user_id = get_user_id(update)
    message = update.effective_message

    if not user_id or not message:
        return

    try:
        mcp_context_handler: MCPContextHandler = context.bot_data.get("mcp_context_handler")

        if not mcp_context_handler:
            await message.reply_text(await t(context, user_id, "mcp.errors.system_not_available"))
            return

        # Get query from command arguments
        query = " ".join(context.args or [])
        if not query:
            await message.reply_text(await t(context, user_id, "mcp.ask.no_query"))
            return

        # Check active context
        active_context = await mcp_context_handler.get_active_context(user_id)
        if not active_context:
            # Show context selection
            await _show_context_selection_for_query(update, context, query)
            return

        # Execute query
        await _execute_mcp_query(update, context, query, mcp_context_handler)

    except Exception as e:
        logger.error("Error in mcpask command", user_id=user_id, error=str(e))
        await message.reply_text(await t(context, user_id, "mcp.errors.ask_failed", error=str(e)))


async def mcpremove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mcpremove command - Remove MCP server."""
    user_id = get_user_id(update)
    message = update.effective_message

    if not user_id or not message:
        return

    try:
        mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
        if not mcp_manager:
            await message.reply_text(await t(context, user_id, "mcp.errors.system_not_available"))
            return

        args = context.args or []

        if args:
            # Direct removal with confirmation
            server_name = args[0]
            keyboard = [
                [
                    InlineKeyboardButton(
                        await t(context, user_id, "mcp.buttons.confirm_remove"),
                        callback_data=f"mcp_confirm_remove:{server_name}"
                    ),
                    InlineKeyboardButton(
                        await t(context, user_id, "mcp.buttons.cancel"),
                        callback_data="mcp_cancel"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(
                await t(context, user_id, "mcp.remove.confirm", server_name=server_name),
                reply_markup=reply_markup
            )
        else:
            # Show removal selection menu
            await _show_removal_selection_menu(update, context, mcp_manager)

    except Exception as e:
        logger.error("Error in mcpremove command", user_id=user_id, error=str(e))
        await message.reply_text(await t(context, user_id, "mcp.errors.remove_failed", error=str(e)))


async def mcpstatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mcpstatus command - Show system status."""
    user_id = get_user_id(update)
    message = update.effective_message

    if not user_id or not message:
        return

    try:
        mcp_manager: MCPManager = context.bot_data.get("mcp_manager")
        mcp_context_handler: MCPContextHandler = context.bot_data.get("mcp_context_handler")

        if not mcp_manager or not mcp_context_handler:
            await message.reply_text(await t(context, user_id, "mcp.errors.system_not_available"))
            return

        # Show status loading message
        status_msg = await message.reply_text(await t(context, user_id, "mcp.status.checking"))

        # Get system status
        servers = await mcp_manager.get_user_servers(user_id)
        active_context = await mcp_context_handler.get_active_context(user_id)
        context_summary = await mcp_context_handler.get_context_summary(user_id)

        # Build status message
        text_lines = [await t(context, user_id, "mcp.status.title")]
        text_lines.append("")

        # Claude CLI status (placeholder - would need actual check)
        text_lines.append(f"🤖 Claude CLI: ✅ {await t(context, user_id, 'mcp.status.connected')}")

        # Active context
        if active_context:
            server_name = active_context['selected_server']
            display_name = active_context.get('display_name', server_name)
            text_lines.append(f"🎯 {await t(context, user_id, 'mcp.status.active_context', context=display_name)}")
        else:
            text_lines.append(f"🎯 {await t(context, user_id, 'mcp.status.no_context')}")

        # Servers summary
        enabled_count = len([s for s in servers if s['is_enabled']])
        active_count = len([s for s in servers if s['status'] == 'active'])

        text_lines.append(f"📊 {await t(context, user_id, 'mcp.status.servers_summary', total=len(servers), enabled=enabled_count, active=active_count)}")
        text_lines.append("")

        # Usage statistics
        if context_summary.get("recent_usage"):
            usage = context_summary["recent_usage"]["overall"]
            total_queries = usage.get("total_queries", 0)
            success_rate = (usage.get("successful_queries", 0) / total_queries * 100) if total_queries > 0 else 0
            avg_time = usage.get("avg_response_time", 0)
            total_cost = usage.get("total_cost", 0)

            text_lines.append(f"📈 {await t(context, user_id, 'mcp.status.usage_stats')}")
            text_lines.append(f"   • {await t(context, user_id, 'mcp.status.queries_count', count=total_queries)}")
            text_lines.append(f"   • {await t(context, user_id, 'mcp.status.success_rate', rate=success_rate:.1f)}")
            if avg_time:
                text_lines.append(f"   • {await t(context, user_id, 'mcp.status.avg_response', time=avg_time:.1f)}")
            if total_cost > 0:
                text_lines.append(f"   • {await t(context, user_id, 'mcp.status.total_cost', cost=total_cost:.4f)}")

        # Control buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    await t(context, user_id, "mcp.buttons.list_servers"),
                    callback_data="mcp_list"
                ),
                InlineKeyboardButton(
                    await t(context, user_id, "mcp.buttons.select_context"),
                    callback_data="mcp_select_context"
                )
            ],
            [
                InlineKeyboardButton(
                    await t(context, user_id, "mcp.buttons.refresh_status"),
                    callback_data="mcp_refresh_all"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await status_msg.edit_text(
            "\n".join(text_lines),
            reply_markup=reply_markup,
            parse_mode=None
        )

    except Exception as e:
        logger.error("Error in mcpstatus command", user_id=user_id, error=str(e))
        await message.reply_text(await t(context, user_id, "mcp.errors.status_failed", error=str(e)))


# Helper functions for interactive wizards and menus

async def _show_server_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, mcp_manager: MCPManager) -> None:
    """Show server type selection menu."""
    user_id = get_user_id(update)
    message = update.effective_message

    templates = server_config_registry.get_template_list()

    keyboard = []
    for template in templates:
        keyboard.append([
            InlineKeyboardButton(
                template["display_name"],
                callback_data=f"mcp_add_type:{template['server_type']}"
            )
        ])

    # Add cancel button
    keyboard.append([
        InlineKeyboardButton(
            await t(context, user_id, "mcp.buttons.cancel"),
            callback_data="mcp_cancel"
        )
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        await t(context, user_id, "mcp.add.select_type"),
        reply_markup=reply_markup
    )


async def _show_context_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     mcp_manager: MCPManager, mcp_context_handler: MCPContextHandler) -> None:
    """Show context selection menu."""
    user_id = get_user_id(update)
    message = update.effective_message

    # Get enabled servers
    servers = await mcp_manager.get_user_servers(user_id)
    enabled_servers = [s for s in servers if s['is_enabled']]

    if not enabled_servers:
        await message.reply_text(await t(context, user_id, "mcp.select.no_enabled_servers"))
        return

    # Get current active context
    active_context = await mcp_context_handler.get_active_context(user_id)
    active_server = active_context.get('selected_server') if active_context else None

    keyboard = []
    for server in enabled_servers:
        server_name = server['server_name']
        display_name = server.get('display_name', server['server_type'])

        # Mark current active server
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

    await message.reply_text(
        await t(context, user_id, "mcp.select.choose_context"),
        reply_markup=reply_markup
    )


async def _execute_mcp_query(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           query: str, mcp_context_handler: MCPContextHandler) -> None:
    """Execute MCP query with active context."""
    user_id = get_user_id(update)
    message = update.effective_message

    # Show processing message
    processing_msg = await message.reply_text(
        await t(context, user_id, "mcp.ask.processing", query=query[:50])
    )

    try:
        # Get current directory from user data
        settings = context.bot_data.get("settings")
        current_dir = context.user_data.get("current_directory", settings.approved_directory)
        session_id = context.user_data.get("claude_session_id")

        # Execute contextual query
        claude_response = await mcp_context_handler.execute_contextual_query(
            user_id=user_id,
            query=query,
            working_directory=str(current_dir),
            session_id=session_id
        )

        # Update session ID
        context.user_data["claude_session_id"] = claude_response.session_id

        # Delete processing message
        await processing_msg.delete()

        # Send response
        from ...utils.formatting import ResponseFormatter
        formatter = ResponseFormatter(settings)
        formatted_messages = formatter.format_claude_response(claude_response.content)

        for i, msg in enumerate(formatted_messages):
            await message.reply_text(
                msg.text,
                parse_mode=msg.parse_mode,
                reply_markup=msg.reply_markup,
                reply_to_message_id=message.message_id if i == 0 else None
            )
            if i < len(formatted_messages) - 1:
                await asyncio.sleep(0.5)

    except MCPContextError as e:
        await processing_msg.edit_text(
            await t(context, user_id, "mcp.ask.context_error", error=str(e))
        )
    except Exception as e:
        logger.error("MCP query execution failed", user_id=user_id, query=query[:100], error=str(e))
        await processing_msg.edit_text(
            await t(context, user_id, "mcp.ask.execution_error", error=str(e))
        )


async def _handle_quick_add(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          server_type: str, mcp_manager: MCPManager) -> None:
    """Handle quick server addition."""
    user_id = get_user_id(update)
    message = update.effective_message

    template = server_config_registry.get_template(server_type)
    if not template:
        await message.reply_text(
            await t(context, user_id, "mcp.add.invalid_type", server_type=server_type)
        )
        return

    await message.reply_text(
        await t(context, user_id, "mcp.add.quick_not_supported", server_type=server_type)
    )

    # Start interactive wizard
    await _show_server_type_selection(update, context, mcp_manager)
