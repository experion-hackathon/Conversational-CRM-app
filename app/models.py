"""SQLAlchemy models for the three tables this system owns.

Matches DATA-MODEL-conversational-crm-T-1-v2.0.md Section 1 exactly:
interactions, interaction_attendees, commitments. There is deliberately no
`accounts` or `contacts` table (decision DAT-12, PRD v1.8 Section 7 Data
Ownership NFR) -- account/contact data is read live via app.adapters.crm_adapter.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, new_id


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("INT"))
    # Adapter-provided account identifier -- NOT a local FOREIGN KEY (DAT-12).
    # NULL exactly when match_status='unmatched' (F-1 AC1/AC4).
    account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)  # 'typed' | 'business_card'
    match_status: Mapped[str] = mapped_column(String, nullable=False, default="unmatched")  # 'matched' | 'unmatched'
    manual_entry_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    attendees: Mapped[list["InteractionAttendee"]] = relationship("InteractionAttendee", back_populates="interaction", cascade="all, delete-orphan")
    commitments: Mapped[list["Commitment"]] = relationship("Commitment", back_populates="interaction", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("source_type IN ('typed', 'business_card')", name="ck_interactions_source_type"),
        CheckConstraint("match_status IN ('matched', 'unmatched')", name="ck_interactions_match_status"),
        Index("idx_interactions_account_captured", "account_id", "captured_at", "id"),
        Index("idx_interactions_match_status", "match_status"),
    )


class InteractionAttendee(Base):
    __tablename__ = "interaction_attendees"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ATT"))
    interaction_id: Mapped[str] = mapped_column(String, ForeignKey("interactions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)

    interaction: Mapped["Interaction"] = relationship("Interaction", back_populates="attendees")

    __table_args__ = (
        Index("idx_attendees_interaction_id", "interaction_id"),
    )


class Commitment(Base):
    __tablename__ = "commitments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("CMT"))
    interaction_id: Mapped[str] = mapped_column(String, ForeignKey("interactions.id"), nullable=False)
    # Denormalized from the parent interaction (DAT-1) -- adapter-provided
    # identifier, not a local FOREIGN KEY (DAT-12). NULL iff parent unmatched.
    account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[str | None] = mapped_column(String, nullable=True)  # ISO-8601 date, NULL = unspecified (F-2 AC2/AC4)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")  # 'open' | 'complete' (decision DAT-5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    interaction: Mapped["Interaction"] = relationship("Interaction", back_populates="commitments")

    __table_args__ = (
        CheckConstraint("status IN ('open', 'complete')", name="ck_commitments_status"),
        Index("idx_commitments_status_duedate", "status", "due_date"),
        Index("idx_commitments_interaction_id", "interaction_id"),
    )
