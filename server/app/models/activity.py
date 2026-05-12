from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Text, Date, Enum as SAEnum, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class ActivityStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class ReadyMode(str, enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"


class ReadyStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"


class VideoStatus(str, enum.Enum):
    NONE = "none"
    UPLOADING = "uploading"
    READY = "ready"


class UploadType(str, enum.Enum):
    MANUAL = "manual"
    AUTO = "auto"


class UploadStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class StorageProvider(str, enum.Enum):
    ALIYUN = "aliyun"
    TENCENT = "tencent"
    QINIU = "qiniu"


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    MATCHED = "matched"
    UNMATCHED = "unmatched"


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[ActivityStatus] = mapped_column(
        SAEnum(ActivityStatus), default=ActivityStatus.ACTIVE
    )
    wotu_album_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    wotu_album_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    storage_path_prefix: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    ready_mode: Mapped[ReadyMode] = mapped_column(
        SAEnum(ReadyMode), default=ReadyMode.AUTO
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    programs: Mapped[List["Program"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan", order_by="Program.sequence_number"
    )
