from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.activity import UploadType, UploadStatus, StorageProvider


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    storage_provider: Mapped[StorageProvider] = mapped_column(
        SAEnum(StorageProvider), default=StorageProvider.ALIYUN
    )
    upload_type: Mapped[UploadType] = mapped_column(
        SAEnum(UploadType), default=UploadType.MANUAL
    )
    upload_source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[UploadStatus] = mapped_column(
        SAEnum(UploadStatus), default=UploadStatus.UPLOADING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    program = relationship("Program", back_populates="videos")
