from collections.abc import Callable
from dataclasses import dataclass

from domains.contracts import (
    AnalysisResult,
    KnowledgeItem,
    KnowledgeSource,
    Problem,
    ToolSet,
)
from tools import ToolResult

PromptBuilder = Callable[[Problem, list[KnowledgeItem], list[ToolResult]], str]
ResultParser = Callable[[str, Problem, list[KnowledgeItem], list[ToolResult]], AnalysisResult]


@dataclass(frozen=True)
class DomainDefinition:
    """Everything a domain registers without changing the core workflow."""

    name: str
    knowledge_source: KnowledgeSource
    tool_set: ToolSet
    prompt_builder: PromptBuilder
    result_parser: ResultParser

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Domain name must not be empty.")
        if not isinstance(self.knowledge_source, KnowledgeSource):
            raise TypeError("Domain knowledge_source must implement KnowledgeSource.")
        if not isinstance(self.tool_set, ToolSet):
            raise TypeError("Domain tool_set must be a ToolSet.")
        if not callable(self.prompt_builder) or not callable(self.result_parser):
            raise TypeError("Domain prompt builder and result parser must be callable.")


class DomainRegistry:
    """Register and resolve domain capabilities by name."""

    def __init__(self) -> None:
        self._domains: dict[str, DomainDefinition] = {}

    def register(self, definition: DomainDefinition) -> None:
        if not isinstance(definition, DomainDefinition):
            raise TypeError("Only DomainDefinition instances can be registered.")
        if definition.name in self._domains:
            raise ValueError(f"Domain already registered: {definition.name}.")
        self._domains[definition.name] = definition

    def resolve(self, name: str) -> DomainDefinition | None:
        return self._domains.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(self._domains)
