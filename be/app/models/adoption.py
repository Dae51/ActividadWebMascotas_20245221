from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .pet import Pet
    from .user import User


class AdoptionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


adoption_status_enum = SqlEnum(
    AdoptionStatus,
    name="adoptionstatus",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class Adoption(Base):
    __tablename__ = "adoptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    adopter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    previous_owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[AdoptionStatus] = mapped_column(
        adoption_status_enum,
        default=AdoptionStatus.PENDING,
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    pet: Mapped["Pet"] = relationship(back_populates="adoptions")
    adopter: Mapped["User"] = relationship(
        back_populates="adoption_requests",
        foreign_keys=[adopter_id],
    )
    previous_owner: Mapped["User"] = relationship(
        back_populates="previous_owner_adoptions",
        foreign_keys=[previous_owner_id],
    )
