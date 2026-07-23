import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import REPO_PATH
from rag.retriever import retrieve
from workflow.analyzer import build_index

QUESTIONS_PATH = PROJECT_ROOT / "eval" / "questions.json"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
LATEST_JSON = RESULTS_DIR / "latest.json"
SUMMARY_MD = RESULTS_DIR / "summary.md"


def load_questions() -> list[dict[str, Any]]:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def file_name(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).name


def result_matches(
    result: dict[str, Any],
    expected_functions: list[str],
    expected_files: list[str],
) -> bool:
    """判断单条检索结果是否命中评测样本的期望目标。

    命中规则采用严格匹配：如果样本同时声明 expected_functions 与 expected_files，
    则函数名和文件名都必须匹配；如果其中一个列表为空，则该维度不参与判断。

    Args:
        result: retrieve 返回的单条结构化结果。
        expected_functions: 期望命中的函数名列表。
        expected_files: 期望命中的文件名列表。

    Returns:
        True 表示该检索结果命中预期目标。
    """
    function_ok = (
        not expected_functions
        or result.get("function_name") in expected_functions
    )
    file_ok = (
        not expected_files
        or file_name(result.get("file_path")) in expected_files
    )
    return function_ok and file_ok


def evaluate_case(case: dict[str, Any], index, docs: list[dict[str, Any]]) -> dict[str, Any]:
    """执行单条检索评测样本。

    该函数负责调用 retrieve 获取 top-k 结果，并基于 result_matches 生成 hit@1、
    hit@k、延迟和候选详情。它只评估检索是否命中，不调用 LLM 生成答案。

    Args:
        case: questions.json 中的一条评测样本。
        index: build_index 返回的 FAISS 索引。
        docs: build_index 返回的函数 metadata 列表。

    Returns:
        单条样本的评测结果，包括命中情况、延迟和完整检索候选。
    """
    k = int(case.get("k", 3))
    expected_functions = case.get("expected_functions", [])
    expected_files = case.get("expected_files", [])

    started = time.perf_counter()
    retrieved = retrieve(case["question"], index, docs, k=k)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    matches = [
        result_matches(result, expected_functions, expected_files)
        for result in retrieved
    ]

    return {
        "id": case["id"],
        "category": case.get("category"),
        "question": case["question"],
        "expected_functions": expected_functions,
        "expected_files": expected_files,
        "k": k,
        "hit_at_1": bool(matches[:1] and matches[0]),
        "hit_at_k": any(matches),
        "latency_ms": latency_ms,
        "retrieved": [
            {
                "rank": item.get("rank"),
                "score": item.get("score"),
                "function_name": item.get("function_name"),
                "file_path": item.get("file_path"),
                "start_line": item.get("start_line"),
                "end_line": item.get("end_line"),
                "matched_expected": matches[idx],
                "code": item.get("code"),
            }
            for idx, item in enumerate(retrieved)
        ],
    }


def build_summary(results: list[dict[str, Any]], total_latency_ms: float) -> dict[str, Any]:
    """汇总检索评测指标。

    Recall@1 表示预期函数是否出现在第一条检索结果；Recall@K 表示预期函数是否
    出现在当前样本配置的 top-k 检索结果中。missed_cases 只记录未在 top-k 中命中
    的样本。

    Args:
        results: 所有样本的评测结果。
        total_latency_ms: 索引构建与检索评测的总耗时，单位毫秒。

    Returns:
        汇总指标字典，包含样本数、Recall@1、Recall@K、命中数和 missed cases。
    """
    total = len(results)
    hit_at_1 = sum(1 for item in results if item["hit_at_1"])
    hit_at_k = sum(1 for item in results if item["hit_at_k"])
    failed = [item for item in results if not item["hit_at_k"]]

    recall_at_1 = hit_at_1 / total if total else 0
    recall_at_k = hit_at_k / total if total else 0

    return {
        "total_cases": total,
        "recall_at_1": round(recall_at_1, 4),
        "recall_at_k": round(recall_at_k, 4),
        "hit_at_1": hit_at_1,
        "hit_at_k": hit_at_k,
        "missed_cases": [item["id"] for item in failed],
        "total_latency_ms": total_latency_ms,
    }


def write_outputs(summary: dict[str, Any], results: list[dict[str, Any]]) -> None:
    """写出检索评测结果文件。

    Args:
        summary: build_summary 生成的汇总指标。
        results: 所有样本的详细评测结果。

    Side Effects:
        写入 eval/results/latest.json 和 eval/results/summary.md。
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo_path": REPO_PATH,
        "summary": summary,
        "results": results,
    }

    with open(LATEST_JSON, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    lines = [
        "# Retrieval Eval Summary",
        "",
        f"- Repo path: `{REPO_PATH}`",
        f"- Total cases: {summary['total_cases']}",
        f"- Recall@1: {summary['recall_at_1']:.2%} ({summary['hit_at_1']}/{summary['total_cases']})",
        f"- Recall@K: {summary['recall_at_k']:.2%} ({summary['hit_at_k']}/{summary['total_cases']})",
        f"- Total latency: {summary['total_latency_ms']} ms",
        "",
        "## Missed Cases",
        "",
    ]

    if summary["missed_cases"]:
        lines.extend(f"- `{case_id}`" for case_id in summary["missed_cases"])
    else:
        lines.append("- None")

    lines.extend(["", "## Per Case", ""])
    for item in results:
        status = "PASS" if item["hit_at_k"] else "FAIL"
        lines.append(
            f"- `{item['id']}` {status}: "
            f"hit@1={item['hit_at_1']}, hit@k={item['hit_at_k']}, "
            f"latency={item['latency_ms']} ms"
        )

    with open(SUMMARY_MD, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


def main():
    questions = load_questions()

    build_started = time.perf_counter()
    index, docs = build_index(REPO_PATH)
    build_latency_ms = round((time.perf_counter() - build_started) * 1000, 2)

    results = [evaluate_case(case, index, docs) for case in questions]
    eval_latency_ms = round(sum(item["latency_ms"] for item in results), 2)
    summary = build_summary(results, build_latency_ms + eval_latency_ms)

    write_outputs(summary, results)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {LATEST_JSON}")
    print(f"Wrote {SUMMARY_MD}")


if __name__ == "__main__":
    main()
