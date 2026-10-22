from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

CarStatus = Literal["available", "rented", "maintenance"]
BookingStatus = Literal["pending", "confirmed", "active", "completed", "cancelled"]


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


# PATCH /users/me: передаются только поля, которые нужно изменить.
# Значение по умолчанию None не проверяется, а явный null в запросе даст 422.
class UserUpdate(BaseModel):
    name: str = Field(None, min_length=1, max_length=100)
    email: str = Field(None, min_length=3, max_length=255)
    password: str = Field(None)


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)


class LocationOut(BaseModel):
    id: int
    name: str
    address: str
    city: str

    model_config = {"from_attributes": True}


def normalize_plate(value):
    # "а123вс 77" и "А123ВС77" — один и тот же номер
    if value is None:
        return value
    return value.replace(" ", "").upper()


class CarCreate(BaseModel):
    category_id: int
    location_id: int
    brand: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=50)
    license_plate: str = Field(min_length=1, max_length=20)
    year: int = Field(ge=1990)
    price_per_day: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

    _plate = field_validator("license_plate")(normalize_plate)


# PATCH /cars/{id}: все поля необязательные, меняются только переданные
class CarUpdate(BaseModel):
    category_id: int = None
    location_id: int = None
    brand: str = Field(None, min_length=1, max_length=50)
    model: str = Field(None, min_length=1, max_length=50)
    license_plate: str = Field(None, min_length=1, max_length=20)
    year: int = Field(None, ge=1990)
    price_per_day: Decimal = Field(None, gt=0, max_digits=10, decimal_places=2)
    status: CarStatus = None

    _plate = field_validator("license_plate")(normalize_plate)


class CarOut(BaseModel):
    id: int
    category_id: int
    location_id: int
    brand: str
    model: str
    license_plate: str
    year: int
    price_per_day: Decimal
    status: str
    created_at: datetime
    # Заполняется, только если в GET /cars переданы start_date и end_date
    available: bool | None = None

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    car_id: int
    pickup_location_id: int
    return_location_id: int
    start_date: date
    end_date: date


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingOut(BaseModel):
    id: int
    user_id: int
    car_id: int
    pickup_location_id: int
    return_location_id: int
    start_date: date
    end_date: date
    total_price: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
