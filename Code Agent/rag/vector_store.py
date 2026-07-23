from typing import Any

import faiss
import numpy as np


def create_vector_store(vectors: list[np.ndarray]) -> faiss.IndexFlatL2:
    """Create an in-memory FAISS L2 index from embedding vectors."""
    if not vectors:
        raise ValueError("Cannot create a vector store without vectors.")

    matrix = np.vstack(vectors).astype("float32")
    index = faiss.IndexFlatL2(matrix.shape[1])
    index.add(matrix)
    return index


def search_vector_store(
    index: Any,
    query_vector: np.ndarray,
    limit: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Search a vector store and return distances and document positions."""
    return index.search(
        np.asarray([query_vector], dtype="float32"),
        limit,
    )
