#!/usr/bin/env python3
"""
Simple Telegram Bot Example - Modern python-telegram-bot (v21+)
Shows proper setup and graceful shutdown
"""

import asyncio
import logging
import signal
import sys
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.application = None
        self.shutdown_flag = False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text("Hello! Bot is running.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/status - Show bot status
        """
        await update.message.reply_text(help_text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        await update.message.reply_text(f"Bot is running! PID: {os.getpid()}")

    async def echo_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Echo text messages"""
        await update.message.reply_text(f"You said: {update.message.text}")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")

    def setup_handlers(self):
        """Setup command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))

        # Message handler for text messages (non-commands)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo_handler)
        )

        # Error handler
        self.application.add_error_handler(self.error_handler)

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}. Shutting down...")
            self.shutdown_flag = True
            if self.application and self.application.running:
                self.application.stop_running()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        """Run the bot"""
        try:
            # Setup signal handlers
            self.setup_signal_handlers()

            # Build application
            self.application = ApplicationBuilder().token(self.token).build()

            # Setup handlers
            self.setup_handlers()

            logger.info("Starting bot...")

            # Method 1: Simple run_polling (recommended for most cases)
            # This handles initialization, start, and cleanup automatically
            await self.application.run_polling(
                drop_pending_updates=True,
                stop_signals=None  # We handle signals manually
            )

        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise

    async def run_manual(self):
        """
        Alternative: Manual control for more complex scenarios
        Use this when you need more control over the lifecycle
        """
        try:
            # Setup signal handlers
            self.setup_signal_handlers()

            # Build application
            self.application = ApplicationBuilder().token(self.token).build()

            # Setup handlers
            self.setup_handlers()

            logger.info("Starting bot (manual mode)...")

            # Manual initialization and start
            async with self.application:
                await self.application.start()
                await self.application.updater.start_polling(drop_pending_updates=True)

                logger.info("Bot is running. Press Ctrl+C to stop.")

                # Keep running until shutdown
                while not self.shutdown_flag:
                    await asyncio.sleep(1)

                logger.info("Stopping bot...")
                await self.application.updater.stop()
                await self.application.stop()

            logger.info("Bot stopped successfully")

        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise


async def main():
    """Main function"""
    # Replace with your bot token
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Please set your bot token!")
        sys.exit(1)

    bot = SimpleTelegramBot(BOT_TOKEN)

    # Choose one of these methods:

    # Method 1: Simple (recommended)
    await bot.run()

    # Method 2: Manual control (for advanced use cases)
    # await bot.run_manual()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
