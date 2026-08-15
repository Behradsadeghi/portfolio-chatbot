"""
eval_retrieval.py

Gam-e 2c: keyfiyat-e retrieval ro ADAD mikonim, na hads.

CHERA IN, VA CHERA ALAN
-----------------------
Ta hala 6 ta soal dasti test kardim va cheshmi negah kardim. Vaghti
27 chunk dari in javab mide, vali:
  - baad az har taghir (chunk avaz she, model avaz she, TOP_K avaz she)
    bayad hameshun ro dobare cheshmi bebini
  - nemituni begi "behtar shod" ya "badtar shod" - faghat hes dari

Pas ye "golden set" minevisim: soal + chunk-i ke BAYAD peyda beshe.
Baad RECALL@K ro hesab mikonim.

RECALL@K CHIE
-------------
Az hame-ye chunk-haye dorost, chand darsadesh tuye K ta natije-ye
aval umad?

Mesal: soal-e "medical data" do ta javab-e dorost dare (AlzMRI-Net va
Research Assistant). Age faghat yekish tu top-3 biad:
    recall@3 = 1/2 = 0.50

CHERA RECALL, NA PRECISION?
---------------------------
To ye RAG pipeline, baad az retrieval ye LLM mishine ke chunk-haye
bi-rabt ro nadide begire. Pas chunk-e ezafi (precision-e paiin)
zarar-e kami dare - faghat token-e ezafi.

Vali chunk-e ja-mande (recall-e paiin) GHABEL-E JOBRAN NIST. Age
AlzMRI-Net be model narese, model az vojudesh khabar nadare va javab
ro natamam mide - ya badtar, az khodesh dar miare.

Pas baraye ma recall metric-e asli-e.

Estefade:
    python scripts/eval_retrieval.py
"""

import json
import os
import time
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .config import INDEX_PATH, EMBEDDING_MODEL, EMBEDDING_DIM

K_VALUES = [1, 3, 5, 8]


# GOLDEN SET
# ----------
# "expected" = onvan-e chunk-haii ke BAYAD peyda beshan.
# Inaro DASTI neveshtam - in kar-e to-st, na kar-e model. Age bezari
# model khodesh javab-haye dorost ro moshakhas kone, dari model ro ba
# khodesh test mikoni ke bi-mani-e.
GOLDEN_SET = [
    {
        "query": "how can I contact him?",
        "expected": ["Contact information"],
    },
    {
        "query": "where has he worked?",
        "expected": [
            "AI Engineer — Softlab S.p.A.",
            "Machine Learning Engineer — Fraud Detection, SnappBox",
        ],
    },
    {
        "query": "does he know Docker?",
        "expected": ["Cloud & Infrastructure"],
    },
    {
        "query": "what did he study?",
        "expected": ["University of Milan (UniMi)", "University of Guilan"],
    },
    {
        "query": "can he deploy models to production?",
        "expected": [
            "Machine Learning Engineer — Fraud Detection, SnappBox",
            "AI Engineer — Softlab S.p.A.",
        ],
    },
    {
        "query": "has he worked with medical data?",
        "expected": ["AlzMRI-Net", "Research Assistant — University of Guilan"],
    },
    {
        "query": "what LLM frameworks does he use?",
        "expected": ["LLM & GenAI"],
    },
    {
        "query": "tell me about his graph neural network work",
        "expected": ["Transaction Fraud Detection Using GNNs and Tabular Models"],
    },
    {
        "query": "has he built anything with agents?",
        "expected": ["Essay Agent"],
    },
    {
        "query": "does he speak Italian?",
        "expected": ["Languages"],
    },
    {
        "query": "what is his experience with computer vision?",
        "expected": ["PotholeSegmentation", "AlzMRI-Net"],
    },
    {
        "query": "where is he based?",
        "expected": ["Contact information"],
    },
]


def embed_query(client, text: str) -> np.ndarray:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return np.array(response.embeddings[0].values)


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY peyda nashod.")

    client = genai.Client(api_key=api_key)
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    chunks = index["chunks"]
    titles = [c["title"] for c in chunks]

    doc_matrix = np.array([c["embedding"] for c in chunks])
    doc_norms = doc_matrix / np.linalg.norm(doc_matrix, axis=1, keepdims=True)

    max_k = max(K_VALUES)
    recalls = {k: [] for k in K_VALUES}
    failures = []

    print(f"{len(GOLDEN_SET)} ta soal test mishe...\n")

    for case in GOLDEN_SET:
        query_vec = embed_query(client, case["query"])
        query_vec = query_vec / np.linalg.norm(query_vec)
        scores = doc_norms @ query_vec
        ranked = np.argsort(scores)[::-1][:max_k]
        ranked_titles = [titles[i] for i in ranked]

        expected = set(case["expected"])
        for k in K_VALUES:
            found = expected & set(ranked_titles[:k])
            recalls[k].append(len(found) / len(expected))

        # kodum expected-ha aslan tu top-max_k nayumadan?
        missed = expected - set(ranked_titles)
        if missed:
            failures.append((case["query"], sorted(missed), ranked_titles[:3]))

        time.sleep(0.3)  # free tier rate limit

    print("=" * 60)
    print("RECALL@K")
    print("=" * 60)
    for k in K_VALUES:
        avg = sum(recalls[k]) / len(recalls[k])
        bar = "█" * int(avg * 30)
        print(f"  recall@{k}: {avg:.1%}  {bar}")

    if failures:
        print()
        print("=" * 60)
        print(f"CHUNK-HAYE JA-MANDE (tu top-{max_k} ham nayumadan)")
        print("=" * 60)
        for query, missed, top3 in failures:
            print(f'\n  "{query}"')
            print(f"    ja mande: {missed}")
            print(f"    be jash umad: {top3}")
    else:
        print("\nHame-ye chunk-haye entezari tu top-{} umadan.".format(max_k))


if __name__ == "__main__":
    main()
