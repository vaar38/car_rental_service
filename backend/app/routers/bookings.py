from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Car
from app.schemas import BookingCreate, BookingOut
from app.security import get_current_user


router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(
    data: BookingCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if date.today() > data.start_date:
        raise HTTPException(status_code=400, detail="Нельзя забронировать на прошедшую дату.")
    if data.end_date <= data.start_date:
        raise HTTPException(status_code=400, detail="Аренда минимум на 1 день: дата окончания должна быть позже даты начала")

    car = db.query(Car).filter(Car.id == data.car_id).first()
    if car is None:
        raise HTTPException(status_code=404, detail="Машина не найдена")

    overlapping = db.query(Booking).filter(
        Booking.car_id == data.car_id,
        Booking.status.in_(["pending", "confirmed", "active"]),
        Booking.start_date < data.end_date,
        Booking.end_date > data.start_date,
    ).first()
    if overlapping is not None:
        raise HTTPException(status_code=409, detail="Машина уже забронирована на эти даты")