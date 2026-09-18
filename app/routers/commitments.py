"""GET /commitments/due, PATCH /commitments/{commitmentId}/complete.
F-4, US-15/US-16; also F-8's home to-do list, US-20/US-21/US-23."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import require_session
from app.database import get_db
from app.schemas import Commitment as CommitmentSchema
from app.schemas import DueCommitmentsResponse, ErrorCode, ErrorResponse
from app.services import commitments_service

router = APIRouter(prefix="/commitments", tags=["commitments"])


def _to_schema(c) -> CommitmentSchema:
    return CommitmentSchema(id=c.id, account_id=c.account_id, interaction_id=c.interaction_id, text=c.text, due_date=c.due_date, status=c.status)


@router.get("/due", response_model=DueCommitmentsResponse)
def list_due_commitments(
    due_soon_window_days: int | None = Query(default=None, ge=1),
    reference_date: date | None = Query(default=None),
    _session: str = Depends(require_session),
    db: Session = Depends(get_db),
):
    overdue, due_soon, unspecified, message = commitments_service.list_due_commitments(
        db, reference_date=reference_date, due_soon_window_days=due_soon_window_days
    )
    return DueCommitmentsResponse(
        overdue=[_to_schema(c) for c in overdue],
        due_soon=[_to_schema(c) for c in due_soon],
        unspecified=[_to_schema(c) for c in unspecified],
        message=message,
    )


@router.patch("/{commitment_id}/complete", response_model=CommitmentSchema)
def mark_commitment_complete(
    commitment_id: str,
    _session: str = Depends(require_session),
    db: Session = Depends(get_db),
):
    try:
        commitment = commitments_service.mark_commitment_complete(db, commitment_id)
    except commitments_service.CommitmentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(error_code=ErrorCode.COMMITMENT_NOT_FOUND, message="No commitment exists with that id.").model_dump(),
        ) from None
    return _to_schema(commitment)
