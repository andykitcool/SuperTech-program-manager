"""鍠斿浘鐓х墖鍚屾 API 绔偣"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Activity, Photo, SystemSettings
from app.models.sync_task import SyncTask, SyncTaskStatus
from app.schemas.photo import PhotoOut
from app.services.wotu_client import WotuServiceClient
from app.services.wotu_sync import wotu_sync_manager
from app.services.wotu_models import WotuPhotoInfo
from app.utils.auth import get_current_user
from app.utils.rbac import allowed_activity_ids, require_activity_access

router = APIRouter()

# ---- API sync mode cache (module-level, non-persistent) ----
_api_sync_cache: Dict[int, dict] = {}

BEIJING_TZ = timezone(timedelta(hours=8))
WOTU_SERVICE_URL_KEY = "wotu_service_url"
WOTU_API_KEY_KEY = "wotu_api_key"
WOTU_CALLBACK_BASE_URL_KEY = "wotu_callback_base_url"


class ApiSyncConfigUpdate(BaseModel):
    service_url: Optional[str] = None
    api_key: Optional[str] = None
    callback_base_url: Optional[str] = None


class ApiSyncConfigOut(BaseModel):
    service_url: str = ""
    api_key: str = ""
    callback_base_url: str = ""
    has_api_key: bool = False
    callback_urls: dict = Field(default_factory=dict)
    configured: bool = False


def _get_setting_value(db: Session, key: str, default: str = "") -> str:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting and setting.value is not None else default


def _set_setting_value(db: Session, key: str, value: str, description: str = "") -> None:
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        setting = SystemSettings(key=key, value=value, description=description)
        db.add(setting)
    else:
        setting.value = value
        if description:
            setting.description = description


def _load_api_sync_config(db: Session) -> dict:
    settings = get_settings()
    service_url = (_get_setting_value(db, WOTU_SERVICE_URL_KEY, "") or settings.WOTU_SERVICE_URL).strip().rstrip("/")
    api_key = (_get_setting_value(db, WOTU_API_KEY_KEY, "") or settings.WOTU_API_KEY).strip()
    callback_base_url = (
        _get_setting_value(db, WOTU_CALLBACK_BASE_URL_KEY, "") or settings.PUBLIC_API_BASE_URL
    ).strip().rstrip("/")
    return {
        "service_url": service_url,
        "api_key": api_key,
        "callback_base_url": callback_base_url,
    }


def _callback_urls(base_url: str) -> dict:
    base = base_url.strip().rstrip("/")
    if not base:
        return {"photo_uploaded": "", "task_complete": "", "task_progress": ""}
    return {
        "photo_uploaded": f"{base}/api/admin/callback/photo-uploaded",
        "task_complete": f"{base}/api/admin/callback/task-complete",
        "task_progress": f"{base}/api/admin/callback/task-progress",
    }


def _api_config_response(db: Session, request: Request) -> ApiSyncConfigOut:
    config = _load_api_sync_config(db)
    callback_base_url = config["callback_base_url"] or str(request.base_url).rstrip("/")
    return ApiSyncConfigOut(
        service_url=config["service_url"],
        api_key="",
        callback_base_url=config["callback_base_url"],
        has_api_key=bool(config["api_key"]),
        callback_urls=_callback_urls(callback_base_url),
        configured=bool(config["service_url"] and config["api_key"] and config["callback_base_url"]),
    )


def _require_api_sync_config(db: Session, request: Request) -> dict:
    config = _load_api_sync_config(db)
    missing = []
    if not config["service_url"]:
        missing.append("API 服务地址")
    if not config["api_key"]:
        missing.append("API 密钥")
    if not config["callback_base_url"]:
        missing.append("回调 URL")
    if missing:
        raise HTTPException(status_code=500, detail=f"API 同步配置不完整：{', '.join(missing)}")
    return config


def _update_api_cache(task_id: int, data: dict):
    """Update in-memory progress cache for API sync mode."""
    existing = _api_sync_cache.get(task_id, {})
    existing.update(data)
    existing["updated_at"] = datetime.now(BEIJING_TZ).strftime("%H:%M:%S")
    _api_sync_cache[task_id] = existing


def _verify_callback_key(
    x_api_key: str = Header("", alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Dependency: verify API Key on callback endpoints."""
    api_key = _load_api_sync_config(db)["api_key"]
    if not api_key:
        raise HTTPException(status_code=500, detail="Wotu API key is not configured")
    if x_api_key != api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")


