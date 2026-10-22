"""Справочники: категории и пункты выдачи."""


def test_read_is_public(client, category, location):
    assert client.get("/api/categories").status_code == 200
    assert client.get("/api/locations").status_code == 200


def test_write_requires_staff(client, client_user):
    _, headers = client_user
    assert client.post("/api/categories", json={"name": "SUV"}, headers=headers).status_code == 403
    assert client.post("/api/locations", json={"name": "A", "address": "B", "city": "C"}, headers=headers).status_code == 403


def test_category_crud(client, staff_user):
    _, headers = staff_user
    created = client.post("/api/categories", json={"name": "Test SUV"}, headers=headers)
    assert created.status_code == 201
    category_id = created.json()["id"]

    assert client.post("/api/categories", json={"name": "Test SUV"}, headers=headers).status_code == 409

    updated = client.put(f"/api/categories/{category_id}", json={"name": "Test Crossover", "description": "4x4"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Test Crossover"

    assert client.delete(f"/api/categories/{category_id}", headers=headers).status_code == 204
    assert client.put(f"/api/categories/{category_id}", json={"name": "X"}, headers=headers).status_code == 404


def test_category_with_cars_cannot_be_deleted(client, staff_user, car):
    _, headers = staff_user
    assert client.delete(f"/api/categories/{car.category_id}", headers=headers).status_code == 409


def test_location_crud(client, staff_user):
    _, headers = staff_user
    body = {"name": "Center", "address": "Tverskaya 1", "city": "Moscow"}
    created = client.post("/api/locations", json=body, headers=headers)
    assert created.status_code == 201
    location_id = created.json()["id"]

    updated = client.put(f"/api/locations/{location_id}", json={**body, "city": "Kazan"}, headers=headers)
    assert updated.json()["city"] == "Kazan"

    assert client.delete(f"/api/locations/{location_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/locations/{location_id}", headers=headers).status_code == 404


def test_location_in_use_cannot_be_deleted(client, staff_user, car):
    _, headers = staff_user
    assert client.delete(f"/api/locations/{car.location_id}", headers=headers).status_code == 409


def test_empty_name_rejected(client, staff_user):
    _, headers = staff_user
    assert client.post("/api/categories", json={"name": ""}, headers=headers).status_code == 422
