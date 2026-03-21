from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models.adoption import Adoption, AdoptionStatus



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
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(adoption)
    return adoption



def get_by_id(db: Session, adoption_id: int) -> Adoption | None:
    stmt = select(Adoption).where(Adoption.id == adoption_id)
    return db.scalar(stmt)



def complete(db: Session, adoption: Adoption) -> Adoption:
    adoption.status = AdoptionStatus.COMPLETED
    adoption.completed_at = datetime.now(timezone.utc)

    db.add(adoption)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(adoption)
    return adoption
