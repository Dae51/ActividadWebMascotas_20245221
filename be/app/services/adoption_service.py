from sqlalchemy.orm import Session

from ..models.adoption import Adoption
from ..models.notification import NotificationType
from ..repositories import adoption_repo, pet_repo
from . import notification_service



def request_adoption(
    db: Session,
    pet_id: int,
    adopter_id: int,
    message: str | None,
) -> Adoption | None:
    pet = pet_repo.get_by_id(db, pet_id)
    if pet is None or not pet.is_for_adoption or adopter_id == pet.owner_id:
        return None

    adoption = adoption_repo.create(
        db=db,
        pet_id=pet_id,
        adopter_id=adopter_id,
        previous_owner_id=pet.owner_id,
        message=message,
    )
    notification_service.send(
        db=db,
        user_id=pet.owner_id,
        title="New adoption request",
        message=message or f"Your pet {pet.name} has a new adoption request.",
        ntype=NotificationType.ADOPTION_REQUEST,
        related_pet_id=pet.id,
    )
    return adoption



def complete_adoption(db: Session, adoption_id: int, owner_id: int) -> Adoption | None:
    adoption = adoption_repo.get_by_id(db, adoption_id)
    if adoption is None:
        return None

    pet = pet_repo.get_by_id(db, adoption.pet_id)
    if pet is None or pet.owner_id != owner_id:
        return None

    adoption = adoption_repo.complete(db, adoption)
    pet_repo.transfer_ownership(db, pet, adoption.adopter_id)
    notification_service.send(
        db=db,
        user_id=adoption.adopter_id,
        title="Adoption completed",
        message=f"Your adoption for {pet.name} has been completed.",
        ntype=NotificationType.ADOPTION_COMPLETED,
        related_pet_id=pet.id,
    )
    return adoption
