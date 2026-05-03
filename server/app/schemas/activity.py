from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.activity import ActivityStatus, ReadyMode, ReadyStatus, VideoStatus


# ---- Activity Schemas ----

class ActivityCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    venue: Optional[str] = None
    wotu_album_id: Optional[str] = None
    wotu_album_url: Optional[str] = None
    storage_path_prefix: Optional[str] = None
    cover_image: Optional[str] = None


class ActivityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    venue: Optional[str] = None
    status: Optional[ActivityStatus] = None
    wotu_album_id: Optional[str] = None
    wotu_album_url: Optional[str] = None
    storage_path_prefix: Optional[str] = None
    cover_image: Optional[str] = None


class ActivityOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    event_date: Optional[date]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    venue: Optional[str]
    status: ActivityStatus
    wotu_album_id: Optional[str]
    wotu_album_url: Optional[str]
    storage_path_prefix: Optional[str]
    cover_image: Optional[str]
    program_count: int = 0
    ready_program_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---- Program Schemas ----

class ProgramCreate(BaseModel):
    name: str = Field(..., max_length=200)
    sequence_number: int = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    ready_mode: ReadyMode = ReadyMode.AUTO


class ProgramUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    sequence_number: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    ready_mode: Optional[ReadyMode] = None
    ready_status: Optional[ReadyStatus] = None


class ProgramOut(BaseModel):
    id: int
    access_token: str
    activity_id: int
    name: str
    sequence_number: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration: Optional[float]
    video_url: Optional[str]
    video_thumbnail_url: Optional[str] = None
    video_status: VideoStatus
    photo_count: int
    ready_mode: ReadyMode
    ready_status: ReadyStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProgramListOut(BaseModel):
    id: int
    name: str
    sequence_number: int
    video_status: VideoStatus
    photo_count: int
    ready_status: ReadyStatus

    model_config = {"from_attributes": True}


class ProgramPublicOut(BaseModel):
    """家长端公开节目信息（COZE智能体链接访问）"""
    id: int
    access_token: str
    name: str
    sequence_number: int
    activity_id: int
    video_url: Optional[str]
    video_status: VideoStatus
    photo_count: int

    model_config = {"from_attributes": True}
