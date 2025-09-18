#!/usr/bin/env python3
"""
Telegram Bot with Process Management
Fixes "Conflict: terminated by other getUpdates request" error
"""

import asyncio
import fcntl
import logging
import os
import psutil
import signal
import sys
import time
from typing import Optional
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application, 
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes,
    MessageHandler,
    filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBotManager:
    """
    Manages Telegram bot lifecycle with proper process control
    """

    def __init__(self, token: str, lock_file_path: str = "/tmp/telegram_bot.lock"):
        self.token = token
        self.lock_file_path = lock_file_path
        self.lock_file = None
        self.application: Optional[Application] = None
        self.shutdown_flag = False

    def acquire_lock(self) -> bool:
        """
        Acquire exclusive lock to prevent multiple instances
        Returns True if lock acquired, False if another instance is running
        """
        try:
            self.lock_file = open(self.lock_file_path, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write PID to lock file for debugging
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()

            logger.info(f"Lock acquired. PID: {os.getpid()}")
            return True

        except (IOError, OSError) as e:
            logger.error(f"Could not acquire lock: {e}")
            logger.error("Another bot instance is already running!")
            return False

    def release_lock(self):
        """Release the process lock"""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                os.unlink(self.lock_file_path)
                logger.info("Lock released successfully")
            except Exception as e:
                logger.error(f"Error releasing lock: {e}")

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
            self.shutdown_flag = True

            # Stop the application gracefully
            if self.application and self.application.running:
                logger.info("Stopping application...")
                self.application.stop_running()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

        # On Unix systems, also handle SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)

    def kill_existing_instances(self, process_name_pattern: str = "python"):
        """
        Kill any existing bot processes to clean up zombies
        """
        current_pid = os.getpid()
        killed_count = 0

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Skip current process
                    if proc.info['pid'] == current_pid:
                        continue

                    # Check if process matches our bot pattern
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if (process_name_pattern in proc.info['name'] and 
                        'telegram' in cmdline.lower() and 
                        __file__ in cmdline):

                        logger.warning(f"Found existing bot process PID {proc.info['pid']}")
                        logger.info(f"Command: {cmdline}")

                        # Try graceful termination first
                        proc.terminate()

                        # Wait for graceful shutdown
                        try:
                            proc.wait(timeout=5)
                            logger.info(f"Process {proc.info['pid']} terminated gracefully")
                            killed_count += 1
                        except psutil.TimeoutExpired:
                            # Force kill if graceful shutdown fails
                            logger.warning(f"Force killing process {proc.info['pid']}")
                            proc.kill()
                            killed_count += 1

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process already gone or no permission
                    continue

        except Exception as e:
            logger.error(f"Error while cleaning up processes: {e}")

        if killed_count > 0:
            logger.info(f"Cleaned up {killed_count} existing bot process(es)")
            time.sleep(2)  # Give time for cleanup

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            f"Bot started! PID: {os.getpid()}"
        )

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        await update.message.reply_text("Stopping bot gracefully...")
        self.shutdown_flag = True
        self.application.stop_running()

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        status_msg = f"""
Bot Status:
PID: {os.getpid()}
Lock file: {self.lock_file_path}
Running: {not self.shutdown_flag}
Application running: {self.application.running if self.application else False}
        """
        await update.message.reply_text(status_msg)

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Echo any text message"""
        await update.message.reply_text(f"Echo: {update.message.text}")

    def build_application(self) -> Application:
        """Build and configure the Telegram application"""
        application = ApplicationBuilder().token(self.token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("stop", self.stop_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))

        # Add error handler
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            logger.error(f"Exception while handling an update: {context.error}")

        application.add_error_handler(error_handler)

        return application

    async def run_bot(self):
        """Main bot execution method"""
        try:
            # Setup signal handlers
            self.setup_signal_handlers()

            # Build application
            self.application = self.build_application()

            logger.info("Starting Telegram bot...")

            # Initialize application
            await self.application.initialize()
            await self.application.start()

            # Start polling with custom parameters
            await self.application.updater.start_polling(
                drop_pending_updates=True,  # Drop pending updates on restart
                allowed_updates=None,       # Allow all update types
            )

            logger.info("Bot is running. Press Ctrl+C to stop.")

            # Keep running until shutdown signal
            while not self.shutdown_flag:
                await asyncio.sleep(1)

                # Check if application is still running
                if not self.application.running:
                    logger.info("Application stopped, breaking main loop")
                    break

        except Exception as e:
            logger.error(f"Error in bot execution: {e}")
            raise
        finally:
            # Cleanup
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")

        if self.application:
            try:
                if self.application.updater.running:
                    await self.application.updater.stop()
                    logger.info("Updater stopped")

                if self.application.running:
                    await self.application.stop()
                    logger.info("Application stopped")

                await self.application.shutdown()
                logger.info("Application shutdown complete")

            except Exception as e:
                logger.error(f"Error during application cleanup: {e}")

        self.release_lock()
        logger.info("Cleanup complete")

    def run(self):
        """
        Main entry point for the bot
        """
        try:
            # Kill any existing instances
            logger.info("Checking for existing bot instances...")
            self.kill_existing_instances()

            # Try to acquire lock
            if not self.acquire_lock():
                sys.exit(1)

            # Run the bot
            asyncio.run(self.run_bot())

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)
        finally:
            self.release_lock()


def main():
    """Main function"""
    # Replace with your bot token
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Please set your bot token!")
        sys.exit(1)

    # Create and run bot manager
    bot_manager = TelegramBotManager(
        token=BOT_TOKEN,
        lock_file_path="/tmp/my_telegram_bot.lock"
    )

    bot_manager.run()


if __name__ == "__main__":
    main()
