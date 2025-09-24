"""Main entry point for Claude Code Telegram Bot."""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Dict

import structlog

from src import __version__
from src.config.features import FeatureFlags
from src.config.loader import load_config
from src.config.settings import Settings
from src.exceptions import ConfigurationError
from src.errors import handle_errors, ErrorHandler, DevClaudeError
from src.di import ApplicationContainer, initialize_di, shutdown_di, get_di_container
from src.bot.integration import initialize_enhanced_modules, get_enhanced_integration


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging."""
    level = logging.DEBUG if debug else logging.INFO

    # Clear any existing handlers to prevent duplication
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure standard logging with single handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    
    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.dev.ConsoleRenderer(colors=True)
                if debug
                else structlog.processors.JSONRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def acquire_bot_lock() -> None:
    """Ensure only one bot instance is running."""
    lock_file = Path("/tmp/claude_bot.lock")

    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                old_pid = int(f.read().strip())

            # Check if process is still running
            try:
                os.kill(old_pid, 0)  # Signal 0 just checks if process exists
                print(f"❌ Bot already running with PID {old_pid}")
                print("Stop the existing instance first or wait for it to finish.")
                sys.exit(1)
            except OSError:
                # Process doesn't exist, remove stale lock file
                lock_file.unlink()
        except (ValueError, FileNotFoundError):
            # Invalid or missing lock file, remove it
            lock_file.unlink(missing_ok=True)

    # Create new lock file with current PID
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))

    # Register cleanup function
    def cleanup_lock():
        lock_file.unlink(missing_ok=True)

    import atexit
    atexit.register(cleanup_lock)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Claude Code Telegram Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", action="version", version=f"Claude Code Telegram Bot {__version__}"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument("--config-file", type=Path, help="Path to configuration file")

    return parser.parse_args()


@handle_errors(retry_count=2, operation_name="create_application")
async def create_application(config: Settings) -> Dict[str, Any]:
    """
    Create and configure the application components using DI Container.

    This replaces manual dependency management with professional DI patterns
    as recommended by Enhanced Architect Bot analysis.
    """
    logger = structlog.get_logger()
    logger.info("Creating application components via DI Container")

    # Initialize DI container
    container = await initialize_di(config)

    # Initialize storage system
    storage = container.get("storage")
    await storage.initialize()

    # Initialize enhanced modules
    logger.info("Initializing enhanced modules")
    await initialize_enhanced_modules()

    # Create application via container factory
    app_components = container.get("application")

    logger.info("Application components created successfully via DI Container")

    return app_components


@handle_errors(retry_count=1, operation_name="run_application")
async def run_application(app: Dict[str, Any]) -> None:
    """Run the application with graceful shutdown handling."""
    logger = structlog.get_logger()
    bot: ClaudeCodeBot = app["bot"]
    claude_integration: ClaudeIntegration = app["claude_integration"]
    storage: Storage = app["storage"]

    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info("Shutdown signal received", signal=signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start the bot
        logger.info("Starting Claude Code Telegram Bot")

        # Run bot in background task
        bot_task = asyncio.create_task(bot.start())
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        # Wait for either bot completion or shutdown signal
        done, pending = await asyncio.wait(
            [bot_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error("Application error", error=str(e))
        raise
    finally:
        # Graceful shutdown
        logger.info("Shutting down application")

        try:
            await bot.stop()
            await claude_integration.shutdown()
            await storage.close()
            await shutdown_di()  # Shutdown DI container
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))

        logger.info("Application shutdown complete")


async def main() -> None:
    """Main application entry point."""
    args = parse_args()

    # Acquire process lock to prevent multiple instances
    acquire_bot_lock()

    setup_logging(debug=args.debug)

    logger = structlog.get_logger()
    logger.info("Starting Claude Code Telegram Bot", version=__version__)

    try:
        # Load configuration
        from src.config import FeatureFlags, load_config

        config = load_config(config_file=args.config_file)
        features = FeatureFlags(config)

        logger.info(
            "Configuration loaded",
            environment="production" if config.is_production else "development",
            enabled_features=features.get_enabled_features(),
            debug=config.debug,
        )

        # Initialize bot and Claude integration
        app = await create_application(config)
        await run_application(app)

    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error", error=str(e))
        sys.exit(1)


def run() -> None:
    """Synchronous entry point for setuptools."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)


if __name__ == "__main__":
    run()
