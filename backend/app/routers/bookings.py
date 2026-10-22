from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Car, Location, Role
from app.schemas import BookingCreate, BookingOut, BookingStatusUpdate
from app.security import get_current_user, is_staff, require_staff


router = APIRouter(prefix="/api/bookings", tags=["bookings"])

# Какие статусы сотрудник может поставить из текущего
ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"active", "cancelled"},
    "active": {"completed"},
    "completed": set(),
    "cancelled": set(),
}
# Клиент может отменить бронь, пока машину не выдали
CANCELLABLE_STATUSES = {"pending", "confirmed"}


def get_visible_booking(booking_id, user, db):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    # Чужая бронь для клиента выглядит так же, как несуществующая
    if booking is None or (booking.user_id != user.id and not is_staff(user, db)):
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    return booking


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
    if car.status == "maintenance":
        raise HTTPException(status_code=409, detail="Машина на обслуживании")

    for location_id in {data.pickup_location_id, data.return_location_id}:
        if db.query(Location).filter(Location.id == location_id).first() is None:
            raise HTTPException(status_code=404, detail="Пункт выдачи не найден")

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
    try:
        db.commit()
    except IntegrityError:
        # Два запроса одновременно прошли проверку выше,
        # второй отклонило ограничение no_overlapping_bookings в базе
        db.rollback()
        raise HTTPException(status_code=409, detail="Машина уже забронирована на эти даты")
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


# Смена статуса сотрудником при подтверждении, выдаче и возврате машины
@router.patch("/{booking_id}", response_model=BookingOut)
def update_booking_status(
    booking_id: int,
    data: BookingStatusUpdate,
    staff=Depends(require_staff),
    db: Session = Depends(get_db),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    if data.status not in ALLOWED_TRANSITIONS[booking.status]:
        raise HTTPException(status_code=409, detail=f"Нельзя перевести бронь из {booking.status} в {data.status}")

    car = db.query(Car).filter(Car.id == booking.car_id).first()
    if data.status == "active":
        car.status = "rented"
    elif data.status == "completed":
        # Машина возвращена: снова свободна и стоит в пункте возврата
        car.status = "available"
        car.location_id = booking.return_location_id

    booking.status = data.status
    db.commit()
    db.refresh(booking)
    return booking


# Отмена: запись не удаляется, статус меняется на cancelled
@router.delete("/{booking_id}", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = get_visible_booking(booking_id, user, db)
    if booking.status not in CANCELLABLE_STATUSES:
        raise HTTPException(status_code=409, detail=f"Бронь в статусе {booking.status} отменить нельзя")

    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking
