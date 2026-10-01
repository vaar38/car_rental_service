from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Location
from app.schemas import LocationCreate, LocationOut
from app.security import require_staff

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[LocationOut])
def get_locations(db: Session = Depends(get_db)):
    return db.query(Location).all()


@router.post("", response_model=LocationOut, status_code=201)
def create_location(data: LocationCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    location = Location(name=data.name, address=data.address, city=data.city)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location
