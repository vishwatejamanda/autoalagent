"""LLM routing engine with multi-provider fallback, audit logging, and JSON helpers."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from pydantic import BaseModel, ValidationError

from app.config import get_settings
from llm.mistral import MistralProvider
from llm.nvidia import NvidiaProvider
from llm.provider import (
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
    LLMServerError,
    LLMTimeoutError,
    LLMValidationError,
)

logger = logging.getLogger(__name__)


# ======================================================================
# JSON repair utilities
# ======================================================================

def _extract_json_block(text: str) -> str:
    """Try to extract a JSON payload from Markdown fenced code blocks."""
    # Match ```json ... ``` or ``` ... ```
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _repair_json(text: str) -> str:
    """Best-effort repair of common JSON issues returned by LLMs.

    Handles:
    - Extracting JSON from Markdown code blocks
    - Trailing commas before } or ]
    - Single quotes → double quotes (simplistic)
    - Missing closing braces / brackets
    """
    text = _extract_json_block(text)

    # Replace single quotes with double quotes (only outside existing double-quoted strings).
    # This is intentionally simplistic – it covers the majority of LLM outputs.
    if '"' not in text and "'" in text:
        text = text.replace("'", '"')

    # Remove trailing commas:  ,} or ,]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Balance braces / brackets
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    if open_braces > 0:
        text += "}" * open_braces
    if open_brackets > 0:
        text += "]" * open_brackets

    return text


# ======================================================================
# Audit logging helper
# ======================================================================

def _log_llm_call(
    *,
    provider: str,
    model: str,
    task: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cost: float,
    latency_ms: float,
    success: bool,
    error: str | None = None,
) -> None:
    """Persist an LLMCall audit record (fire-and-forget, non-blocking)."""
    try:
        from app.database import engine
        from models.audit import LLMCall
        from sqlmodel import Session

        with Session(engine) as session:
            record = LLMCall(
                provider=provider,
                model=model,
                task=task,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=int(latency_ms),
                success=success,
                error=error[:500] if error else "",
            )
            session.add(record)
            session.commit()
    except Exception:
        # Audit logging must never crash the main request.
        logger.exception("Failed to log LLM call to audit table")


def _estimate_cost(provider_name: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Delegate cost estimation to the appropriate provider helper."""
    if provider_name == "mistral":
        return MistralProvider.estimate_cost(model, prompt_tokens, completion_tokens)
    if provider_name == "nvidia":
        return NvidiaProvider.estimate_cost(model, prompt_tokens, completion_tokens)
    return 0.0


# ======================================================================
# LLMRouter
# ======================================================================

