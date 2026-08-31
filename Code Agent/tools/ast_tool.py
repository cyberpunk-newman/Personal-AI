import ast
import textwrap
from typing import Any

from parser.ast_parser import extract_functions, get_expression_name
from tools.base import BaseTool, ToolRequest


class ASTTool(BaseTool):
    """Extract functions, class relationships, and calls from Python source."""

    name = "ast"
    task_types = ("code_analysis",)

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        contexts = request.payload.get("contexts", [])
        if not isinstance(contexts, list):
            raise ValueError("AST analysis requires a contexts list.")

        analyses = []
        for position, context in enumerate(contexts):
            if not isinstance(context, dict):
                raise ValueError("AST contexts must contain dictionaries.")
            source = context.get("code", "")
            if not isinstance(source, str):
                raise ValueError("AST context code must be a string.")
            source = textwrap.dedent(source)
            tree = ast.parse(source)
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "bases": [
                            name
                            for base in node.bases
                            if (name := get_expression_name(base))
                        ],
                    })
            calls = sorted({
                name
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                if (name := get_expression_name(node.func))
            })
            analyses.append({
                "context_index": position,
                "file_path": context.get("file_path"),
                "functions": extract_functions(source),
                "classes": classes,
                "calls": calls,
            })
        return {"analyses": analyses, "analysis_count": len(analyses)}
