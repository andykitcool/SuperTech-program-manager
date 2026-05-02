import os
import uuid
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.utils.auth import get_current_user
from app.models import Program, Video, Photo, Activity
from app.models.activity import UploadType, UploadStatus, StorageProvider, VideoStatus
from app.services.storage_service import get_storage_service, get_upload_token
from app.utils.video_metadata import extract_video_metadata

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_storage_key(program: Program, filename: str = "") -> str:
    """Build storage key: videos/{event_date}/{uuid}{ext}."""
    ext = os.path.splitext(filename)[1] if filename else ".mp4"
    date_str = "unknown"
    if program.activity and program.activity.event_date:
        date_str = program.activity.event_date.strftime("%Y-%m-%d")
    return f"videos/{date_str}/{uuid.uuid4().hex}{ext}"


def _extract_key_from_url(storage_url: str) -> Optional[str]:
    """Extract storage key from a full URL."""
    if not storage_url:
        return None
    storage = get_storage_service()
    if not storage:
        return None
    domain = storage.domain if hasattr(storage, 'domain') and storage.domain else ""
    key = storage_url
    if domain and key.startswith(domain + "/"):
        key = key[len(domain) + 1:]
    elif key.startswith("http"):
        from urllib.parse import urlparse
        parsed = urlparse(key)
        key = parsed.path.lstrip("/")
    # Skip files already in TEMP
    if key and not key.startswith("TEMP/"):
        return key
    return None


async def _move_to_temp(storage_url: str):
    """Move a cloud storage file to TEMP/ folder (best-effort)."""
    key = _extract_key_from_url(storage_url)
    if not key:
        return
    try:
        storage = get_storage_service()
        if not storage:
            return
        dest_key = f"TEMP/{key}"
        await storage.move_file(key, dest_key)
        logger.info(f"Moved storage file {key} -> {dest_key}")
    except Exception as e:
        logger.warning(f"Failed to move storage file {storage_url} to TEMP: {e}")


def _parse_datetime_from_filename(filename: str):
    """Parse recording start time from filename like '2026-03-29 18-00-16.mp4'.
    Returns datetime or None.
    """
    import re
    from datetime import datetime as dt_cls
    basename = os.path.splitext(filename)[0]
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2})-(\d{2})-(\d{2})", basename)
    if not m:
        return None
    try:
        return dt_cls(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6]))
    except ValueError:
        return None


async def _update_program_video_metadata(program: Program, video_url: str, filename: str = ""):
    """Extract duration and creation_time from video and update program record."""
    from datetime import timedelta
    start_dt = None
    try:
        meta = await extract_video_metadata(video_url)
        if meta.get("duration") is not None:
            program.duration = meta["duration"]
        if meta.get("creation_time"):
            try:
                ct_str = meta["creation_time"].replace("Z", "+00:00")
                from dateutil.parser import parse as parse_dt
                start_dt = parse_dt(ct_str)
                if start_dt.tzinfo is not None:
                    start_dt = start_dt.replace(tzinfo=None)
            except Exception as e:
                logger.warning(f"Failed to parse creation_time '{meta['creation_time']}': {e}")
    except Exception as e:
        logger.warning(f"Failed to extract video metadata: {e}")

    # Fallback: parse start_time from filename
    if start_dt is None and filename:
        start_dt = _parse_datetime_from_filename(filename)

    if start_dt is not None:
        program.start_time = start_dt
        if program.duration is not None:
            program.end_time = start_dt + timedelta(seconds=program.duration)


# ── Schemas ──────────────────────────────────────────────────────────

class VideoTokenRequest(BaseModel):
    program_id: int
    filename: str

class VideoTokenResponse(BaseModel):
    token: str
    key: str
    upload_url: str = "https://up.qiniup.com"

class VideoConfirmRequest(BaseModel):
    program_id: int
    key: str
    filename: str
    file_size: int


# ── Delete video ────────────────────────────────────────────────────

