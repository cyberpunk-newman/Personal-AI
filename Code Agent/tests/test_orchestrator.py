import unittest

from workflow.orchestrator import Orchestrator, StepStatus, run_workflow


class OrchestratorTests(unittest.TestCase):
    def test_runs_retrieval_analysis_and_llm_in_order(self):
        calls = []
        docs = [{"function_name": "target", "code": "return 1"}]

        def fake_retrieve(query, index, metadata, *, k):
            calls.append("retrieve")
            self.assertEqual((query, index, metadata, k), ("question", "index", docs, 2))
            return docs

        def fake_analyze(query, contexts):
            calls.append("analyze")
            self.assertEqual((query, contexts), ("question", docs))
            return "prepared prompt"

        def fake_llm(prompt):
            calls.append("llm")
            self.assertEqual(prompt, "prepared prompt")
            return "answer"

        result = run_workflow(
            "  question  ",
            "index",
            docs,
            k=2,
            retrieve_fn=fake_retrieve,
            analyzer_fn=fake_analyze,
            llm_fn=fake_llm,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.answer, "answer")
        self.assertEqual(result.contexts, docs)
        self.assertEqual(calls, ["retrieve", "analyze", "llm"])
        self.assertEqual(
            [step.name for step in result.context.steps],
            ["retrieve", "analyze", "llm"],
        )
        self.assertTrue(
            all(step.status is StepStatus.SUCCEEDED for step in result.context.steps)
        )
        self.assertEqual(result.context.steps[0].output["context_count"], 1)

    def test_empty_question_is_rejected_before_dependencies_run(self):
        def unexpected(*args, **kwargs):
            self.fail("workflow dependency must not run for an empty question")

        result = run_workflow(
            "   ",
            object(),
            [],
            retrieve_fn=unexpected,
            analyzer_fn=unexpected,
            llm_fn=unexpected,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "validate_input")
        self.assertEqual(result.error.error_type, "ValueError")
        self.assertEqual(result.context.steps[0].status, StepStatus.FAILED)

    def test_no_retrieval_results_still_produces_an_answer(self):
        captured = {}

        def fake_analyze(query, contexts):
            captured["contexts"] = contexts
            return "prompt without contexts"

        result = run_workflow(
            "question",
            object(),
            [],
            retrieve_fn=lambda *args, **kwargs: [],
            analyzer_fn=fake_analyze,
            llm_fn=lambda prompt: "no matching code",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.answer, "no matching code")
        self.assertEqual(captured["contexts"], [])
        self.assertEqual(result.context.steps[0].output["context_count"], 0)

    def test_retrieval_failure_is_returned_with_step_details(self):
        def fail_retrieval(*args, **kwargs):
            raise RuntimeError("index unavailable")

        result = Orchestrator(
            retrieve_fn=fail_retrieval,
            analyzer_fn=lambda *args: self.fail("analysis must not run"),
            llm_fn=lambda *args: self.fail("LLM must not run"),
        ).run("question", object(), [])

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "retrieve")
        self.assertEqual(result.error.error_type, "RuntimeError")
        self.assertEqual(result.error.message, "index unavailable")
        self.assertEqual(len(result.context.steps), 1)
        self.assertEqual(result.context.steps[0].status, StepStatus.FAILED)

    def test_analyzer_failure_preserves_retrieval_trace(self):
        def fail_analysis(query, contexts):
            raise ValueError("prompt could not be built")

        result = run_workflow(
            "question",
            object(),
            [],
            retrieve_fn=lambda *args, **kwargs: [],
            analyzer_fn=fail_analysis,
            llm_fn=lambda *args: self.fail("LLM must not run"),
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "analyze")
        self.assertEqual(result.error.error_type, "ValueError")
        self.assertEqual(
            [step.status for step in result.context.steps],
            [StepStatus.SUCCEEDED, StepStatus.FAILED],
        )

    def test_llm_failure_preserves_completed_step_trace(self):
        def fail_llm(prompt):
            raise TimeoutError("model timed out")

        result = run_workflow(
            "question",
            object(),
            [],
            retrieve_fn=lambda *args, **kwargs: [],
            analyzer_fn=lambda query, contexts: "prompt",
            llm_fn=fail_llm,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "llm")
        self.assertEqual(
            [step.status for step in result.context.steps],
            [StepStatus.SUCCEEDED, StepStatus.SUCCEEDED, StepStatus.FAILED],
        )


if __name__ == "__main__":
    unittest.main()
