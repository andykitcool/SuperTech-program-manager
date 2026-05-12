from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DecorationMaterial(Base):
    """
    装饰素材模型
    支持三种类型：background（背景）、frame（相框）、sticker（装饰贴纸）
    """
    __tablename__ = "decoration_materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # background / frame / sticker
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    storage_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 子分类，如"生日"、"节日"
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
