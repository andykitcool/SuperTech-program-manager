"""
打印任务调度器：异步提交蓝阔云打印任务 + 状态轮询
"""

import asyncio
import logging
import threading
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import PrintRecord, Photo, SystemSettings
from app.utils.activity_print_settings import get_activity_print_settings

logger = logging.getLogger(__name__)

# 全局轮询控制
_polling_running = False
_polling_thread: Optional[threading.Thread] = None
PRINT_RENDER_MODE_KEY = "print_render_mode"
PRINT_RENDER_MULTIPLIER_KEY = "print_render_multiplier"
PRINT_DISPATCH_MODE_KEY = "print_dispatch_mode"
PRINT_RENDER_MODE_SERVER = "server"
PRINT_DISPATCH_MODE_LANKUO = "lankuo"
PRINT_DISPATCH_MODE_LOCAL_CLIENT = "local_client"
DEFAULT_PRINT_RENDER_MULTIPLIER = 1


def _callback_url_enabled(config: Optional[dict]) -> bool:
    return bool(str((config or {}).get("callbackUrl") or "").strip())


def _normalize_lankuo_task_state(value) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip().upper()
    if text in {"2", "DONE", "SUCCESS", "SUCCEEDED", "FINISHED", "COMPLETED", "OK"}:
        return "success"
    if text in {"3", "ERROR", "FAILED", "FAIL", "CANCEL", "CANCELLED", "CANCELED"}:
        return "failed"
    if text in {"0", "1", "WAITING", "PENDING", "QUEUED", "PRINTING", "SENDING", "PROCESSING", "RUNNING"}:
        return "printing"
    return None


def _normalize_dm_paper_size(value: Optional[str]) -> Optional[str]:
    """只允许蓝阔 dmPaperSize 纸张代码，避免把画布像素尺寸传给蓝阔。"""
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text if text.isdigit() else None


def _get_print_render_mode(db: Session, activity_id: Optional[int] = None) -> str:
    if activity_id:
        return str(get_activity_print_settings(db, activity_id).get("print_render_mode") or "frontend").strip()
    setting = db.query(SystemSettings).filter(SystemSettings.key == PRINT_RENDER_MODE_KEY).first()
    return (setting.value if setting and setting.value else "frontend").strip()


def _get_print_render_multiplier(db: Session, activity_id: Optional[int] = None) -> int:
    if activity_id:
        try:
            value = int(get_activity_print_settings(db, activity_id).get("print_render_multiplier") or DEFAULT_PRINT_RENDER_MULTIPLIER)
        except (TypeError, ValueError):
            value = DEFAULT_PRINT_RENDER_MULTIPLIER
        return min(max(value, 1), 3)
    setting = db.query(SystemSettings).filter(SystemSettings.key == PRINT_RENDER_MULTIPLIER_KEY).first()
    try:
        value = int(setting.value) if setting and setting.value else DEFAULT_PRINT_RENDER_MULTIPLIER
    except (TypeError, ValueError):
        value = DEFAULT_PRINT_RENDER_MULTIPLIER
    return min(max(value, 1), 3)


def get_print_dispatch_mode(db: Session, activity_id: Optional[int] = None) -> str:
    if activity_id:
        mode = str(get_activity_print_settings(db, activity_id).get("print_dispatch_mode") or PRINT_DISPATCH_MODE_LANKUO).strip()
        if mode not in {PRINT_DISPATCH_MODE_LANKUO, PRINT_DISPATCH_MODE_LOCAL_CLIENT, "disabled"}:
            return PRINT_DISPATCH_MODE_LANKUO
        return mode
    setting = db.query(SystemSettings).filter(SystemSettings.key == PRINT_DISPATCH_MODE_KEY).first()
    mode = (setting.value if setting and setting.value else PRINT_DISPATCH_MODE_LANKUO).strip()
    if mode not in {PRINT_DISPATCH_MODE_LANKUO, PRINT_DISPATCH_MODE_LOCAL_CLIENT, "disabled"}:
        return PRINT_DISPATCH_MODE_LANKUO
    return mode


def should_dispatch_lankuo(db: Session, lankuo_config: Optional[dict], activity_id: Optional[int] = None) -> bool:
    return bool(lankuo_config) and get_print_dispatch_mode(db, activity_id) == PRINT_DISPATCH_MODE_LANKUO


