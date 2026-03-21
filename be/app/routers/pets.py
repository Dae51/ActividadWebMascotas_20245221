from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.pet import PetCreate, PetOut, PetUpdate
from ..services import pet_service
from .deps import get_current_user


router = APIRouter(prefix="/pets", tags=["pets"])


@router.get("/catalog", response_model=list[PetOut])
def get_catalog(db: Session = Depends(get_db)):
    return pet_service.get_adoption_catalog(db)


@router.get("/mine", response_model=list[PetOut])
def get_my_pets(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return pet_service.get_my_pets(db, current_user.id)


@router.post("/", response_model=PetOut, status_code=status.HTTP_201_CREATED)
def add_pet(
    pet_data: PetCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return pet_service.add_pet(db, current_user.id, pet_data)


@router.patch("/{pet_id}", response_model=PetOut)
def update_pet(
    pet_id: int,
    pet_data: PetUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pet = pet_service.update_pet(db, pet_id, current_user.id, pet_data)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )
    return pet
