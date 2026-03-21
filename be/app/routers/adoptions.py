from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.adoption import AdoptionOut, AdoptionRequest
from ..services import adoption_service
from .deps import get_current_user


router = APIRouter(prefix="/adoptions", tags=["adoptions"])


@router.post("/request", response_model=AdoptionOut, status_code=status.HTTP_201_CREATED)
def request_adoption(
    adoption_request: AdoptionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    adoption = adoption_service.request_adoption(
        db,
        adoption_request.pet_id,
        current_user.id,
        adoption_request.message,
    )
    if adoption is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adoption request could not be created",
        )
    return adoption


@router.post("/{adoption_id}/complete", response_model=AdoptionOut)
def complete_adoption(
    adoption_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    adoption = adoption_service.complete_adoption(db, adoption_id, current_user.id)
    if adoption is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adoption not found or not allowed",
        )
    return adoption
