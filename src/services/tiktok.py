"""TikTok video downloader using TikWM API.

Downloads TikTok videos without watermark via https://api.tikwm.com/api/
"""

import os
import re
import uuid
import asyncio
import aiohttp

from src.utils.logger import setup_logger

logger = setup_logger("tiktok")

TIKWM_API_URL = "https://api.tikwm.com/api/"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def is_tiktok_url(url: str) -> bool:
    """Check if a URL is a valid TikTok link."""
    patterns = [
        r"https?://(www\.)?tiktok\.com/@[\w.]+/video/\d+",
        r"https?://vm\.tiktok\.com/\w+",
        r"https?://vt\.tiktok\.com/\w+",
        r"https?://(www\.)?tiktok\.com/t/\w+",
    ]
    return any(re.match(pattern, url.strip()) for pattern in patterns)


async def get_video_info(tiktok_url: str) -> dict:
    """Fetch video metadata from TikWM API.

    Args:
        tiktok_url: The TikTok video URL.

    Returns:
        Dict with video info including download URL.

    Raises:
        Exception: If API request fails after retries.
    """
    params = {
        "url": tiktok_url,
        "count": 12,
        "cursor": 0,
        "web": 1,
        "hd": 1,
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Fetching video info (attempt %d/%d): %s",
                attempt,
                MAX_RETRIES,
                tiktok_url,
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    TIKWM_API_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    data = await response.json()

                    if data.get("code") != 0:
                        raise Exception(
                            f"TikWM API error: {data.get('msg', 'Unknown error')}"
                        )

                    video_data = data.get("data", {})
                    if not video_data:
                        raise Exception("TikWM API returned empty data")

                    logger.info(
                        "Got video info: id=%s, title=%s",
                        video_data.get("id"),
                        video_data.get("title", "")[:50],
                    )
                    return video_data

        except asyncio.CancelledError:
            raise
        except Exception as e:
            last_error = e
            logger.warning(
                "Attempt %d failed: %s", attempt, str(e)
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    raise Exception(
        f"Failed to get video info after {MAX_RETRIES} attempts: {last_error}"
    )


async def download_video(
    tiktok_url: str, download_dir: str
) -> tuple[str, dict]:
    """Download a TikTok video without watermark.

    Args:
        tiktok_url: The TikTok video URL.
        download_dir: Directory to save the downloaded video.

    Returns:
        Tuple of (file_path, video_info_dict).

    Raises:
        Exception: If download fails.
    """
    # Ensure download directory exists
    os.makedirs(download_dir, exist_ok=True)

    # Get video info from API
    video_info = await get_video_info(tiktok_url)

    # Prefer HD play URL, fallback to standard play URL
    video_url = video_info.get("hdplay") or video_info.get("play")
    if not video_url:
        raise Exception("No video download URL found in API response")

    # Ensure the video URL has a scheme
    if video_url.startswith("//"):
        video_url = "https:" + video_url

    # Generate unique filename
    video_id = video_info.get("id", uuid.uuid4().hex[:12])
    file_path = os.path.join(download_dir, f"tiktok_{video_id}.mp4")

    # Download the video file
    logger.info("Downloading video: %s", video_url[:100])
    async with aiohttp.ClientSession() as session:
        async with session.get(
            video_url,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as response:
            if response.status != 200:
                raise Exception(
                    f"Failed to download video: HTTP {response.status}"
                )

            with open(file_path, "wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)

    # Validate downloaded file
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        os.remove(file_path)
        raise Exception("Downloaded video file is empty")

    logger.info(
        "Video downloaded successfully: %s (%.2f MB)",
        file_path,
        file_size / (1024 * 1024),
    )

    return file_path, video_info


def cleanup_video(file_path: str) -> None:
    """Remove a downloaded video file.

    Args:
        file_path: Path to the video file to remove.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug("Cleaned up video file: %s", file_path)
    except OSError as e:
        logger.warning("Failed to clean up video file %s: %s", file_path, e)
