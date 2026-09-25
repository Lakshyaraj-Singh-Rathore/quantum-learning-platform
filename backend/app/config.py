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
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_embed_model: str = "gemini-embedding-001"

    qbraid_api_key: str = ""
    qbraid_device_id: str = "ionq:ionq:sim:simulator"

    celery_soft_time_limit: int = 8
    celery_hard_time_limit: int = 15
    #: Run simulation tasks inline instead of dispatching to a worker.
    #: Useful for local development without Redis; never enable in production.
    celery_task_always_eager: bool = False

    content_dir: str = "/content"
    samples_dir: str = "/samples"

    bootstrap_instructor_email: str = "instructor@local.dev"
    bootstrap_instructor_password: str = "instructor123"
    bootstrap_admin_email: str = "admin@local.dev"
    bootstrap_admin_password: str = "admin123"

    max_dynamic_qubits: int = 15
    # Statevector memory is 16 bytes * 2**n: 20 qubits is ~400 MB and 24+ gets
    # the worker OOM-killed. Cap static circuits too, or any user can take the
    # backend down with a 30-qubit circuit.
    max_static_qubits: int = 20
    #: GPU statevector lives in VRAM, so it has its own ceiling. 26 qubits is
    #: 537 MB at fp32, which leaves a 6 GB card room for the desktop
    #: compositor; 28 would fill it and stutter or OOM mid-run.
    max_gpu_qubits: int = 26
    #: Refuse new GPU work above this temperature. Set 0 to disable the check.
    gpu_temp_limit_c: int = 80
    #: Minimum gap between GPU submissions, so repeated Run presses cannot
    #: chain back-to-back bursts.
    gpu_cooldown_seconds: float = 3.0
    max_dynamic_shots: int = 4096
    while_cap: int = 32
    embedding_dim: int = 768


@lru_cache
def get_settings() -> Settings:
    return Settings()
