"""Configuration read from environment variables. No committed secrets/values."""
import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    shared_username: str = field(default_factory=lambda: os.environ.get("SHARED_USERNAME", "demo"))
    shared_password: str = field(default_factory=lambda: os.environ.get("SHARED_PASSWORD", "change-me"))
    session_secret_key: str = field(default_factory=lambda: os.environ.get("SESSION_SECRET_KEY", "dev-only-insecure-key"))

    database_path: str = field(default_factory=lambda: os.environ.get("DATABASE_PATH", "./data/conversational_crm.db"))
    chroma_persist_dir: str = field(default_factory=lambda: os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma"))

    nlu_engine: str = field(default_factory=lambda: os.environ.get("NLU_ENGINE", "rule_based"))
    aws_region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"))
    bedrock_text_model_id: str = field(default_factory=lambda: os.environ.get("BEDROCK_TEXT_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"))
    bedrock_embedding_model_id: str = field(default_factory=lambda: os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"))

    due_soon_window_days: int = field(default_factory=lambda: int(os.environ.get("DUE_SOON_WINDOW_DAYS", "7")))
    home_top_n: int = field(default_factory=lambda: int(os.environ.get("HOME_TOP_N", "5")))

    rate_limit_per_minute: int = field(default_factory=lambda: int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30")))
    login_lockout_attempts: int = field(default_factory=lambda: int(os.environ.get("LOGIN_LOCKOUT_ATTEMPTS", "5")))
    login_lockout_window_minutes: int = field(default_factory=lambda: int(os.environ.get("LOGIN_LOCKOUT_WINDOW_MINUTES", "15")))

    # Comma-separated list of allowed frontend origins (e.g. the Vercel deployment
    # URL(s)). Empty by default -- same-origin/local dev needs no CORS at all.
    cors_allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
        )
    )
    # "strict" for same-site deployments (default); must be "none" when the
    # frontend and backend are on different origins (e.g. Vercel + Render),
    # since a Strict/Lax cookie is never sent on a cross-site request.
    cookie_samesite: str = field(default_factory=lambda: os.environ.get("COOKIE_SAMESITE", "strict"))


def get_settings() -> Settings:
    # Re-read on every call so tests can monkeypatch os.environ per-test.
    return Settings()
