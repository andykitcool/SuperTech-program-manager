"""Wotu photo sync service based on pure HTTP APIs."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.services.wotu_downloader import WotuDownloader
from app.services.wotu_models import WotuPhotoInfo, WotuSyncStats, WotuSyncTask, WotuTaskPhase
from app.services.wotu_scraper import WotuScraper

logger = logging.getLogger(__name__)
BEIJING_TZ = timezone(timedelta(hours=8))


class WotuSyncManager:
    """Single-process Wotu sync manager used by admin APIs."""

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._task: Optional[WotuSyncTask] = None
        self._stats = WotuSyncStats()
        self._photos: list[dict] = []
        self._logs: list[dict] = []
        self._scraper: Optional[WotuScraper] = None
        self._downloader: Optional[WotuDownloader] = None
        self._sync_task_id = 0
        self._callbacks = {
            "on_log": [],
            "on_stats": [],
            "on_photo_new": [],
            "on_photo_update": [],
        }

    @property
    def running(self) -> bool:
        return self._running

    @property
    def stats(self) -> dict:
        return self._stats.to_dict()

    @property
    def photos(self) -> list[dict]:
        return self._photos

    @property
    def logs(self) -> list[dict]:
        return self._logs

    def on(self, event: str, callback):
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit(self, event: str, data=None):
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception:
                pass

    def _add_log(self, message: str, level: str = "info"):
        entry = {"message": message, "level": level, "time": datetime.now(BEIJING_TZ).strftime("%H:%M:%S")}
        self._logs.append(entry)
        self._logs = self._logs[-500:]
        self._emit("on_log", entry)
        getattr(logger, level, logger.info)(message)

    def _update_photo(self, photo_dict: dict):
        for index, existing in enumerate(self._photos):
            if existing.get("id") == photo_dict.get("id"):
                self._photos[index] = photo_dict
                self._emit("on_photo_update", photo_dict)
                return
        self._photos.append(photo_dict)
        self._emit("on_photo_new", photo_dict)

    def _update_stats(self, stats_dict: dict):
        phase_value = stats_dict.get("phase", "idle")
        try:
            phase = WotuTaskPhase(phase_value)
        except ValueError:
            phase = WotuTaskPhase.ERROR
        self._stats = WotuSyncStats(
            phase=phase,
            total_found=int(stats_dict.get("total_found", 0) or 0),
            total_downloaded=int(stats_dict.get("total_downloaded", 0) or 0),
            total_uploaded=int(stats_dict.get("total_uploaded", 0) or 0),
            total_failed=int(stats_dict.get("total_failed", 0) or 0),
            total_skipped=int(stats_dict.get("total_skipped", 0) or 0),
            total_bytes=int(stats_dict.get("total_bytes", 0) or 0),
            speed=float(stats_dict.get("speed", 0) or 0),
            scroll_count=int(stats_dict.get("scroll_count", 0) or 0),
            current_tab=str(stats_dict.get("current_tab", "") or ""),
            error_msg=str(stats_dict.get("error_msg", "") or ""),
        )
        self._emit("on_stats", self._stats.to_dict())

    def _create_sync_task_record(self, activity_id: int, url: str, activity_name: str, config: dict) -> int:
        from app.database import SessionLocal
        from app.models.sync_task import SyncTask, SyncTaskStatus

        db = SessionLocal()
        try:
            task = SyncTask(
                activity_id=activity_id,
                activity_name=activity_name,
                wotu_album_url=url,
                status=SyncTaskStatus.RUNNING,
                config_json=json.dumps(config, ensure_ascii=False),
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task.id
        except Exception as exc:
            logger.error("创建同步任务记录失败: %s", exc)
            return 0
        finally:
            db.close()

    def _update_sync_task_record(self, task_id: int, status: str, stats: dict, error_msg: str = ""):
        if not task_id:
            return
        from app.database import SessionLocal
        from app.models.sync_task import SyncTask, SyncTaskStatus

        db = SessionLocal()
        try:
            task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
            if not task:
                return
            task.status = SyncTaskStatus(status)
            task.total_found = stats.get("total_found", 0)
            task.total_downloaded = stats.get("total_downloaded", 0)
            task.total_uploaded = stats.get("total_uploaded", 0)
            task.total_failed = stats.get("total_failed", 0)
            task.total_skipped = stats.get("total_skipped", 0)
            task.total_bytes = stats.get("total_bytes", 0)
            if error_msg:
                task.error_msg = error_msg
            if status != "running":
                task.finished_at = datetime.now()
            db.commit()
        except Exception as exc:
            logger.error("更新同步任务记录失败: %s", exc)
        finally:
            db.close()

    async def inspect_album(self, url: str) -> dict:
        scraper = WotuScraper(page_size=60)
        try:
            scraper.set_callbacks(on_log=self._add_log)
            await scraper.open_album(url)
            tabs = await scraper.detect_tabs()
            if not tabs:
                tabs = [dict(scraper._current_tab or {"index": 0, "name": "默认分类", "category_id": scraper.album_ref.category_id, "sort": scraper._album_sort})]
            categories = []
            total = 0
            for tab in tabs:
                await scraper.switch_tab(tab)
                await scraper.fetch_until_empty(no_new_pages=1)
                count = scraper.total_found
                total += count
                categories.append({
                    "index": int(tab.get("index", len(categories)) or len(categories)),
                    "name": str(tab.get("name") or tab.get("category_id") or "默认分类"),
                    "category_id": str(tab.get("category_id") or ""),
                    "sort": str(tab.get("sort") or scraper._album_sort or "4"),
                    "count": count,
                })
            return {"album_id": scraper.album_ref.album_id, "url": url, "total": total, "categories": categories}
        finally:
            await scraper.close()

    def start_sync(
        self,
        activity_id: int,
        url: str,
        concurrency: int = 5,
        scroll_delay: int = 5,
        tab_mode: str = "current",
        tab_subdir: bool = True,
        storage_path_prefix: str = "",
        activity_name: str = "",
        selected_categories: Optional[list[dict]] = None,
        no_new_stop_rounds: int = 3,
    ):
        with self._lock:
            if self._running:
                return False, "任务正在运行中"
            self._photos = []
            self._logs = []
            self._stats = WotuSyncStats(phase=WotuTaskPhase.SCRAPING)
            self._task = WotuSyncTask(
                activity_id=activity_id,
                url=url,
                concurrency=max(1, min(int(concurrency or 5), 20)),
                scroll_delay=max(1, min(int(scroll_delay or 5), 30)),
                no_new_stop_rounds=max(1, min(int(no_new_stop_rounds or 3), 999)),
                tab_mode=tab_mode or "current",
                tab_subdir=bool(tab_subdir),
                selected_categories=selected_categories or [],
            )
            self._running = True

        config = {
            "concurrency": self._task.concurrency,
            "scroll_delay": self._task.scroll_delay,
            "no_new_stop_rounds": self._task.no_new_stop_rounds,
            "tab_mode": self._task.tab_mode,
            "tab_subdir": self._task.tab_subdir,
            "selected_categories": self._task.selected_categories,
            "storage_path_prefix": storage_path_prefix,
        }
        self._sync_task_id = self._create_sync_task_record(activity_id, url, activity_name, config)
        thread = threading.Thread(target=self._run_task, args=(activity_id, storage_path_prefix), daemon=True)
        thread.start()
        return True, "任务已启动"

    def stop_sync(self):
        self._running = False
        if self._scraper:
            self._scraper.request_stop()
        if self._downloader:
            self._downloader.request_stop()
        self._stats.phase = WotuTaskPhase.IDLE
        self._add_log("用户已请求停止任务", "warning")
        self._update_stats({"phase": "idle"})

    def _run_task(self, activity_id: int, storage_path_prefix: str):
        try:
            asyncio.run(self._run_task_async(activity_id, storage_path_prefix))
        except Exception as exc:
            self._add_log(f"任务执行出错: {exc}", "error")
            logger.exception("Wotu sync task failed")
            self._update_stats({"phase": "error", "error_msg": str(exc)})
        finally:
            self._running = False
            self._scraper = None
            self._downloader = None
            final_stats = self._stats.to_dict()
            if final_stats.get("phase") == "completed":
                self._update_sync_task_record(self._sync_task_id, "completed", final_stats)
            elif final_stats.get("phase") == "error":
                self._update_sync_task_record(self._sync_task_id, "failed", final_stats, final_stats.get("error_msg", ""))
            else:
                self._update_sync_task_record(self._sync_task_id, "stopped", final_stats)

    async def _run_task_async(self, activity_id: int, storage_path_prefix: str):
        task = self._task
        if not task:
            return

        scraper = WotuScraper(headless=True, scroll_delay=0)
        self._scraper = scraper
        downloader = WotuDownloader(
            activity_id=activity_id,
            storage_path_prefix=storage_path_prefix,
            concurrency=task.concurrency,
            max_retries=task.max_retries,
            timeout=task.timeout,
        )
        self._downloader = downloader

        grand_total_found = 0
        grand_total_downloaded = 0
        grand_total_uploaded = 0
        grand_total_failed = 0
        grand_total_skipped = 0
        grand_total_bytes = 0
        poll_round = 0
        base_interval = max(1, int(task.scroll_delay or 5))
        current_interval = base_interval
        consecutive_max_idle = 0
        processed_ids: set[str] = set()

        def emit_totals(phase="scraping", current_tab=""):
            self._update_stats({
                "phase": phase,
                "total_found": grand_total_found,
                "total_downloaded": grand_total_downloaded,
                "total_uploaded": grand_total_uploaded,
                "total_failed": grand_total_failed,
                "total_skipped": grand_total_skipped,
                "total_bytes": grand_total_bytes,
                "scroll_count": poll_round,
                "current_tab": current_tab,
                "speed": downloader._stats.speed,
            })

        async def on_photo_uploaded(photo: WotuPhotoInfo, filepath: str):
            nonlocal grand_total_uploaded
            try:
                storage_url, file_size = await self._download_and_upload_photo(photo, activity_id, storage_path_prefix)
                await asyncio.to_thread(self._save_photo_record, photo, activity_id, storage_url, file_size)
                grand_total_uploaded += 1
                self._add_log(f"上传成功: {photo.filename}")
            except Exception as exc:
                self._add_log(f"上传失败: {photo.filename} - {exc}", "error")

        try:
            self._add_log(f"开始监听喔图相册：{task.url}")
            self._add_log(f"API基础间隔 {base_interval}s，无新照片退避上限 30s，连续 {task.no_new_stop_rounds} 次后自动停止")
            await scraper.open_album(task.url)

            tabs_to_process = [dict(scraper._current_tab or {"index": 0, "name": "默认分类", "category_id": scraper.album_ref.category_id, "active": True})]
            all_tabs = []
            if task.selected_categories:
                all_tabs = await scraper.detect_tabs()
                selected_ids = {str(item.get("category_id") or "") for item in task.selected_categories}
                tabs_to_process = [tab for tab in all_tabs if str(tab.get("category_id") or "") in selected_ids] or task.selected_categories
                self._add_log("监听分类：" + "、".join(str(t.get("name") or t.get("category_id")) for t in tabs_to_process))
            elif task.tab_mode == "all":
                all_tabs = await scraper.detect_tabs()
                if len(all_tabs) >= 2:
                    tabs_to_process = all_tabs
                    self._add_log(f"监听全部 {len(all_tabs)} 个分类")
                else:
                    self._add_log("没有多分类信息，仅监听当前分类", "warning")

            while self._running and not scraper._stopped:
                poll_round += 1
                round_new = 0
                self._add_log(f"第 {poll_round} 轮检查开始")

                for tab_info in tabs_to_process:
                    if not self._running or scraper._stopped:
                        break
                    tab_name = str(tab_info.get("name") or tab_info.get("category_id") or "默认分类")
                    await scraper.switch_tab(tab_info)

                    def on_photo_found(photo, tab_label=tab_name):
                        payload = photo.to_dict()
                        payload["tab"] = tab_label
                        self._update_photo(payload)

                    scraper.set_callbacks(on_log=self._add_log, on_photo_found=on_photo_found)

                    while self._running and not scraper._stopped:
                        has_data = await scraper.fetch_next_page()
                        batch = scraper.get_new_photos()
                        if not has_data and not batch:
                            break
                        unseen = []
                        for photo in batch:
                            marker = f"{tab_info.get('category_id') or ''}:{photo.id or photo.url}"
                            if marker in processed_ids:
                                continue
                            processed_ids.add(marker)
                            unseen.append(photo)
                        if not unseen:
                            break

                        round_new += len(unseen)
                        grand_total_found += len(unseen)
                        self._add_log(f"[{tab_name}] 发现 {len(unseen)} 张新照片，开始转存")
                        dl_base_downloaded = downloader._stats.total_downloaded
                        dl_base_failed = downloader._stats.total_failed
                        dl_base_skipped = downloader._stats.total_skipped
                        dl_base_bytes = downloader._stats.total_bytes
                        downloader.set_callbacks(
                            on_progress=lambda _stats: emit_totals("downloading", tab_name),
                            on_log=self._add_log,
                            on_photo_complete=self._update_photo,
                            on_photo_uploaded=on_photo_uploaded,
                        )
                        await downloader.download_batch(unseen)
                        grand_total_downloaded += downloader._stats.total_downloaded - dl_base_downloaded
                        grand_total_failed += downloader._stats.total_failed - dl_base_failed
                        grand_total_skipped += downloader._stats.total_skipped - dl_base_skipped
                        grand_total_bytes += downloader._stats.total_bytes - dl_base_bytes
                        emit_totals("scraping", tab_name)

                if not self._running or scraper._stopped:
                    break

                if round_new:
                    current_interval = base_interval
                    consecutive_max_idle = 0
                    self._add_log(f"本轮发现 {round_new} 张新照片，{current_interval} 秒后继续检查")
                else:
                    if current_interval >= 30:
                        consecutive_max_idle += 1
                    else:
                        consecutive_max_idle = 0
                    current_interval = min(current_interval + 5, 30)
                    if consecutive_max_idle >= task.no_new_stop_rounds:
                        self._add_log(f"已连续 {consecutive_max_idle} 个 30 秒轮询没有新照片，自动停止任务", "warning")
                        self._running = False
                        break
                    self._add_log(f"本轮没有新照片，{current_interval} 秒后继续检查")
                emit_totals("scraping")

                for _ in range(current_interval):
                    if not self._running or scraper._stopped:
                        break
                    await asyncio.sleep(1)

            await scraper.close()
            self._scraper = None
            self._add_log(
                f"同步停止：发现 {grand_total_found}，下载 {grand_total_downloaded}，上传 {grand_total_uploaded}，"
                f"失败 {grand_total_failed}，跳过 {grand_total_skipped}"
            )
            self._update_stats({
                "phase": "completed" if not self._running and consecutive_max_idle >= task.no_new_stop_rounds else "idle",
                "total_found": grand_total_found,
                "total_downloaded": grand_total_downloaded,
                "total_uploaded": grand_total_uploaded,
                "total_failed": grand_total_failed,
                "total_skipped": grand_total_skipped,
                "total_bytes": grand_total_bytes,
                "speed": 0,
            })
        except Exception as exc:
            self._add_log(f"任务执行出错: {exc}", "error")
            logger.exception("Wotu sync task failed")
            self._update_stats({"phase": "error", "error_msg": str(exc)})
        finally:
            await scraper.close()
            self._running = False
            self._scraper = None
            self._downloader = None

    async def _download_and_upload_photo(self, photo: WotuPhotoInfo, activity_id: int, storage_path_prefix: str = "") -> tuple[str, int]:
        from app.services.storage_service import get_storage_service

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(photo.url)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
            content = resp.content

        storage = get_storage_service()
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        photo_date = "unknown"
        if photo.shoot_time:
            try:
                photo_date = datetime.strptime(photo.shoot_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            except ValueError:
                pass
        prefix = (storage_path_prefix or "").strip().strip("/")
        storage_key = f"photos/{photo_date}/{uuid.uuid4().hex}{ext}"
        if prefix:
            storage_key = f"{prefix}/{storage_key}"
        storage_url = await storage.upload_file(content, storage_key)
        return storage_url, len(content)

    def _save_photo_record(self, photo: WotuPhotoInfo, activity_id: int, storage_url: str, file_size: int):
        save_photo_record(photo, activity_id, storage_url, file_size)


def save_photo_record(
    photo: WotuPhotoInfo,
    activity_id: int,
    storage_url: str,
    file_size: int,
    storage_provider: str = "",
):
    """Standalone function to save a photo record to DB and trigger Program matching.
    Used by both WotuSyncManager and callback API.
    """
    from app.database import SessionLocal
    import json
    from app.models import Photo, Program, SystemSettings
    from app.models.activity import ReadyStatus, VideoStatus
    from app.models.activity import SyncStatus
    from app.services.storage_service import get_storage_service

    db = SessionLocal()
    try:
        existing = db.query(Photo).filter(Photo.wotu_photo_id == photo.id).first()
        if existing:
            return
        shoot_time = None
        if photo.shoot_time:
            try:
                shoot_time = datetime.strptime(photo.shoot_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        storage = get_storage_service()
        provider_name = storage_provider or (storage.provider_name if storage else "qiniu")
        db_photo = Photo(
            activity_id=activity_id,
            program_id=None,
            filename=photo.filename,
            storage_url=storage_url,
            wotu_url=photo.url,
            wotu_photo_id=photo.id,
            wotu_category_id=photo.category_id or None,
            wotu_category_name=photo.category_name or photo.tab or None,
            storage_provider=provider_name,
            shoot_time=shoot_time,
            width=photo.width,
            height=photo.height,
            file_size=file_size,
            sync_status=SyncStatus.MATCHED,
        )
        db.add(db_photo)
        if shoot_time:
            setting = db.query(SystemSettings).filter(
                SystemSettings.key == f"activity_{activity_id}_photo_match_categories"
            ).first()
            selected_category_ids = None
            if setting and setting.value not in (None, ""):
                try:
                    parsed = json.loads(setting.value)
                    if isinstance(parsed, list):
                        selected_category_ids = [str(item) for item in parsed if str(item) != ""]
                except Exception:
                    selected_category_ids = None
            if selected_category_ids is not None and (not selected_category_ids or str(photo.category_id or "") not in selected_category_ids):
                db.commit()
                return
            programs = db.query(Program).filter(Program.activity_id == activity_id, Program.start_time.isnot(None)).all()
            for program in programs:
                program_end = program.start_time + timedelta(seconds=program.duration) if program.duration and program.duration > 0 else program.start_time
                if program.start_time <= shoot_time <= program_end:
                    db_photo.program_id = program.id
                    program.photo_count = db.query(Photo).filter(Photo.program_id == program.id).count() + 1
                    if program.ready_mode.value == "auto":
                        program.ready_status = ReadyStatus.READY if program.video_status == VideoStatus.READY and program.photo_count >= 1 else ReadyStatus.PENDING
                    break
        db.commit()
    finally:
        db.close()


wotu_sync_manager = WotuSyncManager()
