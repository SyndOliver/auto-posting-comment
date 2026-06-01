"""Main entry point for the Auto Post & Comment Bot.

Initializes the Telegram bot, sets up handlers, and starts polling.
"""

import asyncio
import sys

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.config import config
from src.bot.handlers import (
    start_command,
    help_command,
    list_sku_command,
    reload_sku_command,
    status_command,
    history_command,
    handle_message,
)
from src.models.database import init_db
from src.utils.logger import setup_logger

logger = setup_logger("main")


async def post_init(application) -> None:
    """Post-initialization hook - runs after bot starts."""
    await init_db()
    logger.info("Database initialized.")


def main() -> None:
    """Start the bot."""
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration errors:")
        for err in errors:
            logger.error("  - %s", err)
        logger.error(
            "Please check your .env file. See .env.example for reference."
        )
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("🤖 Auto Post & Comment Bot starting...")
    logger.info("=" * 50)
    logger.info("Telegram admin IDs: %s", config.telegram_admin_ids)
    logger.info("Facebook Pages: %d configured", len(config.fb_pages))
    for page in config.fb_pages:
        logger.info("  - %s (ID: %s)", page.name, page.page_id)
    logger.info("Comment delay: %d seconds", config.comment_delay_seconds)
    logger.info("SKU mapping file: %s", config.sku_mapping_file)
    logger.info("=" * 50)

    # Build the Telegram bot application
    app = (
        ApplicationBuilder()
        .token(config.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list_sku", list_sku_command))
    app.add_handler(CommandHandler("reload_sku", reload_sku_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("history", history_command))

    # Register message handler for TikTok links
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    # Start the bot
    logger.info("Bot is running! Press Ctrl+C to stop.")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    main()
