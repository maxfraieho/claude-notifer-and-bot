"""
Unit tests for RBAC system.

Tests role-based access control implementation.
"""

import pytest
from datetime import datetime, timedelta

from src.security.rbac import (
    RBACManager,
    Permission,
    Role,
    RoleRegistry,
    UserRole,
)
from src.errors import ValidationError, SecurityError


class TestRole:
    """Test Role class functionality."""

    def test_role_creation(self):
        """Test role creation with basic properties."""
        role = Role(
            name="test_role",
            description="Test role for testing",
            priority=10
        )

        assert role.name == "test_role"
        assert role.description == "Test role for testing"
        assert role.priority == 10
        assert len(role.permissions) == 0

    def test_role_permissions(self):
        """Test role permission management."""
        role = Role(name="test")

        # Add permissions
        role.add_permission(Permission.HELP)
        role.add_permission(Permission.STATUS)

        assert Permission.HELP in role.permissions
        assert Permission.STATUS in role.permissions
        assert role.has_permission(Permission.HELP)
        assert not role.has_permission(Permission.ADMIN_SYSTEM)

        # Remove permission
        role.remove_permission(Permission.HELP)
        assert Permission.HELP not in role.permissions
        assert not role.has_permission(Permission.HELP)

    def test_role_inheritance(self):
        """Test role inheritance functionality."""
        # Create parent role
        parent = Role(name="parent")
        parent.add_permission(Permission.HELP)
        parent.add_permission(Permission.STATUS)

        # Create child role that inherits from parent
        child = Role(name="child", inherits_from=parent)
        child.add_permission(Permission.LS)

        # Check inherited permissions
        all_permissions = child.get_all_permissions()
        assert Permission.HELP in all_permissions
        assert Permission.STATUS in all_permissions
        assert Permission.LS in all_permissions

        # Check has_permission works with inheritance
        assert child.has_permission(Permission.HELP)  # Inherited
        assert child.has_permission(Permission.LS)    # Direct


class TestRoleRegistry:
    """Test RoleRegistry functionality."""

    def test_role_registration(self):
        """Test role registration and retrieval."""
        registry = RoleRegistry()

        # Check default roles are registered
        assert "viewer" in registry.roles
        assert "user" in registry.roles
        assert "developer" in registry.roles
        assert "admin" in registry.roles

        # Test role retrieval
        viewer_role = registry.get_role("viewer")
        assert viewer_role is not None
        assert viewer_role.name == "viewer"

        # Test non-existent role
        assert registry.get_role("nonexistent") is None

    def test_custom_role_registration(self):
        """Test registering custom roles."""
        registry = RoleRegistry()

        custom_role = Role(
            name="custom",
            description="Custom test role",
            priority=50
        )
        custom_role.add_permission(Permission.DEBUG)

        registry.register_role(custom_role)

        retrieved = registry.get_role("custom")
        assert retrieved is not None
        assert retrieved.name == "custom"
        assert retrieved.has_permission(Permission.DEBUG)

    def test_role_hierarchy(self):
        """Test role hierarchy information."""
        registry = RoleRegistry()
        hierarchy = registry.get_role_hierarchy()

        assert "admin" in hierarchy
        assert "developer" in hierarchy

        admin_info = hierarchy["admin"]
        assert admin_info["priority"] == 100
        assert admin_info["inherits_from"] == "developer"

        developer_info = hierarchy["developer"]
        assert developer_info["inherits_from"] == "user"


class TestUserRole:
    """Test UserRole class functionality."""

    def test_user_role_creation(self):
        """Test user role assignment creation."""
        user_role = UserRole(
            user_id=123,
            role_name="user",
            granted_by=456
        )

        assert user_role.user_id == 123
        assert user_role.role_name == "user"
        assert user_role.granted_by == 456
        assert not user_role.is_expired()

    def test_user_role_expiration(self):
        """Test user role expiration logic."""
        # Non-expiring role
        user_role = UserRole(user_id=123, role_name="user")
        assert not user_role.is_expired()

        # Expired role
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        expired_role = UserRole(
            user_id=123,
            role_name="user",
            expires_at=past_time
        )
        assert expired_role.is_expired()

        # Future expiration
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        future_role = UserRole(
            user_id=123,
            role_name="user",
            expires_at=future_time
        )
        assert not future_role.is_expired()


