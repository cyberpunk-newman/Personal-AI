import numpy as np
from typing import Any

from agent.rag import embed


def retrieve(query: str, index, docs: list[dict[str, Any]] | list[str], k: int = 3) -> list[dict[str, Any]]:
    """从 FAISS 索引中检索与问题最相关的函数片段。

    Args:
        query: 用户问题或评测问题。
        index: 与 docs 顺序对齐的 FAISS 索引。
        docs: build_index 返回的函数 metadata 列表。兼容旧版纯文本 docs。
        k: 返回的最大候选数量。

    Returns:
        检索结果列表。每个结果包含 rank、score、function_name、file_path、
        start_line、end_line、code 和 text。score 是 FAISS L2 distance，数值越小
        表示向量距离越近。
    """
    if not docs:
        return []

    limit = min(k, len(docs))
    q_vec = embed(query)
    distances, indices = index.search(np.asarray([q_vec], dtype="float32"), limit)

    results = []
    for rank, (idx, score) in enumerate(zip(indices[0], distances[0]), start=1):
        if 0 <= idx < len(docs):
            doc = docs[idx]
            if isinstance(doc, dict):
                result = dict(doc)
            else:
                result = {
                    "function_name": None,
                    "file_path": None,
                    "start_line": None,
                    "end_line": None,
                    "code": doc,
                    "text": doc,
                }
            result["rank"] = rank
            result["score"] = float(score)
            results.append(result)

    return results
