import unittest
from types import SimpleNamespace

import numpy as np

from core.llm import ask_llm
from rag.embedding import embed


class EmbeddingTests(unittest.TestCase):
    def test_embedding_uses_configurable_client_and_returns_float32(self):
        calls = {}

        class Embeddings:
            def create(self, **kwargs):
                calls.update(kwargs)
                return SimpleNamespace(
                    data=[SimpleNamespace(embedding=[1, 2, 3])]
                )

        client = SimpleNamespace(embeddings=Embeddings())

        vector = embed(
            "code",
            client_factory=lambda: client,
            model="embedding-model",
        )

        np.testing.assert_array_equal(vector, np.asarray([1, 2, 3], dtype="float32"))
        self.assertEqual(vector.dtype, np.float32)
        self.assertEqual(calls, {"model": "embedding-model", "input": "code"})


class LlmTests(unittest.TestCase):
    def test_llm_uses_deterministic_chat_completion(self):
        calls = {}

        class Completions:
            def create(self, **kwargs):
                calls.update(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))]
                )

        client = SimpleNamespace(
            chat=SimpleNamespace(completions=Completions())
        )

        answer = ask_llm(
            "prompt",
            client_factory=lambda: client,
            model="llm-model",
        )

        self.assertEqual(answer, "answer")
        self.assertEqual(calls["model"], "llm-model")
        self.assertEqual(calls["messages"], [{"role": "user", "content": "prompt"}])
        self.assertEqual(calls["temperature"], 0)


if __name__ == "__main__":
    unittest.main()
