"""Backward-compatible imports for the former configuration module."""

from core.config import (
    EMBEDDING_MODEL,
    LLM_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    REPO_PATH,
    get_openai_client,
)

__all__ = [
    "EMBEDDING_MODEL",
    "LLM_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "REPO_PATH",
    "get_openai_client",
]
