from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models.pet import PetStatus


Species = Literal["dog", "cat", "rabbit", "bird"]


class PetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    species: Species
    breed: str | None = Field(default=None, max_length=100)
    age_years: Decimal | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    photo_url: str | None = Field(default=None, max_length=500)
    is_for_adoption: bool = False


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    species: Species | None = None
    breed: str | None = Field(default=None, max_length=100)
    age_years: Decimal | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    photo_url: str | None = Field(default=None, max_length=500)
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


class PetBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    species: str
    photo_url: str | None = None
