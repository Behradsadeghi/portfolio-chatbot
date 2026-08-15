"""
answer.py

Gam-e 3: az chunk-haye retrieve-shode ye javab-e vaghei misazim.

TA HALA CHI DASHTIM
-------------------
Ye search engine: soal mikhord tu, chunk miumad birun. Hich kas javab
nemidad. Hala LLM ro vasl mikonim.

SE TASMIM-E ASLI-YE IN FILE
---------------------------
1. GROUNDING - model faghat az chunk-ha javab bede, na az danesh-e
   khodesh. Chera mohem-e: Gemini az ghabl kheili chiz-ha dar morede
   "AI engineer" mikhune. Age azash beporsi "che skill-haii dare?"
   mitune ye javab-e ghashang-e KOLI bede ke rabti be Behrad nadare.
   In hamun hallucination-e - va to ye chatbot-e resume, khatarnak-e:
   ye recruiter momkene ru chizi hesab kone ke to nagofti.

2. CITATION - model bayad bege har jomle az kodum chunk umad. Do
   fayede: (a) user mitune check kone, (b) MA mitunim moshkel ro
   debug konim - age javab ghalat bud, mifahmim chunk-e ghalat umad
   ya model chunk-e dorost ro bad khund.

3. REFUSAL - age javab tu chunk-ha nabud, model bayad BEGE ke nemidune.
   In sakht-tarin bakhsh-e: model-ha az default mikhan komak konan,
   pas tamayol daran chizi az khodeshun besazan. Bayad sarih bekhaym
   ke naكone.

Estefade:
    python -m scripts.answer "does he know Docker?"
    python -m scripts.answer --k 3 "does he know Docker?"

CHERA --k
---------
k ye HYPERPARAMETER-e, na ye adad-e sabet. k-e kamtar = token-e kamtar,
latency-e paiin-tar, va hovas-parti-ye kamtar baraye model. k-e bishtar
= recall-e balatar.

Kodum behtare? Nemishe az ru-ye teori goft - bayad har do ro rooye
hamun soal-ha bebini va javab-ha ro moghayese koni. In flag baraye
hamun-e.
"""

import json
import os
import sys
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .rag import SYSTEM_PROMPT, build_context, load_index
from .config import (
    INDEX_PATH,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    TOP_K,
    GENERATION_MODEL,
    TEMPERATURE,
)


def main():
    args = sys.argv[1:]

    # --k <adad> ro az argument-ha dar miarim (age nabashe, TOP_K-e bala)
    k = TOP_K
    if "--k" in args:
        i = args.index("--k")
        k = int(args[i + 1])
        args = args[:i] + args[i + 2:]

    if not args:
        raise SystemExit('Estefade: python -m scripts.answer [--k N] "soale to"')

    query = " ".join(args)

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY peyda nashod.")

    client = genai.Client(api_key=api_key)
    chunks, matrix = load_index()

    retrieved = retrieve(client, chunks, matrix, query, k)
    context = build_context(retrieved)

    user_message = f"""Context passages:

{context}

Visitor's question: {query}"""

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            # TEMPERATURE = 0
            # ----------------
            # Temperature meghdar-e tasadof-e model ro kontrol mikone.
            # Baraye neveshtan-e she'r, bala khub-e. Baraye javab dadan
            # az ru-ye sanad, ma DAGHIGHAN aks-esh ro mikhaym: hamishe
            # hamun javab az hamun context. Ham ghabel-e etminan-tar,
            # ham eval-e ma ma'ni peyda mikone (age har bar javab avaz
            # she, nemituni begi behtar shod ya na).
            temperature=TEMPERATURE,
        ),
    )

    print(f'\nSoal: "{query}"   (k={k})\n')
    print("-" * 60)
    print(response.text)
    print("-" * 60)
    print("\nChunk-haii ke dade shod:")
    for i, (chunk, score) in enumerate(retrieved, start=1):
        print(f"  [{i}] {score:.3f}  {chunk['section']} > {chunk['title']}")


if __name__ == "__main__":
    main()
