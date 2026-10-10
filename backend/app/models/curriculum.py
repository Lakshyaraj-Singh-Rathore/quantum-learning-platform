"""Curriculum registry: sections, topics, lesson links and topic mastery.

Companion to ``app/curriculum.py``, which holds the canonical data. These are
the persisted rows; that module decides what they should say.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONType


class CurriculumSection(Base):
    """One of the ten top-level curriculum sections."""

    __tablename__ = "curriculum_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    letter: Mapped[str] = mapped_column(String(2), default="")
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)


class CurriculumTopic(Base):
    """A teachable unit. The primary key *is* the stable topic identifier.

    Storing the namespaced id (``qc.qubits``) as the primary key, rather than a
    surrogate integer, makes it impossible for two rows to claim the same
    identity and lets lessons, mastery and prerequisites reference it directly
    without a join.
    """

    __tablename__ = "curriculum_topics"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    namespace: Mapped[str] = mapped_column(String(20), index=True)
    module: Mapped[str] = mapped_column(String(80), default="", index=True)
    section_slug: Mapped[str] = mapped_column(
        ForeignKey("curriculum_sections.slug"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    description: Mapped[str] = mapped_column(Text, default="")
    learning_objectives: Mapped[list] = mapped_column(JSONType, default=list)
    #: draft | review | published | retired. Only published reaches learners.
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    #: Registry revision, bumped when the topic definition changes.
    revision: Mapped[int] = mapped_column(Integer, default=1)
    #: Quiz slugs that evidence this topic.
    assessments: Mapped[list] = mapped_column(JSONType, default=list)
    #: Demo/visualization keys this topic reuses.
    visualizations: Mapped[list] = mapped_column(JSONType, default=list)


class TopicPrerequisite(Base):
    """A directed edge in the dependency graph."""

    __tablename__ = "topic_prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_topics.id"), index=True
    )
    prerequisite_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_topics.id"), index=True
    )
    #: required blocks progression; recommended only warns.
    kind: Mapped[str] = mapped_column(String(20), default="required")
    #: Why the edge exists. Added by the M4 expansion so a prerequisite can be
    #: reviewed rather than merely accepted; empty for edges that predate it.
    rationale: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (UniqueConstraint("topic_id", "prerequisite_id", name="uq_topic_prereq"),)


class LessonTopic(Base):
    """Explicit lesson -> topic link, replacing keyword inference.

    Many-to-many: a lesson legitimately teaches several topics, and a topic is
    taught by several lessons. ``confidence`` records how certain the mapping
    is, which is what decides whether *existing* mastery may be carried onto
    the topic during migration.
    """

    __tablename__ = "lesson_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_slug: Mapped[str] = mapped_column(String(120), index=True)
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_topics.id"), index=True
    )
    #: high | medium | low
    confidence: Mapped[str] = mapped_column(String(16), default="medium")
    is_primary: Mapped[bool] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("lesson_slug", "topic_id", name="uq_lesson_topic"),)


class TopicMastery(Base):
    """Mastery of a stable topic, kept separate from lesson completion.

    ``status`` distinguishes the three kinds the migration spec requires:

    ``mapped``
        Carried over from a legacy tag row because the mapping is documented
        and the confidence is high. Carries provenance in ``evidence``.
    ``verified``
        Earned through an explicit criterion: a passed assessment or a
        completed lesson, recorded at the time it happened.
    ``legacy_only``
        Preserved for audit but not counted. Never used to satisfy a
        prerequisite.
    """

    __tablename__ = "topic_mastery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_topics.id"), index=True
    )
    #: 0..1
    mastery_level: Mapped[float] = mapped_column(Float, default=0.0)
    #: mapped | verified | legacy_only
    status: Mapped[str] = mapped_column(String(20), default="verified", index=True)
    #: How the mastery was established, e.g. "quiz:grover" or "migration:tag:noise".
    source: Mapped[str] = mapped_column(String(120), default="")
    #: Provenance: originating row ids, scores and the mapping used.
    evidence: Mapped[dict] = mapped_column(JSONType, default=dict)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", "topic_id", "source", name="uq_topic_mastery"),)


class LessonCompletion(Base):
    """A learner finished a lesson.

    Deliberately separate from TopicMastery. Reading a lesson is not evidence
    of mastery, and a learner must not be credited with every topic a completed
    lesson happens to mention.
    """

    __tablename__ = "lesson_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_slug: Mapped[str] = mapped_column(String(120), index=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "lesson_slug", name="uq_lesson_completion"),
    )
