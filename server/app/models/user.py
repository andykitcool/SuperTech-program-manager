from datetime import datetime
from typing import Optional, List
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="wechat", index=True)
    username: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unionid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    assignments: Mapped[List["UserRoleAssignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    permissions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    assignments: Mapped[List["UserRoleAssignment"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "activity_id", name="uq_user_role_activity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    activity_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[AppUser] = relationship(back_populates="assignments")
    role: Mapped[Role] = relationship(back_populates="assignments")
