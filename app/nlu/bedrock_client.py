"""Real AWS Bedrock client -- the architecture's actual declared C-NLU technology
(solution.json SOL-6/SOL-4; data_integration decision DAT-2: Amazon Titan Text
Embeddings V2, 1024-dimension, cosine similarity).

NOT exercised by this codebase's test suite: no AWS credentials or Bedrock
model access exist in the environment this backend was implemented in. This
is real, reviewable code against the documented Bedrock Runtime API shape,
not a placeholder -- but it is disclosed as `implementation_status: partial`
for this specific boundary in the backend report, not claimed as verified.
"""
from __future__ import annotations

import json
import re
from datetime import date

import boto3

from app.config import get_settings
from app.nlu.base import ExtractedAttendee, ExtractedCommitment, ExtractionResult

_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


def _extract_json_object(raw: str) -> str:
    """Some Bedrock text models (observed: Mistral) wrap their JSON answer in a
    markdown code fence despite being told to respond with JSON only -- strip
    that wrapper rather than failing to parse a genuinely correct extraction."""
    match = _FENCED_JSON.search(raw)
    return match.group(1) if match else raw

_EXTRACTION_PROMPT = """Extract from the sales interaction note below:
1. Every distinct attendee name mentioned (with company/role if stated).
2. Every distinct commitment or next step, with a due date if one is stated or
   clearly implied (e.g. "by Friday"), resolved against the reference date
   {reference_date}. If no date is stated or it is vague ("soon"), omit due_date.

Respond ONLY with JSON: {{"attendees": [{{"name": str, "company": str|null, "role": str|null}}],
"commitments": [{{"text": str, "due_date": "YYYY-MM-DD"|null}}]}}

Note: {raw_text}
"""


class BedrockNLUClient:
    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self._client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def _invoke_text_model(self, prompt: str) -> str:
        # Converse (not invoke_model) deliberately: it normalizes request/response
        # shape across model families (Anthropic, Mistral, Titan Text, Llama,
        # Cohere Command R, ...), so BEDROCK_TEXT_MODEL_ID can be swapped in .env
        # without a code change, rather than hand-coding one vendor's message
        # format the way invoke_model requires.
        response = self._client.converse(
            modelId=self._settings.bedrock_text_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1024},
        )
        return response["output"]["message"]["content"][0]["text"]

    def extract(self, raw_text: str, reference_date: date) -> ExtractionResult:
        prompt = _EXTRACTION_PROMPT.format(reference_date=reference_date.isoformat(), raw_text=raw_text)
        raw = self._invoke_text_model(prompt)
        data = json.loads(_extract_json_object(raw))
        attendees = [
            ExtractedAttendee(name=a["name"], company=a.get("company"), role=a.get("role"))
            for a in data.get("attendees", [])
        ]
        commitments = []
        for c in data.get("commitments", []):
            due = date.fromisoformat(c["due_date"]) if c.get("due_date") else None
            commitments.append(ExtractedCommitment(text=c["text"], due_date=due))
        return ExtractionResult(attendees=attendees, commitments=commitments)

    def answer_question(self, question: str, context_text: str) -> str:
        prompt = f"Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer concisely from the context only."
        return self._invoke_text_model(prompt)

    def synthesize_brief(self, history_text: str, has_relationship_signal: bool, relationship_context: str) -> tuple[str, str | None]:
        prompt = (
            f"Summarize this customer relationship history in 2-3 sentences:\n{history_text}\n\n"
            "Then, if the notes indicate where the relationship currently stands, add one sentence "
            "on that; otherwise say nothing further."
        )
        text = self._invoke_text_model(prompt)
        relationship_status = text if has_relationship_signal else None
        return text, relationship_status

    def embed(self, text: str) -> list[float]:
        response = self._client.invoke_model(
            modelId=self._settings.bedrock_embedding_model_id,
            body=json.dumps({"inputText": text}),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        return payload["embedding"]
