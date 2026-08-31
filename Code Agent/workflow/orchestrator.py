from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents.planner import TaskPlan, TaskType, plan_question, validate_task_plan
from core.llm import ask_llm
from rag.retriever import retrieve
from workflow.prompt_builder import build_prompt


class StepStatus(str, Enum):
    """Execution state of one workflow step."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class WorkflowError:
    """Structured information about a workflow failure."""

    step: str
    error_type: str
    message: str


@dataclass
class WorkflowStep:
    """Traceable input, output, and error state for one workflow step."""

    name: str
    input: dict[str, Any]
    status: StepStatus
    output: dict[str, Any] | None = None
    error: WorkflowError | None = None


@dataclass
class WorkflowContext:
    """State shared across a single analysis workflow execution."""

    query: str
    index: Any
    docs: list[dict[str, Any]]
    k: int = 3
    plan: TaskPlan | None = None
    steps: list[WorkflowStep] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Unified result returned by the analysis workflow."""

    context: WorkflowContext
    answer: str | None = None
    contexts: list[dict[str, Any]] = field(default_factory=list)
    error: WorkflowError | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class WorkflowExecutionError(RuntimeError):
    """Compatibility exception raised when a workflow result has failed."""

    def __init__(self, error: WorkflowError):
        self.error = error
        super().__init__(f"Workflow step '{error.step}' failed: {error.message}")


class Orchestrator:
    """Coordinate retrieval, analysis preparation, and LLM execution."""

    def __init__(
        self,
        *,
        retrieve_fn: Callable[..., list[dict[str, Any]]] = retrieve,
        analyzer_fn: Callable[[str, list[dict[str, Any]]], str] = build_prompt,
        llm_fn: Callable[[str], str] = ask_llm,
        planner_fn: Callable[[str], TaskPlan] = plan_question,
    ) -> None:
        self._retrieve = retrieve_fn
        self._analyze = analyzer_fn
        self._ask_llm = llm_fn
        self._plan = planner_fn

    def run(
        self,
        query: str,
        index: Any,
        docs: list[dict[str, Any]],
        *,
        k: int = 3,
    ) -> AnalysisResult:
        """Run one question through the complete analysis workflow."""
        context = WorkflowContext(query=query.strip(), index=index, docs=docs, k=k)
        result = AnalysisResult(context=context)

        if not context.query:
            error = WorkflowError(
                step="validate_input",
                error_type="ValueError",
                message="Question must not be empty.",
            )
            context.steps.append(
                WorkflowStep(
                    name="validate_input",
                    input={"query": query},
                    status=StepStatus.FAILED,
                    error=error,
                )
            )
            result.error = error
            return result

        try:
            context.plan = validate_task_plan(self._plan(context.query))
        except Exception as exc:
            return self._fail(
                result,
                step="plan",
                step_input={"query": context.query},
                exc=exc,
            )

        context.steps.append(
            WorkflowStep(
                name="plan",
                input={"query": context.query},
                status=StepStatus.SUCCEEDED,
                output={"plan": context.plan.to_dict()},
            )
        )

        prompt = ""
        for task in context.plan.tasks:
            task_input = {"task": task.to_dict()}

            if task.type is TaskType.CODE_SEARCH:
                step_input = {
                    **task_input,
                    "query": context.query,
                    "document_count": len(docs),
                    "k": k,
                }
                try:
                    result.contexts = self._retrieve(
                        context.query,
                        index,
                        docs,
                        k=k,
                    )
                except Exception as exc:
                    return self._fail(
                        result,
                        step="retrieve",
                        step_input=step_input,
                        exc=exc,
                    )
                context.steps.append(
                    WorkflowStep(
                        name="retrieve",
                        input=step_input,
                        status=StepStatus.SUCCEEDED,
                        output={
                            "contexts": result.contexts,
                            "context_count": len(result.contexts),
                        },
                    )
                )

            elif task.type is TaskType.CODE_ANALYSIS:
                step_input = {
                    **task_input,
                    "query": context.query,
                    "contexts": result.contexts,
                }
                try:
                    prompt = self._analyze(context.query, result.contexts)
                except Exception as exc:
                    return self._fail(
                        result,
                        step="analyze",
                        step_input=step_input,
                        exc=exc,
                    )
                context.steps.append(
                    WorkflowStep(
                        name="analyze",
                        input=step_input,
                        status=StepStatus.SUCCEEDED,
                        output={"prompt": prompt},
                    )
                )

            elif task.type is TaskType.ANSWER_GENERATION:
                step_input = {**task_input, "prompt": prompt}
                try:
                    result.answer = self._ask_llm(prompt)
                except Exception as exc:
                    return self._fail(
                        result,
                        step="llm",
                        step_input=step_input,
                        exc=exc,
                    )
                context.steps.append(
                    WorkflowStep(
                        name="llm",
                        input=step_input,
                        status=StepStatus.SUCCEEDED,
                        output={"answer": result.answer},
                    )
                )

        return result

    @staticmethod
    def _fail(
        result: AnalysisResult,
        *,
        step: str,
        step_input: dict[str, Any],
        exc: Exception,
    ) -> AnalysisResult:
        error = WorkflowError(
            step=step,
            error_type=type(exc).__name__,
            message=str(exc),
        )
        result.context.steps.append(
            WorkflowStep(
                name=step,
                input=step_input,
                status=StepStatus.FAILED,
                error=error,
            )
        )
        result.error = error
        return result


def run_workflow(
    query: str,
    index: Any,
    docs: list[dict[str, Any]],
    *,
    k: int = 3,
    retrieve_fn: Callable[..., list[dict[str, Any]]] = retrieve,
    analyzer_fn: Callable[[str, list[dict[str, Any]]], str] = build_prompt,
    llm_fn: Callable[[str], str] = ask_llm,
    planner_fn: Callable[[str], TaskPlan] = plan_question,
) -> AnalysisResult:
    """Public workflow entry point for all code-analysis questions."""
    return Orchestrator(
        retrieve_fn=retrieve_fn,
        analyzer_fn=analyzer_fn,
        llm_fn=llm_fn,
        planner_fn=planner_fn,
    ).run(query, index, docs, k=k)
