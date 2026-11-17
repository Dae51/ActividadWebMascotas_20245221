from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.user import User


def get_by_username(db: Session, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    return db.scalar(stmt)


def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return db.scalar(stmt)


def get_by_id(db: Session, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id)
    return db.scalar(stmt)


def create(
    db: Session,
    username: str,
    email: str,
    password_hash: str,
    full_name: str | None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        full_name=full_name,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user
