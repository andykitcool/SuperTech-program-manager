import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.utils.auth import get_current_user
from app.models import Music
from app.services.storage_service import get_storage_service
from app.api.upload import _move_to_temp

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class MusicOut(BaseModel):
    id: int
    name: str
    duration: Optional[float] = None
    filename: str
    file_size: Optional[int] = None
    storage_url: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class MusicListResponse(BaseModel):
    items: list[MusicOut]
    total: int
    page: int
    page_size: int


# ── DB migration ─────────────────────────────────────────────────────

def _ensure_musics_table():
    """Create musics table if not exists (for existing databases)."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        result = db.execute(text("SHOW TABLES LIKE 'musics'"))
        if not result.fetchone():
            db.execute(text("""
                CREATE TABLE musics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL COMMENT '音乐名称',
                    duration FLOAT NULL COMMENT '时长(秒)',
                    filename VARCHAR(512) NOT NULL COMMENT '原始文件名',
                    file_size INT NULL COMMENT '文件大小(字节)',
                    storage_url VARCHAR(1024) NULL COMMENT '云端存储地址',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            db.commit()
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────

def _build_music_storage_key(filename: str) -> str:
    """Build storage key: musics/{uuid}{ext}."""
    ext = os.path.splitext(filename)[1] if filename else ".mp3"
    return f"musics/{uuid.uuid4().hex}{ext}"


def _extract_audio_duration(file_content: bytes, filename: str) -> Optional[float]:
    """Extract audio duration from file content using mutagen or ffprobe."""
    try:
        from mutagen import File as MutagenFile
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        try:
            audio = MutagenFile(tmp_path)
            if audio is not None and hasattr(audio.info, 'length'):
                return round(audio.info.length, 1)
        finally:
            os.unlink(tmp_path)
    except ImportError:
        logger.info("mutagen not installed, trying ffprobe")
    except Exception as e:
        logger.warning(f"mutagen failed: {e}")

    # Fallback: ffprobe
    try:
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", tmp_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return round(float(result.stdout.strip()), 1)
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")

    return None


# ── API endpoints ────────────────────────────────────────────────────

@router.get("/musics", response_model=MusicListResponse)
def list_musics(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """获取音乐列表"""
    total = db.query(Music).count()
    musics = (
        db.query(Music)
        .order_by(Music.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return MusicListResponse(
        items=[MusicOut(
            id=m.id,
            name=m.name,
            duration=m.duration,
            filename=m.filename,
            file_size=m.file_size,
            storage_url=m.storage_url,
            created_at=m.created_at.isoformat() if m.created_at else "",
        ) for m in musics],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/musics/upload", response_model=MusicOut)
async def upload_music(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """上传音乐文件"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # Validate file extension
    allowed_exts = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，仅支持 {', '.join(allowed_exts)}")

    content = await file.read()
    file_size = len(content)

    # Upload to cloud storage
    storage_key = _build_music_storage_key(file.filename)
    storage = get_storage_service()
    if not storage:
        raise HTTPException(status_code=500, detail="存储服务未配置")
    storage_url = await storage.upload_file(content, storage_key)

    # Extract duration
    duration = _extract_audio_duration(content, file.filename)

    # Save to DB
    music_name = name or os.path.splitext(file.filename)[0]
    music = Music(
        name=music_name,
        duration=duration,
        filename=file.filename,
        file_size=file_size,
        storage_url=storage_url,
    )
    db.add(music)
    db.commit()
    db.refresh(music)

    return MusicOut(
        id=music.id,
        name=music.name,
        duration=music.duration,
        filename=music.filename,
        file_size=music.file_size,
        storage_url=music.storage_url,
        created_at=music.created_at.isoformat() if music.created_at else "",
    )


@router.delete("/musics/{music_id}")
async def delete_music(
    music_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """删除音乐"""
    music = db.query(Music).filter(Music.id == music_id).first()
    if not music:
        raise HTTPException(status_code=404, detail="音乐不存在")

    if music.storage_url:
        await _move_to_temp(music.storage_url)

    db.delete(music)
    db.commit()
    return {"message": "deleted", "id": music_id}
