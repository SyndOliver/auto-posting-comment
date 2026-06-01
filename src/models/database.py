"""SQLite database for logging post history.

Tracks all posts and comments made through the bot for auditing
and the /history command.
"""

import os
import aiosqlite
from datetime import datetime

from src.utils.logger import setup_logger

logger = setup_logger("database")

DB_PATH = os.getenv("DB_PATH", "./data/bot_history.db")


async def init_db() -> None:
    """Initialize the database and create tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS post_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tiktok_url TEXT NOT NULL,
                sku TEXT NOT NULL,
                product_name TEXT DEFAULT '',
                caption TEXT DEFAULT '',
                page_name TEXT NOT NULL,
                page_id TEXT NOT NULL,
                post_id TEXT DEFAULT '',
                video_id TEXT DEFAULT '',
                comment_id TEXT DEFAULT '',
                affiliate_link TEXT DEFAULT '',
                post_url TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                error_msg TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        logger.info("Database initialized: %s", DB_PATH)


async def log_post(
    tiktok_url: str,
    sku: str,
    product_name: str,
    caption: str,
    page_name: str,
    page_id: str,
    post_id: str = "",
    video_id: str = "",
    comment_id: str = "",
    affiliate_link: str = "",
    post_url: str = "",
    status: str = "success",
    error_msg: str = "",
) -> int:
    """Log a post action to the database.

    Returns:
        The row ID of the inserted record.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO post_history (
                tiktok_url, sku, product_name, caption,
                page_name, page_id, post_id, video_id,
                comment_id, affiliate_link, post_url,
                status, error_msg, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tiktok_url,
                sku,
                product_name,
                caption,
                page_name,
                page_id,
                post_id,
                video_id,
                comment_id,
                affiliate_link,
                post_url,
                status,
                error_msg,
                datetime.now().isoformat(),
            ),
        )
        await db.commit()
        row_id = cursor.lastrowid
        logger.debug("Logged post action: id=%d, status=%s", row_id, status)
        return row_id


async def get_recent_history(limit: int = 10) -> list[dict]:
    """Get recent post history.

    Args:
        limit: Maximum number of records to return.

    Returns:
        List of post history records as dicts.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM post_history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_stats() -> dict:
    """Get posting statistics.

    Returns:
        Dict with total posts, successful posts, failed posts, and today's count.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Total counts
        cursor = await db.execute(
            "SELECT COUNT(*) FROM post_history"
        )
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM post_history WHERE status = 'success'"
        )
        success = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM post_history WHERE status = 'failed'"
        )
        failed = (await cursor.fetchone())[0]

        # Today's count
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT COUNT(*) FROM post_history WHERE created_at LIKE ?",
            (f"{today}%",),
        )
        today_count = (await cursor.fetchone())[0]

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "today": today_count,
        }
