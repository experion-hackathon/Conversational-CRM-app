"""Verifies the actual configured thresholds trigger for real, against a
dedicated low-threshold server instance -- not just that the mechanism exists
in code, but that the Nth request/attempt is genuinely where the boundary is.
"""
import httpx
import pytest
from server import running_server


@pytest.fixture(scope="module")
def rate_limited_server():
    with running_server({"RATE_LIMIT_PER_MINUTE": "3"}) as s:
        yield s


@pytest.fixture(scope="module")
def lockout_server():
    with running_server({"LOGIN_LOCKOUT_ATTEMPTS": "3", "LOGIN_LOCKOUT_WINDOW_MINUTES": "15"}) as s:
        yield s


def test_rate_limit_triggers_at_the_configured_threshold_not_before_or_after(rate_limited_server):
    with httpx.Client(base_url=rate_limited_server.base_url) as setup:
        r = setup.post("/auth/login", json={"username": "qa-user", "password": "qa-password-for-independent-testing"})
        token = r.cookies.get("session")

    client = httpx.Client(base_url=rate_limited_server.base_url)
    client.cookies.set("session", token)

    statuses = []
    for _ in range(4):
        resp = client.post("/qa", json={"question": "what did we discuss with Acme"})
        statuses.append(resp.status_code)

    assert statuses[:3] == [200, 200, 200], f"first 3 requests (at the limit) should all succeed, got {statuses}"
    assert statuses[3] == 429, f"4th request (over the limit of 3/min) should be rate-limited, got {statuses}"
    fourth = client.post("/qa", json={"question": "what did we discuss with Acme"})
    assert fourth.status_code == 429
    assert fourth.json()["error_code"] == "RATE_LIMITED"
    assert "Retry-After" in fourth.headers
    client.close()


def test_rate_limit_is_per_session_not_global(rate_limited_server):
    """A second, independent session must not be affected by another session's rate limit."""
    with httpx.Client(base_url=rate_limited_server.base_url) as setup_a:
        ra = setup_a.post("/auth/login", json={"username": "qa-user", "password": "qa-password-for-independent-testing"})
        token_a = ra.cookies.get("session")
    client_a = httpx.Client(base_url=rate_limited_server.base_url)
    client_a.cookies.set("session", token_a)
    for _ in range(4):
        client_a.post("/qa", json={"question": "what did we discuss with Acme"})
    exhausted = client_a.post("/qa", json={"question": "what did we discuss with Acme"})
    assert exhausted.status_code == 429

    with httpx.Client(base_url=rate_limited_server.base_url) as setup_b:
        rb = setup_b.post("/auth/login", json={"username": "qa-user", "password": "qa-password-for-independent-testing"})
        token_b = rb.cookies.get("session")
    client_b = httpx.Client(base_url=rate_limited_server.base_url)
    client_b.cookies.set("session", token_b)
    fresh = client_b.post("/qa", json={"question": "what did we discuss with Acme"})
    assert fresh.status_code == 200, "a second session's own budget must be independent of the first session's"
    client_a.close()
    client_b.close()


def test_login_lockout_triggers_at_the_configured_attempt_count(lockout_server):
    with httpx.Client(base_url=lockout_server.base_url) as c:
        statuses = []
        for _ in range(3):
            r = c.post("/auth/login", json={"username": "qa-user", "password": "wrong-password"})
            statuses.append(r.status_code)
        assert statuses == [401, 401, 401], f"first 3 wrong attempts should each be a plain 401, got {statuses}"

        locked = c.post("/auth/login", json={"username": "qa-user", "password": "wrong-password"})
        assert locked.status_code == 429, f"4th attempt should trip the lockout (429), got {locked.status_code}"
        assert locked.json()["error_code"] == "LOGIN_LOCKED"

        still_locked_even_with_correct_password = c.post(
            "/auth/login", json={"username": "qa-user", "password": "qa-password-for-independent-testing"}
        )
        assert still_locked_even_with_correct_password.status_code == 429, (
            "lockout must block even the correct password until the window/attempt count resets -- "
            f"got {still_locked_even_with_correct_password.status_code}"
        )
