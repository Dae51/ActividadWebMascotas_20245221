from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models.pet import Pet
from ..repositories import pet_repo
from ..schemas.pet import PetCreate, PetUpdate


def get_my_pets(db: Session, owner_id: int) -> list[Pet]:
    return pet_repo.get_by_owner(db, owner_id)


def get_adoption_catalog(db: Session, limit: int, offset: int) -> list[Pet]:
    return pet_repo.get_for_adoption(db, limit, offset)


def _get_owned_pet(db: Session, pet_id: int, owner_id: int) -> Pet:
    pet = pet_repo.get_by_id(db, pet_id)
    if pet is None:
        raise ApiError(404, "Pet not found", "pet_not_found")
    if pet.owner_id != owner_id:
        raise ApiError(
            403,
            "You are not allowed to modify this pet",
            "not_pet_owner",
        )
    return pet


def get_pet(db: Session, pet_id: int) -> Pet:
    pet = pet_repo.get_by_id(db, pet_id)
    if pet is None:
        raise ApiError(404, "Pet not found", "pet_not_found")
    return pet


def add_pet(db: Session, owner_id: int, pet_data: PetCreate) -> Pet:
    return pet_repo.create(db, owner_id, pet_data.model_dump())


def update_pet(
    db: Session,
    pet_id: int,
    owner_id: int,
    pet_data: PetUpdate,
) -> Pet:
    pet = _get_owned_pet(db, pet_id, owner_id)
    return pet_repo.update(db, pet, pet_data.model_dump(exclude_unset=True))


def delete_pet(db: Session, pet_id: int, owner_id: int) -> None:
    pet = _get_owned_pet(db, pet_id, owner_id)
    pet_repo.delete(db, pet)
