from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.orm import Session

from app.config import ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS, SECRET_KEY
from app.database import get_db
from app.models import Role, User

password_hash = PasswordHash([BcryptHasher()])
bearer = HTTPBearer()


def hash_password(password):
    return password_hash.hash(password)


def verify_password(password, hashed):
    return password_hash.verify(password, hashed)


def create_token(user, token_type):
    if token_type == "access":
        expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    else:
        expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)

    payload = {
        "sub": str(user.id),          # чей токен
        "ver": user.token_version,    # версия: после выхода старые токены не подойдут
        "type": token_type,           # access или refresh
        "exp": expires,               # когда истекает
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# Проверяет токен и возвращает пользователя из базы
def get_user_from_token(token, token_type, db):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Неверный или просроченный токен")

    if payload["type"] != token_type:
        raise HTTPException(status_code=401, detail="Неверный тип токена")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None or user.token_version != payload["ver"]:
        raise HTTPException(status_code=401, detail="Токен больше не действует")

    return user


# Подключается к эндпоинту, если нужен вошедший пользователь
def get_current_user(credentials=Depends(bearer), db: Session = Depends(get_db)):
    return get_user_from_token(credentials.credentials, "access", db)


# Подключается к эндпоинту, если нужен сотрудник
def require_staff(user=Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == user.role_id).first()
    if role.name != "staff":
        raise HTTPException(status_code=403, detail="Доступно только сотрудникам")
    return user
