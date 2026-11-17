from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from ..database import get_db, transaction
from ..schemas.pet import PetCreate, PetOut, PetUpdate
from ..services import pet_service
from .deps import get_current_user


router = APIRouter(prefix="/pets", tags=["pets"])


@router.get("/catalog", response_model=list[PetOut])
def get_catalog(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return pet_service.get_adoption_catalog(db, limit, offset)


@router.get("/mine", response_model=list[PetOut])
def get_my_pets(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return pet_service.get_my_pets(db, current_user.id)


@router.get("/{pet_id}", response_model=PetOut)
def get_pet(
    pet_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return pet_service.get_pet(db, pet_id)


@router.post("/", response_model=PetOut, status_code=status.HTTP_201_CREATED)
def add_pet(
    pet_data: PetCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with transaction(db):
        return pet_service.add_pet(db, current_user.id, pet_data)


@router.patch("/{pet_id}", response_model=PetOut)
def update_pet(
    pet_id: int,
    pet_data: PetUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with transaction(db):
        return pet_service.update_pet(db, pet_id, current_user.id, pet_data)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(
    pet_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    with transaction(db):
        pet_service.delete_pet(db, pet_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
