from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.adoption import AdoptionStatus
from .pet import PetBrief
from .user import UserBrief


class AdoptionRequest(BaseModel):
    pet_id: int
    message: str | None = None


class AdoptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    adopter_id: int
    previous_owner_id: int
    status: AdoptionStatus
    message: str | None = None


class AdoptionDetailOut(AdoptionOut):
    requested_at: datetime
    completed_at: datetime | None = None
    pet: PetBrief
    adopter: UserBrief
