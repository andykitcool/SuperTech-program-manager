"""HTTP client for wotu-getphoto-by-deepseek service (API sync mode)."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class WotuServiceClient:
    """HTTP client that calls the wotu-getphoto-by-deepseek service API."""

    def __init__(self, base_url: str = "", api_key: str = ""):
        settings = get_settings()
        self.base_url = (base_url or settings.WOTU_SERVICE_URL).rstrip("/")
        self.api_key = api_key or settings.WOTU_API_KEY
        self._http = httpx.AsyncClient(timeout=30)

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key} if self.api_key else {}

    async def start_sync(
        self,
        task_id: int,
        activity_id: int,
        url: str,
        config: dict,
        callback_urls: dict,
        api_key: str = "",
    ) -> dict:
        """Start a sync task on the remote wotu service.

        Args:
            task_id: supertech's sync_task ID
            activity_id: activity ID
            url: wotu album URL
            config: sync config dict (concurrency, scroll_delay, etc.)
            callback_urls: dict with keys "photo_uploaded", "task_complete", "task_progress"
            api_key: API key for callback auth

        Returns:
            Response dict from remote service.
        """
        payload = {
            "task_id": task_id,
            "activity_id": activity_id,
            "url": url,
            "callback_url": callback_urls.get("photo_uploaded", ""),
            "callback_complete_url": callback_urls.get("task_complete", ""),
            "callback_progress_url": callback_urls.get("task_progress", ""),
            "api_key": api_key or self.api_key,
            "config": {
                "concurrency": config.get("concurrency", 5),
                "scroll_delay": config.get("scroll_delay", 5),
                "no_new_stop_rounds": config.get("no_new_stop_rounds", 3),
                "tab_mode": config.get("tab_mode", "current"),
                "selected_categories": config.get("selected_categories", []),
                "storage_path_prefix": config.get("storage_path_prefix", ""),
            },
        }
        logger.info("WotuServiceClient.start_sync: task_id=%s url=%s", task_id, url)
        resp = await self._http.post(
            f"{self.base_url}/api/v1/sync/start",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def stop_sync(self, task_id: int) -> dict:
        """Request the remote wotu service to stop a sync task."""
        logger.info("WotuServiceClient.stop_sync: task_id=%s", task_id)
        resp = await self._http.post(
            f"{self.base_url}/api/v1/sync/stop",
            json={"task_id": task_id},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_status(self, task_id: int) -> dict:
        """Query sync status from the remote wotu service."""
        resp = await self._http.get(
            f"{self.base_url}/api/v1/sync/status",
            params={"task_id": task_id},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._http.aclose()


# Module-level singleton
_wotu_client: Optional[WotuServiceClient] = None


def get_wotu_client() -> WotuServiceClient:
    global _wotu_client
    if _wotu_client is None:
        _wotu_client = WotuServiceClient()
    return _wotu_client


async def close_wotu_client():
    global _wotu_client
    if _wotu_client:
        await _wotu_client.close()
        _wotu_client = None
