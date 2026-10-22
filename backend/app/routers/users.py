from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserOut, UserUpdate
from app.security import get_current_user, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(user=Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    changes = data.model_dump(exclude_unset=True)

    if "email" in changes:
        existing = db.query(User).filter(User.email == changes["email"], User.id != user.id).first()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Пользователь с таким email уже есть")
        user.email = changes["email"]

    if "name" in changes:
        user.name = changes["name"]

    if "password" in changes:
        if len(changes["password"]) < 8:
            raise HTTPException(status_code=400, detail="Пароль должен быть не короче 8 символов")
        user.password_hash = hash_password(changes["password"])
        # После смены пароля все старые токены перестают работать, нужно войти заново
        user.token_version = user.token_version + 1

    db.commit()
    db.refresh(user)
    return user
