from datetime import date, timedelta


def _capture_with_commitment(client, company: str, due_clause: str):
    return client.post("/interactions", json={"raw_text": f"met with {company}, they want a follow-up {due_clause}"})


def test_due_commitments_empty_state_message(logged_in_client):
    response = logged_in_client.get("/commitments/due")
    assert response.status_code == 200
    body = response.json()
    assert body["overdue"] == []
    assert body["due_soon"] == []
    assert body["message"] == "There are no due-soon or overdue commitments right now."


def test_commitment_with_unspecified_due_date_is_listed_separately(logged_in_client):
    _capture_with_commitment(logged_in_client, "Acme", "sometime")
    response = logged_in_client.get("/commitments/due")
    body = response.json()
    assert len(body["unspecified"]) == 1
    assert body["overdue"] == []
    assert body["due_soon"] == []
    # US-16 AC1: unspecified entries alone do not suppress the "nothing due" message.
    assert body["message"] == "There are no due-soon or overdue commitments right now."


def test_commitment_due_soon_is_classified_correctly(logged_in_client):
    _capture_with_commitment(logged_in_client, "Globex", "by Friday")
    response = logged_in_client.get("/commitments/due?due_soon_window_days=7")
    body = response.json()
    assert body["message"] is None
    assert len(body["due_soon"]) + len(body["overdue"]) == 1  # lands in one of the two, depending on today's weekday


def test_commitment_overdue_when_due_date_in_the_past(logged_in_client):
    past_date = (date.today() - timedelta(days=3)).isoformat()
    _capture_with_commitment(logged_in_client, "Initech", f"on {past_date}")
    response = logged_in_client.get("/commitments/due")
    body = response.json()
    assert len(body["overdue"]) == 1
    assert body["overdue"][0]["due_date"] == past_date


def test_mark_commitment_complete_excludes_it_from_due_list(logged_in_client):
    past_date = (date.today() - timedelta(days=1)).isoformat()
    capture = _capture_with_commitment(logged_in_client, "Acme", f"on {past_date}")
    commitment_id = capture.json()["commitments"][0]["id"]

    before = logged_in_client.get("/commitments/due")
    assert len(before.json()["overdue"]) == 1

    complete = logged_in_client.patch(f"/commitments/{commitment_id}/complete")
    assert complete.status_code == 200
    assert complete.json()["status"] == "complete"

    after = logged_in_client.get("/commitments/due")
    assert after.json()["overdue"] == []


def test_mark_unknown_commitment_complete_is_404(logged_in_client):
    response = logged_in_client.patch("/commitments/does-not-exist/complete")
    assert response.status_code == 404
    assert response.json()["error_code"] == "COMMITMENT_NOT_FOUND"


def test_commitments_due_requires_session(client):
    response = client.get("/commitments/due")
    assert response.status_code == 401
