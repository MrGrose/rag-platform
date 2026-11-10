import asyncio
import re

import httpx

from rag_platform.application.ports.llm import LlmCompletion, LlmProvider
from rag_platform.domain.errors import ServiceUnavailableError

_CHUNK_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


class OpenAiCompatibleLlmProvider(LlmProvider):
    """Chat completions over any OpenAI-compatible endpoint.

    Retries 429, 5xx and network errors with exponential backoff. Citations are
    read from chunk identifiers the model repeats from the prompt.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        if not api_key.strip():
            raise ServiceUnavailableError("LLM_API_KEY is required for a non-fake provider")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._temperature = temperature
        self._max_tokens = max_tokens
        self.model_name = model

    async def complete(self, system_prompt: str, user_prompt: str) -> LlmCompletion:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        last_error = "llm request failed"
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = f"llm transport error: {exc}"
            else:
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = f"llm upstream status {response.status_code}"
                elif response.status_code >= 400:
                    raise ServiceUnavailableError(
                        f"llm rejected the request: {response.status_code} {response.text[:200]}"
                    )
                else:
                    data = response.json()
                    text = (data["choices"][0]["message"]["content"] or "").strip()
                    if not text:
                        raise ServiceUnavailableError("llm returned an empty completion")
                    return LlmCompletion(
                        text=text,
                        citation_chunk_ids=_CHUNK_ID.findall(text),
                    )
            if attempt < self._max_retries:
                await asyncio.sleep(2**attempt)
        raise ServiceUnavailableError(last_error)
