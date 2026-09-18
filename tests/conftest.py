
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    chroma_path = str(tmp_path / "chroma")

    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("CHROMA_PERSIST_DIR", chroma_path)
    monkeypatch.setenv("SHARED_USERNAME", "demo")
    monkeypatch.setenv("SHARED_PASSWORD", "demo-password")
    monkeypatch.setenv("NLU_ENGINE", "rule_based")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")  # tests should not hit the rate limiter incidentally
    monkeypatch.setenv("LOGIN_LOCKOUT_ATTEMPTS", "3")
    monkeypatch.setenv("LOGIN_LOCKOUT_WINDOW_MINUTES", "15")

    import app.auth as auth_module
    import app.database as database_module
    import app.vector_store as vector_store_module

    database_module._engine = None
    database_module._SessionLocal = None
    database_module.init_engine(db_path)

    vector_store_module.reset_for_tests(chroma_path)
    auth_module.reset_state_for_tests()

    from app.main import app

    # base_url uses https:// because the session cookie is set with the
    # Secure flag (SEC-2) -- httpx's cookie jar correctly refuses to resend a
    # Secure cookie over a plain http:// connection, which the default
    # TestClient base_url uses. This is the standard fix, not a relaxation of
    # the Secure flag itself (still enforced in the actual response headers).
    with TestClient(app, base_url="https://testserver") as c:
        yield c


@pytest.fixture()
def logged_in_client(client):
    response = client.post("/auth/login", json={"username": "demo", "password": "demo-password"})
    assert response.status_code == 200, response.text
    return client
