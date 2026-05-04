import os
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional, Any
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


class DesktopUploadInitRequest(BaseModel):
    activity_id: int
    program_id: Optional[int] = None
    program_number: Optional[int] = None
    program_name: Optional[str] = None
    filename: str
    file_size: int
    recorded_at: Optional[datetime] = None
    source: Optional[str] = "supertech-AutoUploadVideo"


class DesktopUploadInitResponse(BaseModel):
    upload_id: str
    storage_key: str
    provider: str
    program_id: int
    program_name: str
    program_sequence_number: int
    upload_url: Optional[str] = None
    upload_token: Optional[str] = None
    resume_config: dict[str, Any] = {}
    supported: bool = True
    unsupported_reason: Optional[str] = None


class DesktopUploadCompleteRequest(BaseModel):
    upload_id: str
    activity_id: int
    program_id: Optional[int] = None
    program_number: Optional[int] = None
    program_name: Optional[str] = None
    storage_key: str
    filename: str
    file_size: int
    etag: Optional[str] = None
    file_hash: Optional[str] = None
    recorded_at: Optional[datetime] = None
    source: Optional[str] = "supertech-AutoUploadVideo"


class DesktopUploadAbortRequest(BaseModel):
    upload_id: str
    storage_key: Optional[str] = None
    provider_upload_id: Optional[str] = None
    reason: Optional[str] = None


class DesktopVideoOut(BaseModel):
    id: int
    activity_id: int
    program_id: int
    program_name: str
    program_sequence_number: int
    filename: str
    file_size: Optional[int]
    recorded_at: Optional[datetime] = None
    storage_url: Optional[str]
    storage_provider: str
    upload_type: str
    upload_source: Optional[str]
    status: str
    created_at: datetime


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


# ── Desktop direct-to-cloud upload ──────────────────────────────────

def _apply_recorded_at(program: Program, recorded_at: Optional[datetime]):
    if not recorded_at:
        return
    program.start_time = recorded_at
    if program.duration is not None:
        program.end_time = recorded_at + timedelta(seconds=program.duration)


def _resolve_desktop_program(
    db: Session,
    activity_id: int,
    program_id: Optional[int] = None,
    program_number: Optional[int] = None,
    program_name: Optional[str] = None,
) -> tuple[Program, bool]:
    parsed_name = program_name.strip() if program_name else ""
    program: Optional[Program] = None

    if program_number is not None:
        program = (
            db.query(Program)
            .filter(
                Program.activity_id == activity_id,
                Program.sequence_number == program_number,
            )
            .first()
        )

    if not program and program_id is not None:
        program = (
            db.query(Program)
            .filter(
                Program.id == program_id,
                Program.activity_id == activity_id,
            )
            .first()
        )

    if not program and parsed_name:
        program = (
            db.query(Program)
            .filter(
                Program.activity_id == activity_id,
                Program.name == parsed_name,
            )
            .first()
        )

    changed = False
    if program:
        if parsed_name and program.name != parsed_name:
            program.name = parsed_name
            changed = True
        return program, changed

    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if program_number is None:
        max_sequence = (
            db.query(func.max(Program.sequence_number))
            .filter(Program.activity_id == activity_id)
            .scalar()
        ) or 0
        program_number = max_sequence + 1

    program = Program(
        activity_id=activity_id,
        sequence_number=program_number,
        name=parsed_name or f"节目{program_number:03d}",
    )
    db.add(program)
    db.flush()
    return program, True


def _build_desktop_video_out(video: Video) -> DesktopVideoOut:
    program = video.program
    return DesktopVideoOut(
        id=video.id,
        activity_id=video.activity_id,
        program_id=video.program_id,
        program_name=program.name if program else "",
        program_sequence_number=program.sequence_number if program else 0,
        filename=video.filename,
        file_size=video.file_size,
        recorded_at=video.recorded_at,
        storage_url=video.storage_url,
        storage_provider=video.storage_provider.value if hasattr(video.storage_provider, "value") else str(video.storage_provider),
        upload_type=video.upload_type.value if hasattr(video.upload_type, "value") else str(video.upload_type),
        upload_source=video.upload_source,
        status=video.status.value if hasattr(video.status, "value") else str(video.status),
        created_at=video.created_at,
    )


