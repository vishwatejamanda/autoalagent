"""Base LLM provider interface and shared data models."""

from abc import ABC, abstractmethod
from pydantic import BaseModel


class LLMMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str  # system, user, assistant
    content: str


class LLMResponse(BaseModel):
    """Structured response from an LLM provider."""

    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Base exception for all LLM-related errors."""


class LLMRateLimitError(LLMError):
    """Raised when the provider returns HTTP 429 (rate limited)."""


class LLMServerError(LLMError):
    """Raised when the provider returns a 5xx server error."""


class LLMTimeoutError(LLMError):
    """Raised when the request to the provider times out."""


class LLMValidationError(LLMError):
    """Raised when the LLM response fails JSON/Pydantic validation."""


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Base class for all LLM providers."""

    provider_name: str = ""

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        json_schema: dict | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    def get_model(self, task: str = "strong") -> str:
        """Return the appropriate model name for a task type (strong/cheap)."""
        ...
