"""F-1 (Conversational Interaction Capture) and F-2 (Automatic Extraction &
Thread Tagging) business logic. Realizes US-1..US-9 (per data_integration's
traceability, DATA-AND-INTEGRATION-conversational-crm-T-1-v2.0.md Section 4).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.adapters.crm_adapter import CRMAdapter
from app.models import Commitment, Interaction, InteractionAttendee
from app.nlu.base import NLUClient
from app.vector_store import update_chunk_account, upsert_interaction_chunk


class EmptyNoteError(Exception):
    pass


class InteractionNotFoundError(Exception):
    pass


class AccountNotFoundError(Exception):
    pass


class InteractionAlreadyMatchedError(Exception):
    pass


def capture_typed_interaction(
    db: Session,
    raw_text: str,
    nlu: NLUClient,
    crm: CRMAdapter,
    reference_date: date | None = None,
) -> Interaction:
    """US-1, US-2, US-5, US-6, US-7, US-8, US-9 (F-1 AC1/AC3/AC5/AC6, F-2 AC1-AC4)."""
    if not raw_text or not raw_text.strip():
        # US-2 AC1: reject empty/whitespace-only, no row created.
        raise EmptyNoteError()

    reference_date = reference_date or datetime.now(timezone.utc).date()

    # F-1 AC1/AC6: match against exactly one seeded account, from the entry's
    # own content -- no precondition customer-selection step (US-6).
    matched_account = crm.find_account_by_name_fragment(raw_text)

    interaction = Interaction(
        account_id=matched_account.id if matched_account else None,
        raw_text=raw_text,
        source_type="typed",
        match_status="matched" if matched_account else "unmatched",
        manual_entry_required=False,
        captured_at=datetime.now(timezone.utc),
    )
    db.add(interaction)
    db.flush()  # assign interaction.id

    # F-1 AC5 / F-2 AC1-AC2: extract attendees and commitments synchronously,
    # in the same request (solution.json decision SOL-3).
    extraction = nlu.extract(raw_text, reference_date)
    for a in extraction.attendees:
        db.add(InteractionAttendee(interaction_id=interaction.id, name=a.name, company=a.company, role=a.role))
    for c in extraction.commitments:
        db.add(Commitment(
            interaction_id=interaction.id,
            account_id=interaction.account_id,  # F-2 AC3: same thread as source note
            text=c.text,
            due_date=c.due_date.isoformat() if c.due_date else None,
            status="open",
        ))

    db.commit()
    db.refresh(interaction)

    # F-3/F-5 semantic retrieval support: embed the raw text once at capture
    # time (decision DAT-2). This runs AFTER the SQLite commit -- Chroma is a
    # secondary, best-effort search index (DAT-2), not the source of truth, so
    # a write here must never precede the transaction it depends on. Doing it
    # before commit meant a commit failure (e.g. DAT-3's busy-timeout path)
    # could leave an orphaned Chroma chunk pointing at an interaction row that
    # was rolled back and never existed.
    try:
        embedding = nlu.embed(raw_text)
        upsert_interaction_chunk(
            interaction_id=interaction.id,
            account_id=interaction.account_id,
            text=raw_text,
            embedding=embedding,
            embedded_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception:
        # Indexing failure must not lose an already-committed interaction --
        # the note is safely persisted; it is just not yet semantically
        # searchable. Not a defect either way is acceptable to lose silently
        # forever, but re-indexing is out of this task's scope (no background
        # job exists to retry it) and disclosed as such.
        pass

    return interaction


def capture_business_card(db: Session, extracted_name: str | None, extracted_company: str | None, extracted_role: str | None) -> Interaction:
    """US-4 (F-1 AC2): business-card path. `extracted_*` is None when the image
    could not be read or no fields were recognized -- manual_entry_required=true
    in that case, with no fabricated fields (US-4 AC2)."""
    manual_entry_required = extracted_name is None
    interaction = Interaction(
        account_id=None,
        raw_text=f"[business card scan] {extracted_name or ''}".strip(),
        source_type="business_card",
        match_status="unmatched",
        manual_entry_required=manual_entry_required,
        captured_at=datetime.now(timezone.utc),
    )
    db.add(interaction)
    db.flush()
    if extracted_name:
        db.add(InteractionAttendee(interaction_id=interaction.id, name=extracted_name, company=extracted_company, role=extracted_role))
    db.commit()
    db.refresh(interaction)
    return interaction


def list_unmatched(db: Session) -> list[Interaction]:
    """US-3 (F-1 AC4): oldest unresolved first."""
    return (
        db.query(Interaction)
        .filter(Interaction.match_status == "unmatched")
        .order_by(Interaction.captured_at.asc())
        .all()
    )


def resolve_customer(db: Session, interaction_id: str, account_id: str, crm: CRMAdapter) -> Interaction:
    """US-3 (F-1 AC4): manually attach an unmatched note to the selected account."""
    interaction = db.get(Interaction, interaction_id)
    if interaction is None:
        raise InteractionNotFoundError()
    if crm.get_account(account_id) is None:
        raise AccountNotFoundError()
    if interaction.match_status != "unmatched":
        raise InteractionAlreadyMatchedError()

    interaction.account_id = account_id
    interaction.match_status = "matched"
    for commitment in interaction.commitments:
        commitment.account_id = account_id
    db.commit()
    db.refresh(interaction)

    try:
        update_chunk_account(interaction_id, account_id)
    except Exception:
        pass  # same non-fatal-indexing rationale as capture_typed_interaction (V-BACK-3)

    return interaction
