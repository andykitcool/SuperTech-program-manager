from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.activity import UploadType, UploadStatus, StorageProvider


class VideoOut(BaseModel):
    id: int
    program_id: int
    activity_id: int
    filename: str
    file_size: Optional[int]
    duration: Optional[int]
    storage_url: Optional[str]
    storage_provider: StorageProvider
    upload_type: UploadType
    upload_source: Optional[str]
    status: UploadStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
