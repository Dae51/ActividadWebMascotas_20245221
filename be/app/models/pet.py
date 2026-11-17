from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .adoption import Adoption
    from .notification import Notification
    from .user import User


class PetStatus(str, Enum):
    ACTIVE = "active"
    ADOPTED = "adopted"
    PENDING = "pending"


pet_status_enum = SqlEnum(
    PetStatus,
    name="petstatus",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    age_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_for_adoption: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    status: Mapped[PetStatus] = mapped_column(
        pet_status_enum, default=PetStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="pets")
    adoptions: Mapped[list["Adoption"]] = relationship(
        back_populates="pet", passive_deletes=True
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="related_pet"
    )
