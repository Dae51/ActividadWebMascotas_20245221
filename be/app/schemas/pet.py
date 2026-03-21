from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from ..models.pet import PetStatus


class PetCreate(BaseModel):
    name: str
    species: str
    breed: str | None = None
    age_years: Decimal | None = None
    description: str | None = None
    photo_url: str | None = None
    is_for_adoption: bool = False


class PetUpdate(BaseModel):
    name: str | None = None
    species: str | None = None
    breed: str | None = None
    age_years: Decimal | None = None
    description: str | None = None
    photo_url: str | None = None
    is_for_adoption: bool | None = None


class PetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    species: str
    breed: str | None = None
    age_years: Decimal | None = None
    description: str | None = None
    photo_url: str | None = None
    is_for_adoption: bool
    status: PetStatus
    created_at: datetime
    updated_at: datetime
