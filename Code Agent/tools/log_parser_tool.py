import re
from typing import Any

from tools.base import BaseTool, ToolRequest


class LogParserTool(BaseTool):
    """Extract error signatures and stack frames from crash-log knowledge."""

    name = "log_parser"
    task_types = ("log_analysis",)

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        contexts = request.payload.get("contexts", [])
        if not isinstance(contexts, list):
            raise ValueError("Log analysis requires a contexts list.")
        errors: set[str] = set()
        frames: set[str] = set()
        for context in contexts:
            if not isinstance(context, dict):
                raise ValueError("Log contexts must contain dictionaries.")
            content = context.get("content", "")
            if not isinstance(content, str):
                raise ValueError("Log context content must be a string.")
            errors.update(re.findall(r"\b[A-Z][A-Za-z]+(?:Error|Exception)\b", content))
            frames.update(re.findall(r"(?:at|in)\s+([A-Za-z_][\w.]*)", content))
        return {
            "error_signatures": sorted(errors),
            "stack_frames": sorted(frames),
        }
