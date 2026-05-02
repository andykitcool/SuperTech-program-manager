"""喔图照片同步服务 - 编排抓取、下载、上传、入库流程"""

import json
import os
import asyncio
import logging
import threading
from datetime import datetime, timezone, timedelta as _timedelta
from typing import Optional

_BEIJING_TZ = timezone(_timedelta(hours=8))

from app.services.wotu_models import WotuPhotoInfo, WotuSyncStats, WotuSyncTask, WotuTaskPhase
from app.services.wotu_scraper import WotuScraper
from app.services.wotu_downloader import WotuDownloader

logger = logging.getLogger(__name__)


class WotuSyncManager:
    """喔图照片同步管理器（单例）"""

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._task: Optional[WotuSyncTask] = None
        self._stats = WotuSyncStats()
        self._photos: list[dict] = []
        self._logs: list[dict] = []
        self._scraper: Optional[WotuScraper] = None
        self._downloader: Optional[WotuDownloader] = None
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
        """注册回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit(self, event: str, data=None):
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

    def _add_log(self, message: str, level: str = "info"):
        entry = {"message": message, "level": level, "time": datetime.now(_BEIJING_TZ).strftime("%H:%M:%S")}
        self._logs.append(entry)
        if len(self._logs) > 500:
            self._logs = self._logs[-500:]
        self._emit("on_log", entry)

    def _update_photo(self, photo_dict: dict):
        for i, p in enumerate(self._photos):
            if p.get("id") == photo_dict.get("id"):
                self._photos[i] = photo_dict
                self._emit("on_photo_update", photo_dict)
                return
        self._photos.append(photo_dict)
        self._emit("on_photo_new", photo_dict)

    def _update_stats(self, stats_dict: dict):
        self._stats = WotuSyncStats(
            phase=WotuTaskPhase(stats_dict.get("phase", "idle")),
            total_found=stats_dict.get("total_found", 0),
            total_downloaded=stats_dict.get("total_downloaded", 0),
            total_uploaded=stats_dict.get("total_uploaded", 0),
            total_failed=stats_dict.get("total_failed", 0),
            total_skipped=stats_dict.get("total_skipped", 0),
            total_bytes=stats_dict.get("total_bytes", 0),
            speed=stats_dict.get("speed", 0),
            scroll_count=stats_dict.get("scroll_count", 0),
            current_tab=stats_dict.get("current_tab", ""),
            error_msg=stats_dict.get("error_msg", ""),
        )
        self._emit("on_stats", self._stats.to_dict())

    def _create_sync_task_record(self, activity_id: int, url: str, activity_name: str, config: dict) -> int:
        """在数据库中创建同步任务记录，返回 task_id"""
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
        except Exception as e:
            logger.error(f"创建同步任务记录失败: {e}")
            return 0
        finally:
            db.close()

    def _update_sync_task_record(self, task_id: int, status: str, stats: dict, error_msg: str = None):
        """更新同步任务记录的最终状态和统计"""
        if not task_id:
            return
        from app.database import SessionLocal
        from app.models.sync_task import SyncTask
        from datetime import datetime
        from app.models.sync_task import SyncTaskStatus
        db = SessionLocal()
        try:
            task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
            if task:
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
        except Exception as e:
            logger.error(f"更新同步任务记录失败: {e}")
        finally:
            db.close()

    def start_sync(self, activity_id: int, url: str, concurrency: int = 5,
                   scroll_delay: int = 5, tab_mode: str = "current",
                   tab_subdir: bool = True, storage_path_prefix: str = "",
                   activity_name: str = ""):
        """启动同步任务（在后台线程中运行）"""
        with self._lock:
            if self._running:
                return False, "任务正在运行中"

            self._photos = []
            self._stats = WotuSyncStats(phase=WotuTaskPhase.SCRAPING)
            self._task = WotuSyncTask(
                activity_id=activity_id,
                url=url,
                concurrency=max(1, min(concurrency, 20)),
                scroll_delay=max(0, min(scroll_delay, 60)),
                tab_mode=tab_mode,
                tab_subdir=tab_subdir,
            )
            self._running = True

        # 创建数据库记录
        config = {
            "concurrency": self._task.concurrency,
            "scroll_delay": self._task.scroll_delay,
            "tab_mode": tab_mode,
            "tab_subdir": tab_subdir,
            "storage_path_prefix": storage_path_prefix,
        }
        sync_task_id = self._create_sync_task_record(activity_id, url, activity_name, config)
        self._sync_task_id = sync_task_id

        thread = threading.Thread(
            target=self._run_task,
            args=(activity_id, storage_path_prefix),
            daemon=True
        )
        thread.start()
        return True, "任务已启动"

    def stop_sync(self):
        """停止同步任务"""
        self._running = False
        if self._scraper:
            self._scraper.request_stop()
        if self._downloader:
            self._downloader.request_stop()
        self._stats.phase = WotuTaskPhase.IDLE
        self._add_log("用户已请求停止任务", "warning")
        self._update_stats({"phase": "idle"})

    def _run_task(self, activity_id: int, storage_path_prefix: str):
        """在后台线程中运行同步任务"""
        try:
            asyncio.run(self._run_task_async(activity_id, storage_path_prefix))
        except Exception as e:
            self._add_log(f"任务执行出错: {e}", "error")
            logger.exception("任务执行出错")
            self._update_stats({"phase": "error", "error_msg": str(e)})
        finally:
            self._running = False
            self._scraper = None
            self._downloader = None
            # 更新数据库记录
            final_stats = self._stats.to_dict()
            if final_stats.get("phase") == "completed":
                self._update_sync_task_record(
                    getattr(self, "_sync_task_id", 0), "completed", final_stats
                )
            elif final_stats.get("phase") == "error":
                self._update_sync_task_record(
                    getattr(self, "_sync_task_id", 0), "failed", final_stats,
                    error_msg=final_stats.get("error_msg", ""),
                )
            else:
                self._update_sync_task_record(
                    getattr(self, "_sync_task_id", 0), "stopped", final_stats
                )

    async def _run_task_async(self, activity_id: int, storage_path_prefix: str):
        """异步主流程"""
        task = self._task
        try:
            self._add_log(f"开始抓取相册: {task.url}")
            self._add_log(f"活动ID: {activity_id}, 并发数: {task.concurrency}, 滚动延迟: 1~{task.scroll_delay}s")
            self._add_log(f"选项卡模式: {'下载所有选项卡' if task.tab_mode == 'all' else '仅当前选项卡'}")

            scraper = WotuScraper(headless=True, scroll_delay=task.scroll_delay)
            self._scraper = scraper

            await scraper.open_page(task.url)

            if not self._running:
                self._add_log("任务已停止", "warning")
                self._update_stats({"phase": "idle"})
                return

            # 检测选项卡
            all_tabs = []
            if task.tab_mode == "all":
                all_tabs = await scraper.detect_tabs()
                if not all_tabs or len(all_tabs) < 2:
                    self._add_log("只检测到 1 个选项卡，将下载当前页面所有内容")
                    all_tabs = []
                else:
                    self._add_log(f"共检测到 {len(all_tabs)} 个选项卡")

            tabs_to_process = all_tabs if all_tabs else [{"index": 0, "name": "默认", "active": True}]

            downloader = WotuDownloader(
                activity_id=activity_id,
                storage_path_prefix=storage_path_prefix,
                concurrency=task.concurrency,
                max_retries=task.max_retries,
                timeout=task.timeout,
            )
            self._downloader = downloader

            # 下载并直接转存到云存储（不落盘）
            async def on_photo_uploaded(photo: WotuPhotoInfo, filepath: str):
                try:
                    import httpx
                    from app.services.storage_service import get_storage_service
                    from app.database import SessionLocal
                    from app.models import Photo
                    import uuid

                    # 直接从喔图 URL 下载到内存
                    async with httpx.AsyncClient(timeout=60) as client:
                        resp = await client.get(photo.url)
                        if resp.status_code != 200:
                            raise Exception(f"HTTP {resp.status_code}")
                        content = resp.content

                    storage = get_storage_service()
                    ext = os.path.splitext(photo.filename)[1] or ".jpg"

                    # 用活动日期构建存储路径: photos/{YYYY-MM-DD}/{uuid}{ext}
                    photo_date = "unknown"
                    if photo.shoot_time:
                        try:
                            from datetime import datetime as dt_cls
                            st = dt_cls.strptime(photo.shoot_time, "%Y-%m-%d %H:%M:%S")
                            photo_date = st.strftime("%Y-%m-%d")
                        except ValueError:
                            pass
                    storage_key = f"photos/{photo_date}/{uuid.uuid4().hex}{ext}"
                    storage_url = await storage.upload_file(content, storage_key)

                    # 写入数据库
                    from datetime import datetime
                    from app.models import Program
                    from app.models.activity import ReadyStatus, VideoStatus
                    db = SessionLocal()
                    try:
                        shoot_time = None
                        if photo.shoot_time:
                            try:
                                shoot_time = datetime.strptime(photo.shoot_time, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                pass

                        # 兜底查重：防止并发场景下重复入库
                        existing = db.query(Photo).filter(
                            Photo.wotu_photo_id == photo.id
                        ).first()
                        if existing:
                            self._stats.total_skipped += 1
                            self._add_log(f"已跳过(已同步): {photo.filename} (wotu_id={photo.id})")
                            return

                        db_photo = Photo(
                            activity_id=activity_id,
                            program_id=None,
                            filename=photo.filename,
                            storage_url=storage_url,
                            wotu_photo_id=photo.id,
                            storage_provider=storage.provider_name,
                            shoot_time=shoot_time,
                            width=photo.width,
                            height=photo.height,
                            file_size=len(content),
                            sync_status="matched",
                        )
                        db.add(db_photo)

                        # 根据拍摄时间自动匹配节目
                        if shoot_time:
                            from datetime import timedelta
                            programs = db.query(Program).filter(
                                Program.activity_id == activity_id,
                                Program.start_time.isnot(None),
                            ).all()
                            for prog in programs:
                                prog_end = prog.start_time + timedelta(seconds=prog.duration) if prog.duration and prog.duration > 0 else prog.start_time
                                if prog.start_time <= shoot_time <= prog_end:
                                    db_photo.program_id = prog.id
                                    # 更新节目的 photo_count
                                    prog.photo_count = db.query(Photo).filter(Photo.program_id == prog.id).count()
                                    # 自动就绪判断
                                    if prog.ready_mode.value == "auto":
                                        if prog.video_status == VideoStatus.READY and prog.photo_count >= 1:
                                            prog.ready_status = ReadyStatus.READY
                                        else:
                                            prog.ready_status = ReadyStatus.PENDING
                                    self._add_log(f"照片 {photo.filename} 匹配到节目 [{prog.name}]")
                                    break

                        db.commit()
                        self._stats.total_uploaded += 1
                        self._add_log(f"上传成功: {photo.filename} -> {storage_url[:80]}...")
                    finally:
                        db.close()
                except Exception as e:
                    self._add_log(f"上传失败: {photo.filename} - {e}", "error")
                finally:
                    # 清理临时文件（如果 downloader 仍然生成了）
                    try:
                        if filepath and os.path.exists(filepath):
                            os.remove(filepath)
                    except Exception:
                        pass

            grand_total_found = 0
            grand_total_downloaded = 0
            grand_total_uploaded = 0
            grand_total_failed = 0
            grand_total_skipped = 0
            grand_total_bytes = 0

            for tab_idx, tab_info in enumerate(tabs_to_process):
                if not self._running or scraper._stopped:
                    self._add_log("任务已停止", "warning")
                    break

                tab_name = tab_info["name"]
                is_first_tab = (tab_idx == 0)

                self._add_log(f"\n{'='*50}")
                if all_tabs:
                    self._add_log(f"[选项卡 {tab_idx+1}/{len(tabs_to_process)}] 正在处理: [{tab_name}]")
                else:
                    self._add_log(f"正在处理当前页面...")
                self._add_log(f"{'='*50}")

                if not is_first_tab and all_tabs:
                    switched = await scraper.switch_tab(tab_info)
                    if not switched:
                        self._add_log(f"选项卡 [{tab_name}] 切换失败，跳过", "warning")
                        continue

                batch = scraper.get_new_photos()
                if not batch and scraper.total_found == 0:
                    self._add_log(f"[{tab_name}] 未发现任何图片，跳过", "warning")
                    continue

                self._add_log(f"[{tab_name}] 第1批发现 {len(batch)} 张图片，开始下载")

                def make_photo_callback(tab_label):
                    def on_photo_found(p):
                        p_dict = p.to_dict()
                        p_dict["tab"] = tab_label
                        self._update_photo(p_dict)
                    return on_photo_found

                scraper.set_callbacks(
                    on_progress=lambda data: self._update_stats({
                        "phase": "scraping",
                        "total_found": grand_total_found + data.get("found", 0),
                        "total_downloaded": grand_total_downloaded,
                        "total_uploaded": grand_total_uploaded,
                        "total_failed": grand_total_failed,
                        "total_skipped": grand_total_skipped,
                        "total_bytes": grand_total_bytes,
                        "scroll_count": data.get("batch", 0),
                        "current_tab": tab_name,
                    }),
                    on_log=self._add_log,
                    on_photo_found=make_photo_callback(tab_name),
                )

                tab_downloaded = 0
                tab_failed = 0
                tab_skipped = 0
                tab_bytes = 0
                batch_num = 0
                consecutive_empty = 0

                dl_baseline_downloaded = downloader._stats.total_downloaded
                dl_baseline_failed = downloader._stats.total_failed
                dl_baseline_skipped = downloader._stats.total_skipped
                dl_baseline_bytes = downloader._stats.total_bytes

                while not scraper._stopped and self._running:
                    if batch:
                        batch_num += 1
                        self._add_log(f"[{tab_name}] ===== 第 {batch_num} 批: {len(batch)} 张图片 =====")

                        downloader.set_callbacks(
                            on_progress=self._update_stats,
                            on_log=self._add_log,
                            on_photo_complete=self._update_photo,
                            on_photo_uploaded=on_photo_uploaded,
                        )

                        await downloader.download_batch(batch)

                        tab_downloaded = downloader._stats.total_downloaded - dl_baseline_downloaded
                        tab_failed = downloader._stats.total_failed - dl_baseline_failed
                        tab_skipped = downloader._stats.total_skipped - dl_baseline_skipped
                        tab_bytes = downloader._stats.total_bytes - dl_baseline_bytes

                        consecutive_empty = 0
                    else:
                        consecutive_empty += 1
                        self._add_log(f"[{tab_name}] 无新图片数据 (连续 {consecutive_empty}/5)")
                        if consecutive_empty >= 5:
                            self._add_log(f"[{tab_name}] 连续 5 次无新数据，判定已全部加载完毕")
                            break

                    self._add_log(f"[{tab_name}] 滚动加载更多图片... (已滚动 {batch_num} 批)")
                    self._update_stats({
                        "phase": "scraping",
                        "total_found": grand_total_found + scraper.total_found,
                        "total_downloaded": grand_total_downloaded + tab_downloaded,
                        "total_uploaded": grand_total_uploaded + downloader._stats.total_uploaded,
                        "total_failed": grand_total_failed + tab_failed,
                        "total_skipped": grand_total_skipped + tab_skipped,
                        "total_bytes": grand_total_bytes + tab_bytes,
                        "scroll_count": batch_num,
                        "current_tab": tab_name,
                    })

                    has_more = await scraper.scroll_and_wait(timeout=15)
                    batch = scraper.get_new_photos()

                tab_found = scraper.total_found
                grand_total_found += tab_found
                grand_total_downloaded += tab_downloaded
                grand_total_uploaded += downloader._stats.total_uploaded
                grand_total_failed += tab_failed
                grand_total_skipped += tab_skipped
                grand_total_bytes += tab_bytes

                self._add_log(f"[{tab_name}] 完成! 发现 {tab_found} 张, 下载 {tab_downloaded}, 上传 {downloader._stats.total_uploaded}, 失败 {tab_failed}")

            await scraper.close()
            self._scraper = None

            self._add_log(f"\n{'='*50}")
            self._add_log(
                f"全部完成! 共发现 {grand_total_found} 张, "
                f"下载 {grand_total_downloaded}, 上传 {grand_total_uploaded}, "
                f"失败 {grand_total_failed}, 跳过 {grand_total_skipped}"
            )
            if all_tabs:
                self._add_log(f"共处理 {len(all_tabs)} 个选项卡")
            self._add_log(f"{'='*50}")
            self._update_stats({
                "phase": "completed",
                "total_found": grand_total_found,
                "total_downloaded": grand_total_downloaded,
                "total_uploaded": grand_total_uploaded,
                "total_failed": grand_total_failed,
                "total_skipped": grand_total_skipped,
                "total_bytes": grand_total_bytes,
                "speed": 0,
            })

        except Exception as e:
            self._add_log(f"任务执行出错: {e}", "error")
            logger.exception("任务执行出错")
            self._update_stats({"phase": "error", "error_msg": str(e)})
        finally:
            self._running = False
            self._scraper = None
            self._downloader = None


# 全局单例
wotu_sync_manager = WotuSyncManager()
