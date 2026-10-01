from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    name: str
    address: str
    city: str


class LocationOut(BaseModel):
    id: int
    name: str
    address: str
    city: str

    model_config = {"from_attributes": True}


class CarCreate(BaseModel):
    category_id: int
    location_id: int
    brand: str
    model: str
    year: int
    price_per_day: Decimal


class CarOut(BaseModel):
    id: int
    category_id: int
    location_id: int
    brand: str
    model: str
    year: int
    price_per_day: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
