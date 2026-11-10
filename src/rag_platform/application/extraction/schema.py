import json
import re

from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from rag_platform.domain.errors import ValidationError

FIELDS = ("parties", "dates", "amounts", "obligations", "risks", "decisions", "owners")

SYSTEM_PROMPT = (
    "You extract structured facts from business documents. "
    "Return JSON only, with keys: " + ", ".join(FIELDS) + ', and "missing". '
    'Each field holds a list of objects {"text": "...", "quote": "..."} where quote is copied '
    "verbatim from the document. List a field in missing when the document does not state it."
)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class ExtractedFact(BaseModel):
    text: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class ExtractionPayload(BaseModel):
    parties: list[ExtractedFact] = Field(default_factory=list)
    dates: list[ExtractedFact] = Field(default_factory=list)
    amounts: list[ExtractedFact] = Field(default_factory=list)
    obligations: list[ExtractedFact] = Field(default_factory=list)
    risks: list[ExtractedFact] = Field(default_factory=list)
    decisions: list[ExtractedFact] = Field(default_factory=list)
    owners: list[ExtractedFact] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


def build_user_prompt(text: str) -> str:
    return f"Document:\n{text}\n\nReturn the JSON object."


def parse_payload(raw: str) -> ExtractionPayload:
    cleaned = _FENCE.sub("", raw.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValidationError("the model did not return a JSON object")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON from the model: {exc}") from exc
    try:
        return ExtractionPayload.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(f"JSON does not match the extraction schema: {exc}") from exc
