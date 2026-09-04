from collections.abc import Callable
from typing import Any

from core.config import LLM_MODEL, get_openai_client


def ask_llm(
    prompt: str,
    *,
    client_factory: Callable[[], Any] = get_openai_client,
    model: str = LLM_MODEL,
) -> str:
    """Generate a deterministic answer for a prepared prompt."""
    client = client_factory()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content
