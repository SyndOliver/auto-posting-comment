"""Configuration module - loads settings from environment variables."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class FacebookPageConfig:
    """Configuration for a single Facebook Page."""

    page_id: str
    access_token: str
    name: str


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # Telegram
    telegram_bot_token: str = ""
    telegram_admin_ids: list[int] = field(default_factory=list)

    # Facebook Pages
    fb_pages: list[FacebookPageConfig] = field(default_factory=list)
    fb_app_id: str = ""
    fb_api_version: str = "v21.0"

    # Settings
    comment_delay_seconds: int = 10
    video_download_dir: str = "./downloads"
    sku_mapping_file: str = "./data/sku_mapping.csv"

    @classmethod
    def from_env(cls) -> "Config":
        """Create Config from environment variables."""
        config = cls()

        # Telegram
        config.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        admin_ids_str = os.getenv("TELEGRAM_ADMIN_IDS", "")
        config.telegram_admin_ids = [
            int(uid.strip())
            for uid in admin_ids_str.split(",")
            if uid.strip().isdigit()
        ]

        # Facebook Pages
        pages = []
        for i in range(1, 10):  # Support up to 9 pages
            page_id = os.getenv(f"FB_PAGE{i}_ID", "")
            page_token = os.getenv(f"FB_PAGE{i}_TOKEN", "")
            page_name = os.getenv(f"FB_PAGE{i}_NAME", f"Page {i}")
            if page_id and page_token:
                pages.append(
                    FacebookPageConfig(
                        page_id=page_id,
                        access_token=page_token,
                        name=page_name,
                    )
                )
        config.fb_pages = pages
        config.fb_app_id = os.getenv("FB_APP_ID", "")
        config.fb_api_version = os.getenv("FB_API_VERSION", "v21.0")

        # Settings
        config.comment_delay_seconds = int(
            os.getenv("COMMENT_DELAY_SECONDS", "10")
        )
        config.video_download_dir = os.getenv("VIDEO_DOWNLOAD_DIR", "./downloads")
        config.sku_mapping_file = os.getenv(
            "SKU_MAPPING_FILE", "./data/sku_mapping.csv"
        )

        return config

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of error messages."""
        errors = []
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not self.telegram_admin_ids:
            errors.append("TELEGRAM_ADMIN_IDS is required (at least one admin)")
        if not self.fb_pages:
            errors.append("At least one Facebook Page must be configured (FB_PAGE1_ID, FB_PAGE1_TOKEN)")
        if not self.fb_app_id:
            errors.append("FB_APP_ID is required for video uploads")
        return errors


# Global config instance
config = Config.from_env()
