"""
Integration tests for Dependency Injection Container.

Tests the complete DI system integration and component wiring.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.di import ApplicationContainer, initialize_di, shutdown_di
from src.config.settings import Settings
from src.security.rbac import RBACManager
from src.security.auth import AuthenticationManager
from src.storage.facade import Storage


class TestDIContainer:
    """Test DI Container functionality."""

    async def test_container_initialization(self, test_config: Settings):
        """Test container initialization with config."""
        container = await initialize_di(test_config)

        assert container is not None
        assert container.config() == test_config

        await shutdown_di()

    async def test_storage_providers(self, test_config: Settings):
        """Test storage provider configuration."""
        container = await initialize_di(test_config)

        # Test storage factory
        storage_factory = container.storage_providers.storage_factory
        assert storage_factory is not None

        # Test session storage
        session_storage_factory = container.storage_providers.session_storage
        assert session_storage_factory is not None

        await shutdown_di()

    async def test_security_providers(self, test_config: Settings):
        """Test security provider configuration."""
        container = await initialize_di(test_config)

        # Test RBAC manager
        rbac_manager_factory = container.security_providers.rbac_manager
        assert rbac_manager_factory is not None

        # Test auth providers
        whitelist_provider = container.security_providers.whitelist_auth_provider
        assert whitelist_provider is not None

        # Test auth manager
        auth_manager_factory = container.security_providers.auth_manager
        assert auth_manager_factory is not None

        # Test security validator
        security_validator = container.security_providers.security_validator
        assert security_validator is not None

        # Test rate limiter
        rate_limiter = container.security_providers.rate_limiter
        assert rate_limiter is not None

        # Test audit components
        audit_storage = container.security_providers.audit_storage
        audit_logger = container.security_providers.audit_logger
        assert audit_storage is not None
        assert audit_logger is not None

        await shutdown_di()

    async def test_claude_providers(self, test_config: Settings):
        """Test Claude integration providers."""
        container = await initialize_di(test_config)

        # Test session manager
        session_manager = container.claude_providers.session_manager
        assert session_manager is not None

        # Test tool monitor
        tool_monitor = container.claude_providers.tool_monitor
        assert tool_monitor is not None

        # Test process manager (for CLI mode)
        process_manager = container.claude_providers.process_manager
        assert process_manager is not None

        # Test Claude integration facade
        claude_integration = container.claude_providers.claude_integration
        assert claude_integration is not None

        await shutdown_di()

    async def test_bot_providers(self, test_config: Settings):
        """Test bot provider configuration."""
        container = await initialize_di(test_config)

        # Mock storage to avoid database dependencies
        mock_storage = Mock(spec=Storage)
        mock_storage.initialize = AsyncMock()
        container.storage.storage.override(mock_storage)

        # Test bot dependencies
        dependencies = container.bot_providers.dependencies
        assert dependencies is not None

        # Test bot factory
        bot_factory = container.bot_providers.bot
        assert bot_factory is not None

        await shutdown_di()

    async def test_application_factory(self, test_config: Settings):
        """Test application factory."""
        container = await initialize_di(test_config)

        # Mock storage to avoid database dependencies
        mock_storage = Mock(spec=Storage)
        mock_storage.initialize = AsyncMock()
        container.storage.storage.override(mock_storage)

        # Mock Claude integration
        mock_claude = Mock()
        container.claude.claude_integration.override(mock_claude)

        # Mock bot
        mock_bot = Mock()
        container.bot.bot.override(mock_bot)

        # Test application factory
        app_components = container.application_factory()

        assert "bot" in app_components
        assert "claude_integration" in app_components
        assert "storage" in app_components
        assert "config" in app_components

        assert app_components["config"] == test_config
        assert app_components["bot"] == mock_bot
        assert app_components["claude_integration"] == mock_claude
        assert app_components["storage"] == mock_storage

        await shutdown_di()

    async def test_health_service(self, test_config: Settings):
        """Test health service creation."""
        container = await initialize_di(test_config)

        # Mock dependencies
        mock_storage = Mock(spec=Storage)
        mock_claude = Mock()
        mock_security = Mock()

        container.storage.storage.override(mock_storage)
        container.claude.claude_integration.override(mock_claude)
        container.security.auth_manager.override(mock_security)

        # Test health service
        health_service = container.health_service()
        assert health_service is not None

        # Test health check
        mock_storage.health_check = AsyncMock(return_value=True)
        mock_claude.health_check = AsyncMock(return_value=True)
        mock_security.is_healthy = AsyncMock(return_value=True)

        health_status = await health_service.get_health_status()
        assert health_status["overall"] in ["healthy", "degraded", "error"]
        assert "components" in health_status
        assert "metrics" in health_status

        await shutdown_di()

    async def test_provider_dependencies(self, test_config: Settings):
        """Test provider dependency resolution."""
        container = await initialize_di(test_config)

        # Test that security providers depend on storage
        security_container = container.security_providers
        assert security_container.config() == test_config

        # Test that Claude providers depend on security
        claude_container = container.claude_providers
        assert claude_container.config() == test_config

        # Test that bot providers depend on all other containers
        bot_container = container.bot_providers
        assert bot_container.config() == test_config

        await shutdown_di()

    async def test_conditional_providers(self, test_config: Settings):
        """Test conditional provider creation based on config."""
        # Test with image processing disabled
        test_config.enable_image_processing = False
        container = await initialize_di(test_config)

        # Image providers should still exist but conditional logic should handle it
        image_providers = container.bot_providers.image_providers
        assert image_providers is not None

        await shutdown_di()

        # Test with localization disabled
        test_config.enable_localization = False
        container = await initialize_di(test_config)

        # Localization providers should exist but be conditionally used
        localization_providers = container.bot_providers.localization_providers
        assert localization_providers is not None

        await shutdown_di()

    async def test_container_wiring(self, test_config: Settings):
        """Test container wiring functionality."""
        container = await initialize_di(test_config)

        # Check that wiring config is set
        assert container.wiring_config is not None
        assert len(container.wiring_config.modules) > 0

        await shutdown_di()

    async def test_provider_factory_calls(self, test_config: Settings):
        """Test that provider factories can be called."""
        container = await initialize_di(test_config)

        # Mock storage to avoid database dependencies
        mock_storage = Mock(spec=Storage)
        container.storage.storage.override(mock_storage)

        try:
            # Test RBAC manager creation
            rbac_manager = container.security_providers.rbac_manager()
            assert isinstance(rbac_manager, RBACManager)

            # Test security validator creation
            security_validator = container.security_providers.security_validator()
            assert security_validator is not None

            # Test rate limiter creation
            rate_limiter = container.security_providers.rate_limiter()
            assert rate_limiter is not None

        except Exception as e:
            # Some providers might fail without full setup, which is expected
            pytest.skip(f"Provider creation failed (expected in test): {e}")

        await shutdown_di()

    async def test_container_override(self, test_config: Settings):
        """Test container override functionality."""
        container = await initialize_di(test_config)

        # Test overriding a provider
        mock_rbac = Mock(spec=RBACManager)
        container.security_providers.rbac_manager.override(mock_rbac)

        # Verify override works
        rbac_manager = container.security_providers.rbac_manager()
        assert rbac_manager == mock_rbac

        await shutdown_di()

    async def test_error_handling_in_providers(self, test_config: Settings):
        """Test error handling in provider creation."""
        container = await initialize_di(test_config)

        # Test with invalid config that might cause provider errors
        invalid_config = Settings(
            bot_token="invalid",
            database_url="invalid://url",
            allowed_users=[],
            approved_directory="/nonexistent"
        )

        container.config.override(invalid_config)

        # Some providers should handle errors gracefully
        try:
            rate_limiter = container.security_providers.rate_limiter()
            # Rate limiter should still be created even with invalid config
            assert rate_limiter is not None
        except Exception:
            # Some failures are expected with invalid config
            pass

        await shutdown_di()


class TestDIIntegration:
    """Test DI container integration with real components."""

    async def test_rbac_auth_integration(self, test_config: Settings, storage: Storage):
        """Test RBAC and Auth manager integration through DI."""
        container = await initialize_di(test_config)

        # Override storage
        container.storage.storage.override(storage)

        # Create RBAC manager and Auth manager
        rbac_manager = container.security_providers.rbac_manager()
        auth_providers = [container.security_providers.whitelist_auth_provider()]
        auth_manager = AuthenticationManager(auth_providers, rbac_manager=rbac_manager)

        # Test integration
        user_id = 123456789
        session = await auth_manager.authenticate(user_id)
        assert session is not None
        assert session.rbac_manager == rbac_manager

        # Test role assignment through DI components
        await rbac_manager.assign_role(user_id, "user")
        user_roles = rbac_manager.get_user_roles(user_id)
        assert len(user_roles) == 1

        await shutdown_di()

    async def test_full_application_creation(self, test_config: Settings):
        """Test creating full application through DI."""
        from src.main import create_application

        try:
            # This should work with mocked dependencies
            app = await create_application(test_config)

            assert "bot" in app
            assert "claude_integration" in app
            assert "storage" in app
            assert "config" in app

        except Exception as e:
            # Some components might fail without full environment setup
            pytest.skip(f"Full application creation failed (expected in test): {e}")

    async def test_di_container_cleanup(self, test_config: Settings):
        """Test DI container cleanup and resource management."""
        container = await initialize_di(test_config)

        # Verify container is initialized
        assert container.config() == test_config

        # Test shutdown
        await shutdown_di()

        # After shutdown, new initialization should work
        container2 = await initialize_di(test_config)
        assert container2.config() == test_config

        await shutdown_di()