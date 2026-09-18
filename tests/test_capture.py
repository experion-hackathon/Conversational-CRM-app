

def test_capture_matches_seeded_account_and_extracts_attendees_and_commitment(logged_in_client):
    response = logged_in_client.post(
        "/interactions",
        json={"raw_text": "met Priya and Arjun from Acme, discussed renewal pricing, they want a demo of module X by Friday"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["match_status"] == "matched"
    assert body["account_id"] == "ACC-ACME"

    attendee_names = {a["name"] for a in body["attendees"]}
    assert attendee_names == {"Priya", "Arjun"}  # US-5 AC1: one item per distinct person, not merged.

    assert len(body["commitments"]) == 1
    commitment = body["commitments"][0]
    assert "demo" in commitment["text"].lower()
    assert commitment["due_date"] is not None  # US-8 AC1: "by Friday" resolves to a real date.


def test_capture_with_no_identifiable_person_yields_zero_attendees(logged_in_client):
    response = logged_in_client.post("/interactions", json={"raw_text": "met with Acme, discussed pricing"})
    assert response.status_code == 201
    assert response.json()["attendees"] == []  # US-5 AC2: never fabricate a name.


def test_capture_empty_note_is_rejected(logged_in_client):
    response = logged_in_client.post("/interactions", json={"raw_text": "   "})
    assert response.status_code == 400
    assert response.json()["error_code"] == "EMPTY_NOTE"


def test_capture_unmatched_when_no_account_named(logged_in_client):
    response = logged_in_client.post("/interactions", json={"raw_text": "had a great call today about renewal"})
    assert response.status_code == 201
    body = response.json()
    assert body["match_status"] == "unmatched"
    assert body["account_id"] is None


def test_capture_vague_due_date_is_left_unspecified(logged_in_client):
    response = logged_in_client.post(
        "/interactions",
        json={"raw_text": "met with Globex, they want pricing sometime"},
    )
    assert response.status_code == 201
    commitments = response.json()["commitments"]
    assert len(commitments) == 1
    assert commitments[0]["due_date"] is None  # US-7 AC2: vague term -> unspecified, never guessed.


def test_capture_no_forward_looking_statement_yields_zero_commitments(logged_in_client):
    response = logged_in_client.post("/interactions", json={"raw_text": "met with Initech, discussed the weather"})
    assert response.status_code == 201
    assert response.json()["commitments"] == []


def test_resolve_unmatched_interaction_to_selected_account(logged_in_client):
    capture = logged_in_client.post("/interactions", json={"raw_text": "had a call, no company named"})
    interaction_id = capture.json()["id"]
    assert capture.json()["match_status"] == "unmatched"

    resolved = logged_in_client.post(f"/interactions/{interaction_id}/resolve-customer", json={"account_id": "ACC-GLOBEX"})
    assert resolved.status_code == 200
    assert resolved.json()["match_status"] == "matched"
    assert resolved.json()["account_id"] == "ACC-GLOBEX"


def test_resolve_customer_unknown_interaction_is_404(logged_in_client):
    response = logged_in_client.post("/interactions/does-not-exist/resolve-customer", json={"account_id": "ACC-ACME"})
    assert response.status_code == 404
    assert response.json()["error_code"] == "INTERACTION_NOT_FOUND"


def test_resolve_customer_unknown_account_is_404(logged_in_client):
    capture = logged_in_client.post("/interactions", json={"raw_text": "unmatched note here"})
    interaction_id = capture.json()["id"]
    response = logged_in_client.post(f"/interactions/{interaction_id}/resolve-customer", json={"account_id": "ACC-NOPE"})
    assert response.status_code == 404
    assert response.json()["error_code"] == "ACCOUNT_NOT_FOUND"


def test_resolve_customer_already_matched_is_409(logged_in_client):
    capture = logged_in_client.post("/interactions", json={"raw_text": "met with Acme about renewal"})
    interaction_id = capture.json()["id"]
    assert capture.json()["match_status"] == "matched"

    response = logged_in_client.post(f"/interactions/{interaction_id}/resolve-customer", json={"account_id": "ACC-GLOBEX"})
    assert response.status_code == 409
    assert response.json()["error_code"] == "INTERACTION_ALREADY_MATCHED"


def test_list_unmatched_interactions_oldest_first(logged_in_client):
    logged_in_client.post("/interactions", json={"raw_text": "first unmatched note"})
    logged_in_client.post("/interactions", json={"raw_text": "second unmatched note"})

    response = logged_in_client.get("/interactions/unmatched")
    assert response.status_code == 200
    texts = [i["raw_text"] for i in response.json()]
    assert texts.index("first unmatched note") < texts.index("second unmatched note")


def test_business_card_capture_without_recognizable_fields_requires_manual_entry(logged_in_client):
    files = {"business_card_image": ("card.png", b"not-a-real-image-but-nonempty", "image/png")}
    response = logged_in_client.post("/interactions", files=files)
    assert response.status_code == 201
    body = response.json()
    assert body["manual_entry_required"] is True
    assert body["attendees"] == []  # never fabricate contact details (US-4 AC2)


def test_capture_survives_vector_store_failure(logged_in_client, monkeypatch):
    # V-BACK-3: the SQLite commit is the source of truth; a failure in the
    # secondary Chroma indexing step (which now runs strictly after commit)
    # must not lose an already-committed interaction.
    import app.services.capture_service as capture_service

    def _boom(**kwargs):
        raise RuntimeError("simulated vector store outage")

    monkeypatch.setattr(capture_service, "upsert_interaction_chunk", _boom)

    response = logged_in_client.post("/interactions", json={"raw_text": "met with Acme, discussed pricing"})
    assert response.status_code == 201, response.text
    assert response.json()["account_id"] == "ACC-ACME"

    # The interaction really was persisted, not just returned in-memory.
    unmatched_before = logged_in_client.get("/interactions/unmatched").json()
    listing = logged_in_client.get("/commitments/due").json()  # sanity: DB still reachable
    assert isinstance(listing, dict)
    assert unmatched_before == []  # this one matched Acme, so it's not in the unmatched list
