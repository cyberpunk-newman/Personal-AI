from typing import Any


def build_prompt(query: str, contexts: list[dict[str, Any]]) -> str:
    """Build the same code-analysis prompt used by the baseline application."""
    return f"""
你是一个代码分析助手，请基于以下代码回答问题：

{contexts}

问题：{query}
请解释清楚函数作用和逻辑。
"""
