"""Pure HTTP Wotu/Alltuu album scraper.

Runtime photo sync uses the mobile site's signed API flow:

1. open album HTML
2. fetch authority secret
3. fetch album metadata/categories
4. page through signed v4c/fplN with the last photo `pc` cursor
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import aiohttp

from app.services.wotu_models import WotuPhotoInfo
from app.services.wotu_utils import extract_ext_from_url, sanitize_filename

logger = logging.getLogger(__name__)

ALLTUU_API_RE = re.compile(r"https?://[^\"'<>\\]+/rest/v4c/fpl/[^\"'<>\\]+", re.I)
ALBUM_URL_RE = re.compile(r"/album/([A-Za-z0-9_-]+)(?:/([A-Za-z0-9_-]+))?")
IMAGE_EXT_RE = re.compile(r"\.(?:jpg|jpeg|png|webp)(?:[?#]|$)", re.I)
ALLTUU_CDN_SIGN_KEY = "50f403a08b58841d319b92f0c10dbbd2"
ALLTUU_SIGN_FROM = "100002"
ALLTUU_SIGN_VERSION = "0"
ALLTUU_SIGN_TOKEN = "null"


class WotuApiError(RuntimeError):
    pass


@dataclass
class AlbumRef:
    album_id: str
    category_id: str = ""


class WotuScraper:
    """Fetch Wotu album photo data through HTTP APIs only."""

    def __init__(self, headless: bool = True, scroll_delay: int = 0, page_size: int = 60, request_timeout: int = 30):
        self.headless = headless
        self.scroll_delay = scroll_delay
        self.page_size = page_size
        self.request_timeout = aiohttp.ClientTimeout(total=request_timeout)
        self.album_url = ""
        self.album_ref = AlbumRef("")
        self._session: Optional[aiohttp.ClientSession] = None
        self._html = ""
        self._candidate_api_urls: list[str] = []
        self._secret = ""
        self._album_meta: dict[str, Any] = {}
        self._album_sort = "4"
        self._page_cursor = ""
        self._tabs: list[dict[str, Any]] = []
        self._current_tab: Optional[dict[str, Any]] = None
        self._all_photos: dict[str, WotuPhotoInfo] = {}
        self._photo_order: list[str] = []
        self._new_photos: list[WotuPhotoInfo] = []
        self._on_log: Optional[Callable[[str, str], None]] = None
        self._on_photo_found: Optional[Callable[[WotuPhotoInfo], None]] = None
        self._on_progress: Optional[Callable[[dict], None]] = None
        self._stopped = False
        self._batch_count = 0

    def set_callbacks(self, on_progress=None, on_log=None, on_photo_found=None):
        self._on_progress = on_progress
        self._on_log = on_log
        self._on_photo_found = on_photo_found

    def request_stop(self):
        self._stopped = True

    async def open_page(self, album_url: str):
        await self.open_album(album_url)
        await self.fetch_next_page()

    async def open_album(self, album_url: str):
        self.album_url = album_url.strip()
        self.album_ref = self.parse_album_url(self.album_url)
        self._session = aiohttp.ClientSession(headers=self._default_headers(), timeout=self.request_timeout)
        self._emit_log(f"打开喔图相册 API：{self.album_ref.album_id}")
        self._html = await self._fetch_text(self.album_url)
        self._candidate_api_urls = self._discover_api_urls(self._html)
        self._secret = await self._fetch_authority_secret()
        self._album_meta = await self._fetch_album_meta()
        self._album_sort = self._extract_album_sort(self._album_meta)
        self._tabs = self._extract_tabs_from_meta(self._album_meta)
        self._current_tab = self._default_tab()

    async def detect_tabs(self) -> list[dict]:
        if self._tabs:
            self._emit_log("检测到分类：" + "、".join(t["name"] for t in self._tabs))
            return self._tabs
        self._emit_log("未检测到分类信息，按当前分类处理", "warning")
        return []

    async def switch_tab(self, tab_info: dict) -> bool:
        self.reset_state()
        self._current_tab = dict(tab_info)
        self._emit_log(f"切换 API 分类：{tab_info.get('name') or tab_info.get('category_id') or '默认分类'}")
        return True

    async def fetch_next_page(self) -> bool:
        if self._stopped:
            return False
        if self.scroll_delay > 0:
            await asyncio.sleep(min(self.scroll_delay, 3))
        category_id = str((self._current_tab or {}).get("category_id") or "")
        page = self._batch_count + 1
        body = await self._request_photo_page(category_id, page)
        photo_list = self._find_photo_list_recursive(body)
        if not photo_list:
            return False
        self._page_cursor = self._next_cursor_from_photos(photo_list)
        added = self._add_photos(photo_list)
        self._batch_count += 1
        self._emit_progress({"type": "scraping_progress", "found": len(self._all_photos), "batch": self._batch_count})
        return added > 0

    async def fetch_until_empty(self, max_pages: int = 500, no_new_pages: int = 1) -> bool:
        empty_pages = 0
        for _ in range(max_pages):
            if self._stopped:
                return False
            has_new = await self.fetch_next_page()
            if has_new:
                empty_pages = 0
            else:
                empty_pages += 1
                if empty_pages >= no_new_pages:
                    return True
        return True

    async def scroll_and_wait(self, timeout: int = 15) -> bool:
        return await self.fetch_next_page()

    def get_new_photos(self) -> list[WotuPhotoInfo]:
        batch = self._new_photos[:]
        self._new_photos.clear()
        return batch

    @property
    def total_found(self) -> int:
        return len(self._all_photos)

    @property
    def tabs(self) -> list[dict]:
        return self._tabs

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    def reset_state(self):
        self._all_photos.clear()
        self._photo_order.clear()
        self._new_photos.clear()
        self._batch_count = 0
        self._page_cursor = ""

    @staticmethod
    def parse_album_url(album_url: str) -> AlbumRef:
        parsed = urlparse(album_url)
        match = ALBUM_URL_RE.search(parsed.path)
        if not match:
            raise ValueError("相册地址无效，应为 /album/{album_id}/...")
        category_id = match.group(2) or ""
        qs = parse_qs(parsed.query)
        for key in ("category_id", "categoryId", "classify_id", "classifyId", "cid"):
            if qs.get(key):
                category_id = qs[key][0]
                break
        return AlbumRef(album_id=match.group(1), category_id=category_id)

    def _default_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": self.album_url or "https://m.alltuu.com/",
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        }

    async def _fetch_text(self, url: str) -> str:
        if not self._session:
            raise WotuApiError("HTTP session is not open")
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def _request_photo_page(self, category_id: str, page: int) -> dict:
        if not self._session:
            raise WotuApiError("HTTP session is not open")
        errors: list[str] = []
        empty_signed_page = False
        for url, params in self._build_photo_requests(category_id, page):
            if self._stopped:
                return {}
            try:
                async with self._session.get(url, params=params) as resp:
                    if resp.status >= 400:
                        errors.append(f"{resp.status} {resp.url}")
                        continue
                    text = await resp.text()
                    try:
                        body = json.loads(text)
                    except json.JSONDecodeError:
                        errors.append(f"non-json {resp.url}")
                        continue
                    if self._find_photo_list_recursive(body):
                        self._emit_log(f"API 第 {page} 页加载完成")
                        return body
                    if "rest/v4c/fplN" in str(resp.url):
                        empty_signed_page = True
                    errors.append(f"empty {resp.url}")
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
        if page == 1 and empty_signed_page:
            self._emit_log(f"分类 {category_id or '默认'} 暂无照片", "warning")
            return {}
        if page == 1:
            raise WotuApiError("无法加载喔图照片 API：" + "; ".join(errors[:4]))
        return {}

    def _build_photo_requests(self, category_id: str, page: int) -> list[tuple[str, dict[str, Any]]]:
        requests: list[tuple[str, dict[str, Any]]] = []
        if self._secret and category_id and (page == 1 or self._page_cursor):
            params = {
                "a": self.album_ref.album_id,
                "s": category_id,
                "n": str(self.page_size),
                "pc": self._page_cursor,
                "o": self._current_sort(),
                "t": str(int(time.time() * 1000)),
                "pd": "",
                "v": "1",
                "sk": self._secret,
            }
            requests.append((self._sign_cdn_url("https://v4c.alltuu.com/rest/v4c/fplN", params), {}))
        for url in self._candidate_api_urls:
            requests.append((url, self._page_params(page)))
        return requests

    async def _fetch_authority_secret(self) -> str:
        if not self._session:
            raise WotuApiError("HTTP session is not open")
        params = {"albumId": self.album_ref.album_id}
        url = self._sign_server_url("https://m.alltuu.com/rest-prepub/fc/authority", params)
        async with self._session.get(url, params=params) as resp:
            resp.raise_for_status()
            body = await resp.json(content_type=None)
        data = body.get("data") or body.get("d") or {}
        secret = str(data.get("secret") or "")
        if not secret:
            raise WotuApiError("喔图 authority 接口未返回 secret")
        return secret

    async def _fetch_album_meta(self) -> dict[str, Any]:
        if not self._secret or not self._session:
            return {}
        url = self._sign_cdn_url(
            "https://v4c.alltuu.com/rest/v4c/fa",
            {"a": self.album_ref.album_id, "t": "0", "sk": self._secret},
        )
        async with self._session.get(url) as resp:
            if resp.status >= 400:
                return {}
            body = await resp.json(content_type=None)
        return body.get("d") or body.get("data") or {}

    def _extract_tabs_from_meta(self, meta: dict[str, Any]) -> list[dict[str, Any]]:
        raw_tabs = meta.get("seperateDTOList") or meta.get("separateDTOList") or []
        tabs = []
        if isinstance(raw_tabs, list):
            for index, item in enumerate(raw_tabs):
                if not isinstance(item, dict):
                    continue
                category_id = str(item.get("idEnc") or item.get("id") or item.get("sepIdN") or "")
                if not category_id:
                    continue
                tabs.append({
                    "index": index,
                    "name": str(item.get("name") or category_id),
                    "category_id": category_id,
                    "sort": str(item.get("sortType") or item.get("order") or self._album_sort),
                    "active": category_id == self.album_ref.category_id or (not self.album_ref.category_id and index == 0),
                })
        return tabs

    def _default_tab(self) -> dict[str, Any]:
        if self._tabs:
            if self.album_ref.category_id:
                for tab in self._tabs:
                    if str(tab.get("category_id") or "") == self.album_ref.category_id:
                        return {**tab, "active": True}
            return {**self._tabs[0], "active": True}
        return {
            "index": 0,
            "name": self.album_ref.category_id or "默认分类",
            "category_id": self.album_ref.category_id,
            "sort": self._album_sort,
            "active": True,
        }

    def _extract_album_sort(self, meta: dict[str, Any]) -> str:
        album = meta.get("albumDTO") or {}
        for key in ("sort", "order", "sortType"):
            value = album.get(key)
            if value not in (None, ""):
                return str(value)
        return "4"

    def _current_sort(self) -> str:
        if self._current_tab:
            sort = self._current_tab.get("sort")
            if sort not in (None, ""):
                return str(sort)
        return self._album_sort or "4"

    def _next_cursor_from_photos(self, photo_list: list) -> str:
        for item in reversed(photo_list):
            if not isinstance(item, dict):
                continue
            for key in ("pc", "photoCode", "cursor", "id"):
                value = item.get(key)
                if value not in (None, ""):
                    return str(value)
        return ""

    def _sign_server_url(self, base_url: str, params: dict[str, Any]) -> str:
        timestamp = str(int(time.time() * 1000))
        sign = {**params, "from": ALLTUU_SIGN_FROM, "timestamp": timestamp, "token": ALLTUU_SIGN_TOKEN, "version": ALLTUU_SIGN_VERSION}
        sign_str = "".join(f"/{sign[key]}" for key in sorted(sign))
        digest = hashlib.md5(sign_str.encode("utf-8")).hexdigest()
        return f"{base_url}/v{ALLTUU_SIGN_FROM}-{timestamp}-{ALLTUU_SIGN_TOKEN}-{ALLTUU_SIGN_VERSION}-{digest}"

    def _sign_cdn_url(self, base_url: str, params: dict[str, Any]) -> str:
        parsed = urlparse(base_url)
        path = parsed.path
        for key in sorted(params):
            path += f"/{key}{params[key]}"
        timestamp_hex = format(int(time.time()), "x")
        digest = hashlib.md5(f"{ALLTUU_CDN_SIGN_KEY}{path}{timestamp_hex}".encode("utf-8")).hexdigest()
        return f"{parsed.scheme}://{parsed.netloc}/{digest}/{timestamp_hex}{path}"

    def _page_params(self, page: int) -> dict[str, Any]:
        return {"page": page, "pageNum": page, "pageIndex": page, "pageSize": self.page_size, "limit": self.page_size, "size": self.page_size}

    def _discover_api_urls(self, html: str) -> list[str]:
        normalized = (html or "").replace("\\/", "/")
        return list(dict.fromkeys(urljoin(self.album_url, raw.replace("\\/", "/")) for raw in ALLTUU_API_RE.findall(normalized)))

    def _find_photo_list_recursive(self, obj: Any, depth: int = 0) -> list:
        if depth > 7:
            return []
        markers = ("ol", "bl", "sl", "ssl", "url1920", "n", "shoot_time", "time")
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                keys = set(obj[0].keys())
                if any(marker in keys for marker in markers):
                    return obj
                if any(self._parse_single_photo(item) for item in obj[:3] if isinstance(item, dict)):
                    return obj
            for item in obj[:20]:
                found = self._find_photo_list_recursive(item, depth + 1)
                if found:
                    return found
        elif isinstance(obj, dict):
            for key in ("data", "photos", "list", "items", "result", "records", "photoList", "photo_list", "rows", "content", "d"):
                if key in obj:
                    found = self._find_photo_list_recursive(obj[key], depth + 1)
                    if found:
                        return found
            for val in obj.values():
                found = self._find_photo_list_recursive(val, depth + 1)
                if found:
                    return found
        return []

    def _add_photos(self, photo_list: list) -> int:
        added = 0
        for item in photo_list:
            if not isinstance(item, dict):
                continue
            photo = self._parse_single_photo(item)
            if not photo or not photo.url:
                continue
            if photo.id in self._all_photos:
                continue
            photo.index = len(self._all_photos) + 1
            if self._current_tab:
                photo.tab = str(self._current_tab.get("name") or "")
                photo.category_id = str(self._current_tab.get("category_id") or "")
                photo.category_name = str(self._current_tab.get("name") or "")
            self._all_photos[photo.id] = photo
            self._photo_order.append(photo.id)
            self._new_photos.append(photo)
            added += 1
            if self._on_photo_found:
                self._on_photo_found(photo)
        if added:
            self._emit_log(f"本批新增 {added} 张，累计 {len(self._all_photos)} 张")
        return added

    def _parse_single_photo(self, item: dict) -> Optional[WotuPhotoInfo]:
        url = ""
        for key in ("ol", "bl", "url1920"):
            val = item.get(key, "")
            if isinstance(val, str) and val.startswith("http"):
                url = val
                break
        if not url:
            for val in item.values():
                if isinstance(val, str) and val.startswith("http") and IMAGE_EXT_RE.search(val):
                    url = val
                    break
        if not url:
            return None
        photo = WotuPhotoInfo()
        photo.url = url
        photo.ext = extract_ext_from_url(url) or ".jpg"
        photo.id = str(item.get("id") or item.get("pid") or item.get("photo_id") or item.get("pc") or "")
        for key in ("ssl", "sl", "thumb", "thumb_url"):
            val = item.get(key, "")
            if isinstance(val, str) and val.startswith("http"):
                photo.thumb_url = val
                break
        if not photo.thumb_url:
            photo.thumb_url = url
        raw_name = item.get("n") or item.get("name") or item.get("filename") or ""
        if isinstance(raw_name, str) and raw_name:
            name_no_ext = re.sub(r"\.[^.]+$", "", raw_name)
            photo.filename = sanitize_filename(f"{name_no_ext}{photo.ext}")
        else:
            photo.filename = sanitize_filename(f"{photo.id or hash(url)}{photo.ext}")
        ts = item.get("time", 0) or item.get("shoot_time", 0)
        if ts:
            try:
                ts_int = int(float(ts))
                if ts_int > 1e12:
                    ts_int //= 1000
                photo.shoot_time = datetime.fromtimestamp(ts_int).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError, TypeError):
                photo.shoot_time = str(ts)
        os_val = item.get("os", "")
        if os_val:
            try:
                photo.size = int(float(os_val))
            except (ValueError, TypeError):
                pass
        w = item.get("w", 0) or item.get("width", 0)
        h = item.get("h", 0) or item.get("height", 0)
        if isinstance(w, (int, float)):
            photo.width = int(w)
        if isinstance(h, (int, float)):
            photo.height = int(h)
        return photo

    def _emit_log(self, message: str, level: str = "info"):
        if self._on_log:
            self._on_log(message, level)
        getattr(logger, level, logger.info)(message)

    def _emit_progress(self, data: dict):
        if self._on_progress:
            self._on_progress(data)
