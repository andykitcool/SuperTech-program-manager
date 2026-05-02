"""喔图异步照片下载器 - 下载到临时目录后上传到云存储"""

import os
import asyncio
import time
import logging
import aiohttp

from app.services.wotu_models import WotuPhotoInfo, WotuPhotoStatus, WotuSyncStats
from app.services.wotu_utils import format_size

logger = logging.getLogger(__name__)


class WotuDownloader:
    """异步照片下载器 - 下载后回调上传到云存储"""

    def __init__(
        self,
        activity_id: int,
        storage_path_prefix: str,
        concurrency: int = 5,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        self.activity_id = activity_id
        self.storage_path_prefix = storage_path_prefix
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._on_progress = None
        self._on_log = None
        self._on_photo_complete = None
        self._on_photo_uploaded = None  # 照片上传到云存储后的回调
        self._stopped = False
        self._stats = WotuSyncStats()
        self._speed_samples = []

    def set_callbacks(self, on_progress=None, on_log=None, on_photo_complete=None, on_photo_uploaded=None):
        self._on_progress = on_progress
        self._on_log = on_log
        self._on_photo_complete = on_photo_complete
        self._on_photo_uploaded = on_photo_uploaded

    def _emit_log(self, message: str, level: str = "info"):
        if self._on_log:
            self._on_log(message, level)
        getattr(logger, level, logger.info)(message)

    def _emit_progress(self, stats: WotuSyncStats):
        if self._on_progress:
            self._on_progress(stats.to_dict())

    def _emit_photo_complete(self, photo: WotuPhotoInfo):
        if self._on_photo_complete:
            self._on_photo_complete(photo.to_dict())

    def request_stop(self):
        self._stopped = True

    async def _download_single(self, session, photo, semaphore) -> WotuPhotoInfo:
        """下载单张照片（仅用于触发上传回调，不再落盘）"""
        async with semaphore:
            if self._stopped:
                photo.status = WotuPhotoStatus.FAILED
                photo.error_msg = "用户取消"
                return photo

            photo.status = WotuPhotoStatus.DOWNLOADING

            # 尝试 HEAD 请求获取文件大小
            try:
                async with session.head(photo.url, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        content_length = int(resp.headers.get("content-length", 0))
                        photo.size = content_length
            except Exception:
                pass

            # 标记为成功并触发上传回调
            photo.status = WotuPhotoStatus.SUCCESS
            self._stats.total_downloaded += 1
            self._stats.total_bytes += photo.size
            self._emit_log(f"开始转存: {photo.filename}")
            self._emit_photo_complete(photo)
            self._emit_progress(self._stats)

            # 触发上传回调（传入空 filepath 表示不落盘）
            if self._on_photo_uploaded:
                await self._on_photo_uploaded(photo, "")

            return photo

    async def download_batch(self, photos: list[WotuPhotoInfo]) -> WotuSyncStats:
        """异步并发下载一批，自动过滤已同步的照片"""
        if not photos:
            return self._stats

        # 过滤已同步的照片，避免重复下载和上传
        synced_ids = self._get_synced_photo_ids([p.id for p in photos])
        to_download = []
        for photo in photos:
            if photo.id in synced_ids:
                self._stats.total_skipped += 1
                photo.status = WotuPhotoStatus.SUCCESS
                photo.sync_skip = True
                self._emit_photo_complete(photo)
                self._emit_log(f"已跳过(已同步): {photo.filename}")
            else:
                to_download.append(photo)

        if synced_ids:
            self._emit_log(f"已过滤 {len(synced_ids)} 张已同步照片，剩余 {len(to_download)} 张待下载")
            self._emit_progress(self._stats)

        if not to_download:
            return self._stats

        semaphore = asyncio.Semaphore(self.concurrency)
        connector = aiohttp.TCPConnector(limit=self.concurrency, force_close=True)
        async with aiohttp.ClientSession(connector=connector, timeout=self.timeout) as session:
            tasks = [self._download_single(session, photo, semaphore) for photo in to_download]
            await asyncio.gather(*tasks, return_exceptions=True)

        self._stats.speed = 0
        return self._stats

    def _get_synced_photo_ids(self, photo_ids: list[str]) -> set[str]:
        """查询数据库中已存在的 wotu_photo_id 集合"""
        if not photo_ids:
            return set()
        from app.database import SessionLocal
        from app.models import Photo
        db = SessionLocal()
        try:
            rows = db.query(Photo.wotu_photo_id).filter(
                Photo.wotu_photo_id.in_(photo_ids)
            ).all()
            return {r[0] for r in rows if r[0]}
        except Exception as e:
            self._emit_log(f"查询已同步照片失败: {e}", "warning")
            return set()
        finally:
            db.close()
