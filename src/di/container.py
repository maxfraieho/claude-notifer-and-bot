"""
Enhanced Dependency Injection Container for DevClaude_bot

This implements the DI Container recommendation from Enhanced Architect Bot analysis.
Uses lightweight custom DI implementation compatible with Python 3.12.
"""

from typing import Dict, Any, TypeVar, Type, Callable, Optional, Union
import structlog
from abc import ABC, abstractmethod

from src.config.settings import Settings

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class Provider(ABC):
    """Base provider class for dependency injection."""

    @abstractmethod
    def provide(self, container: 'DIContainer') -> Any:
        """Provide the dependency."""
        pass


class FactoryProvider(Provider):
    """Factory provider that creates new instances."""

    def __init__(self, factory: Callable, *args, **kwargs):
        self.factory = factory
        self.args = args
        self.kwargs = kwargs

    def provide(self, container: 'DIContainer') -> Any:
        """Create new instance using factory."""
        # Resolve dependencies in args and kwargs
        resolved_args = []
        for arg in self.args:
            if isinstance(arg, Provider):
                resolved_args.append(arg.provide(container))
            else:
                resolved_args.append(arg)

        resolved_kwargs = {}
        for key, value in self.kwargs.items():
            if isinstance(value, Provider):
                resolved_kwargs[key] = value.provide(container)
            else:
                resolved_kwargs[key] = value

        return self.factory(*resolved_args, **resolved_kwargs)


class SingletonProvider(Provider):
    """Singleton provider that caches instances."""

    def __init__(self, factory: Callable, *args, **kwargs):
        self.factory = factory
        self.args = args
        self.kwargs = kwargs
        self._instance = None
        self._created = False

    def provide(self, container: 'DIContainer') -> Any:
        """Get or create singleton instance."""
        if not self._created:
            # Resolve dependencies in args and kwargs
            resolved_args = []
            for arg in self.args:
                if isinstance(arg, Provider):
                    resolved_args.append(arg.provide(container))
                else:
                    resolved_args.append(arg)

            resolved_kwargs = {}
            for key, value in self.kwargs.items():
                if isinstance(value, Provider):
                    resolved_kwargs[key] = value.provide(container)
                else:
                    resolved_kwargs[key] = value

            self._instance = self.factory(*resolved_args, **resolved_kwargs)
            self._created = True

        return self._instance


class ValueProvider(Provider):
    """Value provider that returns static values."""

    def __init__(self, value: Any):
        self.value = value

    def provide(self, container: 'DIContainer') -> Any:
        """Return static value."""
        return self.value


class DIContainer:
    """
    Lightweight Dependency Injection Container.

    Implements professional DI patterns recommended by Enhanced Architect Bot.
    """

    def __init__(self):
        self._providers: Dict[str, Provider] = {}
        self._config: Optional[Settings] = None

    def register(self, name: str, provider: Provider):
        """Register a provider with a name."""
        self._providers[name] = provider
        logger.debug("Provider registered", name=name, provider_type=type(provider).__name__)

    def factory(self, name: str, factory: Callable, *args, **kwargs):
        """Register a factory provider."""
        self.register(name, FactoryProvider(factory, *args, **kwargs))

    def singleton(self, name: str, factory: Callable, *args, **kwargs):
        """Register a singleton provider."""
        self.register(name, SingletonProvider(factory, *args, **kwargs))

    def value(self, name: str, value: Any):
        """Register a value provider."""
        self.register(name, ValueProvider(value))

    def get(self, name: str) -> Any:
        """Get dependency by name."""
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not found")

        return self._providers[name].provide(self)

    def has(self, name: str) -> bool:
        """Check if provider exists."""
        return name in self._providers

    def set_config(self, config: Settings):
        """Set configuration."""
        self._config = config
        self.value("config", config)

    def get_config(self) -> Settings:
        """Get configuration."""
        if not self._config:
            raise ValueError("Configuration not set")
        return self._config


