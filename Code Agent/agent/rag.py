"""Backward-compatible RAG imports."""

from rag.embedding import embed
from workflow.analyzer import build_index

__all__ = ["build_index", "embed"]
