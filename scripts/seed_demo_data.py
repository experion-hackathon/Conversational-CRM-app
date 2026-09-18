"""Seed the running backend with realistic, synthetic demo interactions.

Not part of any workflow's evidence -- a local convenience script to give the
UI something to show. Talks to the real running HTTP API, same as a genuine
client would; does not touch the database directly. Safe to re-run (each
capture is additive).
"""
import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "demo"
PASSWORD = "demo-password-123"

NOTES = [
    # Matched to Acme, with attendees + a dated commitment
    "Met with Priya and Arjun from Acme to discuss the Q3 renewal. They want a demo of the new reporting dashboard by Friday.",
    # Matched to Acme, vague due date
    "Quick call with Priya at Acme -- she mentioned they might expand seats next quarter, nothing firm yet. I should follow up with a proposal soon.",
    # Matched to Globex
    "Talked to Sam Rivera from Globex about the integration outage last week. He wants a written incident summary by next Wednesday.",
    # Matched to Globex, discussion only, no commitment
    "Catch-up call with Sam at Globex. Mostly relationship-building, no action items on either side.",
    # Matched to Initech
    "Met with Jordan Lee from Initech to walk through onboarding. Jordan needs the SSO configuration guide sent over by Monday.",
    # Unmatched -- no seeded account name present, should land in the unmatched queue
    "Had a great intro call with a new prospect from a company called Northwind Traders about a potential Q4 pilot.",
    # Unmatched -- business card style capture with no company field recognized
    "Picked up a card from someone named Alex at a conference booth, no company name mentioned, said they'd reach out about a partnership.",
    # Matched to Acme, second commitment for the due-soon list
    "Arjun from Acme flagged a bug in the export feature, needs a fix confirmation by tomorrow.",
]


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        r = client.post("/auth/login", json={"username": USERNAME, "password": PASSWORD})
        if r.status_code != 200:
            print(f"Login failed ({r.status_code}): {r.text}", file=sys.stderr)
            sys.exit(1)
        token = r.cookies.get("session")
        client.cookies.set("session", token)
        print("Logged in as", USERNAME)

        created = 0
        for note in NOTES:
            r = client.post("/interactions", json={"raw_text": note})
            if r.status_code == 201:
                body = r.json()
                created += 1
                print(f"  [{body['match_status']:9s}] {note[:70]}...")
            else:
                print(f"  FAILED ({r.status_code}) for note: {note[:60]}... -> {r.text}", file=sys.stderr)
            time.sleep(0.05)

        print(f"\nSeeded {created}/{len(NOTES)} interactions.")

        unmatched = client.get("/interactions/unmatched").json()
        print(f"Unmatched queue: {len(unmatched)} item(s)")

        due = client.get("/commitments/due").json()
        print(f"Commitments -- overdue: {len(due['overdue'])}, due soon: {len(due['due_soon'])}, unspecified: {len(due['unspecified'])}")


if __name__ == "__main__":
    main()
