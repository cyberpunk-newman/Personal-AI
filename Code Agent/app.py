from agent.rag import build_index
from agent.retriever import retrieve
from agent.llm import ask_llm

print("🔧 Building index...")
index = build_index("data/repo")

while True:
    query = input("\n❓ 请输入问题：")

    contexts = retrieve(query, index)

    prompt = f"""
你是一个代码分析助手，请基于以下代码回答问题：

{contexts}

问题：{query}
请解释清楚函数作用和逻辑。
"""

    answer = ask_llm(prompt)
    print("\n🤖 回答：\n", answer)