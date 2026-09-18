"""POST /qa -- F-3, US-10..US-14."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.crm_adapter import CRMAdapter, get_crm_adapter
from app.auth import check_rate_limit, require_session
from app.database import get_db
from app.nlu import get_nlu_client
from app.nlu.base import NLUClient
from app.schemas import ErrorCode, ErrorResponse, QARequest, QAResponse
from app.services import qa_service

router = APIRouter(tags=["qa"])


@router.post("/qa", response_model=QAResponse)
def ask_question(
    payload: QARequest,
    session: str = Depends(require_session),
    db: Session = Depends(get_db),
    nlu: NLUClient = Depends(get_nlu_client),
    crm: CRMAdapter = Depends(get_crm_adapter),
):
    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(error_code=ErrorCode.EMPTY_QUESTION, message="Question cannot be empty.").model_dump(),
        )
    check_rate_limit(session)
    resolution, account_id, answer_text, message = qa_service.answer_question(
        db, payload.question, payload.account_id, nlu, crm
    )
    return QAResponse(resolution=resolution, account_id=account_id, answer_text=answer_text, message=message)
