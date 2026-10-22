"""Назначает зарегистрированного пользователя сотрудником.

Запуск из папки backend:
    python -m app.make_staff user@example.com
"""
import sys

from app.database import SessionLocal
from app.models import Role, User


def make_staff(email):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"Пользователь {email} не найден. Сначала зарегистрируйтесь через /api/auth/register")
            return 1
        staff_role = db.query(Role).filter(Role.name == "staff").first()
        if staff_role is None:
            print("Роль staff не найдена. Примените миграции: alembic upgrade head")
            return 1
        user.role_id = staff_role.id
        db.commit()
        print(f"{email} теперь сотрудник")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python -m app.make_staff <email>")
        sys.exit(1)
    sys.exit(make_staff(sys.argv[1]))
