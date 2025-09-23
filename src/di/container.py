"""
Enhanced Dependency Injection Container for DevClaude_bot

This implements the DI Container recommendation from Enhanced Architect Bot analysis.
Replaces manual dependency management with a professional DI framework.
"""

from typing import Dict, Any
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
import structlog

from src.config.settings import Settings
from .providers import (
    SecurityProvidersContainer,
    ClaudeProvidersContainer,
    BotProvidersContainer,
    StorageProvidersContainer,
)


logger = structlog.get_logger(__name__)


class ApplicationContainer(containers.DeclarativeContainer):
    """
    Main application dependency injection container.

    Implements professional DI patterns as recommended by Enhanced Architect Bot:
    - Centralized dependency management
    - Type-safe configuration injection
    - Proper lifecycle management
    - Clear separation of concerns
    """

    # Wire with main modules
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.main",
            "src.bot.core",
            "src.claude.facade",
            "src.security.auth",
        ]
    )

    # Configuration provider
    config = providers.Dependency(instance_of=Settings)

    # Storage container
    storage = providers.DependenciesContainer()
    storage_providers = providers.Container(
        StorageProvidersContainer,
        config=config,
        storage=storage.storage,
    )

    # Security container
    security = providers.DependenciesContainer()
    security_providers = providers.Container(
        SecurityProvidersContainer,
        config=config,
        storage=storage.storage,
    )

    # Claude integration container
    claude = providers.DependenciesContainer()
    claude_providers = providers.Container(
        ClaudeProvidersContainer,
        config=config,
        storage=storage.storage,
        security_validator=security.security_validator,
    )

    # Bot container
    bot = providers.DependenciesContainer()
    bot_providers = providers.Container(
        BotProvidersContainer,
        config=config,
        storage=storage.storage,
        security=security,
        claude=claude,
    )

    # Application factory
    @providers.singleton
    @inject
    def application_factory(
        self,
        config: Settings = Provide[config],
        storage: Any = Provide[storage.storage],
        bot: Any = Provide[bot.bot],
        claude_integration: Any = Provide[claude.claude_integration],
    ) -> Dict[str, Any]:
        """Create configured application components."""
        logger.info("Creating application via DI container")

        return {
            "bot": bot,
            "claude_integration": claude_integration,
            "storage": storage,
            "config": config,
        }

    # Health check service
    @providers.singleton
    def health_service(self) -> "HealthService":
        """Create health monitoring service."""
        from .health import HealthService
        return HealthService(
            storage=self.storage.storage(),
            claude_integration=self.claude.claude_integration(),
            security=self.security.auth_manager(),
        )


class DIManager:
    """
    Dependency Injection Manager for simplified container management.

    Provides convenience methods for container initialization and wiring.
    """

    def __init__(self):
        self.container: ApplicationContainer = None
        self._initialized = False

    async def initialize(self, config: Settings) -> ApplicationContainer:
        """Initialize the DI container with configuration."""
        if self._initialized:
            logger.warning("DI container already initialized")
            return self.container

        logger.info("Initializing DI container")

        # Create container
        self.container = ApplicationContainer()

        # Provide configuration
        self.container.config.override(config)

        # Wire dependencies
        self.container.wire(modules=[
            "src.main",
            "src.bot.core",
            "src.claude.facade",
            "src.security.auth",
        ])

        self._initialized = True
        logger.info("DI container initialized successfully")

        return self.container

    def get_container(self) -> ApplicationContainer:
        """Get the initialized container."""
        if not self._initialized:
            raise RuntimeError("DI container not initialized. Call initialize() first.")
        return self.container

    async def shutdown(self):
        """Shutdown the DI container."""
        if self.container:
            logger.info("Shutting down DI container")
            self.container.unwire()
            self._initialized = False
            logger.info("DI container shutdown complete")


# Global DI manager instance
di_manager = DIManager()


# Convenience functions
async def initialize_di(config: Settings) -> ApplicationContainer:
    """Initialize the global DI container."""
    return await di_manager.initialize(config)


def get_di_container() -> ApplicationContainer:
    """Get the global DI container."""
    return di_manager.get_container()


async def shutdown_di():
    """Shutdown the global DI container."""
    await di_manager.shutdown()