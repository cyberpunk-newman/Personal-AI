import numpy as np
from agent.rag import embed, docs

def retrieve(query, index, k=3):
    q_vec = embed(query)
    D, I = index.search(np.array([q_vec]), k)

    results = []
    for idx in I[0]:
        results.append(docs[idx])

    return results