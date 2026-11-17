from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.adoption import AdoptionDetailOut, AdoptionOut, AdoptionRequest
from ..services import adoption_service
from .deps import get_current_user


router = APIRouter(prefix="/adoptions", tags=["adoptions"])


@router.get("/received", response_model=list[AdoptionDetailOut])
def list_received(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return adoption_service.list_received(db, current_user.id)


@router.get("/mine", response_model=list[AdoptionDetailOut])
def list_requested(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return adoption_service.list_requested(db, current_user.id)


@router.post("/request", response_model=AdoptionOut, status_code=status.HTTP_201_CREATED)
def request_adoption(
    adoption_request: AdoptionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return adoption_service.request_adoption(
        db,
        adoption_request.pet_id,
        current_user.id,
        adoption_request.message,
    )


@router.post("/{adoption_id}/approve", response_model=AdoptionOut)
def approve_adoption(
    adoption_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return adoption_service.approve_adoption(db, adoption_id, current_user.id)


@router.post("/{adoption_id}/reject", response_model=AdoptionOut)
def reject_adoption(
    adoption_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return adoption_service.reject_adoption(db, adoption_id, current_user.id)


@router.post("/{adoption_id}/complete", response_model=AdoptionOut)
def complete_adoption(
    adoption_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return adoption_service.complete_adoption(db, adoption_id, current_user.id)
