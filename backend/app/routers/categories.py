from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CarCategory
from app.schemas import CategoryCreate, CategoryOut
from app.security import require_staff

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    return db.query(CarCategory).all()


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    category = CarCategory(name=data.name, description=data.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
