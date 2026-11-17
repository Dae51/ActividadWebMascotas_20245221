from sqlalchemy.orm import Session

from ..database import transaction
from ..errors import ApiError
from ..models.adoption import Adoption, AdoptionStatus
from ..models.notification import Notification, NotificationType
from ..models.pet import Pet, PetStatus
from ..repositories import adoption_repo, pet_repo
from . import notification_service


def _load_pet_for_adoption(db: Session, pet_id: int) -> Pet:
    pet = pet_repo.get_by_id(db, pet_id)
    if pet is None:
        raise ApiError(404, "Pet not found", "pet_not_found")
    return pet


def _load_owned_adoption(
    db: Session,
    adoption_id: int,
    owner_id: int,
) -> tuple[Adoption, Pet]:
    adoption = adoption_repo.get_by_id(db, adoption_id)
    if adoption is None:
        raise ApiError(404, "Adoption not found", "adoption_not_found")

    pet = _load_pet_for_adoption(db, adoption.pet_id)
    if pet.owner_id != owner_id:
        raise ApiError(
            403,
            "You are not allowed to manage this adoption",
            "not_pet_owner",
        )
    return adoption, pet


def request_adoption(
    db: Session,
    pet_id: int,
    adopter_id: int,
    message: str | None,
) -> Adoption:
    pet = _load_pet_for_adoption(db, pet_id)

    if adopter_id == pet.owner_id:
        raise ApiError(400, "You cannot adopt your own pet", "cannot_adopt_own_pet")

    if not pet.is_for_adoption or pet.status != PetStatus.ACTIVE:
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

    with transaction(db):
        adoption = adoption_repo.create(
            db=db,
            pet_id=pet_id,
            adopter_id=adopter_id,
            previous_owner_id=pet.owner_id,
            message=message,
        )
        notification = notification_service.send(
            db=db,
            user_id=pet.owner_id,
            title="New adoption request",
            message=message or f"Your pet {pet.name} has a new adoption request.",
            ntype=NotificationType.ADOPTION_REQUEST,
            related_pet_id=pet.id,
        )

    notification_service.publish(pet.owner_id, notification_service.serialize(notification))
    return adoption


def approve_adoption(db: Session, adoption_id: int, owner_id: int) -> Adoption:
    adoption, pet = _load_owned_adoption(db, adoption_id, owner_id)

    if adoption.status != AdoptionStatus.PENDING:
        raise ApiError(
            409,
            "Only pending requests can be approved",
            "adoption_not_pending",
        )

    with transaction(db):
        adoption = adoption_repo.set_status(db, adoption, AdoptionStatus.APPROVED)
        pet_repo.update(db, pet, {"status": PetStatus.PENDING})
        notification = notification_service.send(
            db=db,
            user_id=adoption.adopter_id,
            title="Adoption approved",
            message=f"Your adoption request for {pet.name} was approved.",
            ntype=NotificationType.ADOPTION_APPROVED,
            related_pet_id=pet.id,
        )

    notification_service.publish(
        adoption.adopter_id, notification_service.serialize(notification)
    )
    return adoption


def reject_adoption(db: Session, adoption_id: int, owner_id: int) -> Adoption:
    adoption, pet = _load_owned_adoption(db, adoption_id, owner_id)

    if adoption.status not in (AdoptionStatus.PENDING, AdoptionStatus.APPROVED):
        raise ApiError(
            409,
            "This adoption can no longer be rejected",
            "adoption_not_rejectable",
        )

    with transaction(db):
        adoption = adoption_repo.set_status(db, adoption, AdoptionStatus.REJECTED)

        remaining_approved = [
            item
            for item in adoption_repo.list_active_for_pet(db, pet.id)
            if item.status == AdoptionStatus.APPROVED
        ]
        if not remaining_approved and pet.status == PetStatus.PENDING:
            pet_repo.update(db, pet, {"status": PetStatus.ACTIVE})

        notification = notification_service.send(
            db=db,
            user_id=adoption.adopter_id,
            title="Adoption rejected",
            message=f"Your adoption request for {pet.name} was rejected.",
            ntype=NotificationType.ADOPTION_REJECTED,
            related_pet_id=pet.id,
        )

    notification_service.publish(
        adoption.adopter_id, notification_service.serialize(notification)
    )
    return adoption


def complete_adoption(db: Session, adoption_id: int, owner_id: int) -> Adoption:
    adoption, pet = _load_owned_adoption(db, adoption_id, owner_id)

    if adoption.status == AdoptionStatus.COMPLETED:
        raise ApiError(
            409,
            "Adoption is already completed",
            "adoption_already_completed",
        )

    if adoption.status != AdoptionStatus.APPROVED:
        raise ApiError(
            409,
            "Only approved adoptions can be completed",
            "adoption_not_approved",
        )

    pending_notifications: list[Notification] = []

    with transaction(db):
        adoption = adoption_repo.complete(db, adoption)
        pet_repo.transfer_ownership(db, pet, adoption.adopter_id)

        for other in adoption_repo.list_active_for_pet(
            db, pet.id, exclude_adoption_id=adoption.id
        ):
            adoption_repo.set_status(db, other, AdoptionStatus.REJECTED)
            pending_notifications.append(
                notification_service.send(
                    db=db,
                    user_id=other.adopter_id,
                    title="Adoption closed",
                    message=f"{pet.name} was adopted by another applicant.",
                    ntype=NotificationType.ADOPTION_REJECTED,
                    related_pet_id=pet.id,
                )
            )

        pending_notifications.append(
            notification_service.send(
                db=db,
                user_id=adoption.adopter_id,
                title="Adoption completed",
                message=f"Your adoption for {pet.name} has been completed.",
                ntype=NotificationType.ADOPTION_COMPLETED,
                related_pet_id=pet.id,
            )
        )

    for notification in pending_notifications:
        notification_service.publish(
            notification.user_id, notification_service.serialize(notification)
        )

    return adoption


def list_received(db: Session, owner_id: int) -> list[Adoption]:
    return adoption_repo.list_for_owner(db, owner_id)


def list_requested(db: Session, adopter_id: int) -> list[Adoption]:
    return adoption_repo.list_for_adopter(db, adopter_id)
