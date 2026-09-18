"""Server-side authorization sweep -- every operation the API-CONTRACT marks
SharedLoginAuth-protected is called directly, with no session, against the
real running server. A UI hiding a button proves nothing (test-agent's own
Section 5 rule); this calls the endpoint itself.
"""
import pytest

PROTECTED_OPERATIONS = [
    ("GET", "/accounts", None),
    ("POST", "/interactions", {"raw_text": "met with Acme"}),
    ("GET", "/interactions/unmatched", None),
    ("POST", "/interactions/does-not-exist/resolve-customer", {"account_id": "ACC-ACME"}),
    ("POST", "/qa", {"question": "what did we discuss with Acme"}),
    ("POST", "/briefs", {"request_text": "brief me on Acme"}),
    ("GET", "/commitments/due", None),
    ("PATCH", "/commitments/does-not-exist/complete", None),
    ("POST", "/auth/logout", None),
]


@pytest.mark.parametrize("method,path,body", PROTECTED_OPERATIONS, ids=[f"{m} {p}" for m, p, _ in PROTECTED_OPERATIONS])
def test_protected_operation_refuses_no_session(anon_client, method, path, body):
    response = anon_client.request(method, path, json=body)
    assert response.status_code == 401, f"{method} {path} returned {response.status_code}, expected 401: {response.text}"
    error = response.json()
    assert error["error_code"] == "UNAUTHENTICATED"
    assert "error_code" in error and "message" in error  # flat Error shape, not nested under "detail"


@pytest.mark.parametrize("method,path,body", PROTECTED_OPERATIONS, ids=[f"{m} {p}" for m, p, _ in PROTECTED_OPERATIONS])
def test_protected_operation_refuses_garbage_cookie(server, method, path, body):
    """A malformed/unknown session token must be refused identically to no session at all -- not treated as valid, not crash the server."""
    import httpx

    with httpx.Client(base_url=server.base_url, cookies={"session": "this-is-not-a-real-session-token"}) as c:
        response = c.request(method, path, json=body)
    assert response.status_code == 401, f"{method} {path} with a garbage cookie returned {response.status_code}, expected 401"


def test_public_operations_do_not_require_a_session(server):
    """GET /health and POST /auth/login are the only unauthenticated operations -- confirm they genuinely work with no cookie."""
    import httpx

    with httpx.Client(base_url=server.base_url) as c:
        health = c.get("/health")
        assert health.status_code == 200
        login = c.post("/auth/login", json={"username": "qa-user", "password": "qa-password-for-independent-testing"})
        assert login.status_code == 200
