from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..errors import ApiError
from ..models.user import User
from ..repositories import user_repo
from ..schemas.token import TokenData
from ..schemas.user import UserCreate


pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)

WS_SCOPE = "ws"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.token_expire_minutes
    )
    payload = {"user_id": user_id, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> TokenData:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    if payload.get("scope") == WS_SCOPE:
        raise JWTError("WebSocket tickets cannot be used as access tokens")

    user_id = payload.get("user_id")
    if user_id is None:
        raise JWTError("Token missing user_id")
    return TokenData(user_id=int(user_id))


def create_ws_ticket(user_id: int) -> tuple[str, int]:
    """Short lived, single purpose credential for the WebSocket handshake."""
    expires_in = settings.ws_ticket_expire_seconds
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {"user_id": user_id, "scope": WS_SCOPE, "exp": expire}
    ticket = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return ticket, expires_in


def decode_ws_ticket(ticket: str) -> TokenData:
    payload = jwt.decode(ticket, settings.secret_key, algorithms=[settings.algorithm])
    if payload.get("scope") != WS_SCOPE:
        raise JWTError("Invalid ticket scope")

    user_id = payload.get("user_id")
    if user_id is None:
        raise JWTError("Ticket missing user_id")
    return TokenData(user_id=int(user_id))


def register(db: Session, user_data: UserCreate) -> User:
    username = user_data.username.strip()
    email = str(user_data.email).strip().lower()

    if user_repo.get_by_username(db, username) is not None:
        raise ApiError(
            status_code=409,
            detail="Username is already registered",
            code="username_conflict",
        )

    if user_repo.get_by_email(db, email) is not None:
        raise ApiError(
            status_code=409,
            detail="Email is already registered",
            code="email_conflict",
        )

    try:
        password_hash = hash_password(user_data.password)
    except (ValueError, TypeError) as exc:
        raise ApiError(
            status_code=400,
            detail="Password could not be processed",
            code="invalid_password",
        ) from exc

    try:
        return user_repo.create(
            db,
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=user_data.full_name,
        )
    except IntegrityError as exc:
        raise ApiError(
            status_code=409,
            detail="User could not be created because it conflicts with an existing record",
            code="user_conflict",
        ) from exc


def login(db: Session, username: str, password: str) -> str | None:
    user = user_repo.get_by_username(db, username)
    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return create_access_token(user.id)
