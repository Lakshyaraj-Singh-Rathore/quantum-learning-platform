from datetime import datetime


from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func

from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.database import Base, JSONType, VectorType


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(String(255))
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    #: "theory" (concepts) or "circuit" (hands-on). Drives the Learn tabs.
    track: Mapped[str] = mapped_column(String(20), default="theory")

    # -- Curriculum placement (M0). Added rather than replacing order_index --
    # so that anything still reading the flat ordering keeps working until it
    # is migrated. ``order_index`` remains the filename-derived position.

    #: Owning topic. Nullable: a lesson the curriculum has not claimed yet is
    #: still a valid lesson, it just sits outside the hierarchy.
    topic_slug: Mapped[str | None] = mapped_column(
        ForeignKey("curriculum_topics.slug"), index=True, nullable=True
    )
    #: Order within the owning topic. Distinct from ``order_index``, which is
    #: the global filename-derived sequence.
    position: Mapped[int] = mapped_column(Integer, default=0)
    #: beginner | intermediate | advanced. Inherited from the topic when set.
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    learning_objectives: Mapped[list] = mapped_column(JSONType, default=list)


class ContentChunk(Base):
    __tablename__ = "content_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_slug: Mapped[str] = mapped_column(String(120), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    embedding = mapped_column(VectorType(get_settings().embedding_dim), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
