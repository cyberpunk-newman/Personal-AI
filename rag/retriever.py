from collections.abc import Callable
from typing import Any

import numpy as np

from rag.embedding import embed
from rag.vector_store import search_vector_store


def retrieve(
    query: str,
    index: Any,
    docs: list[dict[str, Any]] | list[str],
    k: int = 3,
    *,
    embed_fn: Callable[[str], np.ndarray] = embed,
) -> list[dict[str, Any]]:
    """Retrieve the closest indexed code fragments for a query."""
    if not docs or k <= 0:
        return []

    limit = min(k, len(docs))
    distances, indices = search_vector_store(index, embed_fn(query), limit)

    results = []
    for rank, (idx, score) in enumerate(zip(indices[0], distances[0]), start=1):
        if not 0 <= idx < len(docs):
            continue
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
