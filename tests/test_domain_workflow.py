import json
import unittest

from domains import (
    DomainDefinition,
    DomainRegistry,
    InMemoryKnowledgeSource,
    KnowledgeItem,
    KnowledgeSource,
    Problem,
    ToolSet,
)
from domains.prompting import build_analysis_prompt, parse_analysis_response
from domains.scenarios import (
    SCENARIO_EXPECTED_RESULTS,
    SCENARIO_PROBLEMS,
    create_scenario_registry,
    scenario_response,
)
from tools import BaseTool, ToolRegistry
from workflow.domain_orchestrator import DomainOrchestrator, DomainStepStatus


class StubTool(BaseTool):
    name = "stub"
    task_types = ("stub_analysis",)

    def __init__(self, error=None):
        self.error = error

    def execute(self, request):
        if self.error:
            raise self.error
        return {"observed": request.query}


class FailingKnowledgeSource(KnowledgeSource):
    def search(self, problem, *, limit):
        raise OSError("knowledge source offline")


def tool_set(tool=None):
    registry = ToolRegistry()
    selected = tool or StubTool()
    registry.register(selected)
    return ToolSet(registry, selected.task_types)


def response(source="sample"):
    return json.dumps({
        "summary": "summary",
        "evidence": [{"source": source, "detail": "detail"}],
        "causes": ["cause"],
        "recommendations": ["recommendation"],
        "validation_steps": ["validation"],
    })


def definition(name, source=None, selected_tool=None):
    return DomainDefinition(
        name=name,
        knowledge_source=source or InMemoryKnowledgeSource([
            KnowledgeItem(source="sample", content="fixed knowledge"),
        ]),
        tool_set=tool_set(selected_tool),
        prompt_builder=build_analysis_prompt,
        result_parser=parse_analysis_response,
    )


class DomainContractTests(unittest.TestCase):
    def test_problem_and_knowledge_contracts_reject_empty_values(self):
        with self.assertRaisesRegex(ValueError, "domain"):
            Problem(domain="", question="question")
        with self.assertRaisesRegex(ValueError, "question"):
            Problem(domain="test", question=" ")
        with self.assertRaisesRegex(ValueError, "source"):
            KnowledgeItem(source="", content="content")

    def test_tool_set_requires_registered_task_types(self):
        with self.assertRaisesRegex(ValueError, "unregistered"):
            ToolSet(ToolRegistry(), ("missing",))

    def test_domain_registry_rejects_duplicate_names(self):
        registry = DomainRegistry()
        registry.register(definition("sample"))

        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(definition("sample"))


class DomainScenarioTests(unittest.TestCase):
    def test_three_fixed_scenarios_share_one_workflow(self):
        registry = create_scenario_registry()

        for domain, problem in SCENARIO_PROBLEMS.items():
            with self.subTest(domain=domain):
                result = DomainOrchestrator(
                    registry,
                    llm_fn=lambda prompt, name=domain: scenario_response(name),
                ).run(problem)

                self.assertTrue(result.success)
                self.assertEqual(result.analysis.to_dict(), {
                    "domain": domain,
                    **SCENARIO_EXPECTED_RESULTS[domain],
                })
                self.assertEqual(
                    [step.name for step in result.context.steps],
                    [
                        "resolve_domain",
                        "retrieve_knowledge",
                        "execute_tools",
                        "build_prompt",
                        "generate_answer",
                        "parse_result",
                    ],
                )
                self.assertTrue(all(
                    step.status is DomainStepStatus.SUCCEEDED
                    for step in result.context.steps
                ))

    def test_new_domain_is_added_only_through_registration(self):
        registry = DomainRegistry()
        registry.register(definition("new_domain"))

        result = DomainOrchestrator(
            registry,
            llm_fn=lambda prompt: response(),
        ).run(Problem(domain="new_domain", question="What happened?"))

        self.assertTrue(result.success)
        self.assertEqual(result.analysis.domain, "new_domain")
        self.assertEqual(result.context.tool_results[0].tool, "stub")

    def test_empty_knowledge_results_do_not_interrupt_workflow(self):
        registry = DomainRegistry()
        registry.register(definition(
            "empty_knowledge",
            source=InMemoryKnowledgeSource([]),
        ))

        result = DomainOrchestrator(
            registry,
            llm_fn=lambda prompt: response(source="stub"),
        ).run(Problem(domain="empty_knowledge", question="No match?"))

        self.assertTrue(result.success)
        self.assertEqual(result.context.knowledge, [])
        self.assertEqual(
            result.context.steps[1].detail["knowledge_count"],
            0,
        )

    def test_unknown_domain_returns_structured_error(self):
        result = DomainOrchestrator(
            DomainRegistry(),
            llm_fn=lambda prompt: self.fail("LLM must not run"),
        ).run(Problem(domain="missing", question="question"))

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "resolve_domain")
        self.assertEqual(result.error.error_type, "LookupError")

    def test_knowledge_failure_returns_structured_error(self):
        registry = DomainRegistry()
        registry.register(definition("broken", source=FailingKnowledgeSource()))

        result = DomainOrchestrator(
            registry,
            llm_fn=lambda prompt: self.fail("LLM must not run"),
        ).run(Problem(domain="broken", question="question"))

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "retrieve_knowledge")
        self.assertEqual(result.error.error_type, "OSError")

    def test_tool_failure_returns_structured_error(self):
        registry = DomainRegistry()
        registry.register(definition(
            "broken_tool",
            selected_tool=StubTool(error=RuntimeError("tool offline")),
        ))

        result = DomainOrchestrator(
            registry,
            llm_fn=lambda prompt: self.fail("LLM must not run"),
        ).run(Problem(domain="broken_tool", question="question"))

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "execute_tools")
        self.assertIn("tool offline", result.error.message)

    def test_invalid_model_response_is_rejected(self):
        registry = DomainRegistry()
        registry.register(definition("invalid_response"))

        result = DomainOrchestrator(
            registry,
            llm_fn=lambda prompt: "not json",
        ).run(Problem(domain="invalid_response", question="question"))

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "parse_result")
        self.assertEqual(result.error.error_type, "ValueError")

    def test_untraceable_evidence_is_rejected(self):
        registry = DomainRegistry()
        registry.register(definition("untraceable"))

        result = DomainOrchestrator(
            registry,
            llm_fn=lambda prompt: response(source="invented-source"),
        ).run(Problem(domain="untraceable", question="question"))

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "parse_result")
        self.assertIn("unknown sources", result.error.message)

    def test_non_string_model_response_is_structured_failure(self):
        registry = DomainRegistry()
        registry.register(definition("invalid_response_type"))

        result = DomainOrchestrator(
            registry,
            llm_fn=lambda prompt: None,
        ).run(Problem(domain="invalid_response_type", question="question"))

        self.assertFalse(result.success)
        self.assertEqual(result.error.step, "generate_answer")
        self.assertEqual(result.error.error_type, "ValueError")

    def test_json_code_fence_is_supported(self):
        registry = DomainRegistry()
        registry.register(definition("fenced"))

        result = DomainOrchestrator(
            registry,
            llm_fn=lambda prompt: f"```json\n{response()}\n```",
        ).run(Problem(domain="fenced", question="question"))

        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
