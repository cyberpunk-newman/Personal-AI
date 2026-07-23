from collections.abc import Callable
from typing import Any

import numpy as np

from core.config import EMBEDDING_MODEL, get_openai_client


def embed(
    text: str,
    *,
    client_factory: Callable[[], Any] = get_openai_client,
    model: str = EMBEDDING_MODEL,
) -> np.ndarray:
    """Convert text to a one-dimensional float32 embedding."""
    client = client_factory()
    response = client.embeddings.create(model=model, input=text)
    return np.asarray(response.data[0].embedding, dtype="float32")
