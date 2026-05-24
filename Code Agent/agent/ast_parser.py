import ast


def extract_functions(code: str):
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
