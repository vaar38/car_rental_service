from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Car
from app.schemas import CarCreate, CarOut
from app.security import require_staff

router = APIRouter(prefix="/api/cars", tags=["cars"])


@router.get("", response_model=list[CarOut])
def get_cars(db: Session = Depends(get_db)):
    return db.query(Car).all()


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