class TestRBACManager:
    """Test RBACManager functionality."""

    @pytest.fixture
    def rbac_manager(self):
        """Create RBAC manager for testing."""
        return RBACManager()

    async def test_role_assignment(self, rbac_manager):
        """Test assigning roles to users."""
        user_id = 123

        # Assign role
        success = await rbac_manager.assign_role(user_id, "user")
        assert success

        # Check role assignment
        user_roles = rbac_manager.get_user_roles(user_id)
        assert len(user_roles) == 1
        assert user_roles[0].role_name == "user"

    async def test_invalid_role_assignment(self, rbac_manager):
        """Test assigning invalid role."""
        user_id = 123

        with pytest.raises(ValidationError):
            await rbac_manager.assign_role(user_id, "nonexistent_role")

    async def test_role_revocation(self, rbac_manager):
        """Test revoking roles from users."""
        user_id = 123

        # Assign then revoke role
        await rbac_manager.assign_role(user_id, "user")
        success = await rbac_manager.revoke_role(user_id, "user")
        assert success

        # Check role is removed
        user_roles = rbac_manager.get_user_roles(user_id)
        assert len(user_roles) == 0

        # Try to revoke non-existent role
        success = await rbac_manager.revoke_role(user_id, "user")
        assert not success

    async def test_user_permissions(self, rbac_manager):
        """Test getting user permissions."""
        user_id = 123

        # No roles initially
        permissions = rbac_manager.get_user_permissions(user_id)
        assert len(permissions) == 0

        # Assign user role
        await rbac_manager.assign_role(user_id, "user")
        permissions = rbac_manager.get_user_permissions(user_id)
        assert len(permissions) > 0
        assert Permission.HELP in permissions
        assert Permission.STATUS in permissions

    async def test_permission_checking(self, rbac_manager):
        """Test permission checking functionality."""
        user_id = 123

        # No permissions initially
        assert not rbac_manager.has_permission(user_id, Permission.HELP)

        # Assign user role
        await rbac_manager.assign_role(user_id, "user")

        # Check permissions
        assert rbac_manager.has_permission(user_id, Permission.HELP)
        assert rbac_manager.has_permission(user_id, Permission.STATUS)
        assert not rbac_manager.has_permission(user_id, Permission.ADMIN_SYSTEM)

        # Test check_permission with exception
        assert rbac_manager.check_permission(user_id, Permission.HELP, raise_exception=False)

        with pytest.raises(SecurityError):
            rbac_manager.check_permission(user_id, Permission.ADMIN_SYSTEM, raise_exception=True)

    async def test_multiple_roles(self, rbac_manager):
        """Test user with multiple roles."""
        user_id = 123

        # Assign multiple roles
        await rbac_manager.assign_role(user_id, "user")
        await rbac_manager.assign_role(user_id, "developer")

        user_roles = rbac_manager.get_user_roles(user_id)
        role_names = {ur.role_name for ur in user_roles}
        assert "user" in role_names
        assert "developer" in role_names

        # Check combined permissions
        permissions = rbac_manager.get_user_permissions(user_id)
        assert Permission.HELP in permissions  # From user role
        assert Permission.AUDIT in permissions  # From developer role

    async def test_role_replacement(self, rbac_manager):
        """Test replacing existing role assignment."""
        user_id = 123

        # Assign user role
        await rbac_manager.assign_role(user_id, "user")
        assert len(rbac_manager.get_user_roles(user_id)) == 1

        # Assign same role again (should replace)
        await rbac_manager.assign_role(user_id, "user", granted_by=456)
        user_roles = rbac_manager.get_user_roles(user_id)
        assert len(user_roles) == 1
        assert user_roles[0].granted_by == 456

    async def test_highest_role(self, rbac_manager):
        """Test getting user's highest priority role."""
        user_id = 123

        # No roles
        assert rbac_manager.get_highest_role(user_id) is None

        # Single role
        await rbac_manager.assign_role(user_id, "user")
        highest = rbac_manager.get_highest_role(user_id)
        assert highest.name == "user"

        # Multiple roles - admin should be highest
        await rbac_manager.assign_role(user_id, "admin")
        highest = rbac_manager.get_highest_role(user_id)
        assert highest.name == "admin"

    async def test_expired_roles(self, rbac_manager):
        """Test handling of expired roles."""
        user_id = 123

        # Manually add expired role
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        expired_role = UserRole(
            user_id=user_id,
            role_name="user",
            expires_at=past_time
        )
        rbac_manager.user_roles[user_id] = [expired_role]

        # Expired roles should be filtered out
        active_roles = rbac_manager.get_user_roles(user_id)
        assert len(active_roles) == 0

        # Permissions should be empty
        permissions = rbac_manager.get_user_permissions(user_id)
        assert len(permissions) == 0

    def test_rbac_stats(self, rbac_manager):
        """Test RBAC statistics generation."""
        stats = rbac_manager.get_rbac_stats()

        assert "total_users" in stats
        assert "total_roles" in stats
        assert "role_assignments" in stats
        assert "cache_size" in stats
        assert "available_permissions" in stats

        # Initially should have default roles but no users
        assert stats["total_roles"] == 4  # viewer, user, developer, admin
        assert stats["total_users"] == 0

    def test_permission_cache(self, rbac_manager):
        """Test permission caching functionality."""
        user_id = 123

        # Cache should be empty initially
        assert len(rbac_manager._permission_cache) == 0

        # Get permissions (should populate cache)
        permissions = rbac_manager.get_user_permissions(user_id)
        # Cache might still be empty for user with no roles

        # Assign role and get permissions again
        rbac_manager.user_roles[user_id] = [UserRole(user_id=user_id, role_name="user")]
        permissions = rbac_manager.get_user_permissions(user_id)

        # Cache should be populated
        assert user_id in rbac_manager._permission_cache
        assert rbac_manager._permission_cache[user_id] == permissions

        # Clear cache when role is revoked
        rbac_manager.user_roles[user_id] = []
        rbac_manager.get_user_roles(user_id)  # This should clear cache
        assert user_id not in rbac_manager._permission_cache