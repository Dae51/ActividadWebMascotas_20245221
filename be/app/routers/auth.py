from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, transaction
from ..schemas.token import Token, WsTicket
from ..schemas.user import LoginRequest, UserCreate, UserOut
from ..services import auth_service
from .deps import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    with transaction(db):
        return auth_service.register(db, user_data)


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    token = auth_service.login(db, login_data.username, login_data.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return Token(access_token=token)


@router.post("/ws-ticket", response_model=WsTicket)
def ws_ticket(current_user=Depends(get_current_user)):
    ticket, expires_in = auth_service.create_ws_ticket(current_user.id)
    return WsTicket(ticket=ticket, expires_in=expires_in)
