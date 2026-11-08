from rag_platform.domain.errors import ValidationError


def validate_citations(candidate_ids: list[str], allowed_ids: set[str]) -> list[str]:
    invalid = [cid for cid in candidate_ids if cid not in allowed_ids]
    if invalid:
        raise ValidationError(f"citations not in retrieval set: {invalid[:3]}")
    return candidate_ids
