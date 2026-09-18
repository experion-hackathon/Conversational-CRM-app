"""POST /interactions, GET /interactions/unmatched,
POST /interactions/{interactionId}/resolve-customer.
F-1/F-2, US-1..US-9, US-22 (F-8 continue-conversation reuse)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.adapters.crm_adapter import CRMAdapter, get_crm_adapter
from app.auth import check_rate_limit, require_session
from app.database import get_db
from app.nlu import get_nlu_client
from app.nlu.base import NLUClient
from app.schemas import Attendee, ErrorCode, ErrorResponse, ResolveCustomerRequest
from app.schemas import Commitment as CommitmentSchema
from app.schemas import Interaction as InteractionSchema
from app.services import capture_service

router = APIRouter(prefix="/interactions", tags=["interactions"])


def _to_schema(interaction) -> InteractionSchema:
    return InteractionSchema(
        id=interaction.id,
        account_id=interaction.account_id,
        raw_text=interaction.raw_text,
        source_type=interaction.source_type,
        match_status=interaction.match_status,
        manual_entry_required=interaction.manual_entry_required,
        captured_at=interaction.captured_at,
        attendees=[Attendee(id=a.id, name=a.name, company=a.company, role=a.role) for a in interaction.attendees],
        commitments=[
            CommitmentSchema(id=c.id, account_id=c.account_id, interaction_id=c.interaction_id, text=c.text, due_date=c.due_date, status=c.status)
            for c in interaction.commitments
        ],
    )


@router.post("", response_model=InteractionSchema, status_code=201)
async def capture_interaction(
    request: Request,
    session: str = Depends(require_session),
    db: Session = Depends(get_db),
    nlu: NLUClient = Depends(get_nlu_client),
    crm: CRMAdapter = Depends(get_crm_adapter),
):
    check_rate_limit(session)
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload: UploadFile | None = form.get("business_card_image")  # type: ignore[assignment]
        if upload is None:
            raise HTTPException(
                status_code=422,
                detail=ErrorResponse(error_code=ErrorCode.UNSUPPORTED_IMAGE_FORMAT, message="No image was provided.").model_dump(),
            )
        contents = await upload.read()
        if not contents:
            raise HTTPException(
                status_code=422,
                detail=ErrorResponse(error_code=ErrorCode.UNSUPPORTED_IMAGE_FORMAT, message="The uploaded file is empty or unreadable.").model_dump(),
            )
        # [INFERRED -- needs confirmation, solution.json OI-3] No OCR model is
        # wired up in this scope; every business-card submission takes the
        # "legible but no fields recognized" branch honestly, rather than
        # fabricating extracted contact fields.
        interaction = capture_service.capture_business_card(db, extracted_name=None, extracted_company=None, extracted_role=None)
        return _to_schema(interaction)

    body = await request.json()
    raw_text = body.get("raw_text", "")
    try:
        interaction = capture_service.capture_typed_interaction(
            db, raw_text, nlu, crm, reference_date=date.today()
        )
    except capture_service.EmptyNoteError:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(error_code=ErrorCode.EMPTY_NOTE, message="Cannot save an empty note.").model_dump(),
        ) from None
    return _to_schema(interaction)


@router.get("/unmatched", response_model=list[InteractionSchema])
def list_unmatched_interactions(
    _session: str = Depends(require_session),
    db: Session = Depends(get_db),
):
    return [_to_schema(i) for i in capture_service.list_unmatched(db)]


@router.post("/{interaction_id}/resolve-customer", response_model=InteractionSchema)
def resolve_interaction_customer(
    interaction_id: str,
    payload: ResolveCustomerRequest,
    _session: str = Depends(require_session),
    db: Session = Depends(get_db),
    crm: CRMAdapter = Depends(get_crm_adapter),
):
    try:
        interaction = capture_service.resolve_customer(db, interaction_id, payload.account_id, crm)
    except capture_service.InteractionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(error_code=ErrorCode.INTERACTION_NOT_FOUND, message="No interaction exists with that id.").model_dump(),
        ) from None
    except capture_service.AccountNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(error_code=ErrorCode.ACCOUNT_NOT_FOUND, message="No account exists with that id.").model_dump(),
        ) from None
    except capture_service.InteractionAlreadyMatchedError:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(error_code=ErrorCode.INTERACTION_ALREADY_MATCHED, message="This interaction is not currently unmatched.").model_dump(),
        ) from None
    return _to_schema(interaction)
