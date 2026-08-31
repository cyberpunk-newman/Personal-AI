import unittest

from tools.base import BaseTool
from tools.registry import ToolRegistry
from workflow.orchestrator import Orchestrator, StepStatus, run_workflow


class RecordingTool(BaseTool):
    def __init__(self, name, task_type, calls, output=None, error=None):
        self.name = name
        self.task_types = (task_type,)
        self.calls = calls
        self.output = output or {}
        self.error = error

    def execute(self, request):
        self.calls.append((self.name, request.task_type))
        if self.error:
            raise self.error
        return self.output


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
            ["plan", "retrieve", "analyze", "dependency", "llm"],
        )
        self.assertTrue(
            all(step.status is StepStatus.SUCCEEDED for step in result.context.steps)
        )
        self.assertEqual(result.context.steps[1].output["context_count"], 1)
        self.assertEqual(
            [step.input["task"]["id"] for step in result.context.steps[1:]],
            ["task_1", "task_2", "task_3", "task_4"],
        )

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
        self.assertEqual(result.context.steps[1].output["context_count"], 0)

    def test_invalid_planner_output_is_rejected_before_execution(self):
        def unexpected(*args, **kwargs):
            self.fail("execution dependency must not run for an invalid plan")

        result = run_workflow(
            "question",
            object(),
            [],
            planner_fn=lambda query: {"goal": query, "tasks": []},
            retrieve_fn=unexpected,
            analyzer_fn=unexpected,
            llm_fn=unexpected,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "plan")
        self.assertEqual(result.error.error_type, "ValueError")
        self.assertEqual([step.name for step in result.context.steps], ["plan"])

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
        self.assertEqual(len(result.context.steps), 2)
        self.assertEqual(result.context.steps[0].status, StepStatus.SUCCEEDED)
        self.assertEqual(result.context.steps[1].status, StepStatus.FAILED)

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
            [StepStatus.SUCCEEDED, StepStatus.SUCCEEDED, StepStatus.FAILED],
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
            [
                StepStatus.SUCCEEDED,
                StepStatus.SUCCEEDED,
                StepStatus.SUCCEEDED,
                StepStatus.SUCCEEDED,
                StepStatus.FAILED,
            ],
        )

    def test_selects_registered_tools_from_planner_task_types(self):
        calls = []
        registry = ToolRegistry()
        registry.register(RecordingTool(
            "search_stub",
            "code_search",
            calls,
            {"contexts": [], "context_count": 0},
        ))
        registry.register(RecordingTool(
            "ast_stub",
            "code_analysis",
            calls,
            {"analyses": [], "analysis_count": 0},
        ))
        registry.register(RecordingTool(
            "dependency_stub",
            "dependency_analysis",
            calls,
            {"dependencies": [], "dependency_count": 0},
        ))

        result = run_workflow(
            "question",
            object(),
            [],
            analyzer_fn=lambda query, contexts: "prompt",
            llm_fn=lambda prompt: "answer",
            tool_registry=registry,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            calls,
            [
                ("search_stub", "code_search"),
                ("ast_stub", "code_analysis"),
                ("dependency_stub", "dependency_analysis"),
            ],
        )
        self.assertEqual(
            [item.tool for item in result.context.tool_results],
            ["search_stub", "ast_stub", "dependency_stub"],
        )

    def test_tool_failure_is_preserved_in_workflow_trace(self):
        registry = ToolRegistry()
        registry.register(RecordingTool(
            "search_stub",
            "code_search",
            [],
            error=RuntimeError("search offline"),
        ))

        result = run_workflow(
            "question",
            object(),
            [],
            tool_registry=registry,
            analyzer_fn=lambda *args: self.fail("analysis must not run"),
            llm_fn=lambda *args: self.fail("LLM must not run"),
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error.tool, "search_stub")
        self.assertEqual(result.error.message, "search offline")
        self.assertEqual(
            result.context.steps[-1].output["tool_result"]["error"],
            {"error_type": "RuntimeError", "message": "search offline"},
        )


if __name__ == "__main__":
    unittest.main()
