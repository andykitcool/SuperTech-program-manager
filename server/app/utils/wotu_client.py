import asyncio
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WotuClient:
    """Client for fetching photos from Wotu (alltuu.com) via Playwright."""

    async def fetch_photos(self, album_url: str) -> List[dict]:
        """
        Fetch all photos from a Wotu album page.
        Returns list of photo info dicts with keys:
        - photo_id: unique identifier
        - url: original image URL
        - filename: filename
        - shoot_time: datetime of photo capture
        - width, height: image dimensions
        - file_size: file size in bytes
        - thumbnail_url: thumbnail URL
        """
        try:
            from playwright.async_api import async_playwright

            photos = []

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                    viewport={"width": 390, "height": 844},
                )
                page = await context.new_page()

                # Collect API responses
                async def handle_response(response):
                    if "v4c.alltuu.com" in response.url:
                        try:
                            data = await response.json()
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        photo = self._parse_photo_item(item)
                                        if photo:
                                            photos.append(photo)
                            elif isinstance(data, dict):
                                items = data.get("data", data.get("photos", data.get("list", [])))
                                if isinstance(items, list):
                                    for item in items:
                                        if isinstance(item, dict):
                                            photo = self._parse_photo_item(item)
                                            if photo:
                                                photos.append(photo)
                        except Exception:
                            pass

                page.on("response", handle_response)

                logger.info(f"Navigating to Wotu album: {album_url}")
                await page.goto(album_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # Scroll to load more photos
                for _ in range(20):
                    await page.evaluate("window.scrollBy(0, 2000)")
                    await asyncio.sleep(1.5)

                # Also check for tab switching (categories)
                tabs = await page.query_selector_all(".tab-item, .category-tab, [class*='tab']")
                if len(tabs) > 1:
                    for i, tab in enumerate(tabs[1:], 1):
                        try:
                            await tab.click()
                            await asyncio.sleep(2)
                            for _ in range(10):
                                await page.evaluate("window.scrollBy(0, 2000)")
                                await asyncio.sleep(1)
                        except Exception:
                            pass

                await browser.close()

            # Deduplicate by photo_id
            seen = set()
            unique_photos = []
            for photo in photos:
                pid = photo.get("photo_id")
                if pid and pid not in seen:
                    seen.add(pid)
                    unique_photos.append(photo)

            logger.info(f"Fetched {len(unique_photos)} photos from Wotu album")
            return unique_photos

        except ImportError:
            logger.warning("Playwright not installed, returning empty photos list")
            return []
        except Exception as e:
            logger.error(f"Error fetching photos from Wotu: {e}")
            return []

    def _parse_photo_item(self, item: dict) -> Optional[dict]:
        """Parse a single photo item from Wotu API response."""
        # Wotu API responses may vary; try common field patterns
        photo_id = (
            item.get("id")
            or item.get("photo_id")
            or item.get("pid")
            or str(item.get("image_id", ""))
        )
        url = (
            item.get("url")
            or item.get("origin_url")
            or item.get("download_url")
            or item.get("src")
            or item.get("image_url")
        )

        if not url:
            return None

        thumbnail = (
            item.get("thumb_url")
            or item.get("thumbnail")
            or item.get("thumb")
            or item.get("preview_url")
        )

        shoot_time = None
        time_str = item.get("shoot_time") or item.get("create_time") or item.get("date") or item.get("taken_at")
        if time_str:
            try:
                if isinstance(time_str, (int, float)):
                    shoot_time = datetime.fromtimestamp(time_str)
                elif isinstance(time_str, str):
                    for fmt in [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d",
                        "%Y%m%d%H%M%S",
                    ]:
                        try:
                            shoot_time = datetime.strptime(time_str[:19], fmt)
                            break
                        except ValueError:
                            continue
            except (ValueError, OSError):
                pass

        return {
            "photo_id": str(photo_id),
            "url": url,
            "thumbnail_url": thumbnail,
            "filename": url.split("/")[-1].split("?")[0] if url else "photo.jpg",
            "shoot_time": shoot_time,
            "width": item.get("width") or item.get("w"),
            "height": item.get("height") or item.get("h"),
            "file_size": item.get("file_size") or item.get("size"),
        }
