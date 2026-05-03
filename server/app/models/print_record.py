from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PrintRecord(Base):
    __tablename__ = "print_records"

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
    source_record_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    user_identifier: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    template_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    paper_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    print_payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_msg: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    printed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
