import ast
from typing import Any


def get_expression_name(node: ast.AST) -> str:
    """Return a dotted name for a name or attribute AST expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = get_expression_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def extract_functions(code: str) -> list[dict[str, Any]]:
    """Extract regular and async functions from Python source code."""
    tree = ast.parse(code)
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            source = ast.get_source_segment(code, node)
            if source:
                functions.append({
                    "name": node.name,
                    "code": source,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                })

    return functions
