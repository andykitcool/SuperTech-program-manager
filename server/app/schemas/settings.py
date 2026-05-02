from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SettingsOut(BaseModel):
    id: int
    key: str
    value: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    value: str


class StorageTestResult(BaseModel):
    success: bool
    message: str


class StorageTestRequest(BaseModel):
    provider: str
