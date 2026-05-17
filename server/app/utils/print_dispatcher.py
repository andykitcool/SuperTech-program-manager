"""Print task dispatcher for Lankuo cloud printing."""

import asyncio
import json
import logging
import threading
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Photo, PrintRecord, SystemSettings
from app.utils.activity_print_settings import get_activity_print_settings

logger = logging.getLogger(__name__)

_polling_running = False
_polling_thread: Optional[threading.Thread] = None

PRINT_DISPATCH_MODE_KEY = "print_dispatch_mode"
PRINT_DISPATCH_MODE_LANKUO = "lankuo"
PRINT_DISPATCH_MODE_LOCAL_CLIENT = "local_client"
PRINT_DISPATCH_MODE_DISABLED = "disabled"


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
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text if text.isdigit() else None


def get_print_dispatch_mode(db: Session, activity_id: Optional[int] = None) -> str:
    allowed = {PRINT_DISPATCH_MODE_LANKUO, PRINT_DISPATCH_MODE_LOCAL_CLIENT, PRINT_DISPATCH_MODE_DISABLED}
    if activity_id:
        mode = str(get_activity_print_settings(db, activity_id).get("print_dispatch_mode") or PRINT_DISPATCH_MODE_LANKUO).strip()
        return mode if mode in allowed else PRINT_DISPATCH_MODE_LANKUO

    setting = db.query(SystemSettings).filter(SystemSettings.key == PRINT_DISPATCH_MODE_KEY).first()
    mode = (setting.value if setting and setting.value else PRINT_DISPATCH_MODE_LANKUO).strip()
    return mode if mode in allowed else PRINT_DISPATCH_MODE_LANKUO


def should_dispatch_lankuo(db: Session, lankuo_config: Optional[dict], activity_id: Optional[int] = None) -> bool:
    return bool(lankuo_config) and get_print_dispatch_mode(db, activity_id) == PRINT_DISPATCH_MODE_LANKUO


def dispatch_print_task(record_id: int, lankuo_config: dict, db: Session = None):
    del db
    thread = threading.Thread(target=lambda: _do_dispatch(record_id, lankuo_config), daemon=True)
    thread.start()


def _do_dispatch(record_id: int, lankuo_config: dict):
    db = SessionLocal()
    try:
        record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
        if not record:
            logger.error("Print record %s does not exist", record_id)
            return

        photo = db.query(Photo).filter(Photo.id == record.photo_id).first() if record.photo_id else None
        original_photo_url = (photo.storage_url or photo.wotu_url) if photo else None
        file_url = _extract_frontend_rendered_image(db, record) or record.print_image_url or original_photo_url

        if not file_url:
            logger.error("Print record %s has no printable image URL", record_id)
            record.status = "failed"
            record.error_msg = "没有可打印的图片URL"
            db.commit()
            return

        record.print_image_url = file_url

        from app.utils.lankuo_client import LankuoClient

        client = LankuoClient(lankuo_config)
        use_record_paper_size = lankuo_config.get("_printConfigMode") == "activity"
        record_paper_size = _normalize_dm_paper_size(record.paper_size) if use_record_paper_size else None
        config_paper_size = _normalize_dm_paper_size(lankuo_config.get("dmPaperSize")) or "9"
        paper_size = record_paper_size or config_paper_size

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
            logger.info("Print record %s submitted to Lankuo, task_id=%s", record_id, task_id)
        else:
            record.status = "failed"
            record.error_msg = f"蓝阔API未返回task_id: {result}"
            logger.error("Lankuo did not return task_id for print record %s: %s", record_id, result)

        db.commit()

        if _callback_url_enabled(lankuo_config):
            logger.info("Print record %s is waiting for callbackUrl status updates", record_id)
        else:
            _ensure_polling()

    except Exception as exc:
        logger.error("Failed to dispatch print record %s: %s", record_id, exc, exc_info=True)
        try:
            record = db.query(PrintRecord).filter(PrintRecord.id == record_id).first()
            if record and record.status == "printing":
                record.status = "failed"
                record.error_msg = str(exc)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _extract_frontend_rendered_image(db: Session, record: PrintRecord) -> Optional[str]:
    del db
    if not record.print_payload_json:
        return None
    try:
        payload = json.loads(record.print_payload_json)
    except Exception as exc:
        logger.error("Failed to parse print payload for record %s: %s", record.id, exc, exc_info=True)
        return None

    canvas_image = payload.get("_canvas_image")
    if not isinstance(canvas_image, str):
        return None
    if canvas_image.startswith("data:"):
        return _upload_canvas_image(canvas_image, record)
    if canvas_image.startswith(("http://", "https://", "/uploads/")):
        return canvas_image
    return None


