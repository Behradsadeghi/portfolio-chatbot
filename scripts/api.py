"""
api.py

Gam-e 4: script-e command-line ro tabdil be ye service-e hamishe-roshan
mikonim.

CHERA FASTAPI
-------------
Site-e to ru GitHub Pages-e, ke faghat file-e static (HTML/CSS/JS)
serve mikone - nemitune Python run kone. Pas backend bayad ye ja-ye
digeh bashe, va widget az tarigh-e HTTP bahash harf bezane.

CHERA API KEY BAYAD SAMT-E SERVER BASHE
---------------------------------------
Vasvase hast ke JavaScript mostaghim Gemini ro seda bezane. Nakon:
har kasi ba View Source key-et ro mibine va quota-t ro khali mikone.
Key faghat inja mimune, samt-e server.

Run-e local:
    uvicorn scripts.api:app --reload
    curl -X POST localhost:8000/chat -H "Content-Type: application/json" \\
         -d '{"message": "does he know Docker?"}'
"""

import os
import time
from collections import defaultdict

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from .config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GENERATION_MODEL,
    TEMPERATURE,
    TOP_K,
)
from .rag import SYSTEM_PROMPT, build_context, load_index

load_dotenv()

# --- CORS ---------------------------------------------------------------
# Browser az default nemizare ye safhe be ye domain-e DIGE request bezane
# (Same-Origin Policy). Site-e ma ru github.io-e va API ye ja-ye digeh -
# pas bayad SARIH begim in domain ejaze dare.
#
# "*" nemizarim: un ya'ni har site-i tu donya mitune API-ye ma ro seda
# bezane va quota-ye ma ro masraf kone.
ALLOWED_ORIGINS = [
    "https://behradsadeghi.github.io",
    "http://localhost:8000",  # baraye test-e local
    "http://127.0.0.1:5500",  # VS Code Live Server
]

# --- Rate limit ---------------------------------------------------------
# In endpoint OMUMI-e va key-e SHAKHSI-ye to ro masraf mikone. Bedun-e
# rate limit, ye script-e sade mitune tu chand daghighe quota-ye rooz-et
# ro besuzune.
#
# In pia'de-sazi tuye HAFEZE-st: age server restart she paak mishe, va
# age chand instance dashte bashi har kodum shomarande-ye khodesh ro
# dare. Baraye traffic-e in site kafie. (Baraye jeddi-tar: Redis.)
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # sanie
_request_log: dict[str, list[float]] = defaultdict(list)


class ChatRequest(BaseModel):
    # max_length ye guardrail-e sade-st: jelo-ye prompt-e 100 hezar
    # kalame-i ro migire ke faghat token misuzune.
    message: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]


app = FastAPI(title="Portfolio Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# CHERA INJA VA NA DAKHEL-E ENDPOINT
# ----------------------------------
# In do khat vaght-e balaa amadan-e server ye bar ejra mishan. Age
# dakhel-e endpoint bud, HAR request bayad 400KB JSON ro parse mikard
# va normalize mikard - sad barabar kondtar bi-hich dalili.
_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_chunks, _matrix = load_index()


def check_rate_limit(ip: str) -> None:
    now = time.time()
    recent = [t for t in _request_log[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(recent) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment.",
        )
    recent.append(now)
    _request_log[ip] = recent


@app.get("/health")
def health():
    """Host-ha in ro seda mizanan ta bebinan service zende-st."""
    return {"status": "ok", "chunks": len(_chunks)}


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request):
    check_rate_limit(request.client.host if request.client else "unknown")

    try:
        embed_response = _client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=body.message,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=EMBEDDING_DIM,
            ),
        )
        query_vec = np.array(embed_response.embeddings[0].values)
        query_vec = query_vec / np.linalg.norm(query_vec)

        scores = _matrix @ query_vec
        top = np.argsort(scores)[::-1][:TOP_K]
        retrieved = [(_chunks[i], float(scores[i])) for i in top]

        context = build_context(retrieved)
        user_message = (
            f"Context passages:\n\n{context}\n\n"
            f"Visitor's question: {body.message}"
        )

        response = _client.models.generate_content(
            model=GENERATION_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=TEMPERATURE,
            ),
        )

        return ChatResponse(
            answer=response.text,
            sources=[
                {
                    "n": i,
                    "title": chunk["title"],
                    "section": chunk["section"],
                    "url": chunk.get("url"),
                }
                for i, (chunk, _) in enumerate(retrieved, start=1)
            ],
        )

    except Exception as exc:
        # CHERA PAYAM-E VAGHEI RO BE USER NEMIDIM
        # ---------------------------------------
        # Error-e dakheli momkene shamel-e etela'at-e hassas bashe
        # (masir-e file, bakhshi az key, sakhtar-e system). Be user ye
        # payam-e omumi midim, va asl-e error ro log mikonim.
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong. Please try again.",
        )
