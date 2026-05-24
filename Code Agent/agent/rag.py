import os
from typing import Any

import faiss
import numpy as np

from agent.ast_parser import extract_functions
from config import EMBEDDING_MODEL, get_openai_client


def embed(text: str) -> np.ndarray:
    """调用配置中的 embedding 模型，并返回 FAISS 可用的 float32 向量。

    Args:
        text: 需要向量化的文本。

    Returns:
        dtype 为 float32 的一维向量。
    """
    client = get_openai_client()
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return np.asarray(resp.data[0].embedding, dtype="float32")


def build_index(repo_path: str) -> tuple[faiss.IndexFlatL2, list[dict[str, Any]]]:
    """为指定代码仓库构建函数级向量索引。

    该函数会遍历仓库中的 Python 文件，提取函数源码，调用 embedding 模型生成向量，
    并构建 FAISS L2 索引。返回的 docs 与 FAISS 向量顺序一一对应，是检索结果
    metadata 的唯一来源。

    Args:
        repo_path: 待索引代码仓库路径。

    Returns:
        二元组 `(index, docs)`：
        - index: 已写入函数向量的 FAISS 索引。
        - docs: 函数 metadata 列表，包含 function_name、file_path、start_line、
          end_line、code 和 text。

    Raises:
        FileNotFoundError: repo_path 不存在时抛出。
        ValueError: 仓库下没有 Python 文件，或没有可索引函数时抛出。
    """
    if not os.path.isdir(repo_path):
        raise FileNotFoundError(
            f"Repository path does not exist: {repo_path}. "
            "Put Python files under data/repo or set REPO_PATH in .env."
        )

    docs = []
    vectors = []
    py_files = 0
    skipped_files = []

    for root, _, files in os.walk(repo_path):
        for filename in files:
            if not filename.endswith(".py"):
                continue

            py_files += 1
            path = os.path.join(root, filename)

            try:
                with open(path, "r", encoding="utf-8") as file:
                    code = file.read()
                funcs = extract_functions(code)
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                skipped_files.append(f"{path}: {exc}")
                continue

            for fn in funcs:
                text = f"{fn['name']}\n{fn['code']}"
                docs.append({
                    "function_name": fn["name"],
                    "file_path": path,
                    "start_line": fn["start_line"],
                    "end_line": fn["end_line"],
                    "code": fn["code"],
                    "text": text,
                })
                vectors.append(embed(text))

    if py_files == 0:
        raise ValueError(f"No Python files found under repository path: {repo_path}")

    if not vectors:
        detail = ""
        if skipped_files:
            detail = " Skipped files: " + "; ".join(skipped_files)
        raise ValueError(f"No Python functions found under repository path: {repo_path}.{detail}")

    matrix = np.vstack(vectors).astype("float32")
    index = faiss.IndexFlatL2(matrix.shape[1])
    index.add(matrix)

    return index, docs
