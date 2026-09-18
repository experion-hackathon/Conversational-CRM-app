"""F-3 (Natural-Language Memory & Q&A) business logic. US-10..US-14."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.adapters.crm_adapter import CRMAdapter
from app.models import Commitment, Interaction, InteractionAttendee
from app.nlu.base import NLUClient
from app.services.account_resolution import resolve_account_id
from app.vector_store import query_by_account


def answer_question(db: Session, question: str, account_id_hint: str | None, nlu: NLUClient, crm: CRMAdapter):
    """Returns (resolution, account_id, answer_text, message)."""
    account_id = resolve_account_id(question, account_id_hint, crm)
    if account_id is None:
        return "not_identified", None, None, "Could not identify which customer you mean."

    lower = question.lower()

    if "attend" in lower or "who was there" in lower:
        attendees = (
            db.query(InteractionAttendee)
            .join(Interaction)
            .filter(Interaction.account_id == account_id)
            .all()
        )
        if not attendees:
            return "no_attendees_captured", account_id, None, "No attendee information was captured for this customer."
        names = ", ".join(sorted({a.name for a in attendees}))
        return "answered", account_id, f"Attendees: {names}", None

    if "commit" in lower or "promise" in lower:
        commitments = (
            db.query(Commitment)
            .filter(Commitment.account_id == account_id, Commitment.status == "open")
            .all()
        )
        if not commitments:
            return "no_open_commitments", account_id, None, "There are no open commitments for this customer."
        lines = "; ".join(c.text for c in commitments)
        return "answered", account_id, f"Open commitments: {lines}", None

    # Default: "what did we discuss last time" / general question.
    latest = (
        db.query(Interaction)
        .filter(Interaction.account_id == account_id)
        .order_by(Interaction.captured_at.desc(), Interaction.id.desc())
        .first()
    )
    if latest is None:
        return "no_history", account_id, None, "No history exists yet for this customer."

    embedding = nlu.embed(question)
    retrieved = query_by_account(account_id, embedding, n_results=3)
    context = "\n".join(retrieved) if retrieved else latest.raw_text
    answer = nlu.answer_question(question, context)
    return "answered", account_id, answer, None
