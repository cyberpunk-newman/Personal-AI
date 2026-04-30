import os
import faiss
import numpy as np
from agent.ast_parser import extract_functions
from openai import OpenAI

client = OpenAI()

docs = []
vectors = []

def embed(text):
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return np.array(resp.data[0].embedding)

def build_index(repo_path):
    global docs, vectors

    for root, _, files in os.walk(repo_path):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                code = open(path).read()

                funcs = extract_functions(code)
                for fn in funcs:
                    text = f"{fn['name']}\n{fn['code']}"
                    vec = embed(text)

                    docs.append(text)
                    vectors.append(vec)

    dim = len(vectors[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectors))

    return index