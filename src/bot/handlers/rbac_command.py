"""
RBAC Command Handler for DevClaude_bot

Provides administrative commands for role and permission management.
Only accessible to users with admin permissions.
"""

from typing import Any, Dict, List
import structlog
from telegram import Update
from telegram.ext import ContextTypes

from src.errors import handle_errors, SecurityError, ValidationError
from src.security.rbac import RBACManager, Permission, Role
from src.bot.decorators import require_auth, log_command
from src.localization.helpers import get_text

logger = structlog.get_logger(__name__)


class RBACCommandHandler:
    """Handler for RBAC administrative commands."""

    def __init__(self, rbac_manager: RBACManager, auth_manager):
        self.rbac_manager = rbac_manager
        self.auth_manager = auth_manager

    @handle_errors(retry_count=1, operation_name="list_roles")
    @require_auth
    @log_command
    async def list_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all available roles."""
        user_id = update.effective_user.id

        # Check admin permission
        session = await self.auth_manager.get_session(user_id)
        if not session or not session.has_permission(Permission.ADMIN_USERS):
            await update.message.reply_text(
                get_text("error.permission_denied", update.effective_user.language_code)
            )
            return

        roles_info = self.rbac_manager.role_registry.get_role_hierarchy()

        response = "🔐 **System Roles:**\n\n"
        for role_name, info in sorted(roles_info.items(), key=lambda x: x[1]['priority'], reverse=True):
            response += f"**{role_name.title()}** (Priority: {info['priority']})\n"
            response += f"  └ {info['description']}\n"
            response += f"  └ Permissions: {info['permissions_count']}\n"
            if info['inherits_from']:
                response += f"  └ Inherits from: {info['inherits_from']}\n"
            response += "\n"

        await update.message.reply_text(response, parse_mode='Markdown')

    @handle_errors(retry_count=1, operation_name="assign_role")
    @require_auth
    @log_command
    async def assign_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Assign a role to a user."""
        user_id = update.effective_user.id

        # Check admin permission
        session = await self.auth_manager.get_session(user_id)
        if not session or not session.has_permission(Permission.ADMIN_USERS):
            await update.message.reply_text(
                get_text("error.permission_denied", update.effective_user.language_code)
            )
            return

        # Parse arguments: /assign_role <user_id> <role>
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: `/assign_role <user_id> <role_name>`\n\n"
                "Example: `/assign_role 123456789 developer`",
                parse_mode='Markdown'
            )
            return

        try:
            target_user_id = int(args[0])
            role_name = args[1].lower()

            # Assign role
            success = await self.rbac_manager.assign_role(
                user_id=target_user_id,
                role_name=role_name,
                granted_by=user_id
            )

            if success:
                await update.message.reply_text(
                    f"✅ Role `{role_name}` assigned to user `{target_user_id}`",
                    parse_mode='Markdown'
                )
                logger.info(
                    "Role assigned via command",
                    admin_user=user_id,
                    target_user=target_user_id,
                    role=role_name
                )
            else:
                await update.message.reply_text("❌ Failed to assign role")

        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        except ValidationError as e:
            await update.message.reply_text(f"❌ {e.user_message}")
        except Exception as e:
            logger.error("Error assigning role", error=str(e))
            await update.message.reply_text("❌ Error assigning role")

    @handle_errors(retry_count=1, operation_name="revoke_role")
    @require_auth
    @log_command
    async def revoke_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Revoke a role from a user."""
        user_id = update.effective_user.id

        # Check admin permission
        session = await self.auth_manager.get_session(user_id)
        if not session or not session.has_permission(Permission.ADMIN_USERS):
            await update.message.reply_text(
                get_text("error.permission_denied", update.effective_user.language_code)
            )
            return

        # Parse arguments: /revoke_role <user_id> <role>
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: `/revoke_role <user_id> <role_name>`\n\n"
                "Example: `/revoke_role 123456789 developer`",
                parse_mode='Markdown'
            )
            return

        try:
            target_user_id = int(args[0])
            role_name = args[1].lower()

            # Revoke role
            success = await self.rbac_manager.revoke_role(target_user_id, role_name)

            if success:
                await update.message.reply_text(
                    f"✅ Role `{role_name}` revoked from user `{target_user_id}`",
                    parse_mode='Markdown'
                )
                logger.info(
                    "Role revoked via command",
                    admin_user=user_id,
                    target_user=target_user_id,
                    role=role_name
                )
            else:
                await update.message.reply_text("❌ Role not found or already revoked")

        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        except Exception as e:
            logger.error("Error revoking role", error=str(e))
            await update.message.reply_text("❌ Error revoking role")

    @handle_errors(retry_count=1, operation_name="user_roles")
    @require_auth
    @log_command
    async def user_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's roles and permissions."""
        user_id = update.effective_user.id

        # Get target user (self or specified user for admins)
        target_user_id = user_id
        args = context.args

        session = await self.auth_manager.get_session(user_id)
        if not session:
            await update.message.reply_text("❌ Authentication required")
            return

        # If user specified another user ID, check admin permission
        if args and session.has_permission(Permission.ADMIN_USERS):
            try:
                target_user_id = int(args[0])
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID")
                return
        elif args:
            await update.message.reply_text("❌ Permission denied")
            return

        # Get user roles
        user_roles = self.rbac_manager.get_user_roles(target_user_id)
        user_permissions = self.rbac_manager.get_user_permissions(target_user_id)

        if not user_roles:
            await update.message.reply_text(
                f"👤 User `{target_user_id}` has no roles assigned",
                parse_mode='Markdown'
            )
            return

        response = f"👤 **User {target_user_id} Roles & Permissions:**\n\n"

        # Show roles
        response += "🔐 **Roles:**\n"
        for user_role in user_roles:
            role = self.rbac_manager.role_registry.get_role(user_role.role_name)
            response += f"  • {user_role.role_name.title()}"
            if role:
                response += f" (Priority: {role.priority})"
            if user_role.expires_at:
                response += f" [Expires: {user_role.expires_at[:10]}]"
            response += "\n"

        # Show permission count
        response += f"\n⚡ **Total Permissions:** {len(user_permissions)}\n"

        # Show some key permissions
        key_permissions = [
            Permission.ADMIN_SYSTEM,
            Permission.ADMIN_USERS,
            Permission.CLAUDE_ADMIN,
            Permission.GIT_ADMIN,
            Permission.AUDIT,
        ]

        has_key_perms = [p for p in key_permissions if p in user_permissions]
        if has_key_perms:
            response += "\n🔑 **Key Permissions:**\n"
            for perm in has_key_perms:
                response += f"  • {perm.value}\n"

        await update.message.reply_text(response, parse_mode='Markdown')

    @handle_errors(retry_count=1, operation_name="rbac_stats")
    @require_auth
    @log_command
    async def rbac_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show RBAC system statistics."""
        user_id = update.effective_user.id

        # Check admin permission
        session = await self.auth_manager.get_session(user_id)
        if not session or not session.has_permission(Permission.ADMIN_SYSTEM):
            await update.message.reply_text(
                get_text("error.permission_denied", update.effective_user.language_code)
            )
            return

        stats = self.rbac_manager.get_rbac_stats()

        response = "📊 **RBAC System Statistics:**\n\n"
        response += f"👥 Total Users: {stats['total_users']}\n"
        response += f"🔐 Total Roles: {stats['total_roles']}\n"
        response += f"⚡ Available Permissions: {stats['available_permissions']}\n"
        response += f"💾 Cache Size: {stats['cache_size']}\n\n"

        if stats['role_assignments']:
            response += "📋 **Role Distribution:**\n"
            for role, count in sorted(stats['role_assignments'].items()):
                response += f"  • {role.title()}: {count} users\n"

        await update.message.reply_text(response, parse_mode='Markdown')

    def get_handlers(self) -> Dict[str, Any]:
        """Get command handlers for registration."""
        return {
            'list_roles': self.list_roles,
            'assign_role': self.assign_role,
            'revoke_role': self.revoke_role,
            'user_roles': self.user_roles,
            'rbac_stats': self.rbac_stats,
        }