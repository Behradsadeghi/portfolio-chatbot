"""
embed_chunks.py

Gam-e 2: har chunk ro be ye vector tabdil mikonim va zakhire mikonim.

CHERA IN KAR RO MIKONIM
-----------------------
User momkene beporse "kojahaii kar karde?" - vali in kalamat aslan
tuye site-e ma nist (site neveshte "Work Experience"). Search-e
keyword-based injaa fail mishe.

Embedding jomle ro be ye vector-e adad tabdil mikone ke MANA-sh ro
neshun mide, na kalamatesh ro. Do jomle ba mana-ye shabih, vector-e
nazdik daran - pas mitunim "kojahaii kar karde?" ro be chunk-e
"Work Experience" vasl konim.

CHERA JODA AZ RUNTIME EJRA MISHE
---------------------------------
In script ro faghat vaghti mizani ke mohtava-ye site avaz beshe.
Natije (index.json) ro save mikonim, va backend vaght-e balaa
amadan faghat un file ro mikhune. Yani:
  - backend sari balaa miad (embedding-e mojaddad nemizane)
  - hazine-ye API kamtar mishe (26 ta call, na har bar restart)
In elgu esmesh "build-time indexing" hast.
"""

import json
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- config ---------------------------------------------------------------

from .config import CHUNKS_PATH, INDEX_PATH, EMBEDDING_MODEL, EMBEDDING_DIM


def embed_texts(client: genai.Client, texts: list[str], task_type: str) -> list[list[float]]:
    """
    Ye list az mataan ro be list-e vector tabdil mikone.

    task_type CHIE?
    ---------------
    Gemini mituna bedune ke in mataan "sanad" hast ya "soal"-e user.
    Chon in do ta naghsh-e motefavet daran, model vector-e kami
    motefavet misaze ke match behtar bashe:
      - RETRIEVAL_DOCUMENT  -> baraye chunk-haye site (in file)
      - RETRIEVAL_QUERY     -> baraye soal-e user (moghe-ye search)
    Age har do ro yeksan bezani, keyfiyat-e retrieval oft mikone.
    """
    vectors = []
    for i, text in enumerate(texts, start=1):
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIM,
            ),
        )
        vectors.append(response.embeddings[0].values)
        print(f"  embedded {i}/{len(texts)}")
        # free tier rate limit dare - ye maks-e kutah mizanim ke 429 nakhorim
        time.sleep(0.3)
    return vectors


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY peyda nashod.\n"
            "Faile .env.example ro be .env copy kon va key-et ro tush bezar."
        )

    client = genai.Client(api_key=api_key)

    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    print(f"{len(chunks)} chunk load shod. Embedding shoru mishe...\n")

    # CHERA title + text ba ham?
    # ---------------------------
    # matn-e khali-ye ye chunk gahi context nadare. masalan chunk-e
    # skills faghat mige "PyTorch, Scikit-learn, ..." - bedun-e onvan
    # "Machine Learning" mana-sh kamtar roshan-e. onvan ro behesh
    # michasbunim ta vector-e ghani-tari besaze.
    texts = [f"{c['title']}\n{c['text']}" for c in chunks]

    vectors = embed_texts(client, texts, task_type="RETRIEVAL_DOCUMENT")

    index = {
        "model": EMBEDDING_MODEL,
        "dimension": len(vectors[0]),
        "chunks": [
            {**chunk, "embedding": vector}
            for chunk, vector in zip(chunks, vectors)
        ],
    }

    INDEX_PATH.write_text(json.dumps(index), encoding="utf-8")
    size_kb = INDEX_PATH.stat().st_size / 1024
    print(f"\nIndex sakhte shod -> {INDEX_PATH} ({size_kb:.0f} KB)")
    print(f"Dimension-e har vector: {index['dimension']}")


if __name__ == "__main__":
    main()
