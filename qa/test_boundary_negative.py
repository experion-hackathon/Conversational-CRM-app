"""Boundary and negative cases -- the class of input implementations usually
miss: malformed bodies, missing fields, invalid query params, wrong methods,
unknown routes, and adversarial text content.
"""


def test_missing_raw_text_key_defaults_to_empty_note_400(client):
    """POST /interactions parses the body manually (not via a Pydantic model,
    since it must branch on content-type for the multipart path -- see
    app/routers/interactions.py line 72), so a body with no raw_text key at
    all is valid JSON that simply defaults to "" via body.get("raw_text", ""),
    correctly hitting the same EMPTY_NOTE path as an explicit empty string."""
    response = client.post("/interactions", json={})
    assert response.status_code == 400
    assert response.json()["error_code"] == "EMPTY_NOTE"


def test_malformed_json_body_crashes_with_unhandled_500(client):
    """DEFECT (QA-1): app/routers/interactions.py line 72 calls
    `await request.json()` with no try/except. A body that is not valid JSON
    at all (as opposed to valid JSON missing a key) raises an unhandled
    exception, and no exception handler in app/main.py catches it -- the
    request fails with a bare 500, not the contract's flat Error shape, and
    not one of the documented error codes. No stack trace leaks (Starlette's
    default 500 handler is opaque with debug off), but this is still an
    unhandled crash on ordinary malformed input, not a graceful rejection."""
    response = client.post("/interactions", content=b"{not valid json", headers={"Content-Type": "application/json"})
    assert response.status_code in (400, 422), (
        f"QA-1: malformed JSON body crashed the server (got {response.status_code}: {response.text!r}) "
        "instead of a graceful 400/422 -- see app/routers/interactions.py's unguarded `await request.json()`"
    )


def test_non_json_non_multipart_body_crashes_with_unhandled_500(client):
    """DEFECT (QA-1, same root cause): any request whose content-type is
    neither multipart/form-data nor valid JSON falls through to the same
    unguarded `await request.json()` call and crashes the same way."""
    response = client.post("/interactions", content=b"raw_text=hello", headers={"Content-Type": "text/plain"})
    assert response.status_code in (400, 415, 422), (
        f"QA-1: non-JSON, non-multipart body crashed the server (got {response.status_code}: {response.text!r})"
    )


def test_unsupported_method_is_405_not_500(client):
    response = client.put("/accounts")
    assert response.status_code == 405


def test_unknown_route_is_404(client):
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404


def test_due_soon_window_days_rejects_non_positive(client):
    response = client.get("/commitments/due", params={"due_soon_window_days": 0})
    assert response.status_code == 422
    response = client.get("/commitments/due", params={"due_soon_window_days": -1})
    assert response.status_code == 422


def test_due_soon_window_days_rejects_non_integer(client):
    response = client.get("/commitments/due", params={"due_soon_window_days": "not-a-number"})
    assert response.status_code == 422


def test_resolve_customer_unknown_account_is_404_not_500(client):
    capture = client.post("/interactions", json={"raw_text": "met with someone unaffiliated"})
    interaction_id = capture.json()["id"]
    response = client.post(f"/interactions/{interaction_id}/resolve-customer", json={"account_id": "ACC-DOES-NOT-EXIST"})
    assert response.status_code == 404
    assert response.json()["error_code"] == "ACCOUNT_NOT_FOUND"


def test_capture_text_with_sql_injection_style_content_is_stored_verbatim_not_executed(client):
    """Confirms parameterized queries: adversarial text is data, never interpreted as SQL."""
    payload = "met with Acme; DROP TABLE interactions; -- discussed pricing"
    response = client.post("/interactions", json={"raw_text": payload})
    assert response.status_code == 201
    assert response.json()["raw_text"] == payload

    # The table must still exist and be queryable -- prove no injection occurred.
    due = client.get("/commitments/due")
    assert due.status_code == 200


def test_capture_text_with_html_script_content_is_stored_and_returned_as_plain_data(client):
    """The API is a JSON contract, not HTML -- confirm the raw text round-trips as inert data, unescaped/unmodified, with no server-side interpretation."""
    payload = "met with Acme <script>alert(1)</script>, discussed pricing"
    response = client.post("/interactions", json={"raw_text": payload})
    assert response.status_code == 201
    assert response.json()["raw_text"] == payload


def test_capture_text_very_long_input_does_not_crash(client):
    payload = "met with Acme, " + ("discussed pricing and next steps. " * 2000)  # ~70KB
    response = client.post("/interactions", json={"raw_text": payload})
    assert response.status_code == 201
    assert response.json()["raw_text"] == payload


def test_capture_text_with_unicode_and_emoji_is_preserved(client):
    payload = "met with Acme 🎉 — discussed pré-lancement pricing (naïve café ☕️)"
    response = client.post("/interactions", json={"raw_text": payload})
    assert response.status_code == 201
    assert response.json()["raw_text"] == payload


def test_login_with_missing_password_field_is_422_not_500(client):
    response = client.post("/auth/login", json={"username": "qa-user"})
    assert response.status_code == 422


def test_business_card_capture_with_no_matching_field_is_422(client):
    """A genuine multipart request (real multipart/form-data content-type)
    that lacks the specific `business_card_image` field correctly returns
    422 UNSUPPORTED_IMAGE_FORMAT -- this is the actual multipart branch
    working as designed. (httpx's files={} sends no body/content-type at
    all rather than an empty multipart request, so it does not exercise this
    branch -- that case is QA-1 above, a different, real defect.)"""
    response = client.post("/interactions", files={"wrong_field_name": ("card.png", b"data", "image/png")})
    assert response.status_code == 422
    assert response.json()["error_code"] == "UNSUPPORTED_IMAGE_FORMAT"


def test_no_body_no_content_type_crashes_with_unhandled_500(client):
    """DEFECT (QA-1, same root cause): httpx's files={} sends a request with
    no body and no content-type header at all, which also falls through to
    the unguarded `await request.json()` call and crashes the same way."""
    response = client.post("/interactions", files={})
    assert response.status_code in (400, 422), (
        f"QA-1: a bodyless request crashed the server (got {response.status_code}: {response.text!r})"
    )
