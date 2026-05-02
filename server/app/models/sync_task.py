import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey, Text, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SyncTaskStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class SyncTask(Base):
    __tablename__ = "sync_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    activity_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    wotu_album_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[SyncTaskStatus] = mapped_column(
        SAEnum(SyncTaskStatus), default=SyncTaskStatus.RUNNING
    )

    # 配置参数 (JSON 字符串)
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 统计结果
    total_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_downloaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_uploaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # 错误信息
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
