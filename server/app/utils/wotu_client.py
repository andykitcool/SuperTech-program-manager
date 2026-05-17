"""Compatibility client for fetching Wotu photos through pure HTTP APIs."""

from __future__ import annotations

from typing import List

from app.services.wotu_scraper import WotuScraper


class WotuClient:
    async def fetch_photos(self, album_url: str) -> List[dict]:
        scraper = WotuScraper()
        try:
            await scraper.open_album(album_url)
            tabs = await scraper.detect_tabs()
            tabs_to_process = tabs if tabs else [dict(scraper._current_tab or {})]
            photos: list[dict] = []
            for tab in tabs_to_process:
                await scraper.switch_tab(tab)
                await scraper.fetch_until_empty(no_new_pages=1)
                photos.extend(photo.to_dict() for photo in scraper.get_new_photos())
            return photos
        finally:
            await scraper.close()