@router.post("/desktop/init", response_model=DesktopUploadInitResponse)
async def init_desktop_upload(
    body: DesktopUploadInitRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Create a desktop upload session and return cloud direct-upload credentials."""
    program, changed = _resolve_desktop_program(
        db,
        activity_id=body.activity_id,
        program_id=body.program_id,
        program_number=body.program_number,
        program_name=body.program_name,
    )
    if changed:
        db.commit()
        db.refresh(program)

    storage = get_storage_service()
    provider = storage.provider_name if storage else ""
    storage_key = _build_storage_key(program, body.filename)
    upload_id = uuid.uuid4().hex

    if provider == "qiniu":
        return DesktopUploadInitResponse(
            upload_id=upload_id,
            storage_key=storage_key,
            provider=provider,
            program_id=program.id,
            program_name=program.name,
            program_sequence_number=program.sequence_number,
            upload_url="https://up.qiniup.com",
            upload_token=get_upload_token(storage_key, expires=24 * 3600),
            resume_config={
                "part_size": 4 * 1024 * 1024,
                "concurrency": 4,
                "resume_record_key": f"{upload_id}.progress",
            },
        )

    return DesktopUploadInitResponse(
        upload_id=upload_id,
        storage_key=storage_key,
        provider=provider or "unknown",
        program_id=program.id,
        program_name=program.name,
        program_sequence_number=program.sequence_number,
        supported=False,
        unsupported_reason=(
            f"Storage provider '{provider or 'unknown'}' is configured on the server, "
            "but temporary desktop direct-upload credentials are not available. "
            "Configure STS/CAM credentials before enabling this provider for desktop upload."
        ),
    )


@router.post("/desktop/complete", response_model=DesktopVideoOut)
async def complete_desktop_upload(
    body: DesktopUploadCompleteRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Register a desktop direct-uploaded video after cloud upload succeeds."""
    program, _changed = _resolve_desktop_program(
        db,
        activity_id=body.activity_id,
        program_id=body.program_id,
        program_number=body.program_number,
        program_name=body.program_name,
    )

    storage = get_storage_service()
    storage_url = storage.build_url(body.storage_key) if storage else ""
    if not storage_url:
        raise HTTPException(status_code=500, detail="Failed to build storage URL")

    video = Video(
        program_id=program.id,
        activity_id=body.activity_id,
        filename=body.filename,
        file_size=body.file_size,
        recorded_at=body.recorded_at,
        storage_url=storage_url,
        storage_provider=storage.provider_name,
        upload_type=UploadType.AUTO,
        upload_source=body.source or "supertech-AutoUploadVideo",
        status=UploadStatus.READY,
    )
    db.add(video)
    db.flush()

    program.video_url = storage_url
    program.video_status = VideoStatus.READY
    await _update_program_video_metadata(program, storage_url, filename=body.filename)
    _apply_recorded_at(program, body.recorded_at)
    if program.duration is not None:
        video.duration = int(round(program.duration))
    video.recorded_at = body.recorded_at or program.start_time

    from app.api.admin import _match_photos_to_program
    _match_photos_to_program(db, program)

    if program.ready_mode.value == "auto" and program.is_auto_ready:
        program.ready_status = "ready"

    db.commit()
    db.refresh(video)
    return _build_desktop_video_out(video)


@router.post("/desktop/abort")
async def abort_desktop_upload(
    body: DesktopUploadAbortRequest,
    _user: dict = Depends(get_current_user),
):
    """Record a desktop upload abort. Cloud multipart cleanup is provider-specific."""
    return {
        "status": "aborted",
        "upload_id": body.upload_id,
        "storage_key": body.storage_key,
    }


@router.get("/desktop/videos", response_model=list[DesktopVideoOut])
def list_desktop_videos(
    activity_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    videos = (
        db.query(Video)
        .filter(Video.activity_id == activity_id)
        .order_by(Video.created_at.desc())
        .all()
    )
    return [_build_desktop_video_out(video) for video in videos]


@router.delete("/desktop/videos/{video_id}")
async def delete_desktop_video(
    video_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    program = video.program
    storage_url = video.storage_url
    if storage_url:
        await _move_to_temp(storage_url)

    db.delete(video)
    db.flush()

    if program and program.video_url == storage_url:
        latest_video = (
            db.query(Video)
            .filter(
                Video.program_id == program.id,
                Video.status == UploadStatus.READY,
            )
            .order_by(Video.created_at.desc())
            .first()
        )
        if latest_video:
            program.video_url = latest_video.storage_url
            program.video_status = VideoStatus.READY
            program.duration = latest_video.duration
            program.start_time = latest_video.recorded_at
            program.end_time = (
                latest_video.recorded_at + timedelta(seconds=latest_video.duration)
                if latest_video.recorded_at and latest_video.duration is not None
                else None
            )
        else:
            program.video_url = None
            program.video_status = VideoStatus.NONE
            program.duration = None
            program.start_time = None
            program.end_time = None
            if program.ready_mode.value == "auto":
                program.ready_status = "pending"

    db.commit()
    return {"status": "deleted"}


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
