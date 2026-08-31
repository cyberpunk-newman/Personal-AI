from typing import Any

from tools.base import BaseTool, ToolRequest


class ConfigAnalysisTool(BaseTool):
    """Compare observed commercial configuration with expected values."""

    name = "config_analysis"
    task_types = ("configuration_analysis",)

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        observed = request.payload.get("observed_config", {})
        expected = request.payload.get("expected_config", {})
        if not isinstance(observed, dict) or not isinstance(expected, dict):
            raise ValueError("Configuration analysis requires dictionaries.")
        mismatches = [
            {
                "key": key,
                "observed": observed.get(key),
                "expected": expected_value,
            }
            for key, expected_value in expected.items()
            if observed.get(key) != expected_value
        ]
        return {
            "mismatches": mismatches,
            "mismatch_count": len(mismatches),
        }
