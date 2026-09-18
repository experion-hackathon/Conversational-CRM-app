"""F-5 (Brief-Me-on-Customer Summary) business logic. US-17..US-19."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.adapters.crm_adapter import CRMAdapter
from app.models import Commitment, Interaction
from app.nlu.base import NLUClient
from app.services.account_resolution import resolve_account_id
from app.vector_store import query_by_account


def generate_brief(db: Session, request_text: str, account_id_hint: str | None, nlu: NLUClient, crm: CRMAdapter):
    """Returns (resolution, account_id, summary_dict_or_None, message)."""
    account_id = resolve_account_id(request_text, account_id_hint, crm)
    if account_id is None:
        return "not_identified", None, None, "Could not identify the requested customer."

    interactions = (
        db.query(Interaction)
        .filter(Interaction.account_id == account_id)
        .order_by(Interaction.captured_at.desc())
        .all()
    )
    if not interactions:
        return "no_history", account_id, None, "No history exists yet for this customer."

    embedding = nlu.embed(request_text)
    retrieved = query_by_account(account_id, embedding, n_results=5)
    history_context = "\n".join(retrieved) if retrieved else "\n".join(i.raw_text for i in interactions[:3])

    open_commitments = (
        db.query(Commitment)
        .filter(Commitment.account_id == account_id, Commitment.status == "open")
        .all()
    )
    attendee_names = {a.name for i in interactions for a in i.attendees}
    stakeholders = [
        {"id": f"stakeholder-{idx}", "name": name, "company": None, "role": None}
        for idx, name in enumerate(sorted(attendee_names))
    ]
    for c in crm.fetch_contacts(account_id):
        stakeholders.append({"id": c.id, "name": c.name, "company": c.company, "role": c.role})

    # US-18 AC2: "no relationship-status information captured yet" must be a
    # reachable state for a *generated* brief, distinct from the no_history
    # response above. `interactions` is already guaranteed non-empty at this
    # point (V-BACK-1 -- the previous condition `bool(interactions or ...)`
    # was therefore always True and this branch could never fire). This
    # system holds no discrete CRM pipeline/deal-stage field (PRD Section
    # 13.1); a single bare note with no tracked follow-up and no named
    # stakeholder is treated as carrying no discernible relationship-stance
    # signal yet, distinct from a thread with multiple touchpoints, an open
    # commitment, or an identified attendee. [INFERRED -- needs confirmation:
    # this operationalization of "content indicating where the relationship
    # stands" is this task's own judgment call, since PRD Open Question 14
    # leaves whether narrative synthesis is even the right mechanism unresolved.]
    has_relationship_signal = bool(open_commitments) or bool(attendee_names) or len(interactions) > 1
    history_summary, relationship_status = nlu.synthesize_brief(history_context, has_relationship_signal, history_context)

    summary = {
        "history_text": history_summary,
        "open_commitments": [
            {"id": c.id, "account_id": c.account_id, "interaction_id": c.interaction_id, "text": c.text, "due_date": c.due_date, "status": c.status}
            for c in open_commitments
        ],
        "stakeholders": stakeholders,
        "relationship_status": relationship_status,
    }
    return "generated", account_id, summary, None
