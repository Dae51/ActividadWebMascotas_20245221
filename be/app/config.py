import os
from dataclasses import dataclass


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    token_expire_minutes: int
    token_expiration: int
    algorithm: str
    debug: bool


_token_expire_minutes_env = os.getenv("TOKEN_EXPIRE_MINUTES")
_token_expiration_env = os.getenv("TOKEN_EXPIRATION")

if _token_expire_minutes_env is not None:
    _token_expire_minutes = int(_token_expire_minutes_env)
elif _token_expiration_env is not None:
    _token_expire_minutes = max(1, int(_token_expiration_env) // 60)
else:
    _token_expire_minutes = 60

settings = Settings(
    database_url=os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://pawsuser:pawspass@db:5432/pawshome"
    ),
    secret_key=os.getenv("SECRET_KEY", "supersecretkey"),
    token_expire_minutes=_token_expire_minutes,
    token_expiration=_token_expire_minutes * 60,
    algorithm=os.getenv("ALGORITHM", "HS256"),
    debug=_get_bool(os.getenv("DEBUG"), True),
)
