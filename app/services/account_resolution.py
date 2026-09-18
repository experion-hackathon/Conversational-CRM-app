"""Shared account-resolution pattern (decision DAT-4), used identically by
qa_service and brief_service. The API-CONTRACT explicitly documents /briefs
as following "the same account_id-hint-or-resolve-from-text pattern as /qa
(decision DAT-4)" -- this module is the single implementation both endpoints
call, so that claim cannot silently drift out of sync again (V-BACK-2: an
earlier duplicated copy in brief_service.py fell back to text-based
resolution on an invalid hint instead of failing closed like qa_service did).
"""
from __future__ import annotations

from app.adapters.crm_adapter import CRMAdapter


def resolve_account_id(text: str, account_id_hint: str | None, crm: CRMAdapter) -> str | None:
    """An explicit but invalid hint fails closed to "not identified" rather
    than silently falling back to text-based resolution -- a caller-supplied
    account_id is treated as an assertion, not a suggestion."""
    if account_id_hint:
        return account_id_hint if crm.get_account(account_id_hint) else None
    account = crm.find_account_by_name_fragment(text)
    return account.id if account else None
