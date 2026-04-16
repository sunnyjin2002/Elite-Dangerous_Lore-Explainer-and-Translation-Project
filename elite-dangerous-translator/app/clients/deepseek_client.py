"""DeepSeek client placeholder."""

from app.clients.llm_base import LLMClient


class DeepSeekClient:
    """DeepSeek client shell for a future phase."""

    provider_name = "deepseek"


def get_client() -> LLMClient:
    """Return the DeepSeek client placeholder."""
    return DeepSeekClient()
