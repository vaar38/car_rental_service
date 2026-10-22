def test_update_name(client, client_user):
    _, headers = client_user
    response = client.patch("/api/users/me", json={"name": "New Name"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_update_email_taken(client, make_user):
    other, _ = make_user()
    _, headers = make_user()
    response = client.patch("/api/users/me", json={"email": other.email}, headers=headers)
    assert response.status_code == 409


def test_null_field_rejected(client, client_user):
    _, headers = client_user
    assert client.patch("/api/users/me", json={"name": None}, headers=headers).status_code == 422


def test_change_password_logs_out_old_tokens(client, client_user):
    user, headers = client_user
    assert client.patch("/api/users/me", json={"password": "short"}, headers=headers).status_code == 400

    response = client.patch("/api/users/me", json={"password": "new-password-1"}, headers=headers)
    assert response.status_code == 200
    assert client.get("/api/users/me", headers=headers).status_code == 401

    login = client.post("/api/auth/login", json={"email": user.email, "password": "new-password-1"})
    assert login.status_code == 200


def test_cannot_change_role(client, client_user):
    user, headers = client_user
    role_id = user.role_id
    client.patch("/api/users/me", json={"role_id": 999}, headers=headers)
    assert client.get("/api/users/me", headers=headers).json()["role_id"] == role_id
