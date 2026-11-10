PROMPT_VERSION = "v2"

INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"

SYSTEM_PROMPT = (
    "Answer using only the provided context. Cite chunk ids used in the answer. "
    f"If the context does not contain the answer, reply exactly {INSUFFICIENT_CONTEXT}."
)
