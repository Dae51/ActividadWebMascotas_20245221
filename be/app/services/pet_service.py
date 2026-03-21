from ..models.pet import Pet
from ..repositories import pet_repo
from ..schemas.pet import PetCreate, PetUpdate
from sqlalchemy.orm import Session



def get_my_pets(db: Session, owner_id: int) -> list[Pet]:
    return pet_repo.get_by_owner(db, owner_id)



def get_adoption_catalog(db: Session) -> list[Pet]:
    return pet_repo.get_for_adoption(db)



def add_pet(db: Session, owner_id: int, pet_data: PetCreate) -> Pet:
    return pet_repo.create(db, owner_id, pet_data.model_dump())



def update_pet(db: Session, pet_id: int, owner_id: int, pet_data: PetUpdate) -> Pet | None:
    pet = pet_repo.get_by_id(db, pet_id)
    if pet is None or pet.owner_id != owner_id:
        return None

    return pet_repo.update(db, pet, pet_data.model_dump(exclude_unset=True))
