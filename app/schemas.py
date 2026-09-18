"""Pydantic schemas matching API-CONTRACT-conversational-crm-T-1-v2.0.json exactly.

Every schema name below is the same name used in that contract's
components.schemas -- kept in lockstep deliberately so a diff between this
file and the contract is easy to spot.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ErrorCode:
    EMPTY_NOTE = "EMPTY_NOTE"
    UNSUPPORTED_IMAGE_FORMAT = "UNSUPPORTED_IMAGE_FORMAT"
    INTERACTION_NOT_FOUND = "INTERACTION_NOT_FOUND"
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    INTERACTION_ALREADY_MATCHED = "INTERACTION_ALREADY_MATCHED"
    COMMITMENT_NOT_FOUND = "COMMITMENT_NOT_FOUND"
    EMPTY_QUESTION = "EMPTY_QUESTION"
    EMPTY_REQUEST = "EMPTY_REQUEST"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    RETRY_LATER = "RETRY_LATER"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    LOGIN_LOCKED = "LOGIN_LOCKED"
    RATE_LIMITED = "RATE_LIMITED"


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict | None = None


class Account(BaseModel):
    id: str
    name: str


class Attendee(BaseModel):
    id: str
    name: str
    company: str | None = None
    role: str | None = None


class Commitment(BaseModel):
    id: str
    account_id: str | None
    interaction_id: str
    text: str
    due_date: date | None
    status: Literal["open", "complete"]


class Interaction(BaseModel):
    id: str
    account_id: str | None
    raw_text: str
    source_type: Literal["typed", "business_card"]
    match_status: Literal["matched", "unmatched"]
    manual_entry_required: bool = False
    captured_at: datetime
    attendees: list[Attendee] = Field(default_factory=list)
    commitments: list[Commitment] = Field(default_factory=list)


class CaptureTextRequest(BaseModel):
    raw_text: str = Field(min_length=0)


class ResolveCustomerRequest(BaseModel):
    account_id: str


class QARequest(BaseModel):
    question: str
    account_id: str | None = None


class QAResponse(BaseModel):
    resolution: Literal["answered", "no_history", "no_open_commitments", "no_attendees_captured", "not_identified"]
    account_id: str | None = None
    answer_text: str | None = None
    message: str | None = None


class BriefRequest(BaseModel):
    request_text: str
    account_id: str | None = None

    @field_validator("request_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        return v


class BriefSummary(BaseModel):
    history_text: str | None = None
    open_commitments: list[Commitment] = Field(default_factory=list)
    stakeholders: list[Attendee] = Field(default_factory=list)
    relationship_status: str | None = None


class BriefResponse(BaseModel):
    resolution: Literal["generated", "no_history", "not_identified"]
    account_id: str | None = None
    summary: BriefSummary | None = None
    message: str | None = None


class DueCommitmentsResponse(BaseModel):
    overdue: list[Commitment] = Field(default_factory=list)
    due_soon: list[Commitment] = Field(default_factory=list)
    unspecified: list[Commitment] = Field(default_factory=list)
    message: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    authenticated: bool = True


class LogoutResponse(BaseModel):
    invalidated: bool = True