class LLMRouter:
    """Routes LLM calls to the appropriate provider/model with automatic fallback."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._init_providers()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_providers(self) -> None:
        settings = get_settings()
        if settings.MISTRAL_API_KEY and not settings.MISTRAL_API_KEY.startswith("your-"):
            self._providers["mistral"] = MistralProvider()
            logger.info("Mistral provider initialised")
        if settings.NVIDIA_API_KEY and not settings.NVIDIA_API_KEY.startswith("your-"):
            self._providers["nvidia"] = NvidiaProvider()
            logger.info("NVIDIA provider initialised")

        if not self._providers:
            logger.warning("No LLM providers configured – all calls will fail")

    # ------------------------------------------------------------------
    # Provider ordering
    # ------------------------------------------------------------------

    def _provider_chain(self, preferred: str | None = None) -> list[str]:
        """Return an ordered list of provider names (primary first, then fallbacks)."""
        settings = get_settings()
        primary = preferred or settings.DEFAULT_PROVIDER or "mistral"

        chain: list[str] = []
        if primary in self._providers:
            chain.append(primary)
        # Append remaining providers in deterministic order as fallbacks
        for name in sorted(self._providers.keys()):
            if name not in chain:
                chain.append(name)
        return chain

    # ------------------------------------------------------------------
    # chat()
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[LLMMessage],
        task: str = "strong",
        json_schema: dict | None = None,
        temperature: float = 0.2,
        provider: str | None = None,
    ) -> LLMResponse:
        """Route to the best available provider with automatic fallback.

        Parameters
        ----------
        messages:
            Conversation messages.
        task:
            ``"strong"`` or ``"cheap"`` – selects the model tier within the provider.
        json_schema:
            Optional JSON schema; when given the provider enables JSON mode.
        temperature:
            Sampling temperature.
        provider:
            Force a specific provider (e.g. ``"mistral"``).

        Returns
        -------
        LLMResponse
            The provider's response with token counts.

        Raises
        ------
        LLMError
            When all providers have been exhausted.
        """
        chain = self._provider_chain(preferred=provider)

        if not chain:
            raise LLMError("No LLM providers are configured")

        last_error: Exception | None = None

        for provider_name in chain:
            prov = self._providers[provider_name]
            model = prov.get_model(task)

            start = time.perf_counter()
            try:
                response = await prov.chat(
                    messages=messages,
                    model=model,
                    json_schema=json_schema,
                    temperature=temperature,
                )
                latency_ms = (time.perf_counter() - start) * 1000

                # Audit log (success)
                cost = _estimate_cost(
                    provider_name, model, response.prompt_tokens, response.completion_tokens
                )
                _log_llm_call(
                    provider=provider_name,
                    model=model,
                    task=task,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=response.total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    success=True,
                )

                return response

            except (LLMRateLimitError, LLMServerError, LLMTimeoutError) as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                logger.warning(
                    "Provider %s failed (will try fallback): %s", provider_name, exc
                )
                _log_llm_call(
                    provider=provider_name,
                    model=model,
                    task=task,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost=0.0,
                    latency_ms=latency_ms,
                    success=False,
                    error=str(exc),
                )
                last_error = exc
                continue

            except LLMError as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                logger.error("Provider %s returned non-retryable error: %s", provider_name, exc)
                _log_llm_call(
                    provider=provider_name,
                    model=model,
                    task=task,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost=0.0,
                    latency_ms=latency_ms,
                    success=False,
                    error=str(exc),
                )
                last_error = exc
                continue

        raise LLMError(f"All LLM providers exhausted. Last error: {last_error}")

    # ------------------------------------------------------------------
    # chat_json()
    # ------------------------------------------------------------------

    async def chat_json(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        task: str = "strong",
        temperature: float = 0.2,
        max_retries: int = 3,
    ) -> tuple[BaseModel, LLMResponse]:
        """Chat expecting a structured JSON response validated against a Pydantic model.

        Includes automatic JSON extraction, repair, and retry on validation failure.

        Parameters
        ----------
        messages:
            Conversation messages (should include a system message).
        response_model:
            The Pydantic model to validate the response against.
        task:
            Model tier – ``"strong"`` or ``"cheap"``.
        temperature:
            Sampling temperature.
        max_retries:
            Maximum number of retries when the JSON output fails validation.

        Returns
        -------
        tuple[BaseModel, LLMResponse]
            The parsed Pydantic model instance and the raw LLM response.

        Raises
        ------
        LLMValidationError
            When the response cannot be parsed/validated after all retries.
        """
        schema = response_model.model_json_schema()

        # Augment the first system message (or prepend one) with JSON instructions.
        working_messages = list(messages)
        json_instruction = (
            "You MUST respond with ONLY valid JSON (no markdown, no extra text) "
            f"matching this schema:\n{json.dumps(schema, indent=2)}"
        )

        if working_messages and working_messages[0].role == "system":
            working_messages[0] = LLMMessage(
                role="system",
                content=working_messages[0].content + "\n\n" + json_instruction,
            )
        else:
            working_messages.insert(
                0, LLMMessage(role="system", content=json_instruction)
            )

        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            response = await self.chat(
                messages=working_messages,
                task=task,
                json_schema=schema,
                temperature=temperature,
            )

            raw = response.content

            # --- Attempt to parse ----------------------------------
            try:
                parsed = self._parse_and_validate(raw, response_model)
                return parsed, response
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "JSON validation failed (attempt %d/%d): %s",
                    attempt,
                    max_retries,
                    exc,
                )

                if attempt < max_retries:
                    # Ask the LLM to fix its output
                    working_messages.append(
                        LLMMessage(role="assistant", content=raw)
                    )
                    working_messages.append(
                        LLMMessage(
                            role="user",
                            content=(
                                "Your previous response was not valid JSON or did not match "
                                f"the required schema. Error:\n{exc}\n\n"
                                "Please respond with ONLY the corrected JSON. "
                                "No markdown fences, no explanation."
                            ),
                        )
                    )

        raise LLMValidationError(
            f"Failed to get valid JSON after {max_retries} attempts. Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_and_validate(raw: str, model: type[BaseModel]) -> BaseModel:
        """Extract, repair, parse, and validate JSON against *model*."""
        # First: try raw text directly
        try:
            data = json.loads(raw)
            return model.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            pass

        # Second: attempt repair
        repaired = _repair_json(raw)
        try:
            data = json.loads(repaired)
            return model.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            pass

        # Third: one more extraction attempt (markdown blocks)
        extracted = _extract_json_block(raw)
        if extracted != raw:
            repaired_extracted = _repair_json(extracted)
            data = json.loads(repaired_extracted)  # let this raise on failure
            return model.model_validate(data)

        # Re-raise the last failure
        data = json.loads(repaired)  # will raise JSONDecodeError
        return model.model_validate(data)  # or ValidationError


# ======================================================================
# Module-level convenience singleton
# ======================================================================

_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Return the global LLMRouter singleton (lazy-initialised)."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def reset_router() -> None:
    """Discard the current router so the next ``get_router()`` call re-reads settings."""
    global _router
    _router = None
