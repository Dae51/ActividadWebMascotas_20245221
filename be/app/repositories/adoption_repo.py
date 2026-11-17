from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from ..models.adoption import Adoption, AdoptionStatus
from ..models.pet import Pet


def _with_relations():
    return (
        selectinload(Adoption.pet),
        selectinload(Adoption.adopter),
    )


def create(
    db: Session,
    pet_id: int,
    adopter_id: int,
    previous_owner_id: int,
    message: str | None,
) -> Adoption:
    adoption = Adoption(
        pet_id=pet_id,
        adopter_id=adopter_id,
        previous_owner_id=previous_owner_id,
        message=message,
    )
    db.add(adoption)
    db.flush()
    db.refresh(adoption)
    return adoption


def get_by_id(db: Session, adoption_id: int) -> Adoption | None:
    stmt = select(Adoption).where(Adoption.id == adoption_id)
    return db.scalar(stmt)


def get_active_request_for_pet_and_adopter(
    db: Session,
    pet_id: int,
    adopter_id: int,
) -> Adoption | None:
    stmt = select(Adoption).where(
        Adoption.pet_id == pet_id,
        Adoption.adopter_id == adopter_id,
        Adoption.status.in_([AdoptionStatus.PENDING, AdoptionStatus.APPROVED]),
    )
    return db.scalar(stmt)


def list_for_owner(db: Session, owner_id: int) -> list[Adoption]:
    stmt = (
        select(Adoption)
        .join(Pet, Adoption.pet_id == Pet.id)
        .where(Pet.owner_id == owner_id)
        .order_by(desc(Adoption.requested_at))
        .options(*_with_relations())
    )
    return list(db.scalars(stmt).all())


def list_for_adopter(db: Session, adopter_id: int) -> list[Adoption]:
    stmt = (
        select(Adoption)
        .where(Adoption.adopter_id == adopter_id)
        .order_by(desc(Adoption.requested_at))
        .options(*_with_relations())
    )
    return list(db.scalars(stmt).all())


def list_active_for_pet(
    db: Session,
    pet_id: int,
    exclude_adoption_id: int | None = None,
) -> list[Adoption]:
    stmt = select(Adoption).where(
        Adoption.pet_id == pet_id,
        Adoption.status.in_([AdoptionStatus.PENDING, AdoptionStatus.APPROVED]),
    )
    if exclude_adoption_id is not None:
        stmt = stmt.where(Adoption.id != exclude_adoption_id)
    return list(db.scalars(stmt).all())


def set_status(db: Session, adoption: Adoption, status: AdoptionStatus) -> Adoption:
    adoption.status = status
    db.add(adoption)
    db.flush()
    db.refresh(adoption)
    return adoption


def complete(db: Session, adoption: Adoption) -> Adoption:
    adoption.status = AdoptionStatus.COMPLETED
    adoption.completed_at = datetime.now(timezone.utc)

    db.add(adoption)
    db.flush()
    db.refresh(adoption)
    return adoption
