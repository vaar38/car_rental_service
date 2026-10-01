from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, User
from app.schemas import RefreshIn, TokensOut, UserLogin, UserOut, UserRegister
from app.security import create_token, get_current_user, get_user_from_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен быть не короче 8 символов")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже есть")

    # Через регистрацию можно стать только клиентом
    client_role = db.query(Role).filter(Role.name == "client").first()

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role_id=client_role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokensOut)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    # Одинаковая ошибка для неверного email и неверного пароля
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    return {
        "access_token": create_token(user, "access"),
        "refresh_token": create_token(user, "refresh"),
    }


@router.post("/refresh", response_model=TokensOut)
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    user = get_user_from_token(data.refresh_token, "refresh", db)
    return {
        "access_token": create_token(user, "access"),
        "refresh_token": create_token(user, "refresh"),
    }


@router.post("/logout", status_code=204)
def logout(user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Увеличиваем версию — все выданные раньше токены перестают работать
    user.token_version = user.token_version + 1
    db.commit()
