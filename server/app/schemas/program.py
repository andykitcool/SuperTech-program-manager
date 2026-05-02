from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.activity import ReadyMode


class ProgramBatchItem(BaseModel):
    """批量导入的单个节目数据"""
    name: str = Field(..., max_length=200)
    sequence_number: int = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    ready_mode: ReadyMode = ReadyMode.AUTO


class ProgramBatchCreate(BaseModel):
    """批量创建节目"""
    programs: List[ProgramBatchItem]
