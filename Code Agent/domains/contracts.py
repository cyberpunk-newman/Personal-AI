from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from tools import ToolRegistry, ToolRequest, ToolResult


@dataclass(frozen=True)
class Problem:
    """Uniform problem submitted to any registered analysis domain."""

    domain: str
    question: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.domain, str) or not self.domain.strip():
            raise ValueError("Problem domain must not be empty.")
        if not isinstance(self.question, str) or not self.question.strip():
            raise ValueError("Problem question must not be empty.")
        if not isinstance(self.payload, dict):
            raise ValueError("Problem payload must be a dictionary.")


@dataclass(frozen=True)
class KnowledgeItem:
    """One item returned by a knowledge source."""

    source: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Knowledge item source must not be empty.")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("Knowledge item content must not be empty.")
        if not isinstance(self.metadata, dict):
            raise ValueError("Knowledge item metadata must be a dictionary.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "content": self.content,
            "metadata": self.metadata,
        }


class KnowledgeSource(ABC):
    """Uniform retrieval contract for code, logs, cases, and documents."""

    @abstractmethod
    def search(self, problem: Problem, *, limit: int) -> list[KnowledgeItem]:
        """Return knowledge relevant to a problem."""


class InMemoryKnowledgeSource(KnowledgeSource):
    """Deterministic source used by fixed scenarios and tests."""

    def __init__(self, items: list[KnowledgeItem]) -> None:
        if not isinstance(items, list) or any(
            not isinstance(item, KnowledgeItem) for item in items
        ):
            raise ValueError("Knowledge source items must be KnowledgeItem instances.")
        self._items = tuple(items)

    def search(self, problem: Problem, *, limit: int) -> list[KnowledgeItem]:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Knowledge search limit must be positive.")
        terms = {
            term.lower()
            for term in problem.question.replace("_", " ").split()
            if len(term) > 2
        }
        ranked = sorted(
            self._items,
            key=lambda item: sum(
                term in f"{item.source} {item.content}".lower() for term in terms
            ),
            reverse=True,
        )
        return list(ranked[:limit])


@dataclass(frozen=True)
class Evidence:
    """Traceable evidence used in the final analysis."""

    source: str
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Evidence source must not be empty.")
        if not isinstance(self.detail, str) or not self.detail.strip():
            raise ValueError("Evidence detail must not be empty.")

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "detail": self.detail}


@dataclass(frozen=True)
class AnalysisResult:
    """Uniform successful output shared by every analysis domain."""

    domain: str
    summary: str
    evidence: tuple[Evidence, ...]
    causes: tuple[str, ...]
    recommendations: tuple[str, ...]
    validation_steps: tuple[str, ...]
    raw_answer: str

    def __post_init__(self) -> None:
        text_fields = {
            "domain": self.domain,
            "summary": self.summary,
            "raw_answer": self.raw_answer,
        }
        if any(
            not isinstance(value, str) or not value.strip()
            for value in text_fields.values()
        ):
            raise ValueError("Analysis text fields must not be empty.")
        if not self.evidence:
            raise ValueError("Analysis result must contain evidence.")
        if any(not isinstance(item, Evidence) for item in self.evidence):
            raise ValueError("Analysis evidence must contain Evidence instances.")
        for name in ("causes", "recommendations", "validation_steps"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or not values or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"Analysis result {name} must contain non-empty strings.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "summary": self.summary,
            "evidence": [item.to_dict() for item in self.evidence],
            "causes": list(self.causes),
            "recommendations": list(self.recommendations),
            "validation_steps": list(self.validation_steps),
        }


class ToolSet:
    """Ordered registered tools that a domain contributes to the workflow."""

    def __init__(self, registry: ToolRegistry, task_types: tuple[str, ...]) -> None:
        if not isinstance(registry, ToolRegistry):
            raise TypeError("Tool set registry must be a ToolRegistry.")
        if not task_types or any(
            not isinstance(task_type, str) or not task_type.strip()
            for task_type in task_types
        ):
            raise ValueError("Tool set task types must be non-empty strings.")
        missing = [
            task_type for task_type in task_types if registry.resolve(task_type) is None
        ]
        if missing:
            raise ValueError(
                f"Tool set contains unregistered task types: {', '.join(missing)}."
            )
        self._registry = registry
        self._task_types = task_types

    @property
    def task_types(self) -> tuple[str, ...]:
        return self._task_types

    def execute(
        self,
        problem: Problem,
        knowledge: list[KnowledgeItem],
    ) -> list[ToolResult]:
        contexts = []
        for item in knowledge:
            context = item.to_dict()
            context.update(item.metadata)
            contexts.append(context)
        payload = {**problem.payload, "contexts": contexts}
        return [
            self._registry.execute(ToolRequest(
                task_id=f"tool_{position}",
                task_type=task_type,
                query=problem.question,
                payload=payload,
            ))
            for position, task_type in enumerate(self._task_types, start=1)
        ]
