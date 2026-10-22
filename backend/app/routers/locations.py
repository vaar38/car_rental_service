from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Car, Location
from app.schemas import LocationCreate, LocationOut
from app.security import require_staff

router = APIRouter(prefix="/api/locations", tags=["locations"])


def get_location_or_404(location_id, db):
    location = db.query(Location).filter(Location.id == location_id).first()
    if location is None:
        raise HTTPException(status_code=404, detail="Пункт выдачи не найден")
    return location


@router.get("", response_model=list[LocationOut])
def get_locations(db: Session = Depends(get_db)):
    return db.query(Location).order_by(Location.id).all()


@router.post("", response_model=LocationOut, status_code=201)
def create_location(data: LocationCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    location = Location(name=data.name, address=data.address, city=data.city)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.put("/{location_id}", response_model=LocationOut)
def update_location(location_id: int, data: LocationCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    location = get_location_or_404(location_id, db)
    location.name = data.name
    location.address = data.address
    location.city = data.city
    db.commit()
    db.refresh(location)
    return location


@router.delete("/{location_id}", status_code=204)
def delete_location(location_id: int, db: Session = Depends(get_db), staff=Depends(require_staff)):
    location = get_location_or_404(location_id, db)
    has_cars = db.query(Car).filter(Car.location_id == location_id).first() is not None
    has_bookings = db.query(Booking).filter(
        or_(Booking.pickup_location_id == location_id, Booking.return_location_id == location_id)
    ).first() is not None
    if has_cars or has_bookings:
        raise HTTPException(status_code=409, detail="Пункт используется машинами или бронями, удалить нельзя")
    db.delete(location)
    db.commit()
    return Response(status_code=204)
