"""Empirically confirms gaps the backend/frontend reports already disclosed
as open items, rather than trusting the disclosure at face value -- an
independent Test stage checks claims, it does not repeat them (test-agent's
own contract). Each test here is EXPECTED to fail, and its failure is the
correct, honest documentation of a real, already-known, upstream-caused gap
(a locked-contract limitation neither implementer had authority to fix) --
not a newly discovered defect. See TEST report Section on Known Gaps for the
full disposition of each.
"""


def test_us6_ac3_active_reprompt_is_not_distinguishable_from_ordinary_unmatched(client):
    """US-6 AC3 requires an active, same-turn conversational prompt for an
    ambiguous entry, distinct from the passive unmatched flag AC1/AC2 already
    cover (backend OI-BACKEND-5/frontend OI-FRONTEND-7). Confirms empirically:
    the actual /interactions response for an ambiguous entry has no field
    distinguishing "needs an active prompt now" from an ordinary unmatched
    note -- both look identical on the wire."""
    response = client.post("/interactions", json={"raw_text": "had a great meeting today, no company mentioned"})
    assert response.status_code == 201
    body = response.json()
    assert body["match_status"] == "unmatched"
    # The full response schema -- there is no field here that could carry
    # "this one specifically needs an active same-turn prompt".
    assert set(body.keys()) == {
        "id", "account_id", "raw_text", "source_type", "match_status",
        "manual_entry_required", "captured_at", "attendees", "commitments",
    }, "if this fails, a new field now exists and US-6 AC3 may be buildable -- re-check OI-BACKEND-5/OI-FRONTEND-7"
    raise AssertionError(
        "US-6 AC3 confirmed not implementable against the current contract: no field distinguishes "
        "an ambiguous entry needing an active prompt from an ordinary unmatched note. Known, disclosed "
        "upstream gap (OI-BACKEND-5 / OI-FRONTEND-7) -- not a new defect, documented here as failing evidence."
    )


def test_f8_us21_due_commitments_response_has_no_top_n_or_pagination_field(client):
    """US-21 requires a top-N-with-see-more list. Confirms the actual
    GET /commitments/due response schema has no such field (OI-BACKEND-1/OI-FRONTEND-1)."""
    response = client.get("/commitments/due")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"overdue", "due_soon", "unspecified", "message"}
    raise AssertionError(
        "US-21 confirmed not implementable server-side: no top-N/pagination field exists on this response. "
        "Known, disclosed upstream gap (OI-BACKEND-1 / OI-FRONTEND-1) -- the frontend's client-side slice "
        "to 5 items is not a server guarantee. Not a new defect."
    )


def test_f8_us23_nothing_due_and_never_had_history_are_the_same_message(client):
    """US-23 requires a distinct "nothing to show yet" state for a genuinely
    first-ever login, separate from US-16/US-20 AC2's "nothing due right now".
    Confirms empirically: a brand-new session (never captured anything) and
    a session with only completed commitments produce the IDENTICAL message,
    proving the contract cannot distinguish them (OI-BACKEND-3/OI-FRONTEND-5)."""
    never_captured = client.get("/commitments/due")
    assert never_captured.status_code == 200
    fresh_message = never_captured.json()["message"]
    assert fresh_message == "There are no due-soon or overdue commitments right now."

    capture = client.post("/interactions", json={"raw_text": "met with Acme, they want a demo by Friday"})
    commitment_id = capture.json()["commitments"][0]["id"]
    client.patch(f"/commitments/{commitment_id}/complete")

    after_completed_history = client.get("/commitments/due")
    completed_message = after_completed_history.json()["message"]

    assert fresh_message != completed_message, (
        "if this fails, the two states are genuinely indistinguishable on the wire, confirming US-23 "
        "cannot be told apart from the ordinary nothing-due state. Known, disclosed upstream gap "
        "(OI-BACKEND-3 / OI-FRONTEND-5) -- not a new defect."
    )
