"""SQLAlchemy ORM models for the RAWK database."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Float, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.database import Base


class MemoryORM(Base):
    """Represents a memory (recorded meeting) in the database."""

    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    audio_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="uploading", nullable=False
    )
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_points: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    action_items: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), nullable=False
    )
