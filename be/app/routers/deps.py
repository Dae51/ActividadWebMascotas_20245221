from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories import user_repo
from ..services.auth_service import decode_token


bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if creds is None:
        raise _unauthorized("Missing authentication credentials")

    try:
        token_data = decode_token(creds.credentials)
    except JWTError as exc:
        raise _unauthorized("Invalid or expired token") from exc

    user = user_repo.get_by_id(db, token_data.user_id)
    if user is None:
        raise _unauthorized("Invalid authentication credentials")

    return user
