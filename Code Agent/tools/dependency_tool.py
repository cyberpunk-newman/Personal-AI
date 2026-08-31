import ast
import textwrap
from typing import Any

from parser.ast_parser import get_expression_name
from tools.base import BaseTool, ToolRequest


class DependencyTool(BaseTool):
    """Analyze imports and function-level call dependencies."""

    name = "dependency"
    task_types = ("dependency_analysis",)

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        source = request.payload.get("source")
        if isinstance(source, str):
            return self._analyze_source(source)

        contexts = request.payload.get("contexts")
        if not isinstance(contexts, list):
            raise ValueError(
                "Dependency analysis requires Python source text or a contexts list."
            )

        dependencies = []
        for position, context in enumerate(contexts):
            if not isinstance(context, dict) or not isinstance(
                context.get("code", ""), str
            ):
                raise ValueError("Dependency contexts must contain code strings.")
            dependencies.append({
                "context_index": position,
                "file_path": context.get("file_path"),
                **self._analyze_source(context.get("code", "")),
            })
        return {
            "dependencies": dependencies,
            "dependency_count": len(dependencies),
        }

    @staticmethod
    def _analyze_source(source: str) -> dict[str, Any]:
        tree = ast.parse(textwrap.dedent(source))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend(
                    f"{module}.{alias.name}" if module else alias.name
                    for alias in node.names
                )

        function_dependencies = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_dependencies[node.name] = sorted({
                    name
                    for child in ast.walk(node)
                    if isinstance(child, ast.Call)
                    if (name := get_expression_name(child.func))
                })

        return {
            "imports": sorted(set(imports)),
            "function_dependencies": function_dependencies,
        }
