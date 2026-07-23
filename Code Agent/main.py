from collections.abc import Callable

from core.config import REPO_PATH
from workflow.analyzer import analyze_question, build_index


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
        try:
            answer = analyze_question(query, index, docs)
        except Exception as exc:
            output_fn(f"\n回答失败：{exc}")
            continue
        output_fn("\n回答：\n", answer)


if __name__ == "__main__":
    main()
