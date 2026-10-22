from tests.conftest import days


def car_body(category, location, **overrides):
    body = {
        "category_id": category.id,
        "location_id": location.id,
        "brand": "Kia",
        "model": "Rio",
        "license_plate": "а123вс 77",
        "year": 2021,
        "price_per_day": "40.00",
    }
    body.update(overrides)
    return body


def test_create_car(client, staff_user, category, location):
    _, headers = staff_user
    response = client.post("/api/cars", json=car_body(category, location), headers=headers)
    assert response.status_code == 201
    assert response.json()["license_plate"] == "А123ВС77"
    assert response.json()["status"] == "available"


def test_create_car_requires_staff(client, client_user, category, location):
    _, headers = client_user
    assert client.post("/api/cars", json=car_body(category, location), headers=headers).status_code == 403


def test_duplicate_plate(client, staff_user, category, location):
    _, headers = staff_user
    assert client.post("/api/cars", json=car_body(category, location), headers=headers).status_code == 201
    # тот же номер в другом написании
    duplicate = car_body(category, location, license_plate="А123ВС77")
    assert client.post("/api/cars", json=duplicate, headers=headers).status_code == 409


def test_unknown_category_or_location(client, staff_user, category, location):
    _, headers = staff_user
    assert client.post("/api/cars", json=car_body(category, location, category_id=99999999), headers=headers).status_code == 404
    assert client.post("/api/cars", json=car_body(category, location, location_id=99999999), headers=headers).status_code == 404


def test_invalid_values(client, staff_user, category, location):
    _, headers = staff_user
    assert client.post("/api/cars", json=car_body(category, location, year=1980), headers=headers).status_code == 422
    assert client.post("/api/cars", json=car_body(category, location, price_per_day="0"), headers=headers).status_code == 422


def test_get_car(client, car):
    assert client.get(f"/api/cars/{car.id}").json()["id"] == car.id
    assert client.get("/api/cars/99999999").status_code == 404


def test_filters(client, make_car, category):
    cheap = make_car(price=30)
    expensive = make_car(price=200)
    ids = {c["id"] for c in client.get("/api/cars", params={"max_price": 100, "category_id": category.id}).json()}
    assert cheap.id in ids and expensive.id not in ids


def test_availability_flag(client, make_car, client_user, booking_body):
    busy = make_car()
    free = make_car()
    in_service = make_car(status="maintenance")
    _, headers = client_user
    assert client.post("/api/bookings", json=booking_body(10, 12, car_id=busy.id), headers=headers).status_code == 201

    cars = {c["id"]: c for c in client.get("/api/cars", params={"start_date": days(11), "end_date": days(13)}).json()}
    assert cars[busy.id]["available"] is False
    assert cars[free.id]["available"] is True
    assert cars[in_service.id]["available"] is False

    # стык дат по правилу отеля: вернули 12-го, можно взять 12-го
    cars = {c["id"]: c for c in client.get("/api/cars", params={"start_date": days(12), "end_date": days(14)}).json()}
    assert cars[busy.id]["available"] is True

    # без дат признак не считается
    assert client.get(f"/api/cars/{busy.id}").json()["available"] is None


def test_availability_dates_validation(client):
    assert client.get("/api/cars", params={"start_date": days(1)}).status_code == 400
    assert client.get("/api/cars", params={"start_date": days(3), "end_date": days(3)}).status_code == 400


def test_put_and_patch(client, staff_user, car, category, location):
    _, headers = staff_user
    replaced = client.put(f"/api/cars/{car.id}", json=car_body(category, location, brand="Lada", license_plate="B777OO"), headers=headers)
    assert replaced.status_code == 200
    assert replaced.json()["brand"] == "Lada"

    patched = client.patch(f"/api/cars/{car.id}", json={"status": "maintenance", "price_per_day": "55.50"}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["status"] == "maintenance"
    assert patched.json()["brand"] == "Lada"

    assert client.patch(f"/api/cars/{car.id}", json={"status": "broken"}, headers=headers).status_code == 422
    assert client.patch(f"/api/cars/{car.id}", json={"brand": None}, headers=headers).status_code == 422


def test_patch_plate_conflict(client, staff_user, make_car):
    _, headers = staff_user
    first = make_car()
    second = make_car()
    response = client.patch(f"/api/cars/{second.id}", json={"license_plate": first.license_plate}, headers=headers)
    assert response.status_code == 409
    # свой же номер — не конфликт
    assert client.patch(f"/api/cars/{first.id}", json={"license_plate": first.license_plate}, headers=headers).status_code == 200


def test_delete_car(client, staff_user, client_user, make_car, booking_body):
    _, staff_headers = staff_user
    _, client_headers = client_user
    unused = make_car()
    booked = make_car()
    client.post("/api/bookings", json=booking_body(5, 7, car_id=booked.id), headers=client_headers)

    assert client.delete(f"/api/cars/{unused.id}", headers=client_headers).status_code == 403
    assert client.delete(f"/api/cars/{unused.id}", headers=staff_headers).status_code == 204
    assert client.get(f"/api/cars/{unused.id}").status_code == 404
    assert client.delete(f"/api/cars/{booked.id}", headers=staff_headers).status_code == 409
