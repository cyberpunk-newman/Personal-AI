from agent.llm import ask_llm
from agent.rag import build_index
from agent.retriever import retrieve
from config import REPO_PATH


def main():
    print(f"Building index from {REPO_PATH}...")

    try:
        index, docs = build_index(REPO_PATH)
    except Exception as exc:
        print(f"Failed to build index: {exc}")
        return

    while True:
        query = input("\n请输入问题：").strip()
        if not query:
            continue

        contexts = retrieve(query, index, docs)

        prompt = f"""
你是一个代码分析助手，请基于以下代码回答问题：

{contexts}

问题：{query}
请解释清楚函数作用和逻辑。
"""

        try:
            answer = ask_llm(prompt)
        except Exception as exc:
            print(f"\n回答失败：{exc}")
            continue

        print("\n回答：\n", answer)


if __name__ == "__main__":
    main()
