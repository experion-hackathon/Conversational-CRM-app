def test_login_success_sets_session_cookie(client):
    response = client.post("/auth/login", json={"username": "demo", "password": "demo-password"})
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert "session" in response.cookies


def test_login_wrong_credentials_is_401(client):
    response = client.post("/auth/login", json={"username": "demo", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_CREDENTIALS"


def test_protected_endpoint_without_session_is_401(client):
    response = client.get("/accounts")
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHENTICATED"


def test_protected_endpoint_with_session_succeeds(logged_in_client):
    response = logged_in_client.get("/accounts")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_login_lockout_after_repeated_failures(client):
    # LOGIN_LOCKOUT_ATTEMPTS=3 in the test fixture.
    for _ in range(3):
        r = client.post("/auth/login", json={"username": "demo", "password": "wrong"})
        assert r.status_code == 401
    locked = client.post("/auth/login", json={"username": "demo", "password": "wrong"})
    assert locked.status_code == 429
    assert locked.json()["error_code"] == "LOGIN_LOCKED"
    assert "Retry-After" in locked.headers


def test_logout_invalidates_session(logged_in_client):
    logout_response = logged_in_client.post("/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"invalidated": True}

    after_logout = logged_in_client.get("/accounts")
    assert after_logout.status_code == 401


def test_logout_without_session_is_401(client):
    response = client.post("/auth/logout")
    assert response.status_code == 401
