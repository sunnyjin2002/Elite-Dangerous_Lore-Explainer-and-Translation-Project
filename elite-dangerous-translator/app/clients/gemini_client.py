"""Gemini client placeholder."""

from app.clients.llm_base import LLMClient


class GeminiClient:
    """Gemini client shell for a future phase."""

    provider_name = "gemini"


def get_client() -> LLMClient:
    """Return the Gemini client placeholder."""
    return GeminiClient()
