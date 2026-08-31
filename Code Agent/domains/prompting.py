import json

from domains.contracts import AnalysisResult, Evidence, KnowledgeItem, Problem
from tools import ToolResult


def build_analysis_prompt(
    problem: Problem,
    knowledge: list[KnowledgeItem],
    tool_results: list[ToolResult],
) -> str:
    """Build one domain-neutral prompt with a stable output contract."""
    input_data = {
        "domain": problem.domain,
        "question": problem.question,
        "knowledge": [item.to_dict() for item in knowledge],
        "tool_results": [item.to_dict() for item in tool_results],
    }
    return (
        "Analyze the supplied problem using only traceable evidence. "
        "Return one JSON object with keys summary, evidence, causes, "
        "recommendations, and validation_steps. Evidence entries must have "
        "source and detail. All sections must be non-empty.\n"
        + json.dumps(input_data, ensure_ascii=False, sort_keys=True)
    )


def parse_analysis_response(
    raw_answer: str,
    problem: Problem,
    knowledge: list[KnowledgeItem],
    tool_results: list[ToolResult],
) -> AnalysisResult:
    """Validate the stable structured response returned for any domain."""
    if not isinstance(raw_answer, str) or not raw_answer.strip():
        raise ValueError("Analysis response must not be empty.")
    text = raw_answer.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:].lstrip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Analysis response must be valid JSON.") from exc
    required = {
        "summary", "evidence", "causes", "recommendations", "validation_steps"
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Analysis response has an invalid structure.")
    if not isinstance(value["evidence"], list):
        raise ValueError("Analysis evidence must be a list.")
    try:
        evidence = tuple(
            Evidence(source=item["source"], detail=item["detail"])
            for item in value["evidence"]
            if isinstance(item, dict) and set(item) == {"source", "detail"}
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Analysis evidence is invalid.") from exc
    if len(evidence) != len(value["evidence"]):
        raise ValueError("Analysis evidence is invalid.")
    allowed_sources = {
        item.source for item in knowledge
    } | {
        item.tool for item in tool_results
    }
    unknown_sources = sorted({
        item.source for item in evidence if item.source not in allowed_sources
    })
    if unknown_sources:
        raise ValueError(
            "Analysis evidence references unknown sources: "
            + ", ".join(unknown_sources)
            + "."
        )
    for key in ("causes", "recommendations", "validation_steps"):
        if not isinstance(value[key], list):
            raise ValueError(f"Analysis {key} must be a list.")
    return AnalysisResult(
        domain=problem.domain,
        summary=value["summary"],
        evidence=evidence,
        causes=tuple(value["causes"]),
        recommendations=tuple(value["recommendations"]),
        validation_steps=tuple(value["validation_steps"]),
        raw_answer=raw_answer,
    )
