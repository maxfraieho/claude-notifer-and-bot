"""Main Telegram bot class.

Features:
- Command registration
- Handler management
- Context injection
- Graceful shutdown
"""

import asyncio
from typing import Any, Callable, Dict, Optional

import structlog
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..config.features import FeatureFlags
from ..config.settings import Settings
from ..exceptions import ClaudeCodeTelegramError
from .features.registry import FeatureRegistry

logger = structlog.get_logger()


class ClaudeCodeBot:
    """Main bot orchestrator."""

    def __init__(self, settings: Settings, dependencies: Dict[str, Any]):
        """Initialize bot with settings and dependencies."""
        self.settings = settings
        self.deps = dependencies
        self.app: Optional[Application] = None
        self.is_running = False
        self.feature_registry: Optional[FeatureRegistry] = None

    async def initialize(self) -> None:
        """Initialize bot application."""
        logger.info("Initializing Telegram bot")

        # Create application with persistence
        from telegram.ext import PicklePersistence
        import os

        # Set up persistence for user_data and context
        persistence_file = os.path.join(os.getcwd(), "data", "telegram_persistence.pickle")
        os.makedirs(os.path.dirname(persistence_file), exist_ok=True)
        persistence = PicklePersistence(filepath=persistence_file)

        builder = Application.builder()
        builder.token(self.settings.telegram_token_str)
        builder.persistence(persistence)

        # Configure connection settings
        builder.connect_timeout(30)
        builder.read_timeout(30)
        builder.write_timeout(30)
        builder.pool_timeout(30)

        self.app = builder.build()

        # Initialize feature registry
        self.feature_registry = FeatureRegistry(
            config=self.settings,
            storage=self.deps.get("storage"),
            security=self.deps.get("security"),
        )

        # Add feature registry to dependencies
        self.deps["features"] = self.feature_registry

        # Set bot commands for menu
        await self._set_bot_commands()

        # Register handlers
        self._register_handlers()

        # Add middleware
        self._add_middleware()

        # Add Claude availability middleware
        from .middleware.claude_availability import claude_availability_middleware
        self.app.add_handler(
            MessageHandler(
                filters.ALL, self._create_middleware_handler(claude_availability_middleware)
            ),
            group=-4,
        )

        # Set error handler
        self.app.add_error_handler(self._error_handler)

        # Set up Claude availability monitoring if enabled
        features = FeatureFlags(self.settings)
        if features.claude_availability_monitor:
            from .features.availability_monitor import setup_availability_monitor
            await setup_availability_monitor(self.app, self.settings)

        # TODO: Fix TaskScheduler import issues
        # Initialize task scheduler for automated task execution
        # await self._setup_task_scheduler()

        logger.info("Bot initialization complete")

    async def _set_bot_commands(self) -> None:
        """Set bot command menu."""
        commands = [
            BotCommand("start", "Start bot and show help"),
            BotCommand("help", "Show available commands"),
            BotCommand("new", "Start new Claude session"),
            BotCommand("continue", "Continue last session"),
            BotCommand("ls", "List files in current directory"),
            BotCommand("cd", "Change directory"),
            BotCommand("pwd", "Show current directory"),
            BotCommand("status", "Show session status"),
            BotCommand("export", "Export current session"),
            BotCommand("actions", "Show quick actions"),
            BotCommand("git", "Git repository commands"),
            BotCommand("login", "Authenticate Claude CLI"),
            BotCommand("cancel", "Cancel authentication process"),
            BotCommand("schedules", "Manage scheduled tasks"),
            BotCommand("add_schedule", "Add new scheduled task"),
            BotCommand("auto", "Toggle automation mode"),
            BotCommand("restart", "Restart the bot"),
            BotCommand("audit", "Intelligent bot code audit"),
            BotCommand("dracon", "DRACON-YAML bot logic modeling"),
            BotCommand("refactor", "Reverse engineer bot to DRACON schemas"),
            BotCommand("claude_status", "Show Claude CLI availability status"),
            BotCommand("claude_notifications", "Manage Claude availability notifications"),
            BotCommand("claude_history", "Show Claude availability history"),
        ]

        # Add image processing command if enabled
        if self.settings.enable_image_processing:
            commands.append(BotCommand("img", "Process images with Claude"))

        # Add MCP commands
        commands.extend([
            BotCommand("mcpadd", "Add MCP server"),
            BotCommand("mcplist", "List MCP servers"),
            BotCommand("mcpselect", "Select active MCP context"),
            BotCommand("mcpask", "Ask with MCP context"),
            BotCommand("mcpremove", "Remove MCP server"),
            BotCommand("mcpstatus", "Show MCP system status"),
        ])

        await self.app.bot.set_my_commands(commands)
        logger.info("Bot commands set", commands=[cmd.command for cmd in commands])

    def _register_handlers(self) -> None:
        """Register all command and message handlers."""
        from .handlers import callback, command, message, mcp_commands

        # Command handlers
        handlers = [
            ("start", command.start_command),
            ("help", command.help_handler),
            ("new", command.new_handler),
            ("continue", command.continue_session),
            ("end", command.end_session),
            ("ls", command.list_files),
            ("cd", command.change_directory),
            ("pwd", command.pwd_handler),
            ("status", command.status_handler),
            ("export", command.export_session),
            ("actions", command.actions_handler),
            ("git", command.git_handler),
            ("login", command.login_command),
            ("cancel", command.cancel_auth_command),
            ("schedules", command.schedules_command),
            ("add_schedule", command.add_schedule_command),
            ("restart", command.restart_command),
            ("audit", command.audit_command),
            ("dracon", command.dracon_command),
            ("refactor", command.refactor_command),
            ("claude_status", command.claude_status_command),
            ("claude_notifications", command.claude_notifications_command),
            ("claude_history", command.claude_history_command),
        ]

        # Add image processing command if enabled
        if self.settings.enable_image_processing:
            handlers.append(("img", command.img_command))

        # Add task scheduler commands
        from .handlers import task_commands
        handlers.extend([
            ("auto", task_commands.auto_mode_command),
        ])

        # Add MCP command handlers
        handlers.extend([
            ("mcpadd", mcp_commands.mcpadd_command),
            ("mcplist", mcp_commands.mcplist_command),
            ("mcpselect", mcp_commands.mcpselect_command),
            ("mcpask", mcp_commands.mcpask_command),
            ("mcpremove", mcp_commands.mcpremove_command),
            ("mcpstatus", mcp_commands.mcpstatus_command),
        ])

        for cmd, handler in handlers:
            self.app.add_handler(CommandHandler(cmd, self._inject_deps(handler)))

        # Message handlers with priority groups
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._inject_deps(message.handle_text_message),
            ),
            group=10,
        )

        self.app.add_handler(
            MessageHandler(
                filters.Document.ALL, self._inject_deps(message.handle_document)
            ),
            group=10,
        )

        self.app.add_handler(
            MessageHandler(filters.PHOTO, self._inject_deps(message.handle_photo)),
            group=10,
        )

        # Callback query handler
        self.app.add_handler(
            CallbackQueryHandler(self._inject_deps(callback.handle_callback_query))
        )

        logger.info("Bot handlers registered")

    def _inject_deps(self, handler: Callable) -> Callable:
        """Inject dependencies into handlers."""

        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Add dependencies to context
            for key, value in self.deps.items():
                context.bot_data[key] = value

            # Add settings
            context.bot_data["settings"] = self.settings

            return await handler(update, context)

        return wrapped

    def _add_middleware(self) -> None:
        """Add middleware to application."""
        from .middleware.auth import auth_middleware
        from .middleware.rate_limit import rate_limit_middleware
        from .middleware.security import security_middleware

        # Middleware runs in order of group numbers (lower = earlier)
        # Security middleware first (validate inputs)
        self.app.add_handler(
            MessageHandler(
                filters.ALL, self._create_middleware_handler(security_middleware)
            ),
            group=-3,
        )

        # Authentication second
        self.app.add_handler(
            MessageHandler(
                filters.ALL, self._create_middleware_handler(auth_middleware)
            ),
            group=-2,
        )

        # Rate limiting third
        self.app.add_handler(
            MessageHandler(
                filters.ALL, self._create_middleware_handler(rate_limit_middleware)
            ),
            group=-1,
        )

        logger.info("Middleware added to bot")

    def _create_middleware_handler(self, middleware_func: Callable) -> Callable:
        """Create middleware handler that injects dependencies."""

        async def middleware_wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE
        ):
            # Inject dependencies into context
            for key, value in self.deps.items():
                context.bot_data[key] = value
            context.bot_data["settings"] = self.settings

            # Create a dummy handler that continues processing
            async def continue_handler(event, data):
                # This allows the message to continue to the actual handlers
                return None

            # Call middleware with Telegram-style parameters
            result = await middleware_func(continue_handler, update, context.bot_data)
            
            # If middleware returns None, it blocked the request
            # If it returns result of handler, continue processing
            return result

        return middleware_wrapper

    async def start(self) -> None:
        """Start the bot."""
        if self.is_running:
            logger.warning("Bot is already running")
            return

        await self.initialize()

        logger.info(
            "Starting bot", mode="webhook" if self.settings.webhook_url else "polling"
        )

        try:
            self.is_running = True

            if self.settings.webhook_url:
                # Webhook mode
                await self.app.run_webhook(
                    listen="0.0.0.0",
                    port=self.settings.webhook_port,
                    url_path=self.settings.webhook_path,
                    webhook_url=self.settings.webhook_url,
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES,
                )
            else:
                # Polling mode - initialize and start polling manually
                await self.app.initialize()
                await self.app.start()
                await self.app.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                )

                # Keep running until manually stopped
                while self.is_running:
                    await asyncio.sleep(1)
        except Exception as e:
            logger.error("Error running bot", error=str(e))
            raise ClaudeCodeTelegramError(f"Failed to start bot: {str(e)}") from e
        finally:
            self.is_running = False

    async def stop(self) -> None:
        """Gracefully stop the bot."""
        if not self.is_running:
            logger.warning("Bot is not running")
            return

        logger.info("Stopping bot")

        try:
            self.is_running = False  # Stop the main loop first

            # Shutdown feature registry
            if self.feature_registry:
                self.feature_registry.shutdown()

            if self.app:
                # Stop the updater if it's running
                if self.app.updater.running:
                    await self.app.updater.stop()

                # Stop the application
                await self.app.stop()
                await self.app.shutdown()

            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error("Error stopping bot", error=str(e))
            raise ClaudeCodeTelegramError(f"Failed to stop bot: {str(e)}") from e

    async def _error_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle errors globally."""
        import traceback
        error = context.error
        logger.error(
            "Global error handler triggered",
            error=str(error),
            error_type=type(error).__name__ if error else None,
            traceback=traceback.format_exc(),
            update_type=type(update).__name__ if update else None,
            user_id=(
                update.effective_user.id if update and update.effective_user else None
            ),
        )

        # Determine error message for user
        from ..exceptions import (
            AuthenticationError,
            ConfigurationError,
            RateLimitExceeded,
            SecurityError,
        )

        error_messages = {
            AuthenticationError: "🔒 Authentication required. Please contact the administrator.",
            SecurityError: "🛡️ Security violation detected. This incident has been logged.",
            RateLimitExceeded: "⏱️ Rate limit exceeded. Please wait before sending more messages.",
            ConfigurationError: "⚙️ Configuration error. Please contact the administrator.",
            asyncio.TimeoutError: "⏰ Operation timed out. Please try again with a simpler request.",
        }

        error_type = type(error)
        user_message = error_messages.get(
            error_type, "❌ An unexpected error occurred. Please try again."
        )

        # Try to notify user
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(user_message)
            except Exception:
                logger.exception("Failed to send error message to user")

        # Log to audit system if available
        from ..security.audit import AuditLogger

        audit_logger: Optional[AuditLogger] = context.bot_data.get("audit_logger")
        if audit_logger and update and update.effective_user:
            try:
                await audit_logger.log_security_violation(
                    user_id=update.effective_user.id,
                    violation_type="system_error",
                    details=f"Error type: {error_type.__name__}, Message: {str(error)}",
                    severity="medium",
                )
            except Exception:
                logger.exception("Failed to log error to audit system")

    async def _setup_task_scheduler(self) -> None:
        """Initialize task scheduler for automated execution."""
        try:
            logger.info("Setting up task scheduler")

            # Initialize scheduled task repository
            from ..storage.repositories.scheduled_task_repository import ScheduledTaskRepository
            task_repository = ScheduledTaskRepository(self.deps["database"].db_path)
            await task_repository.create_table()

            # Initialize task scheduler
            from .features.task_scheduler import TaskScheduler
            task_scheduler = TaskScheduler(
                repository=task_repository,
                claude_integration=self.deps["claude_integration"],
                settings=self.settings
            )

            # Store in bot context for access by handlers
            self.app.bot_data["task_scheduler"] = task_scheduler
            self.app.bot_data["task_repository"] = task_repository

            logger.info("Task scheduler initialized successfully")

        except Exception as e:
            logger.error("Failed to setup task scheduler", error=str(e), exc_info=True)
            # Don't raise - this is not critical for basic bot operation

    async def get_bot_info(self) -> Dict[str, Any]:
        """Get bot information."""
        if not self.app:
            return {"status": "not_initialized"}

        try:
            me = await self.app.bot.get_me()
            return {
                "status": "running" if self.is_running else "initialized",
                "username": me.username,
                "first_name": me.first_name,
                "id": me.id,
                "can_join_groups": me.can_join_groups,
                "can_read_all_group_messages": me.can_read_all_group_messages,
                "supports_inline_queries": me.supports_inline_queries,
                "webhook_url": self.settings.webhook_url,
                "webhook_port": (
                    self.settings.webhook_port if self.settings.webhook_url else None
                ),
            }
        except Exception as e:
            logger.error("Failed to get bot info", error=str(e))
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            if not self.app:
                return False

            # Try to get bot info
            await self.app.bot.get_me()
            return True
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False