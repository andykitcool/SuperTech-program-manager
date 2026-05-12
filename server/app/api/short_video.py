"""Short video management API."""

import json
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.auth import get_current_user
from app.models import Program, Music, SystemSettings
from app.api.upload import _move_to_temp

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class ShortVideoGenerateRequest(BaseModel):
    program_ids: List[int]
    duration: float = 15.0
    cut_intensity: int = 2
    direction: str = "random"  # forward / backward / random
    music_id: Optional[int] = None  # specific music, or random if None


class ShortVideoAutoConfig(BaseModel):
    enabled: bool = False
    duration: float = 15.0
    cut_intensity: int = 2
    direction: str = "random"
    music_id: Optional[int] = None


class ShortVideoStatusOut(BaseModel):
    id: int
    name: str
    sequence_number: int
    video_url: Optional[str] = None
    short_video_url: Optional[str] = None
    short_video_status: str = "none"

    class Config:
        from_attributes = True


class ShortVideoBatchStatus(BaseModel):
    items: List[ShortVideoStatusOut]
    total: int


class MusicOption(BaseModel):
    id: int
    name: str
    duration: Optional[float] = None

    class Config:
        from_attributes = True


# ── API endpoints ────────────────────────────────────────────────────

@router.get("/short-video/programs/{activity_id}", response_model=ShortVideoBatchStatus)
def get_short_video_programs(
    activity_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """获取活动下所有节目的短视频状态"""
    programs = (
        db.query(Program)
        .filter(Program.activity_id == activity_id)
        .order_by(Program.sequence_number)
        .all()
    )
    return ShortVideoBatchStatus(
        items=[
            ShortVideoStatusOut(
                id=p.id,
                name=p.name,
                sequence_number=p.sequence_number,
                video_url=p.video_url,
                short_video_url=p.short_video_url,
                short_video_status=p.short_video_status or "none",
            )
            for p in programs
        ],
        total=len(programs),
    )


@router.get("/short-video/musics", response_model=List[MusicOption])
def get_music_options(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """获取可选音乐列表（用于短视频生成）"""
    musics = db.query(Music).order_by(Music.name).all()
    return [MusicOption(id=m.id, name=m.name, duration=m.duration) for m in musics]


@router.post("/short-video/generate")
async def generate_short_videos(
    data: ShortVideoGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """批量生成短视频（后台执行）"""
    # Validate programs exist and have videos
    programs = db.query(Program).filter(Program.id.in_(data.program_ids)).all()
    if not programs:
        raise HTTPException(status_code=404, detail="未找到指定节目")

    valid_programs = [p for p in programs if p.video_url]
    if not valid_programs:
        raise HTTPException(status_code=400, detail="所选节目均无原视频，无法生成短视频")

    # Validate music exists if specified
    if data.music_id:
        music = db.query(Music).filter(Music.id == data.music_id).first()
        if not music:
            raise HTTPException(status_code=404, detail="指定音乐不存在")

    # Mark programs as generating
    for p in valid_programs:
        p.short_video_status = "generating"
    db.commit()

    # Queue generation tasks
    for p in valid_programs:
        background_tasks.add_task(
            _run_generate_task,
            program_id=p.id,
            target_duration=data.duration,
            cut_intensity=data.cut_intensity,
            direction=data.direction,
            music_id=data.music_id,
        )

    return {
        "message": "已开始生成",
        "count": len(valid_programs),
        "skipped": len(programs) - len(valid_programs),
    }


async def _run_generate_task(
    program_id: int,
    target_duration: float = 15.0,
    cut_intensity: int = 2,
    direction: str = "random",
    music_id: Optional[int] = None,
):
    """Background task wrapper for short video generation."""
    from app.services.short_video_service import generate_short_video_for_program

    await generate_short_video_for_program(
        program_id=program_id,
        target_duration=target_duration,
        cut_intensity=cut_intensity,
        direction=direction,
        music_id=music_id,
    )


@router.delete("/short-video/programs/{program_id}")
async def delete_short_video(
    program_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """删除节目的短视频"""
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="节目不存在")

    if program.short_video_url:
        await _move_to_temp(program.short_video_url)

    program.short_video_url = None
    program.short_video_status = "none"
    db.commit()
    return {"message": "deleted"}


# ── Auto-generate config ────────────────────────────────────────────

def _get_auto_config_key(activity_id: int) -> str:
    return f"activity_{activity_id}_sv_auto_config"


def get_short_video_auto_config(db: Session, activity_id: int) -> ShortVideoAutoConfig:
    """Get auto-generate config for an activity (internal helper)."""
    key = _get_auto_config_key(activity_id)
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if setting and setting.value:
        try:
            data = json.loads(setting.value)
            return ShortVideoAutoConfig(**data)
        except Exception:
            pass
    return ShortVideoAutoConfig()


@router.get("/short-video/auto-config/{activity_id}", response_model=ShortVideoAutoConfig)
def get_auto_config(
    activity_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """获取活动的短视频自动生成配置"""
    return get_short_video_auto_config(db, activity_id)


@router.put("/short-video/auto-config/{activity_id}", response_model=ShortVideoAutoConfig)
def update_auto_config(
    activity_id: int,
    config: ShortVideoAutoConfig,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """更新活动的短视频自动生成配置"""
    key = _get_auto_config_key(activity_id)
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    value_json = json.dumps(config.model_dump(), ensure_ascii=False)
    if setting:
        setting.value = value_json
    else:
        setting = SystemSettings(key=key, value=value_json, description="短视频自动生成配置")
        db.add(setting)
    db.commit()
    return config


async def try_auto_generate_short_video(
    db: Session,
    program: Program,
    background_tasks: BackgroundTasks,
):
    """Check if auto-generate is enabled for the activity and trigger short video generation."""
    if not program.video_url:
        return
    if program.short_video_status in ("generating", "ready"):
        return

    config = get_short_video_auto_config(db, program.activity_id)
    if not config.enabled:
        return

    # Validate music if specified
    if config.music_id:
        music = db.query(Music).filter(Music.id == config.music_id).first()
        if not music:
            logger.warning(f"Auto-generate: music_id {config.music_id} not found, skipping")
            return

    program.short_video_status = "generating"
    db.commit()

    background_tasks.add_task(
        _run_generate_task,
        program_id=program.id,
        target_duration=config.duration,
        cut_intensity=config.cut_intensity,
        direction=config.direction,
        music_id=config.music_id,
    )
    logger.info(f"Auto-generate triggered for program {program.id} (activity {program.activity_id})")