def dispatch_print_task(record_id: int, lankuo_config: dict, db: Session = None):
    """
    异步调度打印任务到蓝阔云打印
    在后台线程中执行，不阻塞请求响应
    """
    def _run():
        _do_dispatch(record_id, lankuo_config)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _do_dispatch(record_id: int, lankuo_config: dict):
    """在后台线程中执行：获取图片URL → 调用蓝阔API → 更新记录"""
    db = SessionLocal()
    try:
        record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
        if not record:
            logger.error(f"打印记录 {record_id} 不存在")
            return

        # 获取照片 URL
        photo = db.query(Photo).filter(Photo.id == record.photo_id).first() if record.photo_id else None
        original_photo_url = None
        file_url = None

        if photo:
            original_photo_url = photo.storage_url or photo.wotu_url

        # 如果有 canvas_image（base64），需要先上传获取 URL
        # 蓝阔 API 需要一个可访问的文件 URL
        import json
        if record.print_payload_json:
            try:
                payload = json.loads(record.print_payload_json)
                render_mode = _get_print_render_mode(db, record.activity_id)
                if render_mode == PRINT_RENDER_MODE_SERVER:
                    try:
                        from app.utils.canvas_renderer import render_fabric_payload_to_png

                        image_bytes = render_fabric_payload_to_png(
                            payload,
                            multiplier=_get_print_render_multiplier(db, record.activity_id),
                        )
                        file_url = _upload_image_bytes(image_bytes, "png", db, record, suffix="server")
                    except Exception as render_error:
                        logger.error("打印记录 %s 服务端渲染失败，尝试回退到前端渲染图: %s", record_id, render_error, exc_info=True)

                if not file_url:
                    canvas_image = payload.get("_canvas_image")
                    if isinstance(canvas_image, str):
                        if canvas_image.startswith("data:"):
                            file_url = _upload_canvas_image(canvas_image, db, record)
                        elif canvas_image.startswith(("http://", "https://", "/uploads/")):
                            file_url = canvas_image
            except Exception as payload_error:
                logger.error("打印记录 %s 解析画布数据失败: %s", record_id, payload_error, exc_info=True)

        if not file_url:
            file_url = record.print_image_url or original_photo_url

        if not file_url:
            logger.error(f"打印记录 {record_id} 没有可用的图片 URL")
            record.status = "failed"
            record.error_msg = "无可打印的图片URL"
            db.commit()
            return

        record.print_image_url = file_url

        # 调用蓝阔 API 提交打印任务
        from app.utils.lankuo_client import LankuoClient
        client = LankuoClient(lankuo_config)

        # 记录里的 paper_size 只允许保存蓝阔纸张代码。旧数据里可能存在 1500×1500
        # 这样的画布像素尺寸，必须回落到当前有效配置，避免蓝阔 500。
        use_record_paper_size = lankuo_config.get("_printConfigMode") == "activity"
        record_paper_size = _normalize_dm_paper_size(record.paper_size) if use_record_paper_size else None
        config_paper_size = _normalize_dm_paper_size(lankuo_config.get("dmPaperSize")) or "9"
        paper_size = record_paper_size or config_paper_size
        if record.paper_size and not use_record_paper_size:
            logger.info(
                "打印记录 %s 使用全局打印配置，已忽略记录 paper_size=%s",
                record_id,
                record.paper_size,
            )
        elif record.paper_size and not record_paper_size:
            logger.warning(
                "打印记录 %s 的 paper_size=%s 不是蓝阔纸张代码，已改用配置 dmPaperSize=%s",
                record_id,
                record.paper_size,
                config_paper_size,
            )

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                client.add_task(
                    file_url=file_url,
                    copies=record.copies,
                    paper_size=paper_size,
                )
            )
        finally:
            loop.close()

        task_id = result.get("task_id")
        if task_id:
            record.task_id = str(task_id)
            record.status = "printing"
            logger.info(f"打印记录 {record_id} 已提交蓝阔云打印，task_id={task_id}")
        else:
            record.status = "failed"
            record.error_msg = f"蓝阔API未返回task_id: {result}"
            logger.error(f"打印记录 {record_id} 蓝阔API未返回task_id: {result}")

        db.commit()

        # 确保轮询正在运行
        if _callback_url_enabled(lankuo_config):
            logger.info("Print record %s is waiting for callbackUrl status updates", record_id)
        else:
            _ensure_polling()

    except Exception as e:
        logger.error(f"调度打印任务 {record_id} 失败: {e}", exc_info=True)
        try:
            record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
            if record and record.status == "printing":
                record.status = "failed"
                record.error_msg = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _upload_canvas_image(data_url: str, db: Session, record: PrintRecord) -> Optional[str]:
    """将 base64 canvas 图片上传到存储，返回可访问的 URL"""
    try:
        import base64

        # 解析 data URL: data:image/png;base64,xxxxx
        if "," not in data_url:
            return None

        header, body = data_url.split(",", 1)
        # 提取格式
        fmt = "png"
        if "image/jpeg" in header:
            fmt = "jpg"
        elif "image/webp" in header:
            fmt = "webp"

        img_bytes = base64.b64decode(body)
        return _upload_image_bytes(img_bytes, fmt, db, record, suffix="canvas")
    except Exception as e:
        logger.error(f"上传 canvas 图片失败: {e}", exc_info=True)
        return None


