"""Curriculum hierarchy: sections, topics and the prerequisite graph.

Companion to ``app/curriculum.py``, which holds the canonical data. These are
the persisted rows; that module is what decides what the rows should say.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONType


class CurriculumSection(Base):
    """One of the ten top-level sections of the roadmap."""

    __tablename__ = "curriculum_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    #: 1-based display order, matching the roadmap's section numbering.
    position: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")


class CurriculumTopic(Base):
    """A teachable unit within a section. Carries difficulty and objectives.

    This is the stable identifier that mastery and prerequisites hang off.
    """

    __tablename__ = "curriculum_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    section_slug: Mapped[str] = mapped_column(
        ForeignKey("curriculum_sections.slug"), index=True
    )
    #: Order within the section, chosen by conceptual dependency.
    position: Mapped[int] = mapped_column(Integer, default=0)
    #: beginner | intermediate | advanced
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    summary: Mapped[str] = mapped_column(Text, default="")
    learning_objectives: Mapped[list] = mapped_column(JSONType, default=list)


class TopicPrerequisite(Base):
    """A directed edge in the dependency graph.

    ``kind`` distinguishes a hard requirement from an advisory one, so the UI can
    offer diagnostic-based skipping for recommendations without weakening the
    gate on genuinely required material.
    """

    __tablename__ = "topic_prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_slug: Mapped[str] = mapped_column(
        ForeignKey("curriculum_topics.slug"), index=True
    )
    prerequisite_slug: Mapped[str] = mapped_column(
        ForeignKey("curriculum_topics.slug"), index=True
    )
    #: required | recommended
    kind: Mapped[str] = mapped_column(String(20), default="required")
