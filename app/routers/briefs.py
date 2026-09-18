"""POST /briefs -- F-5, US-17..US-19."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.crm_adapter import CRMAdapter, get_crm_adapter
from app.auth import check_rate_limit, require_session
from app.database import get_db
from app.nlu import get_nlu_client
from app.nlu.base import NLUClient
from app.schemas import BriefRequest, BriefResponse, ErrorCode, ErrorResponse
from app.services import brief_service

router = APIRouter(tags=["briefs"])


@router.post("/briefs", response_model=BriefResponse)
def generate_brief(
    payload: BriefRequest,
    session: str = Depends(require_session),
    db: Session = Depends(get_db),
    nlu: NLUClient = Depends(get_nlu_client),
    crm: CRMAdapter = Depends(get_crm_adapter),
):
    if not payload.request_text or not payload.request_text.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(error_code=ErrorCode.EMPTY_REQUEST, message="Request text cannot be empty.").model_dump(),
        )
    check_rate_limit(session)
    resolution, account_id, summary, message = brief_service.generate_brief(
        db, payload.request_text, payload.account_id, nlu, crm
    )
    return BriefResponse(resolution=resolution, account_id=account_id, summary=summary, message=message)
