import pytest
from server import running_server

DEFAULT_USERNAME = "qa-user"
DEFAULT_PASSWORD = "qa-password-for-independent-testing"


@pytest.fixture(scope="module")
def server():
    """A real backend process with generous rate/lockout limits, for tests
    that are not specifically about those thresholds."""
    with running_server() as s:
        yield s


@pytest.fixture()
def anon_client(server):
    """No session cookie -- for authorization-boundary tests."""
    import httpx

    with httpx.Client(base_url=server.base_url) as c:
        yield c


@pytest.fixture()
def client(server):
    """Logged-in session, matching the real login flow (not a fabricated cookie).

    The session cookie is set with Secure (SEC-2), which httpx's cookie jar
    correctly refuses to resend automatically over this suite's plain
    http://127.0.0.1 connection (the same class of issue the backend's own
    TestClient hit -- see BACKEND report v1.0's fixes-made list). Rather than
    stand up TLS for a local QA harness, the token is extracted from the real
    Set-Cookie response and re-attached explicitly -- the login and the token
    itself are both genuine, only the transport-level auto-resend is worked
    around."""
    import httpx

    with httpx.Client(base_url=server.base_url) as c:
        r = c.post("/auth/login", json={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD})
        assert r.status_code == 200, r.text
        token = r.cookies.get("session")
        assert token, "login did not set a session cookie"
        c.cookies.set("session", token)
        yield c
