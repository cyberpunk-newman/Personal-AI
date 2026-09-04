import json

from domains.contracts import InMemoryKnowledgeSource, KnowledgeItem, Problem, ToolSet
from domains.prompting import build_analysis_prompt, parse_analysis_response
from domains.registry import DomainDefinition, DomainRegistry
from tools.ast_tool import ASTTool
from tools.config_analysis_tool import ConfigAnalysisTool
from tools.dependency_tool import DependencyTool
from tools.log_parser_tool import LogParserTool
from tools.registry import ToolRegistry


def _tool_set(*tools) -> ToolSet:
    registry = ToolRegistry()
    task_types = []
    for tool in tools:
        registry.register(tool)
        task_types.extend(tool.task_types)
    return ToolSet(registry, tuple(task_types))


SCENARIO_PROBLEMS = {
    "code_analysis": Problem(
        domain="code_analysis",
        question="Why can login raise an authentication error?",
    ),
    "test_incident": Problem(
        domain="test_incident",
        question="Why does checkout crash after the retry is exhausted?",
    ),
    "commercial_se": Problem(
        domain="commercial_se",
        question="Why are ad conversion events missing?",
        payload={
            "observed_config": {"conversion_tracking": False, "sdk_version": "4.1"},
            "expected_config": {"conversion_tracking": True, "sdk_version": "4.2"},
        },
    ),
}


SCENARIO_EXPECTED_RESULTS = {
    "code_analysis": {
        "summary": "The login path rejects missing tokens.",
        "evidence": [{
            "source": "auth.py",
            "detail": "login raises AuthenticationError when token is absent.",
        }],
        "causes": ["The caller can pass an empty token."],
        "recommendations": ["Validate the token before calling login."],
        "validation_steps": ["Add a test for an empty token and a valid token."],
    },
    "test_incident": {
        "summary": "Checkout crashes after retry exhaustion.",
        "evidence": [{
            "source": "checkout-crash.log",
            "detail": "RetryError is followed by CheckoutController.submit.",
        }],
        "causes": ["Retry exhaustion is not converted to a handled response."],
        "recommendations": ["Handle RetryError at the checkout boundary."],
        "validation_steps": ["Replay the fixed crash case with the payment stub offline."],
    },
    "commercial_se": {
        "summary": "Conversion tracking is disabled and the SDK is outdated.",
        "evidence": [{
            "source": "conversion-sdk-guide",
            "detail": "Tracking must be enabled on SDK 4.2.",
        }],
        "causes": ["The deployed configuration differs from the supported baseline."],
        "recommendations": ["Enable tracking and upgrade the SDK to 4.2."],
        "validation_steps": ["Send a sandbox conversion and confirm ingestion."],
    },
}


def scenario_response(domain: str) -> str:
    """Return the fixed expected response used for deterministic validation."""
    return json.dumps(SCENARIO_EXPECTED_RESULTS[domain], ensure_ascii=False)


def create_scenario_registry() -> DomainRegistry:
    """Register the three Phase 5 scenarios through the same extension API."""
    registry = DomainRegistry()
    registry.register(DomainDefinition(
        name="code_analysis",
        knowledge_source=InMemoryKnowledgeSource([
            KnowledgeItem(
                source="auth.py",
                content="login rejects requests that do not contain a token.",
                metadata={
                    "file_path": "auth.py",
                    "code": (
                        "def login(token):\n"
                        "    if not token:\n"
                        "        raise AuthenticationError('missing token')\n"
                        "    return authenticate(token)\n"
                    ),
                },
            ),
        ]),
        tool_set=_tool_set(ASTTool(), DependencyTool()),
        prompt_builder=build_analysis_prompt,
        result_parser=parse_analysis_response,
    ))
    registry.register(DomainDefinition(
        name="test_incident",
        knowledge_source=InMemoryKnowledgeSource([
            KnowledgeItem(
                source="checkout-crash.log",
                content=(
                    "RetryError: payment service unavailable after 3 attempts\n"
                    "at CheckoutController.submit\n"
                ),
            ),
            KnowledgeItem(
                source="BUG-1042",
                content="Checkout must handle RetryError and return a retryable response.",
            ),
        ]),
        tool_set=_tool_set(LogParserTool()),
        prompt_builder=build_analysis_prompt,
        result_parser=parse_analysis_response,
    ))
    registry.register(DomainDefinition(
        name="commercial_se",
        knowledge_source=InMemoryKnowledgeSource([
            KnowledgeItem(
                source="conversion-sdk-guide",
                content=(
                    "Conversion tracking must be enabled and requires SDK version 4.2."
                ),
            ),
            KnowledgeItem(
                source="CASE-208",
                content="Missing conversions were restored after correcting SDK settings.",
            ),
        ]),
        tool_set=_tool_set(ConfigAnalysisTool()),
        prompt_builder=build_analysis_prompt,
        result_parser=parse_analysis_response,
    ))
    return registry
