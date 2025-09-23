"""
Role-Based Access Control (RBAC) System for DevClaude_bot

Implements comprehensive RBAC as recommended by Enhanced Architect Bot analysis.
Provides fine-grained permission control with role hierarchy.
"""

from typing import Dict, List, Set, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
import structlog

from ..errors import SecurityError, ValidationError

logger = structlog.get_logger(__name__)


class Permission(Enum):
    """System permissions."""

    # Basic permissions
    HELP = "help"
    STATUS = "status"

    # File system permissions
    LS = "ls"
    PWD = "pwd"
    CD = "cd"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"

    # Git permissions
    GIT_READ = "git_read"
    GIT_WRITE = "git_write"
    GIT_ADMIN = "git_admin"

    # Claude permissions
    CLAUDE_BASIC = "claude_basic"
    CLAUDE_SESSIONS = "claude_sessions"
    CLAUDE_ADMIN = "claude_admin"
    CLAUDE_HISTORY = "claude_history"

    # MCP permissions
    MCP_LIST = "mcp_list"
    MCP_ADD = "mcp_add"
    MCP_REMOVE = "mcp_remove"
    MCP_SELECT = "mcp_select"
    MCP_ASK = "mcp_ask"
    MCP_STATUS = "mcp_status"

    # Administrative permissions
    ADMIN_USERS = "admin_users"
    ADMIN_CONFIG = "admin_config"
    ADMIN_LOGS = "admin_logs"
    ADMIN_AUDIT = "admin_audit"
    ADMIN_SYSTEM = "admin_system"

    # Special permissions
    AUDIT = "audit"
    DRACON = "dracon"
    REFACTOR = "refactor"
    SCHEDULES = "schedules"
    ADD_SCHEDULE = "add_schedule"

    # Image processing
    IMAGE_UPLOAD = "image_upload"
    IMAGE_PROCESS = "image_process"

    # Development permissions
    DEBUG = "debug"
    TEST = "test"
    DEVELOPMENT = "development"


