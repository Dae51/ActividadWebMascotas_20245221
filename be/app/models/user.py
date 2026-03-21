from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    pets: Mapped[list["Pet"]] = relationship(
        back_populates="owner", passive_deletes=True
    )
    adoption_requests: Mapped[list["Adoption"]] = relationship(
        back_populates="adopter",
        foreign_keys="Adoption.adopter_id",
        passive_deletes=True,
    )
    previous_owner_adoptions: Mapped[list["Adoption"]] = relationship(
        back_populates="previous_owner",
        foreign_keys="Adoption.previous_owner_id",
        passive_deletes=True,
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", passive_deletes=True
    )
