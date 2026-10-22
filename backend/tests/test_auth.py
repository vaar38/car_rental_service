def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_register_login_me(client):
    body = {"name": "Ivan", "email": "ivan-auth@example.com", "password": "password123"}
    response = client.post("/api/auth/register", json=body)
    assert response.status_code == 201
    assert "password" not in response.text and "password_hash" not in response.json()

    tokens = client.post("/api/auth/login", json={"email": body["email"], "password": body["password"]}).json()
    me = client.get("/api/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == body["email"]


def test_register_rejects_short_password_and_duplicate_email(client):
    assert client.post("/api/auth/register", json={"name": "A", "email": "a-auth@example.com", "password": "short"}).status_code == 400
    body = {"name": "A", "email": "dup-auth@example.com", "password": "password123"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409


def test_login_wrong_password(client):
    body = {"name": "B", "email": "b-auth@example.com", "password": "password123"}
    client.post("/api/auth/register", json=body)
    response = client.post("/api/auth/login", json={"email": body["email"], "password": "wrong-password"})
    assert response.status_code == 401


def test_logout_invalidates_token(client, client_user):
    _, headers = client_user
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/users/me", headers=headers).status_code == 401


def test_refresh(client):
    body = {"name": "C", "email": "c-auth@example.com", "password": "password123"}
    client.post("/api/auth/register", json=body)
    tokens = client.post("/api/auth/login", json={"email": body["email"], "password": body["password"]}).json()
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    # access-токен нельзя использовать как refresh
    assert client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401


def test_no_token(client):
    assert client.get("/api/users/me").status_code == 401