@dataclass
class Role:
    """Role definition with permissions and hierarchy."""

    name: str
    permissions: Set[Permission] = field(default_factory=set)
    description: str = ""
    inherits_from: Optional['Role'] = None
    priority: int = 0  # Higher number = higher priority

    def __post_init__(self):
        """Initialize role with inherited permissions."""
        if self.inherits_from:
            self.permissions.update(self.inherits_from.get_all_permissions())

    def add_permission(self, permission: Permission):
        """Add a permission to this role."""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission):
        """Remove a permission from this role."""
        self.permissions.discard(permission)

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a specific permission."""
        return permission in self.get_all_permissions()

    def get_all_permissions(self) -> Set[Permission]:
        """Get all permissions including inherited ones."""
        all_permissions = self.permissions.copy()
        if self.inherits_from:
            all_permissions.update(self.inherits_from.get_all_permissions())
        return all_permissions


class RoleRegistry:
    """Registry for managing system roles."""

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self):
        """Initialize default system roles."""

        # Viewer role - read-only access
        viewer = Role(
            name="viewer",
            description="Read-only access to basic functions",
            priority=10
        )
        viewer.permissions.update([
            Permission.HELP,
            Permission.STATUS,
            Permission.LS,
            Permission.PWD,
            Permission.READ_FILE,
            Permission.CLAUDE_BASIC,
            Permission.MCP_LIST,
            Permission.MCP_STATUS,
        ])

        # User role - standard user access
        user = Role(
            name="user",
            description="Standard user with file and Claude access",
            inherits_from=viewer,
            priority=20
        )
        user.permissions.update([
            Permission.CD,
            Permission.WRITE_FILE,
            Permission.UPLOAD_FILE,
            Permission.DOWNLOAD_FILE,
            Permission.GIT_READ,
            Permission.CLAUDE_SESSIONS,
            Permission.CLAUDE_HISTORY,
            Permission.MCP_ADD,
            Permission.MCP_REMOVE,
            Permission.MCP_SELECT,
            Permission.MCP_ASK,
            Permission.IMAGE_UPLOAD,
            Permission.IMAGE_PROCESS,
        ])

        # Developer role - development access
        developer = Role(
            name="developer",
            description="Developer with advanced features",
            inherits_from=user,
            priority=30
        )
        developer.permissions.update([
            Permission.DELETE_FILE,
            Permission.GIT_WRITE,
            Permission.AUDIT,
            Permission.DRACON,
            Permission.REFACTOR,
            Permission.SCHEDULES,
            Permission.ADD_SCHEDULE,
            Permission.DEBUG,
            Permission.TEST,
            Permission.DEVELOPMENT,
        ])

        # Admin role - full system access
        admin = Role(
            name="admin",
            description="Full administrative access",
            inherits_from=developer,
            priority=100
        )
        admin.permissions.update([
            Permission.GIT_ADMIN,
            Permission.CLAUDE_ADMIN,
            Permission.ADMIN_USERS,
            Permission.ADMIN_CONFIG,
            Permission.ADMIN_LOGS,
            Permission.ADMIN_AUDIT,
            Permission.ADMIN_SYSTEM,
        ])

        # Register all roles
        self.register_role(viewer)
        self.register_role(user)
        self.register_role(developer)
        self.register_role(admin)

    def register_role(self, role: Role):
        """Register a role in the registry."""
        self.roles[role.name] = role
        logger.debug("Role registered", role=role.name, permissions=len(role.get_all_permissions()))

    def get_role(self, name: str) -> Optional[Role]:
        """Get a role by name."""
        return self.roles.get(name)

    def list_roles(self) -> List[str]:
        """List all available roles."""
        return list(self.roles.keys())

    def get_role_hierarchy(self) -> Dict[str, Dict[str, Any]]:
        """Get role hierarchy information."""
        hierarchy = {}
        for name, role in self.roles.items():
            hierarchy[name] = {
                "description": role.description,
                "priority": role.priority,
                "inherits_from": role.inherits_from.name if role.inherits_from else None,
                "permissions_count": len(role.get_all_permissions()),
                "direct_permissions": [p.value for p in role.permissions],
            }
        return hierarchy


@dataclass
class UserRole:
    """User role assignment with context."""

    user_id: int
    role_name: str
    granted_by: Optional[int] = None
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if role assignment is expired."""
        if not self.expires_at:
            return False

        from datetime import datetime
        expiry = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expiry


