from collections.abc import Callable
from typing import Any

from rag.retriever import retrieve
from tools.base import BaseTool, ToolRequest


class CodeSearchTool(BaseTool):
    """Search indexed code for fragments relevant to a question."""

    name = "code_search"
    task_types = ("code_search",)

    def __init__(
        self,
        retrieve_fn: Callable[..., list[dict[str, Any]]] = retrieve,
    ) -> None:
        self._retrieve = retrieve_fn

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        docs = request.payload.get("docs")
        if not isinstance(docs, list):
            raise ValueError("Code search requires a docs list.")
        k = request.payload.get("k", 3)
        if not isinstance(k, int):
            raise ValueError("Code search k must be an integer.")

        contexts = self._retrieve(
            request.query,
            request.payload.get("index"),
            docs,
            k=k,
        )
        if not isinstance(contexts, list):
            raise TypeError("Code search results must be a list.")
        return {"contexts": contexts, "context_count": len(contexts)}
