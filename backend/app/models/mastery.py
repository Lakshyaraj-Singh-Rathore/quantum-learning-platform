from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserMastery(Base):
    __tablename__ = "user_mastery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tag: Mapped[str] = mapped_column(String(64), index=True)
    # NOTE: the topic_slug stamp added in f1a2b3c4d5e6 was removed in
    # a2b3c4d5e6f7. Topic mastery now lives in ``topic_mastery``, which records
    # provenance back to this row instead of mutating it. This table is once
    # again exactly what it was before the curriculum work: the raw,
    # unmodified history of tag-keyed outcomes.
    score: Mapped[float] = mapped_column(Float, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # lesson|challenge
    slug: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
