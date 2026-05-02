import secrets
import string
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, func, Enum as SAEnum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.activity import ReadyMode, ReadyStatus, VideoStatus


def _generate_access_token(length: int = 12) -> str:
    """Generate a random access token (lowercase letters + digits)."""
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    access_token: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, default=_generate_access_token)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    video_status: Mapped[VideoStatus] = mapped_column(
        SAEnum(VideoStatus), default=VideoStatus.NONE
    )
    photo_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ready_mode: Mapped[ReadyMode] = mapped_column(
        SAEnum(ReadyMode), default=ReadyMode.AUTO
    )
    ready_status: Mapped[ReadyStatus] = mapped_column(
        SAEnum(ReadyStatus), default=ReadyStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    activity: Mapped["Activity"] = relationship(back_populates="programs")
    videos: Mapped[List["Video"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
    photos: Mapped[List["Photo"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )

    @property
    def is_auto_ready(self) -> bool:
        return (
            self.ready_mode == ReadyMode.AUTO
            and self.video_status == VideoStatus.READY
            and self.photo_count >= 1
        )


# Avoid circular import - import here
from app.models.video import Video
from app.models.photo import Photo
