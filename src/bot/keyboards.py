"""Telegram bot inline keyboards."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_post_keyboard() -> InlineKeyboardMarkup:
    """Create a confirmation keyboard for posting."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Đăng ngay", callback_data="confirm_post"),
                InlineKeyboardButton("❌ Hủy", callback_data="cancel_post"),
            ]
        ]
    )


def page_selection_keyboard(pages: list[dict]) -> InlineKeyboardMarkup:
    """Create a page selection keyboard.

    Args:
        pages: List of dicts with 'name' and 'page_id' keys.
    """
    buttons = []
    for page in pages:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"📄 {page['name']}",
                    callback_data=f"select_page_{page['page_id']}",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                "📄 Tất cả Pages", callback_data="select_page_all"
            )
        ]
    )
    return InlineKeyboardMarkup(buttons)
