import os

import faiss
import numpy as np

from agent.ast_parser import extract_functions
from config import EMBEDDING_MODEL, get_openai_client


def embed(text: str) -> np.ndarray:
    client = get_openai_client()
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return np.asarray(resp.data[0].embedding, dtype="float32")


def build_index(repo_path: str):
    if not os.path.isdir(repo_path):
        raise FileNotFoundError(
            f"Repository path does not exist: {repo_path}. "
            "Put Python files under data/repo or set REPO_PATH in .env."
        )

    docs = []
    vectors = []
    py_files = 0
    skipped_files = []

    for root, _, files in os.walk(repo_path):
        for filename in files:
            if not filename.endswith(".py"):
                continue

            py_files += 1
            path = os.path.join(root, filename)

            try:
                with open(path, "r", encoding="utf-8") as file:
                    code = file.read()
                funcs = extract_functions(code)
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                skipped_files.append(f"{path}: {exc}")
                continue

            for fn in funcs:
                text = f"{fn['name']}\n{fn['code']}"
                docs.append({
                    "function_name": fn["name"],
                    "file_path": path,
                    "start_line": fn["start_line"],
                    "end_line": fn["end_line"],
                    "code": fn["code"],
                    "text": text,
                })
                vectors.append(embed(text))

    if py_files == 0:
        raise ValueError(f"No Python files found under repository path: {repo_path}")

    if not vectors:
        detail = ""
        if skipped_files:
            detail = " Skipped files: " + "; ".join(skipped_files)
        raise ValueError(f"No Python functions found under repository path: {repo_path}.{detail}")

    matrix = np.vstack(vectors).astype("float32")
    index = faiss.IndexFlatL2(matrix.shape[1])
    index.add(matrix)

    return index, docs
