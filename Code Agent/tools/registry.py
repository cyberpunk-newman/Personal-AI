from tools.base import BaseTool, ToolError, ToolRequest, ToolResult


class ToolRegistry:
    """Resolve task types to tools without exposing concrete implementations."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if not isinstance(tool, BaseTool):
            raise TypeError("Only BaseTool implementations can be registered.")
        if not isinstance(tool.name, str) or not tool.name.strip() or not tool.task_types:
            raise ValueError("Registered tools require a name and task types.")
        if any(
            not isinstance(task_type, str) or not task_type.strip()
            for task_type in tool.task_types
        ):
            raise ValueError("Registered task types must be non-empty strings.")
        if len(tool.task_types) != len(set(tool.task_types)):
            raise ValueError("A tool cannot register the same task type more than once.")

        duplicates = [
            task_type for task_type in tool.task_types if task_type in self._tools
        ]
        if duplicates:
            raise ValueError(f"Task types already registered: {', '.join(duplicates)}.")
        for task_type in tool.task_types:
            self._tools[task_type] = tool

    def resolve(self, task_type: str) -> BaseTool | None:
        return self._tools.get(task_type)

    def execute(self, request: ToolRequest) -> ToolResult:
        tool = self.resolve(request.task_type)
        if tool is None:
            return ToolResult(
                tool="unregistered",
                task_id=request.task_id,
                success=False,
                error=ToolError(
                    error_type="ToolNotFoundError",
                    message=f"No tool registered for task type: {request.task_type}.",
                ),
            )
        return tool.run(request)

    def mappings(self) -> dict[str, str]:
        """Expose a stable task-type to tool-name mapping for validation."""
        return {task_type: tool.name for task_type, tool in self._tools.items()}
