from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolRequest:
    """Uniform input passed to every registered tool."""

    task_id: str
    task_type: str
    query: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ValueError("Tool request task_id must not be empty.")
        if not isinstance(self.task_type, str) or not self.task_type.strip():
            raise ValueError("Tool request task_type must not be empty.")
        if not isinstance(self.query, str):
            raise ValueError("Tool request query must be a string.")
        if not isinstance(self.payload, dict):
            raise ValueError("Tool request payload must be a dictionary.")


@dataclass(frozen=True)
class ToolError:
    """Structured details for a failed tool execution."""

    error_type: str
    message: str


@dataclass(frozen=True)
class ToolResult:
    """Uniform success or failure result returned by every tool."""

    tool: str
    task_id: str
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: ToolError | None = None

    def __post_init__(self) -> None:
        if self.success and self.error is not None:
            raise ValueError("Successful tool results cannot contain an error.")
        if not self.success and self.error is None:
            raise ValueError("Failed tool results must contain an error.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": (
                {
                    "error_type": self.error.error_type,
                    "message": self.error.message,
                }
                if self.error
                else None
            ),
        }


class BaseTool(ABC):
    """Common execution contract for workflow tools."""

    name: str
    task_types: tuple[str, ...]

    def run(self, request: ToolRequest) -> ToolResult:
        """Execute safely and convert exceptions into structured failures."""
        try:
            output = self.execute(request)
            if not isinstance(output, dict):
                raise TypeError("Tool output must be a dictionary.")
            return ToolResult(
                tool=self.name,
                task_id=request.task_id,
                success=True,
                output=output,
            )
        except Exception as exc:
            return ToolResult(
                tool=self.name,
                task_id=request.task_id,
                success=False,
                error=ToolError(
                    error_type=type(exc).__name__,
                    message=str(exc),
                ),
            )

    @abstractmethod
    def execute(self, request: ToolRequest) -> dict[str, Any]:
        """Implement tool-specific behavior."""
