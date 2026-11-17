from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.pet import Pet, PetStatus


def get_by_owner(db: Session, owner_id: int) -> list[Pet]:
    stmt = select(Pet).where(Pet.owner_id == owner_id).order_by(Pet.id)
    return list(db.scalars(stmt).all())


def get_for_adoption(db: Session, limit: int, offset: int) -> list[Pet]:
    stmt = (
        select(Pet)
        .where(
            Pet.is_for_adoption.is_(True),
            Pet.status == PetStatus.ACTIVE,
        )
        .order_by(Pet.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, pet_id: int) -> Pet | None:
    stmt = select(Pet).where(Pet.id == pet_id)
    return db.scalar(stmt)


def create(db: Session, owner_id: int, data_dict: dict) -> Pet:
    pet = Pet(owner_id=owner_id, **data_dict)
    db.add(pet)
    db.flush()
    db.refresh(pet)
    return pet


def update(db: Session, pet: Pet, data_dict: dict) -> Pet:
    for key, value in data_dict.items():
        setattr(pet, key, value)

    db.add(pet)
    db.flush()
    db.refresh(pet)
    return pet


def transfer_ownership(db: Session, pet: Pet, new_owner_id: int) -> Pet:
    pet.owner_id = new_owner_id
    pet.is_for_adoption = False
    pet.status = PetStatus.ADOPTED

    db.add(pet)
    db.flush()
    db.refresh(pet)
    return pet


def delete(db: Session, pet: Pet) -> None:
    db.delete(pet)
    db.flush()
