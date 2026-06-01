"""Facebook Graph API integration.

Handles video upload (resumable upload API) and commenting on posts.
"""

import os
import asyncio
import aiohttp

from src.config import FacebookPageConfig
from src.utils.logger import setup_logger

logger = setup_logger("facebook")

GRAPH_API_BASE = "https://graph.facebook.com"
GRAPH_VIDEO_BASE = "https://graph-video.facebook.com"


class FacebookService:
    """Service for interacting with Facebook Graph API."""

    def __init__(self, api_version: str = "v21.0", app_id: str = ""):
        self.api_version = api_version
        self.app_id = app_id

    async def upload_video(
        self,
        page_config: FacebookPageConfig,
        video_path: str,
        description: str = "",
    ) -> dict:
        """Upload a video to a Facebook Page.

        Uses the Resumable Upload API for reliability.

        Args:
            page_config: Facebook page configuration.
            video_path: Local path to the video file.
            description: Post description/caption.

        Returns:
            Dict with post_id and/or video_id.

        Raises:
            Exception: If upload fails.
        """
        file_size = os.path.getsize(video_path)
        file_name = os.path.basename(video_path)

        logger.info(
            "Uploading video to page '%s' (%s): %s (%.2f MB)",
            page_config.name,
            page_config.page_id,
            file_name,
            file_size / (1024 * 1024),
        )

        async with aiohttp.ClientSession() as session:
            # ---- Phase 1: Initialize upload session ----
            init_url = (
                f"{GRAPH_API_BASE}/{self.api_version}/{self.app_id}/uploads"
            )
            init_params = {
                "file_name": file_name,
                "file_length": str(file_size),
                "file_type": "video/mp4",
                "access_token": page_config.access_token,
            }

            logger.debug("Initializing upload session...")
            async with session.post(init_url, params=init_params) as resp:
                init_data = await resp.json()
                if "error" in init_data:
                    error_msg = init_data["error"].get("message", "Unknown error")
                    raise Exception(
                        f"Failed to initialize upload session: {error_msg}"
                    )
                upload_session_id = init_data.get("id")
                if not upload_session_id:
                    raise Exception(
                        f"No upload session ID returned: {init_data}"
                    )

            logger.debug("Upload session ID: %s", upload_session_id)

            # ---- Phase 2: Upload video data ----
            upload_url = (
                f"{GRAPH_API_BASE}/{self.api_version}/{upload_session_id}"
            )
            headers = {
                "Authorization": f"OAuth {page_config.access_token}",
                "file_offset": "0",
            }

            logger.debug("Uploading video data...")
            with open(video_path, "rb") as f:
                video_data = f.read()

            async with session.post(
                upload_url, headers=headers, data=video_data
            ) as resp:
                upload_data = await resp.json()
                if "error" in upload_data:
                    error_msg = upload_data["error"].get("message", "Unknown error")
                    raise Exception(f"Failed to upload video data: {error_msg}")

            file_handle = upload_data.get("h") or upload_session_id
            logger.debug("Upload complete, file handle: %s", file_handle)

            # ---- Phase 3: Publish video to page ----
            publish_url = (
                f"{GRAPH_VIDEO_BASE}/{self.api_version}"
                f"/{page_config.page_id}/videos"
            )
            publish_data = {
                "access_token": page_config.access_token,
                "description": description,
                "fbuploader_video_file_chunk": file_handle,
            }

            logger.debug("Publishing video to page...")
            async with session.post(publish_url, data=publish_data) as resp:
                publish_result = await resp.json()
                if "error" in publish_result:
                    error_msg = publish_result["error"].get(
                        "message", "Unknown error"
                    )
                    raise Exception(f"Failed to publish video: {error_msg}")

        video_id = publish_result.get("id")
        post_id = publish_result.get("post_id")

        logger.info(
            "Video published! video_id=%s, post_id=%s",
            video_id,
            post_id,
        )

        return {
            "video_id": video_id,
            "post_id": post_id,
            "page_id": page_config.page_id,
            "page_name": page_config.name,
        }

    async def upload_video_direct(
        self,
        page_config: FacebookPageConfig,
        video_path: str,
        description: str = "",
    ) -> dict:
        """Upload a video directly using multipart form data.

        Fallback method if resumable upload fails (e.g., no APP_ID).

        Args:
            page_config: Facebook page configuration.
            video_path: Local path to the video file.
            description: Post description/caption.

        Returns:
            Dict with post_id and/or video_id.
        """
        logger.info(
            "Direct upload to page '%s': %s",
            page_config.name,
            os.path.basename(video_path),
        )

        publish_url = (
            f"{GRAPH_VIDEO_BASE}/{self.api_version}"
            f"/{page_config.page_id}/videos"
        )

        form = aiohttp.FormData()
        form.add_field("access_token", page_config.access_token)
        form.add_field("description", description)
        form.add_field(
            "source",
            open(video_path, "rb"),
            filename=os.path.basename(video_path),
            content_type="video/mp4",
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                publish_url,
                data=form,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                result = await resp.json()
                if "error" in result:
                    error_msg = result["error"].get("message", "Unknown error")
                    raise Exception(f"Failed to upload video: {error_msg}")

        video_id = result.get("id")
        post_id = result.get("post_id")

        logger.info(
            "Video uploaded! video_id=%s, post_id=%s",
            video_id,
            post_id,
        )

        return {
            "video_id": video_id,
            "post_id": post_id,
            "page_id": page_config.page_id,
            "page_name": page_config.name,
        }

    async def post_video(
        self,
        page_config: FacebookPageConfig,
        video_path: str,
        description: str = "",
    ) -> dict:
        """Upload a video to a Facebook Page, trying resumable first then direct.

        Args:
            page_config: Facebook page configuration.
            video_path: Local path to the video file.
            description: Post description/caption.

        Returns:
            Dict with post_id and/or video_id.
        """
        # Try resumable upload first if app_id is configured
        if self.app_id:
            try:
                return await self.upload_video(
                    page_config, video_path, description
                )
            except Exception as e:
                logger.warning(
                    "Resumable upload failed, falling back to direct: %s",
                    str(e),
                )

        # Fallback to direct upload
        return await self.upload_video_direct(
            page_config, video_path, description
        )

    async def comment_on_post(
        self,
        page_config: FacebookPageConfig,
        post_identifier: str,
        message: str,
    ) -> dict:
        """Comment on a Facebook post.

        Args:
            page_config: Facebook page configuration.
            post_identifier: The post_id or video_id to comment on.
            message: Comment text content.

        Returns:
            Dict with comment_id.

        Raises:
            Exception: If commenting fails.
        """
        logger.info(
            "Commenting on post %s (page: %s)",
            post_identifier,
            page_config.name,
        )

        url = (
            f"{GRAPH_API_BASE}/{self.api_version}"
            f"/{post_identifier}/comments"
        )
        params = {
            "message": message,
            "access_token": page_config.access_token,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as resp:
                result = await resp.json()
                if "error" in result:
                    error_msg = result["error"].get("message", "Unknown error")
                    raise Exception(f"Failed to comment: {error_msg}")

        comment_id = result.get("id")
        logger.info("Comment posted! comment_id=%s", comment_id)

        return {"comment_id": comment_id}

    async def post_and_comment(
        self,
        page_config: FacebookPageConfig,
        video_path: str,
        description: str,
        comment_message: str,
        comment_delay: int = 10,
    ) -> dict:
        """Upload video to a page, then comment on it after a delay.

        Args:
            page_config: Facebook page configuration.
            video_path: Local path to the video file.
            description: Post description/caption.
            comment_message: Message to comment (affiliate link).
            comment_delay: Seconds to wait before commenting.

        Returns:
            Dict with post result and comment result.
        """
        # Step 1: Post the video
        post_result = await self.post_video(
            page_config, video_path, description
        )

        # Step 2: Wait before commenting
        logger.info("Waiting %d seconds before commenting...", comment_delay)
        await asyncio.sleep(comment_delay)

        # Step 3: Comment on the post
        # Use post_id if available, otherwise try video_id
        post_identifier = post_result.get("post_id") or post_result.get(
            "video_id"
        )
        if not post_identifier:
            raise Exception(
                "No post_id or video_id returned from video upload"
            )

        try:
            comment_result = await self.comment_on_post(
                page_config, post_identifier, comment_message
            )
        except Exception as e:
            # If commenting on post_id failed and we have video_id, try that
            video_id = post_result.get("video_id")
            if video_id and post_identifier != video_id:
                logger.warning(
                    "Comment on post_id failed, trying video_id: %s", str(e)
                )
                comment_result = await self.comment_on_post(
                    page_config, video_id, comment_message
                )
            else:
                raise

        return {
            **post_result,
            **comment_result,
            "post_url": self._build_post_url(
                page_config.page_id,
                post_result.get("post_id") or post_result.get("video_id", ""),
            ),
        }

    @staticmethod
    def _build_post_url(page_id: str, post_id: str) -> str:
        """Build a Facebook post URL from page_id and post_id."""
        # Post ID format is usually "page_id_post_id" or just the post_id
        if "_" in post_id:
            return f"https://www.facebook.com/{post_id}"
        return f"https://www.facebook.com/{page_id}/posts/{post_id}"