class SyncStartRequest(BaseModel):
    activity_id: int
    url: str
    concurrency: int = 5
    scroll_delay: int = 5
    no_new_stop_rounds: int = 3
    tab_mode: str = "current"       # "current" | "all"
    tab_subdir: bool = True
    selected_categories: List[dict] = []
    sync_mode: Optional[str] = None  # "local" | "api", None = auto-detect from activity


class AlbumInfoRequest(BaseModel):
    url: str


class SyncModeRequest(BaseModel):
    activity_id: int
    sync_mode: str  # "local" | "api"


@router.get("/sync/api-config", response_model=ApiSyncConfigOut)
def get_api_sync_config(
    request: Request,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Return the remote Wotu API sync configuration without exposing the secret."""
    return _api_config_response(db, request)


@router.put("/sync/api-config", response_model=ApiSyncConfigOut)
def update_api_sync_config(
    data: ApiSyncConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Persist remote Wotu API sync configuration in system settings."""
    if data.service_url is not None:
        _set_setting_value(db, WOTU_SERVICE_URL_KEY, data.service_url.strip().rstrip("/"), "喔图 API 同步服务地址")
    if data.api_key is not None:
        _set_setting_value(db, WOTU_API_KEY_KEY, data.api_key.strip(), "喔图 API 同步共享密钥")
    if data.callback_base_url is not None:
        _set_setting_value(
            db,
            WOTU_CALLBACK_BASE_URL_KEY,
            data.callback_base_url.strip().rstrip("/"),
            "喔图 API 同步回调公网地址",
        )
    db.commit()
    return _api_config_response(db, request)


@router.post("/sync/album-info")
async def album_info(
    data: AlbumInfoRequest,
    _user: dict = Depends(get_current_user),
):
    """Fetch Wotu album total/category counts without importing photos."""
    if not data.url:
        raise HTTPException(status_code=400, detail="Album URL is required")
    try:
        return await wotu_sync_manager.inspect_album(data.url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch album info: {exc}")


@router.put("/sync/mode")
def set_sync_mode(
    data: SyncModeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Set sync mode for an activity (local/api)."""
    if data.sync_mode not in ("local", "api"):
        raise HTTPException(status_code=400, detail="sync_mode must be 'local' or 'api'")
    activity = require_activity_access(db, current_user, data.activity_id, "activity.manage")
    activity.sync_mode = data.sync_mode
    db.commit()
    return {"sync_mode": data.sync_mode}


@router.post("/sync/start")
async def start_sync(
    data: SyncStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Start photo sync. Dispatches to local or API mode based on sync_mode field."""
    activity = require_activity_access(db, current_user, data.activity_id, "activity.manage")
    if data.sync_mode in ("local", "api"):
        sync_mode = data.sync_mode
    else:
        sync_mode = getattr(activity, "sync_mode", None) or "local"

    if sync_mode == "api":
        return await _start_api_sync(data, activity, db, request)
    else:
        return _start_local_sync(data, activity, db)


def _start_local_sync(data: SyncStartRequest, activity, db: Session) -> dict:
    """Start local WotuSyncManager sync (existing logic)."""
    if wotu_sync_manager.running:
        raise HTTPException(status_code=400, detail="Sync task is already running")

    storage_prefix = activity.storage_path_prefix or f"activities/{activity.id}"

    ok, msg = wotu_sync_manager.start_sync(
        activity_id=data.activity_id,
        url=data.url,
        concurrency=data.concurrency,
        scroll_delay=data.scroll_delay,
        no_new_stop_rounds=data.no_new_stop_rounds,
        tab_mode=data.tab_mode,
        tab_subdir=data.tab_subdir,
        selected_categories=data.selected_categories,
        storage_path_prefix=storage_prefix,
        activity_name=activity.name,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


async def _start_api_sync(data: SyncStartRequest, activity, db: Session, request: Request) -> dict:
    """Start sync via wotu-getphoto-by-deepseek service."""
    if wotu_sync_manager.running:
        raise HTTPException(status_code=400, detail="鏈湴鍚屾浠诲姟姝ｅ湪杩愯涓紝璇峰厛鍋滄")

    # Check existing running API sync tasks for this activity
    running_api = db.query(SyncTask).filter(
        SyncTask.activity_id == data.activity_id,
        SyncTask.status == SyncTaskStatus.RUNNING,
    ).first()
    if running_api:
        raise HTTPException(status_code=400, detail="This activity already has a running API sync task")

    api_config = _require_api_sync_config(db, request)

    storage_prefix = activity.storage_path_prefix or f"activities/{activity.id}"
    config = {
        "concurrency": data.concurrency,
        "scroll_delay": data.scroll_delay,
        "no_new_stop_rounds": data.no_new_stop_rounds,
        "tab_mode": data.tab_mode,
        "selected_categories": data.selected_categories,
        "storage_path_prefix": storage_prefix,
    }

    # Create sync task record
    import json
    task = SyncTask(
        activity_id=data.activity_id,
        activity_name=activity.name,
        wotu_album_url=data.url,
        status=SyncTaskStatus.RUNNING,
        config_json=json.dumps(config, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    callback_urls = _callback_urls(api_config["callback_base_url"])

    try:
        client = WotuServiceClient(
            base_url=api_config["service_url"],
            api_key=api_config["api_key"],
        )
        try:
            result = await client.start_sync(
                task_id=task.id,
                activity_id=data.activity_id,
                url=data.url,
                config=config,
                callback_urls=callback_urls,
                api_key=api_config["api_key"],
            )
        finally:
            await client.close()
        _update_api_cache(task.id, {"phase": "scraping", "task_id": task.id})
        return {"message": "API sync task submitted", "task_id": task.id, "remote": result}
    except Exception as exc:
        task.status = SyncTaskStatus.FAILED
        task.error_msg = f"Remote sync service call failed: {exc}"
        task.finished_at = datetime.now()
        db.commit()
        raise HTTPException(status_code=502, detail=f"Remote sync service call failed: {exc}")


@router.post("/sync/stop")
async def stop_sync(
    request: Request,
    activity_id: Optional[int] = Query(None, description="Activity ID for API sync mode"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Stop sync task. For local mode stops WotuSyncManager; for API mode calls remote."""
    # Check if running in local mode first
    if wotu_sync_manager.running:
        wotu_sync_manager.stop_sync()
        return {"message": "Stop requested"}

    # Try API sync mode: find the latest running API task
    if activity_id:
        running_task = db.query(SyncTask).filter(
            SyncTask.activity_id == activity_id,
            SyncTask.status == SyncTaskStatus.RUNNING,
        ).order_by(SyncTask.id.desc()).first()
    else:
        running_task = db.query(SyncTask).filter(
            SyncTask.status == SyncTaskStatus.RUNNING,
        ).order_by(SyncTask.id.desc()).first()

    if not running_task:
        raise HTTPException(status_code=400, detail="No running sync task")

    try:
        api_config = _require_api_sync_config(db, request)
        client = WotuServiceClient(
            base_url=api_config["service_url"],
            api_key=api_config["api_key"],
        )
        try:
            result = await client.stop_sync(running_task.id)
        finally:
            await client.close()
        running_task.status = SyncTaskStatus.STOPPED
        running_task.finished_at = datetime.now()
        db.commit()
        _update_api_cache(running_task.id, {"phase": "stopped"})
        return {"message": "Remote stop requested", "task_id": running_task.id, "remote": result}
    except Exception as exc:
        logger = __import__("logging").getLogger(__name__)
        logger.warning("Failed to notify remote service: %s", exc)
        running_task.status = SyncTaskStatus.STOPPED
        running_task.finished_at = datetime.now()
        db.commit()
        return {"message": "Marked stopped locally; remote notification failed", "task_id": running_task.id}


@router.get("/sync/status")
def sync_status(
    request: Request,
    activity_id: Optional[int] = Query(None, description="Activity ID (required for API mode)"),
    task_id: Optional[int] = Query(None, description="Specific sync task ID (for API mode)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get sync status for local or API mode."""
    # Local mode status
    local_running = wotu_sync_manager.running

    if local_running:
        local_stats = wotu_sync_manager.stats
        return {
            "running": True,
            "mode": "local",
            "stats": local_stats,
            "photo_count": len(wotu_sync_manager.photos),
        }

    # API mode: check cache first, then DB
    if task_id:
        task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
    elif activity_id:
        task = db.query(SyncTask).filter(
            SyncTask.activity_id == activity_id,
        ).order_by(SyncTask.id.desc()).first()
    else:
        task = db.query(SyncTask).order_by(SyncTask.id.desc()).first()

    if task:
        cache = _api_sync_cache.get(task.id, {})
        # Check if we can get live status from remote service
        remote_stats = None
        if task.status == SyncTaskStatus.RUNNING:
            try:
                import asyncio
                api_config = _require_api_sync_config(db, request)

                async def _load_remote_status():
                    client = WotuServiceClient(
                        base_url=api_config["service_url"],
                        api_key=api_config["api_key"],
                    )
                    try:
                        return await client.get_status(task.id)
                    finally:
                        await client.close()

                remote_stats = asyncio.run(_load_remote_status())
            except Exception:
                pass

        stats = {
            "phase": cache.get("phase", task.status.value if task.status else "unknown"),
            "total_found": cache.get("total_found", task.total_found),
            "total_downloaded": cache.get("total_downloaded", task.total_downloaded),
            "total_uploaded": cache.get("total_uploaded", task.total_uploaded),
            "total_failed": cache.get("total_failed", task.total_failed),
            "total_skipped": cache.get("total_skipped", task.total_skipped),
            "total_bytes": cache.get("total_bytes", task.total_bytes),
            "current_tab": cache.get("current_tab", ""),
            "speed": cache.get("speed", 0),
            "error_msg": cache.get("error_msg") or task.error_msg or "",
        }
        if remote_stats:
            stats["remote_phase"] = remote_stats.get("phase")
            stats["remote_running"] = remote_stats.get("running", False)

        is_running = task.status == SyncTaskStatus.RUNNING
        return {
            "running": is_running,
            "mode": "api",
            "task_id": task.id,
            "stats": stats,
            "photo_count": 0,
        }

    return {"running": False, "mode": "local", "stats": {}, "photo_count": 0}


@router.get("/sync/photos")
def sync_photos(
    _user: dict = Depends(get_current_user),
):
    """鑾峰彇宸插悓姝ョ殑鐓х墖鍒楄〃"""
    return wotu_sync_manager.photos


@router.get("/sync/logs")
def sync_logs(
    _user: dict = Depends(get_current_user),
):
    """鑾峰彇鍚屾鏃ュ織"""
    return wotu_sync_manager.logs


@router.get("/sync/activities")
def sync_activities(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List active activities available for sync."""
    from datetime import date
    today = date.today()
    query = db.query(Activity).filter(
        (Activity.event_date.is_(None)) | (Activity.event_date >= today),
    )
    ids = allowed_activity_ids(current_user)
    if ids is not None:
        if not ids:
            return []
        query = query.filter(Activity.id.in_(ids))
    activities = query.order_by(Activity.event_date.desc(), Activity.created_at.desc()).all()

    result = []
    for a in activities:
        result.append({
            "id": a.id,
            "name": a.name,
            "event_date": str(a.event_date) if a.event_date else None,
            "venue": a.venue,
            "wotu_album_url": a.wotu_album_url,
            "storage_path_prefix": a.storage_path_prefix,
        })
    return result


# ---- 鍚屾鍘嗗彶 API ----

@router.get("/sync/history")
def sync_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """鑾峰彇鍚屾鍘嗗彶璁板綍"""
    from app.models.sync_task import SyncTask
    from sqlalchemy import func as sa_func

    total = db.query(sa_func.count(SyncTask.id)).scalar() or 0
    tasks = (
        db.query(SyncTask)
        .order_by(SyncTask.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    import json
    result = []
    for t in tasks:
        config = {}
        if t.config_json:
            try:
                config = json.loads(t.config_json)
            except Exception:
                pass

        # 璁＄畻鎸佺画鏃堕棿
        duration = None
        if t.started_at and t.finished_at:
            delta = (t.finished_at - t.started_at).total_seconds()
            if delta < 60:
                duration = f"{int(delta)}s"
            elif delta < 3600:
                duration = f"{int(delta // 60)}m{int(delta % 60)}s"
            else:
                h = int(delta // 3600)
                m = int((delta % 3600) // 60)
                duration = f"{h}h{m}m"

        result.append({
            "id": t.id,
            "activity_id": t.activity_id,
            "activity_name": t.activity_name,
            "wotu_album_url": t.wotu_album_url,
            "status": t.status.value if t.status else "unknown",
            "config": config,
            "total_found": t.total_found,
            "total_downloaded": t.total_downloaded,
            "total_uploaded": t.total_uploaded,
            "total_failed": t.total_failed,
            "total_skipped": t.total_skipped,
            "total_bytes": t.total_bytes,
            "error_msg": t.error_msg,
            "duration": duration,
            "started_at": str(t.started_at) if t.started_at else None,
            "finished_at": str(t.finished_at) if t.finished_at else None,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---- 鍥炶皟 API (琚?wotu-getphoto-by-deepseek 璋冪敤) ----

class CallbackPhotoUploaded(BaseModel):
    task_id: int
    activity_id: int
    wotu_photo_id: str
    filename: str
    storage_url: str
    wotu_url: str = ""
    storage_provider: str = "qiniu"
    shoot_time: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: int = 0
    wotu_category_id: Optional[str] = None
    wotu_category_name: Optional[str] = None


class CallbackTaskComplete(BaseModel):
    task_id: int
    status: str  # "completed" | "failed" | "stopped"
    total_found: int = 0
    total_downloaded: int = 0
    total_uploaded: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    total_bytes: int = 0
    error_msg: Optional[str] = None


class CallbackTaskProgress(BaseModel):
    task_id: int
    total_found: int = 0
    total_downloaded: int = 0
    total_uploaded: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    total_bytes: int = 0
    speed: float = 0
    current_tab: str = ""


@router.post("/callback/photo-uploaded")
async def callback_photo_uploaded(
    data: CallbackPhotoUploaded,
    _auth: None = Depends(_verify_callback_key),
    db: Session = Depends(get_db),
):
    """Callback: a single photo has been uploaded by wotu-getphoto-by-deepseek.
    Idempotent: skips if wotu_photo_id already exists.
    """
    # Idempotency check
    from app.models.photo import Photo
    existing = db.query(Photo).filter(Photo.wotu_photo_id == data.wotu_photo_id).first()
    if existing:
        return {"ok": True, "photo_id": existing.id, "message": "already exists"}

    # Construct WotuPhotoInfo from callback data
    photo_info = WotuPhotoInfo(
        id=data.wotu_photo_id,
        url=data.wotu_url or "",
        filename=data.filename,
        category_id=data.wotu_category_id or "",
        category_name=data.wotu_category_name or "",
        shoot_time=data.shoot_time or "",
        width=data.width or 0,
        height=data.height or 0,
        tab="",
    )

    from app.services.wotu_sync import save_photo_record
    save_photo_record(
        photo_info,
        data.activity_id,
        data.storage_url,
        data.file_size,
        storage_provider=data.storage_provider,
    )

    # Get the photo ID that was just saved
    photo = db.query(Photo).filter(Photo.wotu_photo_id == data.wotu_photo_id).first()
    photo_id = photo.id if photo else 0

    return {"ok": True, "photo_id": photo_id}


@router.post("/callback/task-complete")
async def callback_task_complete(
    data: CallbackTaskComplete,
    _auth: None = Depends(_verify_callback_key),
    db: Session = Depends(get_db),
):
    """Callback: wotu-getphoto-by-deepseek notifies that a sync task is complete."""
    try:
        new_status = SyncTaskStatus(data.status)
    except ValueError:
        new_status = SyncTaskStatus.COMPLETED if data.status == "completed" else SyncTaskStatus.FAILED

    task = db.query(SyncTask).filter(SyncTask.id == data.task_id).first()
    if task:
        # Only update if still running
        if task.status == SyncTaskStatus.RUNNING:
            task.status = new_status
            task.total_found = data.total_found
            task.total_downloaded = data.total_downloaded
            task.total_uploaded = data.total_uploaded
            task.total_failed = data.total_failed
            task.total_skipped = data.total_skipped
            task.total_bytes = data.total_bytes
            if data.error_msg:
                task.error_msg = data.error_msg
            task.finished_at = datetime.now()
            db.commit()

    _update_api_cache(data.task_id, {
        "phase": data.status,
        "total_found": data.total_found,
        "total_downloaded": data.total_downloaded,
        "total_uploaded": data.total_uploaded,
        "total_failed": data.total_failed,
        "total_skipped": data.total_skipped,
        "total_bytes": data.total_bytes,
        "error_msg": data.error_msg or "",
    })

    return {"ok": True}


@router.post("/callback/task-progress")
async def callback_task_progress(
    data: CallbackTaskProgress,
    _auth: None = Depends(_verify_callback_key),
):
    """Callback: wotu-getphoto-by-deepseek sends periodic progress updates."""
    _update_api_cache(data.task_id, {
        "phase": "scraping" if data.total_downloaded < data.total_found else "uploading",
        "total_found": data.total_found,
        "total_downloaded": data.total_downloaded,
        "total_uploaded": data.total_uploaded,
        "total_failed": data.total_failed,
        "total_skipped": data.total_skipped,
        "total_bytes": data.total_bytes,
        "speed": data.speed,
        "current_tab": data.current_tab,
    })
    return {"ok": True}


# ---- 鐓х墖绠＄悊 API ----

@router.get("/photos/activities")
def list_photo_activities(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """鑾峰彇鏈夊悓姝ョ収鐗囩殑娲诲姩鍒楄〃锛堢敤浜庣収鐗囩鐞嗗崱鐗囧睍绀猴級"""
    query = db.query(
        Activity.id,
        Activity.name,
        Activity.event_date,
        Activity.venue,
        Activity.cover_image,
        func.count(Photo.id).label("photo_count"),
    ).join(Photo, Photo.activity_id == Activity.id, isouter=True)\
     .group_by(Activity.id)\
     .having(func.count(Photo.id) > 0)
    ids = allowed_activity_ids(current_user)
    if ids is not None:
        if not ids:
            return []
        query = query.filter(Activity.id.in_(ids))
    results = query.order_by(Activity.event_date.desc(), Activity.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "event_date": str(r.event_date) if r.event_date else None,
            "venue": r.venue,
            "cover_image": r.cover_image,
            "photo_count": r.photo_count,
        }
        for r in results
    ]


@router.get("/photos/activity/{activity_id}")
def list_activity_photos(
    activity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    category_id: Optional[str] = Query(None, description="鍠斿浘鍒嗙被ID"),
    category_name: Optional[str] = Query(None, description="鍠斿浘鍒嗙被鍚嶇О"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List photos for one activity."""
    activity = require_activity_access(db, current_user, activity_id, "photo.manage")

    query = db.query(Photo).filter(Photo.activity_id == activity_id)
    if category_id:
        query = query.filter(Photo.wotu_category_id == category_id)
    elif category_name:
        query = query.filter(Photo.wotu_category_name == category_name)

    total = query.count()
    photos = query.order_by(Photo.shoot_time.desc(), Photo.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    category_rows = (
        db.query(
            Photo.wotu_category_id.label("category_id"),
            Photo.wotu_category_name.label("category_name"),
            func.count(Photo.id).label("count"),
        )
        .filter(Photo.activity_id == activity_id)
        .group_by(Photo.wotu_category_id, Photo.wotu_category_name)
        .order_by(Photo.wotu_category_name.asc())
        .all()
    )

    return {
        "activity": {
            "id": activity.id,
            "name": activity.name,
            "event_date": str(activity.event_date) if activity.event_date else None,
        },
        "photos": [
            {
                "id": p.id,
                "filename": p.filename,
                "storage_url": p.storage_url,
                "wotu_url": p.wotu_url,
                "shoot_time": str(p.shoot_time) if p.shoot_time else None,
                "width": p.width,
                "height": p.height,
                "file_size": p.file_size,
                "wotu_category_id": p.wotu_category_id,
                "wotu_category_name": p.wotu_category_name,
                "sync_status": p.sync_status.value if p.sync_status else None,
                "created_at": str(p.created_at) if p.created_at else None,
            }
            for p in photos
        ],
        "categories": [
            {
                "category_id": r.category_id or "",
                "category_name": r.category_name or "uncategorized",
                "count": r.count,
            }
            for r in category_rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class DeletePhotosRequest(BaseModel):
    photo_ids: List[int]


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """鍒犻櫎鍗曞紶鐓х墖"""
    from app.api.upload import _move_to_temp

    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    require_activity_access(db, current_user, photo.activity_id, "photo.manage")

    if photo.storage_url:
        await _move_to_temp(photo.storage_url)

    db.delete(photo)
    db.commit()
    return {"message": "deleted", "id": photo_id}


@router.post("/photos/batch-delete")
async def batch_delete_photos(
    data: DeletePhotosRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """鎵归噺鍒犻櫎鐓х墖"""
    from app.api.upload import _move_to_temp

    photos = db.query(Photo).filter(Photo.id.in_(data.photo_ids)).all()
    if not photos:
        raise HTTPException(status_code=404, detail="Photos not found")
    for photo in photos:
        require_activity_access(db, current_user, photo.activity_id, "photo.manage")

    for photo in photos:
        if photo.storage_url:
            await _move_to_temp(photo.storage_url)
        db.delete(photo)

    db.commit()
    return {"message": "deleted", "count": len(photos)}


@router.delete("/photos/activity/{activity_id}/all")
async def delete_all_activity_photos(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete all photos for one activity."""
    from app.api.upload import _move_to_temp

    require_activity_access(db, current_user, activity_id, "photo.manage")

    photos = db.query(Photo).filter(Photo.activity_id == activity_id).all()
    count = len(photos)
    for photo in photos:
        if photo.storage_url:
            await _move_to_temp(photo.storage_url)
        db.delete(photo)

    db.commit()
    return {"message": "deleted", "count": count}
