from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DownloadRecord(Base):
    """
    下载记录模型
    记录用户下载照片的行为，用于个人中心展示
    """
    __tablename__ = "download_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("programs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    photo_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("photos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_identifier: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # openid
    user_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # 下载时的图片URL
    program_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 冗余存储便于展示
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
