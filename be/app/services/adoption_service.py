from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models.adoption import Adoption, AdoptionStatus
from ..models.notification import NotificationType
from ..repositories import adoption_repo, pet_repo
from . import notification_service



def request_adoption(
    db: Session,
    pet_id: int,
    adopter_id: int,
    message: str | None,
) -> Adoption:
    pet = pet_repo.get_by_id(db, pet_id)
    if pet is None:
        raise ApiError(404, "Pet not found", "pet_not_found")

    if adopter_id == pet.owner_id:
        raise ApiError(400, "You cannot adopt your own pet", "cannot_adopt_own_pet")

    if not pet.is_for_adoption:
        raise ApiError(409, "Pet is not available for adoption", "pet_not_available")

    existing_request = adoption_repo.get_active_request_for_pet_and_adopter(
        db,
        pet_id,
        adopter_id,
    )
    if existing_request is not None:
        raise ApiError(
            409,
            "You already have an active adoption request for this pet",
            "adoption_request_exists",
        )

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



def complete_adoption(db: Session, adoption_id: int, owner_id: int) -> Adoption:
    adoption = adoption_repo.get_by_id(db, adoption_id)
    if adoption is None:
        raise ApiError(404, "Adoption not found", "adoption_not_found")

    pet = pet_repo.get_by_id(db, adoption.pet_id)
    if pet is None:
        raise ApiError(404, "Pet not found", "pet_not_found")

    if pet.owner_id != owner_id:
        raise ApiError(
            403,
            "You are not allowed to complete this adoption",
            "not_pet_owner",
        )

    if adoption.status == AdoptionStatus.COMPLETED:
        raise ApiError(
            409,
            "Adoption is already completed",
            "adoption_already_completed",
        )

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
