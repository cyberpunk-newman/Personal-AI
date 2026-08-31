from collections.abc import Callable
from typing import Any

from rag.retriever import retrieve
from tools.ast_tool import ASTTool
from tools.code_search_tool import CodeSearchTool
from tools.dependency_tool import DependencyTool
from tools.registry import ToolRegistry


def create_default_registry(
    retrieve_fn: Callable[..., list[dict[str, Any]]] = retrieve,
) -> ToolRegistry:
    """Build the standard Phase 4 tool set in one composition root."""
    registry = ToolRegistry()
    registry.register(CodeSearchTool(retrieve_fn=retrieve_fn))
    registry.register(ASTTool())
    registry.register(DependencyTool())
    return registry
