"""
search.py

Gam-e 2b: test mikonim ke retrieval vaghean kar mikone.

CHERA IN GAM RO NEMIPARIM
-------------------------
Vasvase-ye ziad hast ke mostaghim berim sar-e vasl kardan-e Gemini va
javab-e ghashang gereftan. Vali age retrieval kharab bashe, model
javab-e ghalat mide va TO NEMIFAHMI moshkel kojast - az model bud ya
az retrieval? Pas avval in laye ro jodagane test mikonim.

In hamun tarz-e fekre ke ye lead donbalesh migarde: har laye ro
jodagane bebin, na kolan az avval ta akhar.

CHERA NUMPY, NA FAISS/CHROMA?
-----------------------------
Vector database-ha (FAISS, Chroma, Pinecone) baraye sad-hezar ta
milion vector sakhte shodan. Unja nemishe hame ro yeki yeki check
kard, pas APPROXIMATE search mikonan - sari, vali 100% daghigh na.

Ma 26 ta vector darim. Hamashun ro ba numpy exact check kardan
zir-e ye milli-sanie tool mikeshe. Ezafe kardan-e FAISS injaa
faghat ye dependency-ye ezafi va pichidegi-ye bi-dalil-e.

Kay bayad avaz she? Vaghti chand-hezar chunk beshe (masalan age
chandin site ro pooshesh bedim). Un vaght migardim samt-e
pgvector ya Chroma.

Estefade:
    python scripts/search.py "kojahaii kar karde?"
"""

import json
import os
import sys
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .config import INDEX_PATH, EMBEDDING_MODEL, EMBEDDING_DIM, TOP_K


def cosine_similarity(query_vec: np.ndarray, doc_matrix: np.ndarray) -> np.ndarray:
    """
    COSINE SIMILARITY CHIE?
    -----------------------
    Do ta vector ro tasavor kon be onvan do ta fleche to faza.
    Cosine similarity zaviye-ye beynshun ro andaze migire:
      1.0  -> daghighan hamsu (mana-ye kheili nazdik)
      0.0  -> amudi (bi-rabt)
     -1.0  -> mokhalef

    Chera zaviye va na fasele? Chon TUL-e vector be andaze-ye matn
    bastegi dare, na be mana-sh. Ye paragraph-e boland va ye jomle-ye
    kutah ba hamun mana, tuleshun fargh dare vali zaviye-shun nazdike.
    """
    # normalize: har vector ro be tul-e 1 mibarim, ta faghat jahat bemune
    query_norm = query_vec / np.linalg.norm(query_vec)
    doc_norms = doc_matrix / np.linalg.norm(doc_matrix, axis=1, keepdims=True)
    # dot product-e do vector-e normalize-shode = cosine-e zaviye-shun
    return doc_norms @ query_norm


def main():
    if len(sys.argv) < 2:
        raise SystemExit('Estefade: python scripts/search.py "soale to"')

    query = " ".join(sys.argv[1:])

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY peyda nashod. .env ro check kon.")

    client = genai.Client(api_key=api_key)
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    chunks = index["chunks"]

    # soal-e user ro embed mikonim - daghat kon task_type injaa
    # RETRIEVAL_QUERY hast, na RETRIEVAL_DOCUMENT
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    query_vec = np.array(response.embeddings[0].values)

    doc_matrix = np.array([c["embedding"] for c in chunks])
    scores = cosine_similarity(query_vec, doc_matrix)

    # argsort soodi mide, pas bar-aks mikonim ta bishtarin aval biad
    top_indices = np.argsort(scores)[::-1][:TOP_K]

    print(f'\nSoal: "{query}"\n')
    print(f"Top {TOP_K} chunk:\n")
    for rank, idx in enumerate(top_indices, start=1):
        chunk = chunks[idx]
        print(f"{rank}. [{scores[idx]:.3f}] {chunk['section']} > {chunk['title']}")
        print(f"   {chunk['text'][:160]}...")
        print()


if __name__ == "__main__":
    main()
