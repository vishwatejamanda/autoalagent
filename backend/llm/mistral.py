"""Mistral AI LLM provider implementation."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from llm.provider import (
    LLMMessage,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
    LLMServerError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

# Rough per-1K-token cost estimates (USD).  Override via env / config if needed.
_COST_TABLE: dict[str, dict[str, float]] = {
    "mistral-large-latest": {"input": 0.002, "output": 0.006},
    "mistral-small-latest": {"input": 0.0002, "output": 0.0006},
}

_DEFAULT_COST = {"input": 0.001, "output": 0.003}

_API_BASE = "https://api.mistral.ai/v1/chat/completions"
_TIMEOUT_SECONDS = 120.0


class MistralProvider(LLMProvider):
    """Mistral AI chat-completion provider."""

    provider_name: str = "mistral"

    def __init__(
        self,
        api_key: str | None = None,
        strong_model: str | None = None,
        cheap_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key: str = api_key if api_key is not None else settings.MISTRAL_API_KEY
        self._strong_model: str = strong_model if strong_model is not None else settings.MISTRAL_STRONG_MODEL
        self._cheap_model: str = cheap_model if cheap_model is not None else settings.MISTRAL_CHEAP_MODEL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_model(self, task: str = "strong") -> str:
        """Return the appropriate model name for a task type."""
        if task == "cheap":
            return self._cheap_model
        return self._strong_model

    @retry(
        retry=retry_if_exception_type((LLMRateLimitError, LLMServerError, LLMTimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        json_schema: dict | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a chat completion request to Mistral AI."""
        if not self._api_key:
            from llm.provider import LLMError
            raise LLMError("Mistral API key is not configured. Please set MISTRAL_API_KEY in settings or .env")
        resolved_model = model or self._strong_model

        # Build the request payload
        payload = self._build_payload(messages, resolved_model, json_schema, temperature)

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    _API_BASE,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            latency = (time.perf_counter() - start) * 1000
            logger.warning("Mistral request timed out after %.0f ms", latency)
            raise LLMTimeoutError(f"Mistral request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            logger.error("Mistral HTTP transport error: %s", exc)
            raise LLMServerError(f"Mistral transport error: {exc}") from exc

        latency_ms = (time.perf_counter() - start) * 1000

        # Handle error status codes
        self._handle_status(resp, latency_ms)

        # Parse successful response
        return self._parse_response(resp, resolved_model, latency_ms)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: list[LLMMessage],
        model: str,
        json_schema: dict | None,
        temperature: float,
    ) -> dict[str, Any]:
        api_messages: list[dict[str, str]] = []

        for msg in messages:
            content = msg.content
            # Inject JSON schema instructions into the system message
            if json_schema and msg.role == "system":
                schema_instructions = (
                    "\n\nYou MUST respond with valid JSON matching this schema:\n"
                    f"```json\n{json.dumps(json_schema, indent=2)}\n```"
                )
                content = content + schema_instructions
            api_messages.append({"role": msg.role, "content": content})

        payload: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "temperature": temperature,
        }

        if json_schema:
            payload["response_format"] = {"type": "json_object"}

        return payload

    def _handle_status(self, resp: httpx.Response, latency_ms: float) -> None:
        if resp.status_code == 429:
            logger.warning("Mistral rate-limited (429) after %.0f ms", latency_ms)
            raise LLMRateLimitError(
                f"Mistral rate limit exceeded: {resp.text}"
            )

        if 500 <= resp.status_code < 600:
            logger.warning(
                "Mistral server error %d after %.0f ms: %s",
                resp.status_code,
                latency_ms,
                resp.text,
            )
            raise LLMServerError(
                f"Mistral server error {resp.status_code}: {resp.text}"
            )

        if resp.status_code != 200:
            logger.error(
                "Mistral unexpected status %d after %.0f ms: %s",
                resp.status_code,
                latency_ms,
                resp.text,
            )
            from llm.provider import LLMError

            raise LLMError(
                f"Mistral unexpected status {resp.status_code}: {resp.text}"
            )

    def _parse_response(
        self, resp: httpx.Response, model: str, latency_ms: float
    ) -> LLMResponse:
        data: dict[str, Any] = resp.json()

        content = ""
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        logger.debug(
            "Mistral %s — %d prompt + %d completion tokens in %.0f ms",
            model,
            prompt_tokens,
            completion_tokens,
            latency_ms,
        )

        return LLMResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            provider=self.provider_name,
        )

    # ------------------------------------------------------------------
    # Cost helpers (used by the router for audit logging)
    # ------------------------------------------------------------------

    @staticmethod
    def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Return an estimated USD cost for a given call."""
        costs = _COST_TABLE.get(model, _DEFAULT_COST)
        return (prompt_tokens / 1000) * costs["input"] + (
            completion_tokens / 1000
        ) * costs["output"]
