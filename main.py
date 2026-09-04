from collections.abc import Callable

from core.config import REPO_PATH
from workflow.analyzer import build_index
from workflow.orchestrator import run_workflow


def main(
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[..., None] = print,
) -> None:
    """Run the interactive command-line interface."""
    output_fn(f"Building index from {REPO_PATH}...")

    try:
        index, docs = build_index(REPO_PATH)
    except Exception as exc:
        output_fn(f"Failed to build index: {exc}")
        return

    while True:
        query = input_fn("\n请输入问题：").strip()
        if not query:
            continue
        result = run_workflow(query, index, docs)
        if result.error is not None:
            output_fn(
                f"\n回答失败（步骤：{result.error.step}）：{result.error.message}"
            )
            continue
        output_fn("\n回答：\n", result.answer)


if __name__ == "__main__":
    main()