@router.delete("/video/{program_id}")
async def delete_video(
    program_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Delete a program's video: move cloud file to TEMP, clear DB record."""
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Move cloud file to TEMP
    if program.video_url:
        await _move_to_temp(program.video_url)

    # Delete Video record
    video = db.query(Video).filter(Video.program_id == program_id).first()
    if video:
        db.delete(video)

    # Reset program video fields
    program.video_url = None
    program.video_thumbnail_url = None
    program.video_status = VideoStatus.NONE
    program.duration = None
    program.start_time = None
    program.end_time = None

    db.commit()
    return {"status": "ok"}


# ── Client-side direct upload: get token ────────────────────────────

@router.post("/video/token", response_model=VideoTokenResponse)
async def get_video_upload_token(
    body: VideoTokenRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate a Qiniu upload token for client-side direct upload."""
    program = db.query(Program).filter(Program.id == body.program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    storage_key = _build_storage_key(program, body.filename)
    token = get_upload_token(storage_key)

    return VideoTokenResponse(token=token, key=storage_key)


# ── Client-side direct upload: confirm ──────────────────────────────

@router.post("/video/confirm")
async def confirm_video_upload(
    body: VideoConfirmRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Called by the client after a successful direct upload to Qiniu."""
    program = db.query(Program).filter(Program.id == body.program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    storage = get_storage_service()
    storage_url = storage.build_url(body.key)
    if not storage_url:
        raise HTTPException(status_code=500, detail="Failed to build storage URL")

    ext = os.path.splitext(body.filename)[1] if body.filename else ".mp4"
    video = Video(
        program_id=body.program_id,
        activity_id=program.activity_id,
        filename=body.filename or f"video_{body.program_id}{ext}",
        file_size=body.file_size,
        storage_url=storage_url,
        storage_provider=storage.provider_name,
        upload_type=UploadType.MANUAL,
        upload_source=None,
        status=UploadStatus.READY,
    )
    db.add(video)
    db.flush()

    program.video_url = storage_url
    program.video_status = VideoStatus.READY

    # Extract video metadata (duration, creation_time) in background
    await _update_program_video_metadata(program, storage_url, filename=body.filename)

    # Auto-match photos by time range
    from app.api.admin import _match_photos_to_program
    _match_photos_to_program(db, program)

    if program.ready_mode.value == "auto" and program.is_auto_ready:
        program.ready_status = "ready"

    db.commit()
    db.refresh(video)

    return {"id": video.id, "storage_url": storage_url, "status": "ready"}


# ── OBS auto-push (server-side relay, kept for OBS compatibility) ──

@router.post("/auto/{activity_id}/{program_name}")
async def auto_upload_video(
    activity_id: int,
    program_name: str,
    file: UploadFile = File(...),
    upload_source: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """API endpoint for OBS auto-push. Finds program by name+activity, uploads video."""
    program = (
        db.query(Program)
        .filter(
            Program.activity_id == activity_id,
            Program.name == program_name,
        )
        .first()
    )
    if not program:
        raise HTTPException(status_code=404, detail=f"Program '{program_name}' not found in activity {activity_id}")

    content = await file.read()
    file_size = len(content)

    storage_key = _build_storage_key(program, file.filename)
    storage = get_storage_service()
    storage_url = await storage.upload_file(content, storage_key)

    video = Video(
        program_id=program.id,
        activity_id=activity_id,
        filename=file.filename or f"video_{program.id}{os.path.splitext(file.filename or '.mp4')[1]}",
        file_size=file_size,
        storage_url=storage_url,
        storage_provider=storage.provider_name,
        upload_type=UploadType.AUTO,
        upload_source=upload_source,
        status=UploadStatus.READY,
    )
    db.add(video)
    db.flush()

    program.video_url = storage_url
    program.video_status = VideoStatus.READY

    # Extract video metadata (duration, creation_time)
    await _update_program_video_metadata(program, storage_url)

    # Auto-match photos by time range
    from app.api.admin import _match_photos_to_program
    _match_photos_to_program(db, program)

    if program.ready_mode.value == "auto" and program.is_auto_ready:
        program.ready_status = "ready"

    db.commit()

    return {"id": video.id, "storage_url": storage_url, "program_id": program.id, "status": "ready"}
