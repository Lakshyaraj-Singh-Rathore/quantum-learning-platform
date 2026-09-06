from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func

from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONType


class SimulationJob(Base):
    __tablename__ = "simulation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    backend: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(32), default="auto")  # auto|static|dynamic
    shots: Mapped[int] = mapped_column(Integer, default=1024)
    circuit_ir: Mapped[dict] = mapped_column(JSONType)
    qasm3: Mapped[str] = mapped_column(Text, default="")
    run_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
