import numpy as np

from agent.rag import embed


def retrieve(query: str, index, docs, k: int = 3):
    if not docs:
        return []

    limit = min(k, len(docs))
    q_vec = embed(query)
    _, indices = index.search(np.asarray([q_vec], dtype="float32"), limit)

    results = []
    for idx in indices[0]:
        if 0 <= idx < len(docs):
            results.append(docs[idx])

    return results
