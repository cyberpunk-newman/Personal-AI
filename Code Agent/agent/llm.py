from config import LLM_MODEL, get_openai_client


def ask_llm(prompt: str) -> str:
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content
