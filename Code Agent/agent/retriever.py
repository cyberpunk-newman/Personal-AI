import numpy as np

from agent.rag import embed


def retrieve(query: str, index, docs, k: int = 3):
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