def _upload_image_bytes(
    img_bytes: bytes,
    fmt: str,
    db: Session,
    record: PrintRecord,
    *,
    suffix: str,
) -> Optional[str]:
    """Upload rendered print image bytes and return a public URL."""
    try:
        from app.services.storage_service import get_storage_service

        storage_path = f"prints/{record.activity_id}/{record.id}_{suffix}.{fmt}"
        storage = get_storage_service()
        if storage is None:
            logger.error("存储服务不可用，无法上传 canvas 图片")
            return None

        loop = asyncio.new_event_loop()
        try:
            url = loop.run_until_complete(
                storage.upload_file(img_bytes, storage_path, content_type=f"image/{fmt}")
            )
        finally:
            loop.close()
        return url
    except Exception as e:
        logger.error("上传打印图片失败: %s", e, exc_info=True)
        return None


def _ensure_polling():
    """确保轮询线程正在运行"""
    global _polling_running, _polling_thread
    if _polling_running and _polling_thread and _polling_thread.is_alive():
        return

    _polling_running = True
    _polling_thread = threading.Thread(target=_polling_loop, daemon=True)
    _polling_thread.start()
    logger.info("打印状态轮询线程已启动")


def _polling_loop():
    """轮询打印任务状态，更新数据库记录"""
    global _polling_running

    while _polling_running:
        db = SessionLocal()
        try:
            # 查找所有正在打印的记录
            printing_records = db.query(PrintRecord).filter(
                PrintRecord.status == "printing",
                PrintRecord.task_id.isnot(None),
            ).all()

            if not printing_records:
                # 没有正在打印的任务，停止轮询
                _polling_running = False
                logger.info("无打印中的任务，轮询线程退出")
                return

            # 获取蓝阔配置
            from app.utils.lankuo_client import get_effective_lankuo_config, LankuoClient
            lankuo_cfg = get_effective_lankuo_config(db)
            if not lankuo_cfg:
                _polling_running = False
                return

            client = LankuoClient(lankuo_cfg)
            loop = asyncio.new_event_loop()

            for record in printing_records:
                try:
                    status_data = loop.run_until_complete(
                        client.get_task_status(record.task_id)
                    )
                    # 蓝阔 V3 API 返回 task_state 字段
                    # task_state 值: WAITING=等待, SENDING=发送中, PRINTING=正在打印, DONE=完成, ERROR=失败
                    task_state = status_data.get("task_state", "")
                    normalized_state = _normalize_lankuo_task_state(task_state)

                    if normalized_state == "success":
                        record.status = "success"
                        from datetime import datetime
                        record.printed_at = datetime.now()
                        logger.info(f"打印记录 {record.id} 打印完成")
                    elif normalized_state == "failed":
                        record.status = "failed"
                        task_result = status_data.get("task_result", {})
                        error_msg = task_result.get("msg", "打印失败") if isinstance(task_result, dict) else "打印失败"
                        record.error_msg = error_msg[:500]
                        logger.warning(f"打印记录 {record.id} 打印失败: {status_data}")
                    # WAITING / SENDING / PRINTING 继续等待
                except Exception as e:
                    logger.error(f"查询打印记录 {record.id} 状态失败: {e}")

            loop.close()
            db.commit()

        except Exception as e:
            logger.error(f"打印状态轮询异常: {e}", exc_info=True)
        finally:
            db.close()

        # 每 5 秒轮询一次
        import time
        time.sleep(5)


def start_print_polling():
    """启动打印状态轮询（应用启动时调用）"""
    _ensure_polling()


def start_print_polling_if_needed():
    """Resume polling after API restarts when callbackUrl is not configured."""
    db = SessionLocal()
    try:
        printing_count = db.query(PrintRecord).filter(
            PrintRecord.status == "printing",
            PrintRecord.task_id.isnot(None),
        ).count()
        if not printing_count:
            return

        from app.utils.lankuo_client import get_effective_lankuo_config

        lankuo_cfg = get_effective_lankuo_config(db)
        if lankuo_cfg and not _callback_url_enabled(lankuo_cfg):
            logger.info(
                "Found %s printing records without callbackUrl; resuming polling",
                printing_count,
            )
            _ensure_polling()
    finally:
        db.close()


def stop_print_polling():
    """停止打印状态轮询"""
    global _polling_running
    _polling_running = False
