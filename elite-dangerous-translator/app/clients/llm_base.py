"""Base abstractions for LLM clients."""

from typing import Protocol


class LLMClient(Protocol):
    """Protocol for future LLM provider clients."""

    provider_name: str