class ApplicationContainer:
    """
    Main application container with pre-configured providers.

    Implements the architecture recommended by Enhanced Architect Bot.
    """

    def __init__(self):
        self.container = DIContainer()
        self._initialized = False

    async def initialize(self, config: Settings):
        """Initialize container with configuration."""
        if self._initialized:
            logger.warning("Container already initialized")
            return

        logger.info("Initializing DI container")

        # Set configuration
        self.container.set_config(config)

        # Register storage providers
        await self._register_storage_providers(config)

        # Register security providers
        await self._register_security_providers(config)

        # Register Claude providers
        await self._register_claude_providers(config)

        # Register bot providers
        await self._register_bot_providers(config)

        # Register application factory
        self._register_application_factory()

        self._initialized = True
        logger.info("DI container initialized successfully")

    async def _register_storage_providers(self, config: Settings):
        """Register storage layer providers."""
        from src.storage.facade import Storage
        from src.storage.session_storage import SQLiteSessionStorage

        # Storage singleton
        self.container.singleton("storage", Storage, config.database_url)

        # Session storage factory
        def create_session_storage():
            storage = self.container.get("storage")
            return SQLiteSessionStorage(storage.db_manager)

        self.container.factory("session_storage", create_session_storage)

    async def _register_security_providers(self, config: Settings):
        """Register security layer providers."""
        from src.security.rbac import RBACManager
        from src.security.auth import (
            AuthenticationManager, WhitelistAuthProvider,
            TokenAuthProvider, InMemoryTokenStorage
        )
        from src.security.validators import SecurityValidator
        from src.security.rate_limiter import RateLimiter
        from src.security.audit import AuditLogger, InMemoryAuditStorage

        # RBAC Manager
        def create_rbac_manager():
            storage = self.container.get("storage")
            return RBACManager(storage=storage)

        self.container.singleton("rbac_manager", create_rbac_manager)

        # Auth providers
        allowed_users = getattr(config, 'allowed_users', [])
        self.container.factory(
            "whitelist_auth_provider",
            WhitelistAuthProvider,
            allowed_users,
            allow_all_dev=config.development_mode
        )

        if config.enable_token_auth:
            self.container.factory("token_storage", InMemoryTokenStorage)

            def create_token_auth_provider():
                token_storage = self.container.get("token_storage")
                return TokenAuthProvider(config.auth_token_secret, token_storage)

            self.container.factory("token_auth_provider", create_token_auth_provider)

        # Auth manager
        def create_auth_manager():
            providers = [self.container.get("whitelist_auth_provider")]
            if config.enable_token_auth:
                providers.append(self.container.get("token_auth_provider"))

            rbac_manager = self.container.get("rbac_manager")
            return AuthenticationManager(providers, rbac_manager=rbac_manager)

        self.container.singleton("auth_manager", create_auth_manager)

        # Security validator
        self.container.factory(
            "security_validator",
            SecurityValidator,
            config.approved_directory,
            flexible_mode=False
        )

        # Rate limiter
        self.container.factory("rate_limiter", RateLimiter, config)

        # Audit components
        self.container.factory("audit_storage", InMemoryAuditStorage)

        def create_audit_logger():
            audit_storage = self.container.get("audit_storage")
            return AuditLogger(audit_storage)

        self.container.factory("audit_logger", create_audit_logger)

    async def _register_claude_providers(self, config: Settings):
        """Register Claude integration providers."""
        from src.claude.session import SessionManager
        from src.claude.monitor import ToolMonitor
        from src.claude.integration import ClaudeProcessManager
        from src.claude.context_memory import ContextMemoryManager
        from src.claude.facade import ClaudeIntegration

        # Session manager
        def create_session_manager():
            session_storage = self.container.get("session_storage")
            return SessionManager(config, session_storage)

        self.container.factory("session_manager", create_session_manager)

        # Tool monitor
        def create_tool_monitor():
            security_validator = self.container.get("security_validator")
            return ToolMonitor(config, security_validator)

        self.container.factory("tool_monitor", create_tool_monitor)

        # Context memory manager
        def create_context_memory():
            storage = self.container.get("storage")
            return ContextMemoryManager(storage)

        self.container.factory("context_memory", create_context_memory)

        # Context commands
        def create_context_commands():
            storage = self.container.get("storage")
            context_memory = self.container.get("context_memory")
            from src.bot.features.context_commands import ContextCommands
            return ContextCommands(storage, context_memory)

        self.container.factory("context_commands", create_context_commands)

        # Unified menu system
        def create_unified_menu():
            storage = self.container.get("storage")
            context_memory = self.container.get("context_memory")
            from src.bot.features.unified_menu import UnifiedMenu
            return UnifiedMenu(storage, context_memory)

        self.container.factory("unified_menu", create_unified_menu)

        # Process manager (for CLI mode)
        if not config.use_sdk:
            self.container.factory("process_manager", ClaudeProcessManager, config)

        # Claude integration facade
        def create_claude_integration():
            process_manager = self.container.get("process_manager") if not config.use_sdk else None
            session_manager = self.container.get("session_manager")
            tool_monitor = self.container.get("tool_monitor")
            context_memory = self.container.get("context_memory")

            return ClaudeIntegration(
                config=config,
                process_manager=process_manager,
                sdk_manager=None,  # SDK disabled for now
                session_manager=session_manager,
                tool_monitor=tool_monitor,
                context_memory=context_memory
            )

        self.container.singleton("claude_integration", create_claude_integration)

    async def _register_bot_providers(self, config: Settings):
        """Register bot layer providers."""
        # Localization (if enabled)
        if config.enable_localization:
            from src.localization import LocalizationManager, UserLanguageStorage

            self.container.factory("localization_manager", LocalizationManager)

            def create_user_language_storage():
                storage = self.container.get("storage")
                return UserLanguageStorage(storage)

            self.container.factory("user_language_storage", create_user_language_storage)

        # MCP components
        from src.mcp.manager import MCPManager
        from src.mcp.context_handler import MCPContextHandler

        def create_mcp_manager():
            storage = self.container.get("storage")
            return MCPManager(config, storage)

        self.container.factory("mcp_manager", create_mcp_manager)

        def create_mcp_context_handler():
            mcp_manager = self.container.get("mcp_manager")
            claude_integration = self.container.get("claude_integration")
            storage = self.container.get("storage")
            return MCPContextHandler(
                mcp_manager=mcp_manager,
                claude_integration=claude_integration,
                storage=storage
            )

        self.container.factory("mcp_context_handler", create_mcp_context_handler)

        # Image processing (if enabled)
        if config.enable_image_processing:
            from src.bot.features.image_processor import ImageProcessor
            from src.bot.handlers.image_command import ImageCommandHandler

            def create_image_processor():
                security_validator = self.container.get("security_validator")
                return ImageProcessor(config, security_validator)

            self.container.factory("image_processor", create_image_processor)

            def create_image_command_handler():
                image_processor = self.container.get("image_processor")
                return ImageCommandHandler(config, image_processor)

            self.container.factory("image_command_handler", create_image_command_handler)

        # Bot dependencies
        def create_bot_dependencies():
            dependencies = {
                "auth_manager": self.container.get("auth_manager"),
                "security_validator": self.container.get("security_validator"),
                "rate_limiter": self.container.get("rate_limiter"),
                "audit_logger": self.container.get("audit_logger"),
                "claude_integration": self.container.get("claude_integration"),
                "storage": self.container.get("storage"),
                "mcp_manager": self.container.get("mcp_manager"),
                "mcp_context_handler": self.container.get("mcp_context_handler"),
                "context_commands": self.container.get("context_commands"),
                "unified_menu": self.container.get("unified_menu"),
            }

            # Add optional components
            if config.enable_localization:
                dependencies["localization"] = self.container.get("localization_manager")
                dependencies["user_language_storage"] = self.container.get("user_language_storage")

            if config.enable_image_processing:
                dependencies["image_command_handler"] = self.container.get("image_command_handler")

            return dependencies

        self.container.factory("bot_dependencies", create_bot_dependencies)

        # Main bot instance
        from src.bot.core import ClaudeCodeBot

        def create_bot():
            dependencies = self.container.get("bot_dependencies")
            return ClaudeCodeBot(config, dependencies)

        self.container.singleton("bot", create_bot)

    def _register_application_factory(self):
        """Register application factory."""
        def create_application():
            return {
                "bot": self.container.get("bot"),
                "claude_integration": self.container.get("claude_integration"),
                "storage": self.container.get("storage"),
                "config": self.container.get("config"),
            }

        self.container.factory("application", create_application)

    def get(self, name: str) -> Any:
        """Get dependency by name."""
        return self.container.get(name)

    def has(self, name: str) -> bool:
        """Check if dependency exists."""
        return self.container.has(name)

    async def shutdown(self):
        """Shutdown container and cleanup resources."""
        logger.info("Shutting down DI container")

        # Cleanup singletons if they have cleanup methods
        try:
            if self.has("storage"):
                storage = self.get("storage")
                if hasattr(storage, 'close'):
                    await storage.close()
        except Exception as e:
            logger.error("Error closing storage", error=str(e))

        try:
            if self.has("claude_integration"):
                claude = self.get("claude_integration")
                if hasattr(claude, 'shutdown'):
                    await claude.shutdown()
        except Exception as e:
            logger.error("Error shutting down Claude integration", error=str(e))

        self._initialized = False
        logger.info("DI container shutdown complete")


# Global container instance
_global_container: Optional[ApplicationContainer] = None


async def initialize_di(config: Settings) -> ApplicationContainer:
    """Initialize the global DI container."""
    global _global_container

    if _global_container is None:
        _global_container = ApplicationContainer()

    await _global_container.initialize(config)
    return _global_container


def get_di_container() -> ApplicationContainer:
    """Get the global DI container."""
    if _global_container is None:
        raise RuntimeError("DI container not initialized. Call initialize_di() first.")
    return _global_container


async def shutdown_di():
    """Shutdown the global DI container."""
    global _global_container

    if _global_container:
        await _global_container.shutdown()
        _global_container = None