from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.models.activity import StorageProvider, SyncStatus


class PhotoOut(BaseModel):
    id: int
    program_id: Optional[int]
    activity_id: int
    filename: str
    storage_url: Optional[str]
    wotu_url: Optional[str]
    storage_provider: StorageProvider
    shoot_time: Optional[datetime]
    width: Optional[int]
    height: Optional[int]
    file_size: Optional[int]
    sync_status: SyncStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class PhotoListOut(BaseModel):
    id: int
    storage_url: Optional[str]
    shoot_time: Optional[datetime]
    width: Optional[int]
    height: Optional[int]

    model_config = {"from_attributes": True}
