import unittest

from tools.ast_tool import ASTTool
from tools.base import BaseTool, ToolRequest
from tools.code_search_tool import CodeSearchTool
from tools.defaults import create_default_registry
from tools.dependency_tool import DependencyTool
from tools.registry import ToolRegistry


def request(task_type, payload=None):
    return ToolRequest(
        task_id="task_1",
        task_type=task_type,
        query="question",
        payload=payload or {},
    )


class StubTool(BaseTool):
    name = "stub"
    task_types = ("stub_task",)

    def __init__(self, output=None, error=None):
        self.output = output or {}
        self.error = error

    def execute(self, tool_request):
        if self.error:
            raise self.error
        return self.output


class DuplicateMappingTool(StubTool):
    task_types = ("stub_task", "stub_task")


class ToolContractTests(unittest.TestCase):
    def test_base_tool_returns_uniform_success_and_failure_results(self):
        success = StubTool(output={"value": 1}).run(request("stub_task"))
        failure = StubTool(error=RuntimeError("unavailable")).run(
            request("stub_task")
        )

        self.assertTrue(success.success)
        self.assertEqual(success.output, {"value": 1})
        self.assertIsNone(success.error)
        self.assertFalse(failure.success)
        self.assertEqual(failure.error.error_type, "RuntimeError")
        self.assertEqual(failure.error.message, "unavailable")

    def test_registry_resolves_mappings_and_rejects_duplicates(self):
        registry = ToolRegistry()
        registry.register(StubTool())

        self.assertEqual(registry.mappings(), {"stub_task": "stub"})
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(StubTool())

    def test_unregistered_task_returns_structured_failure(self):
        result = ToolRegistry().execute(request("missing"))

        self.assertFalse(result.success)
        self.assertEqual(result.error.error_type, "ToolNotFoundError")
        self.assertIn("missing", result.error.message)

    def test_registry_rejects_duplicate_mappings_within_one_tool(self):
        with self.assertRaisesRegex(ValueError, "same task type"):
            ToolRegistry().register(DuplicateMappingTool())

    def test_default_registry_maps_all_phase_four_tools(self):
        mappings = create_default_registry(lambda *args, **kwargs: []).mappings()

        self.assertEqual(mappings["code_search"], "code_search")
        self.assertEqual(mappings["code_analysis"], "ast")
        self.assertEqual(mappings["dependency_analysis"], "dependency")


class CodeSearchToolTests(unittest.TestCase):
    def test_search_passes_uniform_input_to_retriever(self):
        captured = {}

        def fake_retrieve(query, index, docs, *, k):
            captured["args"] = (query, index, docs, k)
            return [{"code": "return 1"}]

        docs = [{"code": "return 1"}]
        result = CodeSearchTool(fake_retrieve).run(request(
            "code_search",
            {"index": "index", "docs": docs, "k": 2},
        ))

        self.assertTrue(result.success)
        self.assertEqual(captured["args"], ("question", "index", docs, 2))
        self.assertEqual(result.output["context_count"], 1)

    def test_invalid_docs_returns_structured_failure(self):
        result = CodeSearchTool().run(request("code_search", {"docs": None}))

        self.assertFalse(result.success)
        self.assertEqual(result.error.error_type, "ValueError")


class ASTToolTests(unittest.TestCase):
    def test_extracts_functions_classes_and_calls(self):
        source = (
            "class Child(Base):\n"
            "    def run(self):\n"
            "        return helper(self.value)\n"
        )
        result = ASTTool().run(request(
            "code_analysis",
            {"contexts": [{"file_path": "sample.py", "code": source}]},
        ))

        analysis = result.output["analyses"][0]
        self.assertTrue(result.success)
        self.assertEqual(analysis["functions"][0]["name"], "run")
        self.assertEqual(analysis["classes"], [{"name": "Child", "bases": ["Base"]}])
        self.assertEqual(analysis["calls"], ["helper"])

    def test_empty_contexts_succeeds_without_results(self):
        result = ASTTool().run(request("code_analysis", {"contexts": []}))

        self.assertTrue(result.success)
        self.assertEqual(result.output, {"analyses": [], "analysis_count": 0})

    def test_invalid_python_returns_syntax_error_details(self):
        result = ASTTool().run(request(
            "code_analysis",
            {"contexts": [{"code": "def broken("}]},
        ))

        self.assertFalse(result.success)
        self.assertEqual(result.error.error_type, "SyntaxError")


class DependencyToolTests(unittest.TestCase):
    def test_extracts_imports_and_function_call_dependencies(self):
        source = (
            "import os\n"
            "from pkg import helper\n\n"
            "def run():\n"
            "    helper()\n"
            "    os.path.exists('x')\n"
        )
        result = DependencyTool().run(request(
            "dependency_analysis",
            {"source": source},
        ))

        self.assertTrue(result.success)
        self.assertEqual(result.output["imports"], ["os", "pkg.helper"])
        self.assertEqual(
            result.output["function_dependencies"]["run"],
            ["helper", "os.path.exists"],
        )

    def test_empty_source_has_no_dependencies(self):
        result = DependencyTool().run(request(
            "dependency_analysis",
            {"source": ""},
        ))

        self.assertTrue(result.success)
        self.assertEqual(result.output, {"imports": [], "function_dependencies": {}})

    def test_contexts_are_analyzed_for_workflow_execution(self):
        result = DependencyTool().run(request(
            "dependency_analysis",
            {"contexts": [{"file_path": "sample.py", "code": "def run():\n    load()\n"}]},
        ))

        self.assertTrue(result.success)
        self.assertEqual(result.output["dependency_count"], 1)
        self.assertEqual(
            result.output["dependencies"][0]["function_dependencies"],
            {"run": ["load"]},
        )

    def test_missing_source_returns_structured_failure(self):
        result = DependencyTool().run(request("dependency_analysis"))

        self.assertFalse(result.success)
        self.assertEqual(result.error.error_type, "ValueError")


if __name__ == "__main__":
    unittest.main()
