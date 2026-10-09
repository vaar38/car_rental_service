from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Car
from app.schemas import CarCreate, CarOut
from app.security import require_staff
from decimal import Decimal

router = APIRouter(prefix="/api/cars", tags=["cars"])


@router.get("", response_model=list[CarOut])
def get_cars(
    db: Session = Depends(get_db),
    category_id: int | None = None,
    location_id: int | None = None,
    status: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
):

    query = db.query(Car)

    if category_id is not None:
        query = query.filter(Car.category_id == category_id)
    if location_id is not None:
        query = query.filter(Car.location_id == location_id)
    if status is not None:
        query = query.filter(Car.status == status)
    if min_price is not None:
        query = query.filter(Car.price_per_day >= min_price)
    if max_price is not None:
        query = query.filter(Car.price_per_day <= max_price)
    return query.all()


@router.get("/{car_id}", response_model=CarOut)
def get_car(car_id: int, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.id == car_id).first()
    if car is None:
        raise HTTPException(status_code=404, detail="Машина не найдена")
    return car


@router.post("", response_model=CarOut, status_code=201)
def create_car(data: CarCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    car = Car(
        category_id=data.category_id,
        location_id=data.location_id,
        brand=data.brand,
        model=data.model,
        year=data.year,
        price_per_day=data.price_per_day,
    )
    db.add(car)
    db.commit()
    db.refresh(car)
    return car
