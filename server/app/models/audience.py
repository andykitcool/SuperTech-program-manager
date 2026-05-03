from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Audience(Base):
    __tablename__ = "audiences"
    __table_args__ = (
        UniqueConstraint("activity_id", "openid", name="uq_audience_activity_openid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    openid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    unionid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_ip: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_ip: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    first_client: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_client: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