class RBACManager:
    """
    Role-Based Access Control Manager.

    Manages user roles, permissions, and access control decisions.
    """

    def __init__(self, storage=None):
        self.role_registry = RoleRegistry()
        self.user_roles: Dict[int, List[UserRole]] = {}
        self.storage = storage
        self._permission_cache: Dict[int, Set[Permission]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL

    async def assign_role(
        self,
        user_id: int,
        role_name: str,
        granted_by: Optional[int] = None,
        expires_at: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Assign a role to a user."""

        # Validate role exists
        role = self.role_registry.get_role(role_name)
        if not role:
            raise ValidationError(f"Role '{role_name}' does not exist", field="role_name", value=role_name)

        # Create role assignment
        user_role = UserRole(
            user_id=user_id,
            role_name=role_name,
            granted_by=granted_by,
            granted_at=datetime.utcnow().isoformat() if hasattr(datetime, 'utcnow') else None,
            expires_at=expires_at,
            context=context or {}
        )

        # Add to user roles
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []

        # Remove existing assignment of same role
        self.user_roles[user_id] = [
            ur for ur in self.user_roles[user_id]
            if ur.role_name != role_name
        ]

        self.user_roles[user_id].append(user_role)

        # Clear permission cache for user
        self._permission_cache.pop(user_id, None)

        # Persist to storage if available
        if self.storage:
            await self._persist_user_role(user_role)

        logger.info(
            "Role assigned to user",
            user_id=user_id,
            role=role_name,
            granted_by=granted_by,
            expires_at=expires_at
        )

        return True

    async def revoke_role(self, user_id: int, role_name: str) -> bool:
        """Revoke a role from a user."""

        if user_id not in self.user_roles:
            return False

        # Remove role assignment
        original_count = len(self.user_roles[user_id])
        self.user_roles[user_id] = [
            ur for ur in self.user_roles[user_id]
            if ur.role_name != role_name
        ]

        revoked = len(self.user_roles[user_id]) < original_count

        if revoked:
            # Clear permission cache
            self._permission_cache.pop(user_id, None)

            # Persist to storage if available
            if self.storage:
                await self._remove_user_role(user_id, role_name)

            logger.info("Role revoked from user", user_id=user_id, role=role_name)

        return revoked

    def get_user_roles(self, user_id: int) -> List[UserRole]:
        """Get all roles assigned to a user."""
        user_roles = self.user_roles.get(user_id, [])

        # Filter out expired roles
        active_roles = [ur for ur in user_roles if not ur.is_expired()]

        # Update user roles if any were expired
        if len(active_roles) < len(user_roles):
            self.user_roles[user_id] = active_roles
            self._permission_cache.pop(user_id, None)  # Clear cache

        return active_roles

    def get_user_permissions(self, user_id: int) -> Set[Permission]:
        """Get all permissions for a user."""

        # Check cache
        if user_id in self._permission_cache:
            return self._permission_cache[user_id]

        permissions = set()
        user_roles = self.get_user_roles(user_id)

        for user_role in user_roles:
            role = self.role_registry.get_role(user_role.role_name)
            if role:
                permissions.update(role.get_all_permissions())

        # Cache permissions
        self._permission_cache[user_id] = permissions

        return permissions

    def has_permission(self, user_id: int, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions

    def check_permission(self, user_id: int, permission: Permission, raise_exception: bool = True) -> bool:
        """Check permission and optionally raise exception if denied."""
        has_perm = self.has_permission(user_id, permission)

        if not has_perm and raise_exception:
            user_roles = [ur.role_name for ur in self.get_user_roles(user_id)]
            raise SecurityError(
                f"Permission '{permission.value}' denied for user {user_id}",
                security_context={
                    "user_id": user_id,
                    "permission": permission.value,
                    "user_roles": user_roles,
                    "required_permission": permission.value
                },
                user_message=f"You don't have permission to perform this action. Required: {permission.value}"
            )

        return has_perm

    def get_highest_role(self, user_id: int) -> Optional[Role]:
        """Get user's highest priority role."""
        user_roles = self.get_user_roles(user_id)

        if not user_roles:
            return None

        highest_role = None
        highest_priority = -1

        for user_role in user_roles:
            role = self.role_registry.get_role(user_role.role_name)
            if role and role.priority > highest_priority:
                highest_priority = role.priority
                highest_role = role

        return highest_role

    async def _persist_user_role(self, user_role: UserRole):
        """Persist user role to storage."""
        # Implementation depends on storage backend
        pass

    async def _remove_user_role(self, user_id: int, role_name: str):
        """Remove user role from storage."""
        # Implementation depends on storage backend
        pass

    def get_rbac_stats(self) -> Dict[str, Any]:
        """Get RBAC system statistics."""
        total_users = len(self.user_roles)
        total_roles = len(self.role_registry.roles)

        role_counts = {}
        for user_roles in self.user_roles.values():
            for user_role in user_roles:
                if not user_role.is_expired():
                    role_counts[user_role.role_name] = role_counts.get(user_role.role_name, 0) + 1

        return {
            "total_users": total_users,
            "total_roles": total_roles,
            "role_assignments": role_counts,
            "cache_size": len(self._permission_cache),
            "available_permissions": len(Permission),
        }