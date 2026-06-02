"""Telegram bot command and message handlers.

Handles all user interactions including:
- /start, /help - Bot info and usage
- /list_sku - Show all available SKUs
- /reload_sku - Reload SKU mapping file
- /status - Bot status and stats
- /history - Recent post history
- Message handler - Process TikTok links + SKU for posting
"""

import html
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.config import config
from src.services.tiktok import is_tiktok_url, download_video, cleanup_video
from src.services.facebook import FacebookService
from src.services.sku_manager import SKUManager
from src.models.database import log_post, get_recent_history, get_stats
from src.utils.logger import setup_logger

logger = setup_logger("handlers")

# Initialize services
sku_manager = SKUManager(config.sku_mapping_file)
fb_service = FacebookService(
    api_version=config.fb_api_version,
    app_id=config.fb_app_id,
)


def is_admin(user_id: int) -> bool:
    """Check if a user is an authorized admin."""
    return user_id in config.telegram_admin_ids


def _e(text: str) -> str:
    """Escape text for HTML parse mode (safe for all user content)."""
    return html.escape(str(text))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bạn không có quyền sử dụng bot này.")
        return

    welcome = (
        "🤖 <b>Auto Post &amp; Comment Bot</b>\n\n"
        "Bot giúp bạn đăng video TikTok lên Facebook Page "
        "và tự động comment link affiliate Shopee.\n\n"
        "📝 <b>Cách sử dụng:</b>\n"
        "Gửi tin nhắn với format:\n"
        "<pre>\n"
        "https://tiktok.com/@user/video/123\n"
        "SKU001\n"
        "Caption bài đăng (tùy chọn)\n"
        "</pre>\n\n"
        "📋 <b>Commands:</b>\n"
        "/help - Hướng dẫn chi tiết\n"
        "/list_sku - Xem danh sách SKU\n"
        "/reload_sku - Reload file SKU\n"
        "/status - Trạng thái bot\n"
        "/history - Lịch sử đăng bài"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not is_admin(update.effective_user.id):
        return

    help_text = (
        "📖 <b>Hướng dẫn sử dụng</b>\n\n"
        "<b>Bước 1:</b> Gửi tin nhắn cho bot với format:\n\n"
        "<pre>\n"
        "Link TikTok\n"
        "SKU sản phẩm\n"
        "Caption (tùy chọn, có thể bỏ trống)\n"
        "</pre>\n\n"
        "<b>Ví dụ:</b>\n"
        "<pre>\n"
        "https://www.tiktok.com/@shop/video/123456\n"
        "SKU001\n"
        "Sản phẩm hot nhất hôm nay!\n"
        "</pre>\n\n"
        "<b>Bước 2:</b> Bot sẽ tự động:\n"
        "1. Download video TikTok (không watermark)\n"
        "2. Đăng video lên tất cả Facebook Pages\n"
        "3. Comment link affiliate Shopee vào bài\n"
        "4. Gửi kết quả về cho bạn\n\n"
        f"⏱ Delay comment: {config.comment_delay_seconds}s\n"
        f"📄 Số Pages: {len(config.fb_pages)}"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def list_sku_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /list_sku command - show all available SKUs."""
    if not is_admin(update.effective_user.id):
        return

    products = sku_manager.get_all_skus()
    if not products:
        await update.message.reply_text("📭 Chưa có SKU nào trong hệ thống.")
        return

    lines = ["📦 <b>Danh sách SKU:</b>\n"]
    for p in products:
        lines.append(f"• <code>{_e(p.sku)}</code> - {_e(p.product_name)}")

    lines.append(f"\n📊 Tổng: {len(products)} SKU")
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.HTML
    )


async def reload_sku_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /reload_sku command - reload SKU mapping file."""
    if not is_admin(update.effective_user.id):
        return

    try:
        count = sku_manager.load()
        await update.message.reply_text(
            f"✅ Đã reload thành công! Tổng: {count} SKU"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi reload SKU: {_e(str(e))}")


async def status_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /status command - show bot status and stats."""
    if not is_admin(update.effective_user.id):
        return

    stats = await get_stats()

    pages_info = "\n".join(
        f"  • {_e(p.name)} (<code>{_e(p.page_id)}</code>)"
        for p in config.fb_pages
    )

    status_text = (
        "📊 <b>Trạng thái Bot</b>\n\n"
        f"🤖 Bot: Online\n"
        f"📦 SKU loaded: {sku_manager.count}\n"
        f"📄 Facebook Pages:\n{pages_info}\n\n"
        f"📈 <b>Thống kê:</b>\n"
        f"  • Tổng bài đăng: {stats['total']}\n"
        f"  • Thành công: {stats['success']}\n"
        f"  • Thất bại: {stats['failed']}\n"
        f"  • Hôm nay: {stats['today']}"
    )
    await update.message.reply_text(status_text, parse_mode=ParseMode.HTML)


async def history_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /history command - show recent post history."""
    if not is_admin(update.effective_user.id):
        return

    records = await get_recent_history(limit=10)
    if not records:
        await update.message.reply_text("📭 Chưa có lịch sử đăng bài.")
        return

    lines = ["📜 <b>10 bài đăng gần nhất:</b>\n"]
    for r in records:
        status_icon = "✅" if r["status"] == "success" else "❌"
        time_str = r["created_at"][:16] if r["created_at"] else "N/A"
        page = _e(r.get("page_name", "N/A"))
        sku = _e(r.get("sku", "N/A"))
        lines.append(
            f"{status_icon} <code>{sku}</code> | {page} | {_e(time_str)}"
        )

    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.HTML
    )


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle incoming messages - process TikTok links with SKU.

    Expected message format:
        Line 1: TikTok URL
        Line 2: SKU
        Line 3+ (optional): Caption/description
    """
    if not is_admin(update.effective_user.id):
        return

    text = update.message.text
    if not text:
        return

    # Parse message lines
    lines = text.strip().split("\n")
    if len(lines) < 2:
        # Not a valid post command - could be a casual message, ignore silently
        # unless it looks like a TikTok URL
        if lines and is_tiktok_url(lines[0].strip()):
            await update.message.reply_text(
                "⚠️ Thiếu SKU! Format đúng:\n\n"
                "<pre>\n"
                "Link TikTok\n"
                "SKU\n"
                "Caption (tùy chọn)\n"
                "</pre>",
                parse_mode=ParseMode.HTML,
            )
        return

    tiktok_url = lines[0].strip()
    sku = lines[1].strip()
    caption = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""

    # Validate TikTok URL
    if not is_tiktok_url(tiktok_url):
        await update.message.reply_text(
            "❌ Link TikTok không hợp lệ. Vui lòng gửi link đúng format."
        )
        return

    # Look up SKU
    product = sku_manager.lookup(sku)
    if not product:
        await update.message.reply_text(
            f"❌ Không tìm thấy SKU: <code>{_e(sku)}</code>\n"
            f"Dùng /list_sku để xem danh sách SKU.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Send processing status
    status_msg = await update.message.reply_text(
        f"⏳ Đang xử lý...\n\n"
        f"🎬 Video: {_e(tiktok_url[:50])}...\n"
        f"📦 SKU: {_e(sku)} - {_e(product.product_name)}\n"
        f"📄 Pages: {len(config.fb_pages)}",
        parse_mode=ParseMode.HTML,
    )

    video_path = None

    try:
        # Step 1: Download TikTok video
        await status_msg.edit_text(
            "⏳ [1/3] Đang download video TikTok..."
        )
        video_path, video_info = await download_video(
            tiktok_url, config.video_download_dir
        )

        tiktok_title = video_info.get("title", "")
        if not caption:
            caption = tiktok_title if tiktok_title else ""

        # Step 2: Post to all pages
        await status_msg.edit_text(
            f"⏳ [2/3] Đang đăng video lên {len(config.fb_pages)} page(s)..."
        )

        comment_message = sku_manager.format_comment(product)

        # Post to all pages concurrently
        tasks = []
        for page_config in config.fb_pages:
            task = fb_service.post_and_comment(
                page_config=page_config,
                video_path=video_path,
                description=caption,
                comment_message=comment_message,
                comment_delay=config.comment_delay_seconds,
            )
            tasks.append(task)

        page_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 3: Process results
        await status_msg.edit_text(
            "⏳ [3/3] Đang ghi log và tổng hợp kết quả..."
        )

        success_lines = []
        error_lines = []

        for i, result in enumerate(page_results):
            page = config.fb_pages[i]

            if isinstance(result, Exception):
                error_msg = str(result)
                error_lines.append(
                    f"❌ {_e(page.name)}: {_e(error_msg[:100])}"
                )
                await log_post(
                    tiktok_url=tiktok_url,
                    sku=sku,
                    product_name=product.product_name,
                    caption=caption,
                    page_name=page.name,
                    page_id=page.page_id,
                    affiliate_link=product.affiliate_link,
                    status="failed",
                    error_msg=error_msg,
                )
            else:
                post_url = result.get("post_url", "N/A")
                success_lines.append(
                    f"✅ {_e(page.name)}\n"
                    f"   📎 {_e(post_url)}\n"
                    f"   💬 Comment: OK"
                )
                await log_post(
                    tiktok_url=tiktok_url,
                    sku=sku,
                    product_name=product.product_name,
                    caption=caption,
                    page_name=page.name,
                    page_id=page.page_id,
                    post_id=result.get("post_id", ""),
                    video_id=result.get("video_id", ""),
                    comment_id=result.get("comment_id", ""),
                    affiliate_link=product.affiliate_link,
                    post_url=post_url,
                    status="success",
                )

        # Build final report (plain text, no parse issues)
        report_parts = ["🎉 Kết quả đăng bài:\n"]

        if success_lines:
            report_parts.append("\n".join(success_lines))

        if error_lines:
            report_parts.append("\n" + "\n".join(error_lines))

        report_parts.append(
            f"\n📦 SKU: {sku} - {product.product_name}"
        )

        await status_msg.edit_text("\n".join(report_parts))

    except Exception as e:
        error_msg = str(e)
        logger.error("Error processing post: %s", error_msg, exc_info=True)
        try:
            await status_msg.edit_text(
                f"❌ Lỗi: {error_msg[:200]}\n\n"
                f"Vui lòng thử lại hoặc kiểm tra logs."
            )
        except Exception:
            # If even the error message fails, try a minimal message
            await status_msg.edit_text("❌ Có lỗi xảy ra. Kiểm tra logs.")
        # Log error for all pages
        for page in config.fb_pages:
            await log_post(
                tiktok_url=tiktok_url,
                sku=sku,
                product_name=product.product_name if product else "",
                caption=caption,
                page_name=page.name,
                page_id=page.page_id,
                affiliate_link=product.affiliate_link if product else "",
                status="failed",
                error_msg=error_msg,
            )

    finally:
        # Cleanup downloaded video
        if video_path:
            cleanup_video(video_path)
