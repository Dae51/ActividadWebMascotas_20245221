from pydantic import BaseModel, ConfigDict

from ..models.adoption import AdoptionStatus


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
