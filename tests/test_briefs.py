def test_brief_for_unrecognized_customer_is_not_identified(logged_in_client):
    response = logged_in_client.post("/briefs", json={"request_text": "brief me on Nobody Inc"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "not_identified"


def test_brief_empty_request_is_400(logged_in_client):
    response = logged_in_client.post("/briefs", json={"request_text": ""})
    assert response.status_code == 400
    assert response.json()["error_code"] == "EMPTY_REQUEST"


def test_brief_for_customer_with_no_history_is_no_history(logged_in_client):
    response = logged_in_client.post("/briefs", json={"request_text": "brief me on Globex"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "no_history"


def test_brief_for_customer_with_history_includes_all_components(logged_in_client):
    logged_in_client.post(
        "/interactions",
        json={"raw_text": "met Priya and Arjun from Acme, they want a demo of module X by Friday"},
    )
    response = logged_in_client.post("/briefs", json={"request_text": "brief me on Acme"})
    assert response.status_code == 200
    body = response.json()
    assert body["resolution"] == "generated"
    assert body["account_id"] == "ACC-ACME"
    summary = body["summary"]
    assert summary["history_text"]
    assert len(summary["open_commitments"]) == 1
    stakeholder_names = {s["name"] for s in summary["stakeholders"]}
    # US-17 AC1: stakeholders drawn from both extracted attendees and the
    # adapter's seeded contacts roster for this account.
    assert "Priya" in stakeholder_names
    assert "Priya Sharma" in stakeholder_names
    # US-18 AC1: a thread with an open commitment and named attendees carries
    # a genuine relationship-stance signal.
    assert summary["relationship_status"] is not None


def test_brief_with_account_id_hint(logged_in_client):
    logged_in_client.post("/interactions", json={"raw_text": "met with Initech, discussed renewal"})
    response = logged_in_client.post("/briefs", json={"request_text": "brief me please", "account_id": "ACC-INITECH"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "generated"
    assert response.json()["account_id"] == "ACC-INITECH"


def test_brief_with_invalid_account_id_hint_is_not_identified(logged_in_client):
    # V-BACK-2: an invalid hint must fail closed, the same as /qa, rather than
    # silently falling back to resolving the account from request_text.
    logged_in_client.post("/interactions", json={"raw_text": "met with Acme, discussed pricing"})
    response = logged_in_client.post("/briefs", json={"request_text": "brief me on Acme", "account_id": "ACC-DOES-NOT-EXIST"})
    assert response.status_code == 200
    assert response.json()["resolution"] == "not_identified"


def test_brief_for_bare_single_note_has_no_relationship_status_yet(logged_in_client):
    # US-18 AC2, V-BACK-1: a single note with no attendees and no commitments
    # carries no discernible relationship-stance signal yet -- distinct from
    # the no_history case, this is a *generated* brief with a null status.
    logged_in_client.post("/interactions", json={"raw_text": "met with Globex, just a casual chat"})
    response = logged_in_client.post("/briefs", json={"request_text": "brief me on Globex"})
    assert response.status_code == 200
    body = response.json()
    assert body["resolution"] == "generated"
    assert body["summary"]["relationship_status"] is None
