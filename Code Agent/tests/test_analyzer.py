import tempfile
import unittest
from pathlib import Path

import numpy as np

from workflow.analyzer import analyze_question, build_index, build_prompt
from rag.retriever import retrieve


class BuildIndexTests(unittest.TestCase):
    def test_builds_function_documents_with_mock_embeddings(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "sample.py"
            source_path.write_text("def greet(name):\n    return f'Hi {name}'\n", encoding="utf-8")

            index, docs = build_index(
                directory,
                embed_fn=lambda _: np.asarray([1.0, 0.0], dtype="float32"),
            )

        self.assertEqual(index.ntotal, 1)
        self.assertEqual(docs[0]["function_name"], "greet")
        self.assertEqual(Path(docs[0]["file_path"]).name, "sample.py")

    def test_missing_repository_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            build_index("/path/that/does/not/exist")

    def test_repository_without_python_files_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "README.md").write_text("empty", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "No Python files"):
                build_index(directory)

    def test_repository_without_functions_is_rejected_without_embedding_call(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "constants.py").write_text("VALUE = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "No Python functions"):
                build_index(directory, embed_fn=lambda _: self.fail("unexpected embedding"))


class AnalyzeQuestionTests(unittest.TestCase):
    def test_mocked_embedding_to_retrieval_to_answer_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "service.py").write_text(
                "def add_todo():\n    return 'created'\n",
                encoding="utf-8",
            )
            vector = np.asarray([1.0, 0.0], dtype="float32")
            index, docs = build_index(directory, embed_fn=lambda _: vector)

            answer = analyze_question(
                "Where is todo created?",
                index,
                docs,
                retrieve_fn=lambda query, store, metadata: retrieve(
                    query,
                    store,
                    metadata,
                    embed_fn=lambda _: vector,
                ),
                llm_fn=lambda prompt: "found" if "add_todo" in prompt else "missing",
            )

        self.assertEqual(answer, "found")

    def test_retrieval_context_is_sent_to_llm(self):
        captured = {}

        def fake_retrieve(query, index, docs):
            self.assertEqual(query, "What does it do?")
            return [{"code": "return 1"}]

        def fake_llm(prompt):
            captured["prompt"] = prompt
            return "answer"

        answer = analyze_question(
            "What does it do?",
            object(),
            [],
            retrieve_fn=fake_retrieve,
            llm_fn=fake_llm,
        )

        self.assertEqual(answer, "answer")
        self.assertIn("return 1", captured["prompt"])
        self.assertIn("What does it do?", captured["prompt"])

    def test_prompt_preserves_baseline_instructions(self):
        prompt = build_prompt("question", [])
        self.assertIn("你是一个代码分析助手", prompt)
        self.assertIn("请解释清楚函数作用和逻辑", prompt)


if __name__ == "__main__":
    unittest.main()
