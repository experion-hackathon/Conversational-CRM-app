"""F-4 (Proactive Commitment Tracking) business logic, US-15/US-16.

Also serves F-8's home to-do list (US-20 through US-23) -- the unified home
surface calls this same computation on login rather than a dedicated home
endpoint (data_integration decision, DATA-AND-INTEGRATION-conversational-crm-
T-1-v2.0.md Section 3).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Commitment


class CommitmentNotFoundError(Exception):
    pass


def list_due_commitments(db: Session, reference_date: date | None = None, due_soon_window_days: int | None = None):
    """US-15 AC1-AC3, US-16 AC1. Returns (overdue, due_soon, unspecified, message)."""
    settings = get_settings()
    reference_date = reference_date or date.today()
    window_days = due_soon_window_days if due_soon_window_days is not None else settings.due_soon_window_days
    due_soon_cutoff = reference_date + timedelta(days=window_days)

    open_commitments = db.query(Commitment).filter(Commitment.status == "open").all()

    overdue, due_soon, unspecified = [], [], []
    for c in open_commitments:
        if not c.due_date:
            unspecified.append(c)
            continue
        try:
            due = date.fromisoformat(c.due_date)
        except ValueError:
            unspecified.append(c)
            continue
        if due < reference_date:
            overdue.append(c)
        elif due <= due_soon_cutoff:
            due_soon.append(c)
        # else: due later than the window -- not listed in either bucket, per
        # US-15 AC2's "falls within the next N days" scoping.

    # due_date is str | None on the model, but every entry landed in these two
    # buckets only after passing the `if not c.due_date` filter above.
    overdue.sort(key=lambda c: c.due_date or "")
    due_soon.sort(key=lambda c: c.due_date or "")

    message = None
    if not overdue and not due_soon:
        message = "There are no due-soon or overdue commitments right now."

    return overdue, due_soon, unspecified, message


def mark_commitment_complete(db: Session, commitment_id: str) -> Commitment:
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise CommitmentNotFoundError()
    commitment.status = "complete"
    db.commit()
    db.refresh(commitment)
    return commitment


def has_any_interaction_history(db) -> bool:
    """F-8 AC4 / US-23: distinguishes 'nothing due right now' from 'nothing at
    all yet' (a genuinely first-ever login). Not yet a contract-level response
    field (Open Item OI-24) -- exposed here for a future response-shape change.
    """
    from app.models import Interaction

    return db.query(Interaction.id).first() is not None
