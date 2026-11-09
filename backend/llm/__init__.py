"""LLM provider layer — routing, fallback, and structured-output helpers.

Quick start::

    from backend.llm import get_router, LLMMessage

    router = get_router()
    response = await router.chat([LLMMessage(role="user", content="Hello!")])
"""

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
from llm.router import LLMRouter, get_router, reset_router

__all__ = [
    # Data models
    "LLMMessage",
    "LLMResponse",
    # Base class
    "LLMProvider",
    # Router
    "LLMRouter",
    "get_router",
    "reset_router",
    # Exceptions
    "LLMError",
    "LLMRateLimitError",
    "LLMServerError",
    "LLMTimeoutError",
    "LLMValidationError",
]
