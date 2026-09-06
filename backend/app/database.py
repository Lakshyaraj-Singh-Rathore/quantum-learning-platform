from sqlalchemy import JSON, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.config import get_settings


class Base(DeclarativeBase):
    pass


#: JSONB on Postgres (production), plain JSON elsewhere so the test suite can
#: run on SQLite without a database server.
JSONType = JSON().with_variant(JSONB(), "postgresql")


class VectorType(TypeDecorator):
    """pgvector column that degrades to JSON on non-Postgres dialects."""

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int) -> None:
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())


settings = get_settings()
_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    _engine_kwargs = {"connect_args": {"check_same_thread": False}}
engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Ensure the schema exists.

    When Alembic owns the database (an ``alembic_version`` table is present,
    which is the case for the Docker/production path where the API runs
    ``alembic upgrade head`` before starting) this is a no-op. ``create_all``
    would otherwise race the migrations and leave the two disagreeing.

    For local development and the test suite -- SQLite, no migrations run --
    it still creates the tables so the app is usable with zero setup.
    """
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    from app import models  # noqa: F401  register models

    if inspect(engine).has_table("alembic_version"):
        return

    Base.metadata.create_all(bind=engine)
