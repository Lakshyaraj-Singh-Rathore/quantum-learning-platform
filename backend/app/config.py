from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://quantum:quantum@postgres:5432/quantum_learn"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    api_cors_origins: str = "*"

    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.0-flash"
    gemini_embed_model: str = "text-embedding-004"

    qbraid_api_key: str = ""
    qbraid_device_id: str = ""

    celery_soft_time_limit: int = 8
    celery_hard_time_limit: int = 15

    content_dir: str = "/content"
    samples_dir: str = "/samples"

    bootstrap_instructor_email: str = "instructor@local.dev"
    bootstrap_instructor_password: str = "instructor123"
    bootstrap_admin_email: str = "admin@local.dev"
    bootstrap_admin_password: str = "admin123"

    max_dynamic_qubits: int = 15
    max_dynamic_shots: int = 4096
    while_cap: int = 32
    embedding_dim: int = 768


@lru_cache
def get_settings() -> Settings:
    return Settings()
