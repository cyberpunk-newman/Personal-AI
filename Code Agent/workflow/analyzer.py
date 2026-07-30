import os
from collections.abc import Callable
from typing import Any

import numpy as np

from core.llm import ask_llm
from parser.ast_parser import extract_functions
from rag.embedding import embed
from rag.retriever import retrieve
from rag.vector_store import create_vector_store


def build_index(
    repo_path: str,
    *,
    embed_fn: Callable[[str], np.ndarray] = embed,
) -> tuple[Any, list[dict[str, Any]]]:
    """Parse Python functions and build their vector index."""
    if not os.path.isdir(repo_path):
        raise FileNotFoundError(
            f"Repository path does not exist: {repo_path}. "
            "Put Python files under data/repo or set REPO_PATH in .env."
        )

    docs = []
    vectors = []
    python_file_count = 0
    skipped_files = []

    for root, _, files in os.walk(repo_path):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            python_file_count += 1
            path = os.path.join(root, filename)
            try:
                with open(path, "r", encoding="utf-8") as source_file:
                    functions = extract_functions(source_file.read())
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                skipped_files.append(f"{path}: {exc}")
                continue

            for function in functions:
                text = f"{function['name']}\n{function['code']}"
                docs.append({
                    "function_name": function["name"],
                    "file_path": path,
                    "start_line": function["start_line"],
                    "end_line": function["end_line"],
                    "code": function["code"],
                    "text": text,
                })
                vectors.append(embed_fn(text))

    if python_file_count == 0:
        raise ValueError(f"No Python files found under repository path: {repo_path}")
    if not vectors:
        detail = ""
        if skipped_files:
            detail = " Skipped files: " + "; ".join(skipped_files)
        raise ValueError(
            f"No Python functions found under repository path: {repo_path}.{detail}"
        )

    return create_vector_store(vectors), docs


def build_prompt(query: str, contexts: list[dict[str, Any]]) -> str:
    """Build the same code-analysis prompt used by the baseline application."""
    return f"""
你是一个代码分析助手，请基于以下代码回答问题：

{contexts}

问题：{query}
请解释清楚函数作用和逻辑。
"""


def analyze_question(
    query: str,
    index: Any,
    docs: list[dict[str, Any]],
    *,
    retrieve_fn: Callable[..., list[dict[str, Any]]] = retrieve,
    llm_fn: Callable[[str], str] = ask_llm,
) -> str:
    """Retrieve relevant code and ask the LLM to answer the question."""
    contexts = retrieve_fn(query, index, docs)
    return llm_fn(build_prompt(query, contexts))
