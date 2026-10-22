from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Booking


def create(client, headers, body):
    return client.post("/api/bookings", json=body, headers=headers)


# --- Создание и расчёт цены ---

def test_create_booking_price_and_owner(client, client_user, booking_body, car):
    user, headers = client_user
    response = create(client, headers, {**booking_body(10, 13), "user_id": 999999, "total_price": 1})
    assert response.status_code == 201
    data = response.json()
    assert Decimal(data["total_price"]) == car.price_per_day * 3
    assert data["user_id"] == user.id
    assert data["status"] == "pending"


@pytest.mark.parametrize("start,end", [(-1, 3), (3, 3), (5, 3)])
def test_invalid_dates(client, client_user, booking_body, start, end):
    _, headers = client_user
    assert create(client, headers, booking_body(start, end)).status_code == 400


def test_unknown_car_and_location(client, client_user, booking_body):
    _, headers = client_user
    assert create(client, headers, booking_body(3, 5, car_id=99999999)).status_code == 404
    body = {**booking_body(3, 5), "return_location_id": 99999999}
    assert create(client, headers, body).status_code == 404


def test_car_in_maintenance(client, client_user, booking_body, make_car):
    _, headers = client_user
    broken = make_car(status="maintenance")
    assert create(client, headers, booking_body(3, 5, car_id=broken.id)).status_code == 409


def test_requires_token(client, booking_body):
    assert client.post("/api/bookings", json=booking_body(3, 5)).status_code == 401


# --- Пересечение дат ---

@pytest.mark.parametrize("start,end,expected", [
    (11, 13, 409),  # внутри существующей 10-12
    (9, 13, 409),   # накрывает существующую
    (9, 11, 409),   # заходит слева
    (12, 14, 201),  # стык справа: вернули 12-го, взяли 12-го
    (8, 10, 201),   # стык слева
])
def test_overlap(client, client_user, make_user, booking_body, start, end, expected):
    _, headers = client_user
    _, other_headers = make_user()
    assert create(client, headers, booking_body(10, 12)).status_code == 201
    assert create(client, other_headers, booking_body(start, end)).status_code == expected


def test_cancelled_booking_frees_dates(client, client_user, booking_body):
    _, headers = client_user
    booking_id = create(client, headers, booking_body(10, 12)).json()["id"]
    assert client.delete(f"/api/bookings/{booking_id}", headers=headers).status_code == 200
    assert create(client, headers, booking_body(10, 12)).status_code == 201


def test_other_car_same_dates(client, client_user, booking_body, make_car):
    _, headers = client_user
    other = make_car()
    assert create(client, headers, booking_body(10, 12)).status_code == 201
    assert create(client, headers, booking_body(10, 12, car_id=other.id)).status_code == 201


def test_database_constraint_blocks_double_booking(db, client_user, car, location):
    """Даже в обход API база не даст сохранить пересекающиеся брони."""
    user, _ = client_user
    start = date.today() + timedelta(days=10)
    common = dict(user_id=user.id, car_id=car.id, pickup_location_id=location.id,
                  return_location_id=location.id, total_price=100, status="pending")
    db.add(Booking(start_date=start, end_date=start + timedelta(days=2), **common))
    db.flush()
    db.add(Booking(start_date=start + timedelta(days=1), end_date=start + timedelta(days=3), **common))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- Просмотр и изоляция чужих данных ---

def test_list_own_and_staff_sees_all(client, client_user, make_user, staff_user, booking_body):
    _, headers = client_user
    _, other_headers = make_user()
    _, staff_headers = staff_user
    mine = create(client, headers, booking_body(10, 12)).json()["id"]
    theirs = create(client, other_headers, booking_body(20, 22)).json()["id"]

    own_ids = [b["id"] for b in client.get("/api/bookings", headers=headers).json()]
    assert own_ids == [mine]

    staff_ids = {b["id"] for b in client.get("/api/bookings", headers=staff_headers).json()}
    assert {mine, theirs} <= staff_ids


def test_foreign_booking_is_404(client, client_user, make_user, staff_user, booking_body):
    _, headers = client_user
    _, other_headers = make_user()
    _, staff_headers = staff_user
    booking_id = create(client, headers, booking_body(10, 12)).json()["id"]

    assert client.get(f"/api/bookings/{booking_id}", headers=headers).status_code == 200
    assert client.get(f"/api/bookings/{booking_id}", headers=staff_headers).status_code == 200
    foreign = client.get(f"/api/bookings/{booking_id}", headers=other_headers)
    missing = client.get("/api/bookings/99999999", headers=other_headers)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()

    # отменить чужую бронь тоже нельзя
    assert client.delete(f"/api/bookings/{booking_id}", headers=other_headers).status_code == 404


# --- Отмена ---

def test_cancel(client, client_user, booking_body):
    _, headers = client_user
    booking_id = create(client, headers, booking_body(10, 12)).json()["id"]
    response = client.delete(f"/api/bookings/{booking_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    # запись не удалена
    assert client.get(f"/api/bookings/{booking_id}", headers=headers).status_code == 200
    # повторно отменить нельзя
    assert client.delete(f"/api/bookings/{booking_id}", headers=headers).status_code == 409


def test_cannot_cancel_active(client, client_user, staff_user, booking_body):
    _, headers = client_user
    _, staff_headers = staff_user
    booking_id = create(client, headers, booking_body(1, 3)).json()["id"]
    client.patch(f"/api/bookings/{booking_id}", json={"status": "confirmed"}, headers=staff_headers)
    client.patch(f"/api/bookings/{booking_id}", json={"status": "active"}, headers=staff_headers)
    assert client.delete(f"/api/bookings/{booking_id}", headers=headers).status_code == 409


# --- Смена статуса сотрудником ---

def test_status_flow_updates_car(client, db, client_user, staff_user, make_car, booking_body):
    _, headers = client_user
    _, staff_headers = staff_user
    car = make_car()
    body = booking_body(1, 3, car_id=car.id)
    return_point = client.post("/api/locations", json={"name": "Airport", "address": "SVO", "city": "Moscow"}, headers=staff_headers).json()["id"]
    body["return_location_id"] = return_point
    booking_id = create(client, headers, body).json()["id"]

    def set_status(status):
        return client.patch(f"/api/bookings/{booking_id}", json={"status": status}, headers=staff_headers)

    assert set_status("active").status_code == 409  # нельзя выдать неподтверждённую
    assert set_status("confirmed").status_code == 200
    assert set_status("active").status_code == 200
    db.refresh(car)
    assert car.status == "rented"

    assert set_status("completed").json()["status"] == "completed"
    db.refresh(car)
    assert car.status == "available"
    assert car.location_id == return_point

    assert set_status("cancelled").status_code == 409  # завершённую не отменить


def test_status_change_requires_staff(client, client_user, booking_body):
    _, headers = client_user
    booking_id = create(client, headers, booking_body(10, 12)).json()["id"]
    response = client.patch(f"/api/bookings/{booking_id}", json={"status": "confirmed"}, headers=headers)
    assert response.status_code == 403


def test_status_change_validation(client, staff_user):
    _, staff_headers = staff_user
    assert client.patch("/api/bookings/99999999", json={"status": "confirmed"}, headers=staff_headers).status_code == 404
    assert client.patch("/api/bookings/1", json={"status": "lost"}, headers=staff_headers).status_code == 422
