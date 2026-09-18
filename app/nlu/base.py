"""C-NLU boundary interface (solution.json C-NLU component; SOL-6).

Two implementations exist behind this interface:
- RuleBasedNLUClient: real, deterministic, fully local -- no cloud dependency.
  This is the engine actually exercised by this backend's test suite and used
  by default (NLU_ENGINE=rule_based), since no AWS credentials are available
  in this development/CI environment.
- BedrockNLUClient (app.nlu.bedrock_client): real boto3 code against the
  architecture's declared technology (AWS Bedrock, decision SOL-6/DAT-2), but
  NOT exercised by any test in this codebase -- there is no AWS access in this
  environment to verify it against. Selected via NLU_ENGINE=bedrock. This is
  disclosed as a real, honest limitation in the backend report's Open Items,
  not silently hidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


@dataclass
class ExtractedAttendee:
    name: str
    company: str | None = None
    role: str | None = None


@dataclass
class ExtractedCommitment:
    text: str
    due_date: date | None = None


@dataclass
class ExtractionResult:
    attendees: list[ExtractedAttendee] = field(default_factory=list)
    commitments: list[ExtractedCommitment] = field(default_factory=list)


class NLUClient(Protocol):
    def extract(self, raw_text: str, reference_date: date) -> ExtractionResult:
        """F-1 AC5 (attendees), F-2 AC1/AC2 (commitments/due dates)."""
        ...

    def answer_question(self, question: str, context_text: str) -> str:
        """F-3: synthesize an answer from retrieved/structured context."""
        ...

    def synthesize_brief(self, history_text: str, has_relationship_signal: bool, relationship_context: str) -> tuple[str, str | None]:
        """F-5: returns (history_summary, relationship_status_or_None)."""
        ...

    def embed(self, text: str) -> list[float]:
        """Embedding for C-VEC (decision DAT-2)."""
        ...
