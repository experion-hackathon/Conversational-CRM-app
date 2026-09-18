"""Conversational CRM API -- C-API (solution.json), FastAPI (SOL-4).

Run: uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.database import init_engine
from app.routers import accounts, auth_router, briefs, commitments, interactions, qa
from app.schemas import ErrorCode, ErrorResponse


@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_engine()
    yield


app = FastAPI(title="Conversational CRM API", version="2.0.0", lifespan=_lifespan)


@app.exception_handler(HTTPException)
def _http_exception_handler(request: Request, exc: HTTPException):
    """API-CONTRACT-conversational-crm-T-1-v2.0.json's Error schema is the
    top-level response body (error_code/message/details), not nested under a
    "detail" key -- FastAPI's default handler nests it, so every route in
    this codebase raises HTTPException(detail=ErrorResponse(...).model_dump())
    and this handler un-nests it back to the contract's actual shape."""
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)
    return JSONResponse(status_code=exc.status_code, content={"error_code": "UNKNOWN", "message": str(exc.detail)}, headers=exc.headers)


@app.exception_handler(OperationalError)
def _sqlite_busy_handler(request: Request, exc: OperationalError):
    """DAT-3: a write that could not be serialized within the busy-timeout/
    retry budget is a 503 with Retry-After, never a silent drop or a 500."""
    return JSONResponse(
        status_code=503,
        headers={"Retry-After": "1"},
        content=ErrorResponse(error_code=ErrorCode.RETRY_LATER, message="The database is briefly busy. Please retry.").model_dump(),
    )


app.include_router(auth_router.router)
app.include_router(accounts.router)
app.include_router(interactions.router)
app.include_router(qa.router)
app.include_router(briefs.router)
app.include_router(commitments.router)


@app.get("/health")
def health():
    return {"status": "ok"}
