from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Car, CarCategory, Location
from app.schemas import CarCreate, CarOut, CarStatus, CarUpdate
from app.security import require_staff

router = APIRouter(prefix="/api/cars", tags=["cars"])

ACTIVE_BOOKING_STATUSES = ["pending", "confirmed", "active"]


def get_car_or_404(car_id, db):
    car = db.query(Car).filter(Car.id == car_id).first()
    if car is None:
        raise HTTPException(status_code=404, detail="Машина не найдена")
    return car


def check_references(db, category_id=None, location_id=None):
    if category_id is not None and db.query(CarCategory).filter(CarCategory.id == category_id).first() is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    if location_id is not None and db.query(Location).filter(Location.id == location_id).first() is None:
        raise HTTPException(status_code=404, detail="Пункт выдачи не найден")


def check_plate_is_free(db, license_plate, car_id=None):
    query = db.query(Car).filter(Car.license_plate == license_plate)
    if car_id is not None:
        query = query.filter(Car.id != car_id)
    if query.first() is not None:
        raise HTTPException(status_code=409, detail="Машина с таким госномером уже есть")


@router.get("", response_model=list[CarOut])
def get_cars(
    db: Session = Depends(get_db),
    category_id: int | None = None,
    location_id: int | None = None,
    status: CarStatus | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    if (start_date is None) != (end_date is None):
        raise HTTPException(status_code=400, detail="Укажите обе даты: start_date и end_date")
    if start_date is not None and end_date <= start_date:
        raise HTTPException(status_code=400, detail="Дата окончания должна быть позже даты начала")

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
    cars = query.order_by(Car.id).all()
    if start_date is None:
        return cars

    # Признак доступности на выбранные даты: машина не на обслуживании
    # и у неё нет активной брони, пересекающейся с периодом
    busy = db.query(Booking.car_id).filter(
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        Booking.start_date < end_date,
        Booking.end_date > start_date,
    )
    busy_ids = {row.car_id for row in busy}
    return [
        CarOut.model_validate(car).model_copy(
            update={"available": car.status != "maintenance" and car.id not in busy_ids}
        )
        for car in cars
    ]


@router.get("/{car_id}", response_model=CarOut)
def get_car(car_id: int, db: Session = Depends(get_db)):
    return get_car_or_404(car_id, db)


@router.post("", response_model=CarOut, status_code=201)
def create_car(data: CarCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    check_references(db, data.category_id, data.location_id)
    check_plate_is_free(db, data.license_plate)

    car = Car(**data.model_dump())
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


# PUT заменяет все данные машины; статус меняется через PATCH
@router.put("/{car_id}", response_model=CarOut)
def replace_car(car_id: int, data: CarCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    car = get_car_or_404(car_id, db)
    check_references(db, data.category_id, data.location_id)
    check_plate_is_free(db, data.license_plate, car_id)

    for field, value in data.model_dump().items():
        setattr(car, field, value)
    db.commit()
    db.refresh(car)
    return car


@router.patch("/{car_id}", response_model=CarOut)
def update_car(car_id: int, data: CarUpdate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    car = get_car_or_404(car_id, db)
    changes = data.model_dump(exclude_unset=True)
    check_references(db, changes.get("category_id"), changes.get("location_id"))
    if "license_plate" in changes:
        check_plate_is_free(db, changes["license_plate"], car_id)

    for field, value in changes.items():
        setattr(car, field, value)
    db.commit()
    db.refresh(car)
    return car


# Машину с историей броней не удаляем: брони на неё ссылаются.
# Чтобы убрать её из оборота, есть PATCH со статусом maintenance.
@router.delete("/{car_id}", status_code=204)
def delete_car(car_id: int, db: Session = Depends(get_db), staff=Depends(require_staff)):
    car = get_car_or_404(car_id, db)
    if db.query(Booking).filter(Booking.car_id == car_id).first() is not None:
        raise HTTPException(status_code=409, detail="У машины есть брони, удалить нельзя. Переведите её в статус maintenance")

    db.delete(car)
    db.commit()
    return Response(status_code=204)
