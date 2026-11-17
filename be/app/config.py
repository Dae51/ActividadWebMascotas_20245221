import logging
import os
import secrets
from dataclasses import dataclass


logger = logging.getLogger("pawshome.config")


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_origins(value: str | None) -> tuple[str, ...]:
    if not value:
        return ("http://localhost:5000", "http://127.0.0.1:5000")
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


def _load_secret_key() -> str:
    secret = os.getenv("SECRET_KEY", "").strip()
    if secret:
        return secret

    logger.warning(
        "SECRET_KEY is not configured. An ephemeral key was generated, so every "
        "issued token will be invalidated when the process restarts."
    )
    return secrets.token_urlsafe(48)


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    token_expire_minutes: int
    ws_ticket_expire_seconds: int
    algorithm: str
    debug: bool
    cors_origins: tuple[str, ...]


settings = Settings(
    database_url=os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://pawsuser:pawspass@db:5432/pawshome"
    ),
    secret_key=_load_secret_key(),
    token_expire_minutes=max(1, int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))),
    ws_ticket_expire_seconds=max(10, int(os.getenv("WS_TICKET_EXPIRE_SECONDS", "60"))),
    algorithm=os.getenv("ALGORITHM", "HS256"),
    debug=_get_bool(os.getenv("DEBUG"), False),
    cors_origins=_get_origins(os.getenv("CORS_ORIGINS")),
)
