import ast
from typing import Any


def extract_functions(code: str) -> list[dict[str, Any]]:
    """提取 Python 源码中的函数定义。

    当前只提取普通函数与异步函数，不提取类本身、导入语句或模块级变量。

    Args:
        code: Python 源码文本。

    Returns:
        函数元数据列表。每个元素包含函数名、源码片段、起始行号和结束行号。
    """
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
