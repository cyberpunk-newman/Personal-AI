from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from core.llm import ask_llm
from domains import AnalysisResult, DomainRegistry, KnowledgeItem, Problem
from tools import ToolResult


class DomainStepStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class DomainWorkflowError:
    step: str
    error_type: str
    message: str


@dataclass(frozen=True)
class DomainWorkflowStep:
    name: str
    status: DomainStepStatus
    detail: dict[str, object] = field(default_factory=dict)
    error: DomainWorkflowError | None = None


@dataclass
class DomainWorkflowContext:
    problem: Problem
    knowledge: list[KnowledgeItem] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    steps: list[DomainWorkflowStep] = field(default_factory=list)


@dataclass
class DomainWorkflowResult:
    context: DomainWorkflowContext
    analysis: AnalysisResult | None = None
    error: DomainWorkflowError | None = None

    @property
    def success(self) -> bool:
        return self.error is None and self.analysis is not None


class DomainOrchestrator:
    """Execute the same workflow for every registered problem domain."""

    def __init__(
        self,
        registry: DomainRegistry,
        *,
        llm_fn: Callable[[str], str] = ask_llm,
    ) -> None:
        if not isinstance(registry, DomainRegistry):
            raise TypeError("Domain workflow requires a DomainRegistry.")
        self._registry = registry
        self._ask_llm = llm_fn

    def run(self, problem: Problem, *, limit: int = 3) -> DomainWorkflowResult:
        context = DomainWorkflowContext(problem=problem)
        result = DomainWorkflowResult(context=context)
        definition = self._registry.resolve(problem.domain)
        if definition is None:
            return self._fail(
                result,
                step="resolve_domain",
                exc=LookupError(f"No domain registered for: {problem.domain}."),
            )
        context.steps.append(DomainWorkflowStep(
            name="resolve_domain",
            status=DomainStepStatus.SUCCEEDED,
            detail={"domain": definition.name},
        ))

        try:
            context.knowledge = definition.knowledge_source.search(
                problem,
                limit=limit,
            )
            if not isinstance(context.knowledge, list) or any(
                not isinstance(item, KnowledgeItem) for item in context.knowledge
            ):
                raise TypeError("Knowledge source returned an invalid item.")
        except Exception as exc:
            return self._fail(result, step="retrieve_knowledge", exc=exc)
        context.steps.append(DomainWorkflowStep(
            name="retrieve_knowledge",
            status=DomainStepStatus.SUCCEEDED,
            detail={"knowledge_count": len(context.knowledge)},
        ))

        try:
            context.tool_results = definition.tool_set.execute(
                problem,
                context.knowledge,
            )
        except Exception as exc:
            return self._fail(result, step="execute_tools", exc=exc)
        failed_tool = next(
            (tool_result for tool_result in context.tool_results if not tool_result.success),
            None,
        )
        if failed_tool is not None:
            if failed_tool.error is None:
                return self._fail(
                    result,
                    step="execute_tools",
                    exc=RuntimeError("Tool failed without error details."),
                )
            return self._fail(
                result,
                step="execute_tools",
                exc=RuntimeError(
                    f"{failed_tool.tool}: {failed_tool.error.message}"
                ),
            )
        context.steps.append(DomainWorkflowStep(
            name="execute_tools",
            status=DomainStepStatus.SUCCEEDED,
            detail={
                "tools": [item.tool for item in context.tool_results],
                "tool_count": len(context.tool_results),
            },
        ))

        try:
            prompt = definition.prompt_builder(
                problem,
                context.knowledge,
                context.tool_results,
            )
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Prompt builder must return a non-empty string.")
        except Exception as exc:
            return self._fail(result, step="build_prompt", exc=exc)
        context.steps.append(DomainWorkflowStep(
            name="build_prompt",
            status=DomainStepStatus.SUCCEEDED,
            detail={"prompt_length": len(prompt)},
        ))

        try:
            raw_answer = self._ask_llm(prompt)
            if not isinstance(raw_answer, str) or not raw_answer.strip():
                raise ValueError("LLM must return a non-empty string.")
        except Exception as exc:
            return self._fail(result, step="generate_answer", exc=exc)
        context.steps.append(DomainWorkflowStep(
            name="generate_answer",
            status=DomainStepStatus.SUCCEEDED,
            detail={"answer_length": len(raw_answer)},
        ))

        try:
            result.analysis = definition.result_parser(
                raw_answer,
                problem,
                context.knowledge,
                context.tool_results,
            )
            if not isinstance(result.analysis, AnalysisResult):
                raise TypeError("Result parser must return an AnalysisResult.")
        except Exception as exc:
            return self._fail(result, step="parse_result", exc=exc)
        context.steps.append(DomainWorkflowStep(
            name="parse_result",
            status=DomainStepStatus.SUCCEEDED,
            detail={"evidence_count": len(result.analysis.evidence)},
        ))
        return result

    @staticmethod
    def _fail(
        result: DomainWorkflowResult,
        *,
        step: str,
        exc: Exception,
    ) -> DomainWorkflowResult:
        error = DomainWorkflowError(
            step=step,
            error_type=type(exc).__name__,
            message=str(exc),
        )
        result.context.steps.append(DomainWorkflowStep(
            name=step,
            status=DomainStepStatus.FAILED,
            error=error,
        ))
        result.error = error
        return result
