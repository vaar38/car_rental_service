"""Общие фикстуры для тестов API.

Тесты идут на настоящем PostgreSQL (миграции должны быть применены).
Каждый тест работает внутри транзакции, которая в конце откатывается,
поэтому в базе ничего не остаётся. Отдельную базу можно задать через
переменную окружения TEST_DATABASE_URL.
"""
import os
from datetime import date, timedelta
from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import engine as app_engine
from app.database import get_db
from app.main import app
from app.models import Car, CarCategory, Location, Role, User
from app.security import create_token, hash_password

engine = create_engine(os.environ["TEST_DATABASE_URL"]) if os.getenv("TEST_DATABASE_URL") else app_engine
_ids = count(1)


def days(n):
    """Дата через n дней от сегодня в формате для JSON."""
    return (date.today() + timedelta(days=n)).isoformat()


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db):
    """Создаёт пользователя с ролью и возвращает (user, заголовки с токеном)."""
    def _make_user(role="client"):
        n = next(_ids)
        role_row = db.query(Role).filter(Role.name == role).one()
        user = User(
            name=f"Test {n}",
            email=f"test-{n}-{role}@example.com",
            password_hash=hash_password("password123"),
            role_id=role_row.id,
            token_version=0,
        )
        db.add(user)
        db.flush()
        headers = {"Authorization": f"Bearer {create_token(user, 'access')}"}
        return user, headers
    return _make_user


@pytest.fixture
def client_user(make_user):
    return make_user("client")


@pytest.fixture
def staff_user(make_user):
    return make_user("staff")


@pytest.fixture
def category(db):
    row = CarCategory(name=f"Category {next(_ids)}")
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def location(db):
    row = Location(name=f"Point {next(_ids)}", address="Street 1", city="Moscow")
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def make_car(db, category, location):
    def _make_car(price=50, status="available"):
        car = Car(
            category_id=category.id,
            location_id=location.id,
            brand="Toyota",
            model="Camry",
            license_plate=f"T{next(_ids)}EST",
            year=2022,
            price_per_day=price,
            status=status,
        )
        db.add(car)
        db.flush()
        return car
    return _make_car


@pytest.fixture
def car(make_car):
    return make_car()


@pytest.fixture
def booking_body(car, location):
    def _body(start, end, car_id=None):
        return {
            "car_id": car_id or car.id,
            "pickup_location_id": location.id,
            "return_location_id": location.id,
            "start_date": days(start),
            "end_date": days(end),
        }
    return _body
