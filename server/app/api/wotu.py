"""喔图照片同步 API 端点"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.utils.auth import get_current_user
from app.services.wotu_sync import wotu_sync_manager
from app.models import Activity, Photo
from app.schemas.photo import PhotoOut

router = APIRouter()


class SyncStartRequest(BaseModel):
    activity_id: int
    url: str
    concurrency: int = 5
    scroll_delay: int = 5
    tab_mode: str = "current"       # "current" | "all"
    tab_subdir: bool = True


@router.post("/sync/start")
def start_sync(
    data: SyncStartRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """启动喔图照片同步"""
    if wotu_sync_manager.running:
        raise HTTPException(status_code=400, detail="任务正在运行中")

    activity = db.query(Activity).filter(Activity.id == data.activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    storage_prefix = activity.storage_path_prefix or f"activities/{activity.id}"

    ok, msg = wotu_sync_manager.start_sync(
        activity_id=data.activity_id,
        url=data.url,
        concurrency=data.concurrency,
        scroll_delay=data.scroll_delay,
        tab_mode=data.tab_mode,
        tab_subdir=data.tab_subdir,
        storage_path_prefix=storage_prefix,
        activity_name=activity.name,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@router.post("/sync/stop")
def stop_sync(
    _user: dict = Depends(get_current_user),
):
    """停止同步任务"""
    wotu_sync_manager.stop_sync()
    return {"message": "已发送停止请求"}


@router.get("/sync/status")
def sync_status(
    _user: dict = Depends(get_current_user),
):
    """获取同步状态"""
    return {
        "running": wotu_sync_manager.running,
        "stats": wotu_sync_manager.stats,
        "photo_count": len(wotu_sync_manager.photos),
    }


@router.get("/sync/photos")
def sync_photos(
    _user: dict = Depends(get_current_user),
):
    """获取已同步的照片列表"""
    return wotu_sync_manager.photos


@router.get("/sync/logs")
def sync_logs(
    _user: dict = Depends(get_current_user),
):
    """获取同步日志"""
    return wotu_sync_manager.logs


@router.get("/sync/activities")
def sync_activities(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """获取所有未过期活动列表（用于选择）"""
    from datetime import date
    today = date.today()
    activities = db.query(Activity).filter(
        (Activity.event_date.is_(None)) | (Activity.event_date >= today),
    ).order_by(Activity.event_date.desc(), Activity.created_at.desc()).all()

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


# ---- 同步历史 API ----

@router.get("/sync/history")
def sync_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """获取同步历史记录"""
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

        # 计算持续时间
        duration = None
        if t.started_at and t.finished_at:
            delta = (t.finished_at - t.started_at).total_seconds()
            if delta < 60:
                duration = f"{int(delta)}秒"
            elif delta < 3600:
                duration = f"{int(delta // 60)}分{int(delta % 60)}秒"
            else:
                h = int(delta // 3600)
                m = int((delta % 3600) // 60)
                duration = f"{h}时{m}分"

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


# ---- 照片管理 API ----

@router.get("/photos/activities")
def list_photo_activities(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """获取有同步照片的活动列表（用于照片管理卡片展示）"""
    results = db.query(
        Activity.id,
        Activity.name,
        Activity.event_date,
        Activity.venue,
        Activity.cover_image,
        func.count(Photo.id).label("photo_count"),
    ).join(Photo, Photo.activity_id == Activity.id, isouter=True)\
     .group_by(Activity.id)\
     .having(func.count(Photo.id) > 0)\
     .order_by(Activity.event_date.desc(), Activity.created_at.desc())\
     .all()

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
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """获取指定活动的照片列表"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    total = db.query(func.count(Photo.id)).filter(Photo.activity_id == activity_id).scalar() or 0
    photos = (
        db.query(Photo)
        .filter(Photo.activity_id == activity_id)
        .order_by(Photo.shoot_time.desc(), Photo.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
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
                "sync_status": p.sync_status.value if p.sync_status else None,
                "created_at": str(p.created_at) if p.created_at else None,
            }
            for p in photos
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
