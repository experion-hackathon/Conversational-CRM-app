"""Genuine concurrent requests against the real running server -- capacity or
state-transition contention that a sequential in-process TestClient cannot
exercise, per test-agent's own required case list.
"""
import concurrent.futures

import httpx


def _login(server):
    with httpx.Client(base_url=server.base_url) as c:
        r = c.post("/auth/login", json={"username": "qa-user", "password": "qa-password-for-independent-testing"})
        token = r.cookies.get("session")
    client = httpx.Client(base_url=server.base_url)
    client.cookies.set("session", token)
    return client


def test_concurrent_resolve_customer_on_the_same_unmatched_interaction_is_not_double_applied(server):
    """DAT-5-class state transition: an unmatched interaction resolved by two
    concurrent requests must end up matched exactly once -- one 200, one 409,
    never two 200s and never a corrupted/duplicated match."""
    setup = _login(server)
    capture = setup.post("/interactions", json={"raw_text": "met with someone from an unnamed company"})
    assert capture.status_code == 201
    interaction_id = capture.json()["id"]
    assert capture.json()["match_status"] == "unmatched"

    def resolve():
        c = _login(server)
        try:
            return c.post(f"/interactions/{interaction_id}/resolve-customer", json={"account_id": "ACC-ACME"})
        finally:
            c.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: resolve(), range(8)))

    statuses = sorted(r.status_code for r in results)
    assert statuses.count(200) == 1, (
        f"DEFECT (QA-3): expected exactly one 200 (first resolver wins) among 8 concurrent resolves, got statuses: {statuses}. "
        "app/services/capture_service.py::resolve_customer reads match_status, then writes, with no locking or "
        "optimistic-concurrency check in between -- under real concurrent requests (this handler is sync `def`, "
        "so FastAPI runs it in a real thread pool, not serialized), two threads can both read 'unmatched' before "
        "either commits, and both then succeed with 200 instead of one winning and the other getting 409."
    )
    assert all(s in (200, 409) for s in statuses), f"unexpected status among concurrent resolves: {statuses}"

    final = setup.get("/interactions/unmatched")
    assert not any(i["id"] == interaction_id for i in final.json()), "interaction still shows as unmatched after being resolved"
    setup.close()


def test_concurrent_mark_complete_on_the_same_commitment_is_idempotent_not_erroring(server):
    """Marking an already-complete commitment complete again is not specified
    as an error anywhere in the contract -- confirm concurrent completions
    all succeed identically (idempotent), rather than crashing or corrupting
    state, since nothing prevents a rep double-tapping "mark complete"."""
    setup = _login(server)
    capture = setup.post("/interactions", json={"raw_text": "met with Acme, they want a demo by Friday"})
    commitment_id = capture.json()["commitments"][0]["id"]

    def complete():
        c = _login(server)
        try:
            return c.patch(f"/commitments/{commitment_id}/complete")
        finally:
            c.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: complete(), range(8)))

    statuses = [r.status_code for r in results]
    assert all(s == 200 for s in statuses), f"expected all concurrent completions to succeed idempotently, got: {statuses}"
    assert all(r.json()["status"] == "complete" for r in results)
    setup.close()


def test_concurrent_captures_do_not_corrupt_each_other(server):
    """Many concurrent, independent captures must each be persisted intact --
    no interleaving/overwriting under real concurrent SQLite writes (WAL mode, DAT-3)."""
    setup = _login(server)

    def capture(i):
        c = _login(server)
        try:
            return c.post("/interactions", json={"raw_text": f"met with Acme, unique marker QA-CONC-{i}"})
        finally:
            c.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(capture, range(10)))

    assert all(r.status_code == 201 for r in results), [r.status_code for r in results]
    texts = {r.json()["raw_text"] for r in results}
    assert len(texts) == 10, "some concurrent captures were lost or overwrote each other"
    for i in range(10):
        assert any(f"QA-CONC-{i}" in t for t in texts), f"marker {i} missing from persisted results"
    setup.close()
