from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Car, CarCategory
from app.schemas import CategoryCreate, CategoryOut
from app.security import require_staff

router = APIRouter(prefix="/api/categories", tags=["categories"])


def get_category_or_404(category_id, db):
    category = db.query(CarCategory).filter(CarCategory.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


def check_name_is_free(db, name, category_id=None):
    query = db.query(CarCategory).filter(CarCategory.name == name)
    if category_id is not None:
        query = query.filter(CarCategory.id != category_id)
    if query.first() is not None:
        raise HTTPException(status_code=409, detail="Категория с таким названием уже есть")


@router.get("", response_model=list[CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    return db.query(CarCategory).order_by(CarCategory.id).all()


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    check_name_is_free(db, data.name)
    category = CarCategory(name=data.name, description=data.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryCreate, db: Session = Depends(get_db), staff=Depends(require_staff)):
    category = get_category_or_404(category_id, db)
    check_name_is_free(db, data.name, category_id)
    category.name = data.name
    category.description = data.description
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db), staff=Depends(require_staff)):
    category = get_category_or_404(category_id, db)
    if db.query(Car).filter(Car.category_id == category_id).first() is not None:
        raise HTTPException(status_code=409, detail="В категории есть машины, удалить нельзя")
    db.delete(category)
    db.commit()
    return Response(status_code=204)
