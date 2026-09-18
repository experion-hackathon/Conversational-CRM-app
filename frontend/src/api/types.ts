/**
 * TypeScript types mirroring app/schemas.py / API-CONTRACT-conversational-crm-T-1-v2.0.json
 * component schemas exactly -- kept in lockstep deliberately, same convention
 * the backend report used for its own Pydantic models.
 */

export type ErrorCode =
  | 'EMPTY_NOTE'
  | 'UNSUPPORTED_IMAGE_FORMAT'
  | 'INTERACTION_NOT_FOUND'
  | 'ACCOUNT_NOT_FOUND'
  | 'INTERACTION_ALREADY_MATCHED'
  | 'COMMITMENT_NOT_FOUND'
  | 'EMPTY_QUESTION'
  | 'EMPTY_REQUEST'
  | 'UNAUTHENTICATED'
  | 'RETRY_LATER'
  | 'INVALID_CREDENTIALS'
  | 'LOGIN_LOCKED'
  | 'RATE_LIMITED'

export interface ErrorResponse {
  error_code: ErrorCode | string
  message: string
  details?: Record<string, unknown> | null
}

export interface Account {
  id: string
  name: string
}

export interface Attendee {
  id: string
  name: string
  company: string | null
  role: string | null
}

export interface Commitment {
  id: string
  account_id: string | null
  interaction_id: string
  text: string
  due_date: string | null
  status: 'open' | 'complete'
}

export interface Interaction {
  id: string
  account_id: string | null
  raw_text: string
  source_type: 'typed' | 'business_card'
  match_status: 'matched' | 'unmatched'
  manual_entry_required: boolean
  captured_at: string
  attendees: Attendee[]
  commitments: Commitment[]
}

export interface QAResponse {
  resolution: 'answered' | 'no_history' | 'no_open_commitments' | 'no_attendees_captured' | 'not_identified'
  account_id: string | null
  answer_text: string | null
  message: string | null
}

export interface BriefSummary {
  history_text: string | null
  open_commitments: Commitment[]
  stakeholders: Attendee[]
  relationship_status: string | null
}

export interface BriefResponse {
  resolution: 'generated' | 'no_history' | 'not_identified'
  account_id: string | null
  summary: BriefSummary | null
  message: string | null
}

export interface DueCommitmentsResponse {
  overdue: Commitment[]
  due_soon: Commitment[]
  unspecified: Commitment[]
  message: string | null
}

export interface LoginResponse {
  authenticated: boolean
}

export interface LogoutResponse {
  invalidated: boolean
}
