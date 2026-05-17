from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.activity import StorageProvider, SyncStatus


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    program_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("programs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    wotu_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    storage_provider: Mapped[StorageProvider] = mapped_column(
        SAEnum(StorageProvider), default=StorageProvider.ALIYUN
    )
    shoot_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    wotu_photo_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, unique=True)
    wotu_category_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    wotu_category_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    sync_status: Mapped[SyncStatus] = mapped_column(
        SAEnum(SyncStatus), default=SyncStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    program = relationship("Program", back_populates="photos")
