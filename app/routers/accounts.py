"""GET /accounts -- US-3 only (listAccounts). Live adapter read, decision DAT-12."""
from fastapi import APIRouter, Depends

from app.adapters.crm_adapter import CRMAdapter, get_crm_adapter
from app.auth import require_session
from app.schemas import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[Account])
def list_accounts(
    _session: str = Depends(require_session),
    crm: CRMAdapter = Depends(get_crm_adapter),
):
    accounts = sorted(crm.fetch_accounts(), key=lambda a: a.name.lower())
    return [Account(id=a.id, name=a.name) for a in accounts]
