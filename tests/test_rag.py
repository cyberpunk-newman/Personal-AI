import unittest

import numpy as np

from rag.retriever import retrieve
from rag.vector_store import create_vector_store


class VectorStoreTests(unittest.TestCase):
    def test_empty_vectors_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "without vectors"):
            create_vector_store([])

    def test_retriever_returns_ranked_metadata(self):
        index = create_vector_store([
            np.asarray([0.0, 0.0], dtype="float32"),
            np.asarray([2.0, 2.0], dtype="float32"),
        ])
        docs = [
            {"function_name": "near", "text": "near"},
            {"function_name": "far", "text": "far"},
        ]

        results = retrieve(
            "question",
            index,
            docs,
            k=5,
            embed_fn=lambda _: np.asarray([0.1, 0.1], dtype="float32"),
        )

        self.assertEqual([item["function_name"] for item in results], ["near", "far"])
        self.assertEqual([item["rank"] for item in results], [1, 2])
        self.assertIsInstance(results[0]["score"], float)

    def test_empty_docs_or_non_positive_k_returns_no_results(self):
        self.assertEqual(retrieve("question", None, []), [])
        self.assertEqual(retrieve("question", None, ["code"], k=0), [])


if __name__ == "__main__":
    unittest.main()
