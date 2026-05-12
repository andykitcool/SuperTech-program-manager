from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Music(TimestampMixin, Base):
    __tablename__ = "musics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="音乐名称")
    duration: Mapped[float | None] = mapped_column(Float, nullable=True, comment="时长(秒)")
    filename: Mapped[str] = mapped_column(String(512), nullable=False, comment="原始文件名")
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="文件大小(字节)")
    storage_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="云端存储地址")