def _upload_canvas_image(data_url: str, record: PrintRecord) -> Optional[str]:
    try:
        import base64

        if "," not in data_url:
            return None

        header, body = data_url.split(",", 1)
        fmt = "png"
        if "image/jpeg" in header:
            fmt = "jpg"
        elif "image/webp" in header:
            fmt = "webp"

        image_bytes = base64.b64decode(body)
        return _upload_image_bytes(image_bytes, fmt, record)
    except Exception as exc:
        logger.error("Failed to upload canvas image: %s", exc, exc_info=True)
        return None


def _upload_image_bytes(image_bytes: bytes, fmt: str, record: PrintRecord) -> Optional[str]:
    try:
        from app.services.storage_service import get_storage_service

        storage = get_storage_service()
        if storage is None:
            logger.error("Storage service is unavailable; cannot upload print image")
            return None

        storage_path = f"prints/{record.activity_id}/{record.id}_canvas.{fmt}"
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                storage.upload_file(image_bytes, storage_path, content_type=f"image/{fmt}")
            )
        finally:
            loop.close()
    except Exception as exc:
        logger.error("Failed to upload print image: %s", exc, exc_info=True)
        return None


def _ensure_polling():
    global _polling_running, _polling_thread
    if _polling_running and _polling_thread and _polling_thread.is_alive():
        return

    _polling_running = True
    _polling_thread = threading.Thread(target=_polling_loop, daemon=True)
    _polling_thread.start()
    logger.info("Print status polling thread started")


def _polling_loop():
    global _polling_running

    while _polling_running:
        db = SessionLocal()
        try:
            printing_records = db.query(PrintRecord).filter(
                PrintRecord.status == "printing",
                PrintRecord.task_id.isnot(None),
            ).all()

            if not printing_records:
                _polling_running = False
                logger.info("No printing records remain; polling thread exits")
                return

            from app.utils.lankuo_client import LankuoClient, get_effective_lankuo_config

            lankuo_cfg = get_effective_lankuo_config(db)
            if not lankuo_cfg:
                _polling_running = False
                return

            client = LankuoClient(lankuo_cfg)
            loop = asyncio.new_event_loop()
            try:
                for record in printing_records:
                    try:
                        status_data = loop.run_until_complete(client.get_task_status(record.task_id))
                        normalized_state = _normalize_lankuo_task_state(status_data.get("task_state", ""))

                        if normalized_state == "success":
                            from datetime import datetime

                            record.status = "success"
                            record.printed_at = datetime.now()
                            logger.info("Print record %s completed", record.id)
                        elif normalized_state == "failed":
                            record.status = "failed"
                            task_result = status_data.get("task_result", {})
                            error_msg = task_result.get("msg", "打印失败") if isinstance(task_result, dict) else "打印失败"
                            record.error_msg = error_msg[:500]
                            logger.warning("Print record %s failed: %s", record.id, status_data)
                    except Exception as exc:
                        logger.error("Failed to query print record %s status: %s", record.id, exc)
            finally:
                loop.close()

            db.commit()

        except Exception as exc:
            logger.error("Print status polling failed: %s", exc, exc_info=True)
        finally:
            db.close()

        import time

        time.sleep(5)


def start_print_polling():
    _ensure_polling()


def start_print_polling_if_needed():
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
            logger.info("Found %s printing records without callbackUrl; resuming polling", printing_count)
            _ensure_polling()
    finally:
        db.close()


def stop_print_polling():
    global _polling_running
    _polling_running = False
