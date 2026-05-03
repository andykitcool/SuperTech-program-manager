"""喔图 Playwright 浏览器自动化模块 - 分批拦截 API + 滚动加载"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Callable, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from app.services.wotu_models import WotuPhotoInfo
from app.services.wotu_utils import extract_ext_from_url, sanitize_filename

logger = logging.getLogger(__name__)

ALLTUU_API_RE = re.compile(r'v4c\.alltuu\.com.*?/rest/v4c/fpl[^/]*/', re.IGNORECASE)


class WotuScraper:
    """喔图相册分批抓取器"""

    def __init__(self, headless: bool = True, scroll_delay: int = 5):
        self.headless = headless
        self.scroll_delay = scroll_delay
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._all_photos: dict[str, WotuPhotoInfo] = {}
        self._photo_order: list[str] = []
        self._new_photos: list[WotuPhotoInfo] = []
        self._on_log: Optional[Callable] = None
        self._on_photo_found: Optional[Callable] = None
        self._on_progress: Optional[Callable] = None
        self._stopped = False
        self._api_count = 0
        self._batch_count = 0

    def set_callbacks(self, on_progress=None, on_log=None, on_photo_found=None):
        self._on_progress = on_progress
        self._on_log = on_log
        self._on_photo_found = on_photo_found

    def _emit_log(self, message: str, level: str = "info"):
        if self._on_log:
            self._on_log(message, level)
        getattr(logger, level, logger.info)(message)

    def _emit_progress(self, data: dict):
        if self._on_progress:
            self._on_progress(data)

    def _emit_photo_found(self, photo: WotuPhotoInfo):
        if self._on_photo_found:
            self._on_photo_found(photo)

    def request_stop(self):
        self._stopped = True

    async def open_page(self, album_url: str):
        """打开相册页面，等待首批API响应"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self._context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
        )
        self._page = await self._context.new_page()
        self._page.on("response", self._handle_response)

        self._emit_log("正在打开相册页面...")

        await self._page.add_init_script("""
            const origOpen = XMLHttpRequest.prototype.open;
            const origSend = XMLHttpRequest.prototype.send;
            window.__xhrIntercepted = 0;
            XMLHttpRequest.prototype.open = function(method, url) {
                this.__url = url;
                return origOpen.apply(this, arguments);
            };
            XMLHttpRequest.prototype.send = function() {
                this.addEventListener('load', function() {
                    if (this.__url && this.__url.includes('alltuu')) {
                        window.__xhrIntercepted++;
                    }
                });
                return origSend.apply(this, arguments);
            };
            const origObserve = IntersectionObserver.prototype.observe;
            IntersectionObserver.prototype.observe = function(target) {
                return origObserve.apply(this, arguments);
            };
        """)

        await self._page.goto(album_url, wait_until="domcontentloaded", timeout=30000)

        self._emit_log("等待页面加载和首次API响应...")
        for i in range(20):
            if self._api_count > 0 or self._stopped:
                break
            await asyncio.sleep(1)
            if i % 5 == 4 and self._api_count == 0:
                self._emit_log(f"仍在等待API响应... ({i+1}s)")

        await asyncio.sleep(2)

        if self._api_count == 0:
            self._emit_log("初始未拦截到API，尝试滚动触发...")
            for _ in range(10):
                await self._page.mouse.wheel(0, 300)
                await asyncio.sleep(0.2)
            await asyncio.sleep(2)

        self._emit_log(f"页面加载完成，第1批: 拦截 {self._api_count} 个API，发现 {len(self._all_photos)} 张图片")

    def reset_state(self):
        """重置抓取状态"""
        self._all_photos.clear()
        self._photo_order.clear()
        self._new_photos.clear()
        self._api_count = 0
        self._batch_count = 0

    async def detect_tabs(self) -> list[dict]:
        """检测页面选项卡"""
        page = self._page
        if not page:
            return []

        tabs = []
        try:
            await asyncio.sleep(1)

            selectors = [
                ".classifyBar-collapsed-items .classifyBar-item",
                "button.classifyBar-item",
                ".classifyBar-item",
                "[class*='classifyBar'] button",
                "[role='tab']",
                "[class*='tab-bar'] [class*='item']",
                "[class*='tab'] [class*='item']",
            ]

            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if len(elements) >= 2:
                    for i, el in enumerate(elements):
                        is_visible = await el.is_visible()
                        if not is_visible:
                            continue
                        name = (await el.inner_text()).strip()
                        if not name or len(name) > 30:
                            continue
                        is_active = False
                        active_attr = await el.get_attribute("active")
                        if active_attr and active_attr.lower() in ("true", "", "active"):
                            is_active = True
                        if not is_active:
                            class_attr = await el.get_attribute("class") or ""
                            if "active" in class_attr.lower() or "current" in class_attr.lower():
                                is_active = True
                        tabs.append({"index": len(tabs), "name": name, "active": is_active})
                    if len(tabs) >= 2:
                        break

            if tabs:
                has_active = any(t["active"] for t in tabs)
                if not has_active:
                    tabs[0]["active"] = True
                self._emit_log(f"检测到 {len(tabs)} 个选项卡: " +
                               ", ".join(f"[{'当前' if t['active'] else ''}{t['name']}]" for t in tabs))
            else:
                self._emit_log("未检测到多个选项卡，将只下载当前页面内容")

        except Exception as e:
            self._emit_log(f"选项卡检测出错: {e}", "warning")

        return tabs

    async def switch_tab(self, tab_info: dict) -> bool:
        """切换到指定选项卡"""
        page = self._page
        if not page:
            return False

        tab_name = tab_info["name"]
        self._emit_log(f"正在切换到选项卡: [{tab_name}]...")
        self.reset_state()

        try:
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)

            clicked = await page.evaluate("""(tabName) => {
                const buttons = document.querySelectorAll('.classifyBar-item, button[class*="classify"]');
                for (const btn of buttons) {
                    const text = (btn.textContent || '').trim();
                    if (text === tabName) { btn.click(); return true; }
                }
                const allElements = document.querySelectorAll('div, span, a, li, button, [role="tab"]');
                for (const el of allElements) {
                    const text = (el.textContent || '').trim();
                    if (text === tabName) { el.click(); return true; }
                }
                return false;
            }""", tab_name)

            if not clicked:
                self._emit_log(f"无法点击选项卡 [{tab_name}]", "warning")
                return False

            self._emit_log(f"已点击选项卡 [{tab_name}]，等待内容加载...")

            for i in range(20):
                if self._api_count > 0 or self._stopped:
                    break
                await asyncio.sleep(1)

            await asyncio.sleep(2)

            if self._api_count == 0:
                self._emit_log(f"尝试滚动触发 [{tab_name}] 的懒加载...")
                await self._page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                for _ in range(5):
                    await page.mouse.wheel(0, 300)
                    await asyncio.sleep(0.2)
                await asyncio.sleep(2)

            if self._api_count > 0:
                self._emit_log(f"选项卡 [{tab_name}] 加载成功，发现 {len(self._all_photos)} 张图片")
                return True
            else:
                self._emit_log(f"选项卡 [{tab_name}] 未加载到图片数据", "warning")
                return False

        except Exception as e:
            self._emit_log(f"切换选项卡出错: {e}", "error")
            return False

    async def close(self):
        """关闭浏览器"""
        try:
            if self._page:
                self._page.remove_listener("response", self._handle_response)
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
        finally:
            self._page = self._context = self._browser = self._playwright = None

    def get_new_photos(self) -> list[WotuPhotoInfo]:
        """取出新增照片"""
        batch = self._new_photos[:]
        self._new_photos.clear()
        if batch:
            self._batch_count += 1
            self._emit_log(f"第 {self._batch_count} 批: {len(batch)} 张新图片 (累计 {len(self._all_photos)} 张)")
        return batch

    async def scroll_and_wait(self, timeout: int = 10) -> bool:
        """滚动触发懒加载"""
        page = self._page
        if not page or self._stopped:
            return False

        import random
        delay = random.uniform(1, max(2, self.scroll_delay))
        self._emit_log(f"随机等待 {delay:.1f} 秒后滚动...")
        await asyncio.sleep(delay)

        if self._stopped:
            return False

        try:
            if page.is_closed():
                self._emit_log("页面已关闭，停止滚动", "warning")
                return False
        except Exception:
            return False

        count_before = self._api_count

        try:
            scroll_rounds = 0
            max_scroll_rounds = 20

            while scroll_rounds < max_scroll_rounds and not self._stopped:
                scroll_rounds += 1
                for _ in range(5):
                    await page.mouse.wheel(0, 300)
                    await asyncio.sleep(0.15)

                await asyncio.sleep(0.5)
                if self._api_count > count_before:
                    self._emit_log(f"滚动第 {scroll_rounds} 轮后触发新API请求")
                    await asyncio.sleep(1.5)
                    return True

                at_bottom = await page.evaluate("""() => {
                    const scrollContainer = document.querySelector('.album-scrollList') ||
                        document.querySelector('.component-scroll');
                    if (scrollContainer) {
                        return (scrollContainer.clientHeight + scrollContainer.scrollTop) >= (scrollContainer.scrollHeight - 200);
                    }
                    return (window.innerHeight + window.scrollY) >= (document.body.scrollHeight - 200);
                }""")

                if at_bottom:
                    self._emit_log(f"已到达页面底部 (滚动 {scroll_rounds} 轮)")
                    break

            self._emit_log("等待可能的延迟加载...")
            for _ in range(int(timeout / 2)):
                if self._stopped:
                    break
                await asyncio.sleep(0.5)
                if self._api_count > count_before:
                    await asyncio.sleep(1.5)
                    return True

        except Exception as e:
            self._emit_log(f"滚动出错: {e}", "warning")

        return False

    @property
    def total_found(self) -> int:
        return len(self._all_photos)

    def _parse_single_photo(self, item: dict) -> Optional[WotuPhotoInfo]:
        """解析单张图片"""
        photo = WotuPhotoInfo()

        url = ""
        for key in ("ol", "bl", "url1920"):
            val = item.get(key, "")
            if val and isinstance(val, str) and val.startswith("http"):
                url = val
                break
        if not url:
            for val in item.values():
                if isinstance(val, str) and val.startswith("http"):
                    if any(ext in val.lower() for ext in ('.jpg', '.jpeg', '.png', '.webp')):
                        url = val
                        break
        if not url:
            return None

        photo.url = url
        photo.ext = extract_ext_from_url(url) or ".jpg"
        photo.id = str(item.get("id", ""))

        for key in ("ssl", "sl"):
            val = item.get(key, "")
            if val and isinstance(val, str) and val.startswith("http"):
                photo.thumb_url = val
                break
        if not photo.thumb_url:
            photo.thumb_url = url

        raw_name = item.get("n", "")
        if raw_name and isinstance(raw_name, str):
            name_no_ext = re.sub(r'\.[^.]+$', '', raw_name)
            photo.filename = sanitize_filename(f"{name_no_ext}{photo.ext}")
        else:
            photo.filename = sanitize_filename(f"{photo.id}{photo.ext}")

        ts = item.get("time", 0) or item.get("shoot_time", 0)
        if ts:
            try:
                ts_int = int(ts)
                if ts_int > 1e12:
                    ts_int = ts_int // 1000
                photo.shoot_time = datetime.fromtimestamp(ts_int).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
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

    def _find_photo_list_recursive(self, obj, depth=0) -> list:
        """递归搜索含图片特征的列表"""
        if depth > 5:
            return []
        markers = ("ol", "bl", "sl", "ssl", "url1920", "n", "shoot_time")
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                keys = set(obj[0].keys())
                if any(m in keys for m in markers):
                    return obj
                if "id" in keys and isinstance(obj[0].get("id"), int):
                    return obj
            for item in obj[:10]:
                r = self._find_photo_list_recursive(item, depth + 1)
                if r:
                    return r
        elif isinstance(obj, dict):
            for key in ("data", "photos", "list", "items", "result", "records",
                        "photoList", "photo_list", "rows", "content"):
                if key in obj:
                    r = self._find_photo_list_recursive(obj[key], depth + 1)
                    if r:
                        return r
            for val in obj.values():
                r = self._find_photo_list_recursive(val, depth + 1)
                if r:
                    return r
        return []

    async def _handle_response(self, response):
        """拦截喔图API响应"""
        if self._stopped:
            return

        if response.status != 200 or not ALLTUU_API_RE.search(response.url):
            return

        self._api_count += 1
        self._emit_log(f"[API #{self._api_count}] 拦截到响应")

        try:
            body = await response.json()
        except Exception as e:
            self._emit_log(f"JSON解析失败: {e}", "warning")
            return

        if not body or not isinstance(body, dict):
            return

        photo_list = self._find_photo_list_recursive(body)

        if not photo_list:
            self._emit_log("API响应中未找到图片列表", "warning")
            return

        added = 0
        for item in photo_list:
            if not isinstance(item, dict):
                continue
            photo = self._parse_single_photo(item)
            if photo and photo.url and photo.id not in self._all_photos:
                photo.index = len(self._all_photos) + 1
                self._all_photos[photo.id] = photo
                self._photo_order.append(photo.id)
                self._new_photos.append(photo)
                added += 1
                self._emit_photo_found(photo)

        if added > 0:
            self._emit_log(f"本批新增 {added} 张 (累计 {len(self._all_photos)} 张)")
            self._emit_progress({
                "type": "scraping_progress",
                "found": len(self._all_photos),
                "batch": self._batch_count + 1,
            })
