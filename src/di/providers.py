"""
Dependency Injection Providers for DevClaude_bot components.

This implements specialized provider containers for different application layers,
following the Enhanced Architect Bot recommendations for better separation of concerns.
"""

from dependency_injector import containers, providers
import structlog

logger = structlog.get_logger(__name__)


class StorageProvidersContainer(containers.DeclarativeContainer):
    """Storage layer dependency providers."""

    config = providers.Dependency()
    storage = providers.Dependency()

    # Storage components
    storage_factory = providers.Factory(
        "src.storage.facade.Storage",
        config.database_url,
    )

    session_storage = providers.Factory(
        "src.storage.session_storage.SQLiteSessionStorage",
        storage.provided.db_manager,
    )


class SecurityProvidersContainer(containers.DeclarativeContainer):
    """Security layer dependency providers."""

    config = providers.Dependency()
    storage = providers.Dependency()

    # RBAC Manager
    rbac_manager = providers.Factory(
        "src.security.rbac.RBACManager",
        storage=storage,
    )

    # Auth providers
    whitelist_auth_provider = providers.Factory(
        "src.security.auth.WhitelistAuthProvider",
        config.allowed_users,
        allow_all_dev=config.development_mode,
    )

    token_storage = providers.Factory(
        "src.security.auth.InMemoryTokenStorage",
    )

    token_auth_provider = providers.Factory(
        "src.security.auth.TokenAuthProvider",
        config.auth_token_secret,
        token_storage,
    )

    # Auth manager with dynamic provider selection and RBAC
    auth_manager = providers.Factory(
        "src.security.auth.AuthenticationManager",
        providers.List(
            whitelist_auth_provider,
            token_auth_provider.provided[config.enable_token_auth],
        ),
        rbac_manager=rbac_manager,
    )

    # Security validator
    security_validator = providers.Factory(
        "src.security.validators.SecurityValidator",
        config.approved_directory,
        flexible_mode=providers.Object(False),  # Can be made configurable
    )

    # Rate limiter
    rate_limiter = providers.Factory(
        "src.security.rate_limiter.RateLimiter",
        config,
    )

    # Audit components
    audit_storage = providers.Factory(
        "src.security.audit.InMemoryAuditStorage",
    )

    audit_logger = providers.Factory(
        "src.security.audit.AuditLogger",
        audit_storage,
    )


class ClaudeProvidersContainer(containers.DeclarativeContainer):
    """Claude integration layer dependency providers."""

    config = providers.Dependency()
    storage = providers.Dependency()
    security_validator = providers.Dependency()

    # Session management
    session_manager = providers.Factory(
        "src.claude.session.SessionManager",
        config,
        storage.session_storage,
    )

    # Tool monitoring
    tool_monitor = providers.Factory(
        "src.claude.monitor.ToolMonitor",
        config,
        security_validator,
    )

    # Process manager (for CLI mode)
    process_manager = providers.Factory(
        "src.claude.integration.ClaudeProcessManager",
        config,
    )

    # SDK manager (for SDK mode) - currently disabled
    sdk_manager = providers.Object(None)

    # Main Claude integration facade
    claude_integration = providers.Factory(
        "src.claude.facade.ClaudeIntegration",
        config=config,
        process_manager=process_manager.provided[~config.use_sdk],
        sdk_manager=sdk_manager.provided[config.use_sdk],
        session_manager=session_manager,
        tool_monitor=tool_monitor,
    )


class LocalizationProvidersContainer(containers.DeclarativeContainer):
    """Localization layer dependency providers."""

    config = providers.Dependency()
    storage = providers.Dependency()

    # Localization manager
    localization_manager = providers.Factory(
        "src.localization.LocalizationManager",
    )

    # User language storage
    user_language_storage = providers.Factory(
        "src.localization.UserLanguageStorage",
        storage,
    )


class MCPProvidersContainer(containers.DeclarativeContainer):
    """MCP (Model Context Protocol) layer dependency providers."""

    config = providers.Dependency()
    storage = providers.Dependency()
    claude_integration = providers.Dependency()

    # MCP manager
    mcp_manager = providers.Factory(
        "src.mcp.manager.MCPManager",
        config,
        storage,
    )

    # MCP context handler
    mcp_context_handler = providers.Factory(
        "src.mcp.context_handler.MCPContextHandler",
        mcp_manager=mcp_manager,
        claude_integration=claude_integration,
        storage=storage,
    )


class ImageProvidersContainer(containers.DeclarativeContainer):
    """Image processing layer dependency providers."""

    config = providers.Dependency()
    security_validator = providers.Dependency()

    # Image processor
    image_processor = providers.Factory(
        "src.bot.features.image_processor.ImageProcessor",
        config,
        security_validator,
    )

    # Image command handler
    image_command_handler = providers.Factory(
        "src.bot.handlers.image_command.ImageCommandHandler",
        config,
        image_processor,
    )


class BotProvidersContainer(containers.DeclarativeContainer):
    """Bot layer dependency providers."""

    config = providers.Dependency()
    storage = providers.Dependency()
    security = providers.Dependency()
    claude = providers.Dependency()

    # Localization providers
    localization_providers = providers.Container(
        LocalizationProvidersContainer,
        config=config,
        storage=storage,
    )

    # MCP providers
    mcp_providers = providers.Container(
        MCPProvidersContainer,
        config=config,
        storage=storage,
        claude_integration=claude.claude_integration,
    )

    # Image providers (conditional)
    image_providers = providers.Container(
        ImageProvidersContainer,
        config=config,
        security_validator=security.security_validator,
    )

    # Bot dependencies dictionary
    dependencies = providers.Dict(
        auth_manager=security.auth_manager,
        security_validator=security.security_validator,
        rate_limiter=security.rate_limiter,
        audit_logger=security.audit_logger,
        claude_integration=claude.claude_integration,
        storage=storage,
        localization=localization_providers.localization_manager.provided[config.enable_localization],
        user_language_storage=localization_providers.user_language_storage.provided[config.enable_localization],
        mcp_manager=mcp_providers.mcp_manager,
        mcp_context_handler=mcp_providers.mcp_context_handler,
        image_command_handler=image_providers.image_command_handler.provided[config.enable_image_processing],
    )

    # Main bot instance
    bot = providers.Factory(
        "src.bot.core.ClaudeCodeBot",
        config,
        dependencies,
    )