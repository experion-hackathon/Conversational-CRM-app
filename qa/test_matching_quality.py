"""Independently investigates a claim the frontend's own report left
unconfirmed (OI-FRONTEND-3(b): "the account-name substring match ... is
case-sensitive-adjacent in one edge case ... not confirmed as a real bug").
Case handling itself (app/adapters/crm_adapter.py's find_account_by_name_fragment
lowercases both sides) is correct -- verified directly below. But the same
function's plain `name.lower() in text_lower` substring check has no word-boundary
check, and that turns out to be a real, reproducible, more serious defect.
"""


def test_account_name_matching_is_genuinely_case_insensitive(client):
    """Refutes the case-sensitivity half of OI-FRONTEND-3(b) directly -- this is not the bug."""
    response = client.post("/interactions", json={"raw_text": "met with ACME today, discussed renewal"})
    assert response.status_code == 201
    assert response.json()["account_id"] == "ACC-ACME"

    response2 = client.post("/interactions", json={"raw_text": "met with acme today, discussed renewal"})
    assert response2.status_code == 201
    assert response2.json()["account_id"] == "ACC-ACME"


def test_account_name_substring_match_has_no_word_boundary_check(client):
    """DEFECT (QA-2): find_account_by_name_fragment does `a.name.lower() in
    text_lower`, a plain substring check with no word-boundary awareness. A
    completely unrelated company whose name happens to CONTAIN a seeded
    account's name as a substring (e.g. "Acmeville", "Globexico") is silently
    matched to that seeded account -- not flagged unmatched, not ambiguous,
    just wrong. This is more serious than an ordinary unmatched note: F-1
    AC1/US-2 AC2 require the system to flag rather than mis-file when a match
    is not genuinely unambiguous, and "Acmeville" unambiguously is NOT the
    seeded "Acme" account. The frontend's own report flagged something
    adjacent to this (OI-FRONTEND-3b) but marked it unconfirmed; this
    reproduces and confirms a real, distinct defect precisely."""
    response = client.post("/interactions", json={"raw_text": "talked to someone from Acmeville realty about a new office lease"})
    assert response.status_code == 201
    body = response.json()
    assert body["match_status"] == "unmatched", (
        f"QA-2: 'Acmeville realty' (not the seeded Acme account) was silently matched to account_id={body['account_id']!r} "
        "instead of being flagged unmatched -- see app/adapters/crm_adapter.py's word-boundary-free substring check"
    )


def test_account_name_substring_match_false_positive_variant_two(client):
    """A second, independent reproduction with a different seeded account, to
    confirm QA-2 is not specific to one account name's letters."""
    response = client.post("/interactions", json={"raw_text": "we're partnering with Globexico Trading on a new deal"})
    assert response.status_code == 201
    body = response.json()
    assert body["match_status"] == "unmatched", (
        f"QA-2 (second reproduction): 'Globexico Trading' was silently matched to account_id={body['account_id']!r}"
    )
