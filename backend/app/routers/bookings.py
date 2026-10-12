from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Car, Role
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
    days = (data.end_date - data.start_date).days
    total_price = car.price_per_day * days
    booking = Booking(
        user_id=user.id,
        car_id=data.car_id,
        pickup_location_id=data.pickup_location_id,
        return_location_id=data.return_location_id,
        start_date=data.start_date,
        end_date=data.end_date,
        total_price=total_price,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=list[BookingOut])
def get_bookings(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Booking)

    role = db.query(Role).filter(Role.id == user.role_id).first()

    if role.name != "staff":
        query = query.filter(Booking.user_id == user.id)
    
    return query.order_by(Booking.start_date).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    
    role = db.query(Role).filter(Role.id == user.role_id).first()

    if role.name != "staff" and booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    
    return booking 