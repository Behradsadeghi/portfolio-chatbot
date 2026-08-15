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
from collections import defaultdict, deque

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
# DO LAYE, chon har kodum ye chiz-e motefavet ro migire:
#
#   1. PER-IP  -> jelo-ye ye nafar ke spam mikone
#   2. GLOBAL  -> jelo-ye ye nafar ke ba 100 ta proxy miad. Per-IP unja
#                 hich kar nemikone, chon har IP "mojaz"-e. Saghf-e koli
#                 tanha chiz-i-e ke jeloshe migire.
#
# Hardud eftetahi-e; ba tavajoh be traffic-e vaghei tanzim mishe.
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # sanie
GLOBAL_LIMIT_REQUESTS = 200
GLOBAL_LIMIT_WINDOW = 3600  # sanie (ye saat)

_request_log: dict[str, list[float]] = defaultdict(list)
_global_log: deque[float] = deque()

# CHERA IN PAAKSAZI LAZEM-E
# -------------------------
# _request_log har IP-ye jadid ro negah midare va khodesh HICH VAGHT
# paak nemikone. Rooye ye instance-e 512MB, ye attack-e IP-rotation
# mitune RAM ro por kone - ya'ni hamun "service ro biar paiin" ke rate
# limit gharar bud jeloshe ro begire.
#
# Pas har chand vaght yek bar IP-haye ghadimi ro mindazim dur.
_last_cleanup = time.time()
CLEANUP_INTERVAL = 300  # sanie


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


def client_ip(request: Request) -> str:
    """
    IP-YE VAGHEI, NA IP-YE PROXY
    ----------------------------
    request.client.host IP-ye kasi ro mide ke MOSTAGHIM be app vasl
    shode. Rooye Render (va aksar-e host-ha) app posht-e ye proxy-e,
    pas un meghdar hamishe IP-ye proxy-e - na bazdid-konande.

    Natije: rate limit ya hame ro yek nafar hesab mikone (do nafar-e
    bi-gonah hamzaman -> dovomi 429 mikhore), ya aslan shelik nemikone.

    IP-ye vaghei tuye X-Forwarded-For hast. Format-esh:
        client, proxy1, proxy2
    Avvalin meghdar client-e.

    DAGHAT: in header ro har kasi mitune ja bezane. Injaa ghabul-esh
    mikonim chon Render khodesh un ro set mikone va nemishe az birun
    override kard. Age rooze-i host avaz she, in farz bayad dobare
    check beshe.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def cleanup_old_entries(now: float) -> None:
    """IP-haye ghadimi ro dur mindaze ta _request_log bi-nahayat roshd nakone."""
    global _last_cleanup
    if now - _last_cleanup < CLEANUP_INTERVAL:
        return
    stale = [
        ip
        for ip, times in _request_log.items()
        if not times or now - times[-1] > RATE_LIMIT_WINDOW
    ]
    for ip in stale:
        del _request_log[ip]
    _last_cleanup = now


def check_rate_limit(ip: str) -> None:
    now = time.time()
    cleanup_old_entries(now)

    # laye-ye 2: saghf-e koli
    while _global_log and now - _global_log[0] > GLOBAL_LIMIT_WINDOW:
        _global_log.popleft()
    if len(_global_log) >= GLOBAL_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="The assistant is busy right now. Please try again later.",
        )

    # laye-ye 1: per-IP
    recent = [t for t in _request_log[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(recent) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment.",
        )

    recent.append(now)
    _request_log[ip] = recent
    _global_log.append(now)


@app.get("/")
def root():
    """
    Bedun-e in, http://localhost:8000 ye 404-e khoshk mide va adam fekr
    mikone server balaa nayumade. In ye "index"-e kuchik-e ke migeh
    service zende-st va che route-haii dare.
    """
    return {
        "service": "Portfolio Chatbot API",
        "endpoints": {
            "GET /health": "liveness check",
            "POST /chat": 'body: {"message": "your question"}',
        },
    }


@app.get("/health")
def health():
    """Host-ha in ro seda mizanan ta bebinan service zende-st."""
    return {
        "status": "ok",
        "chunks": len(_chunks),
        "tracked_ips": len(_request_log),
        "requests_this_hour": len(_global_log),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request):
    check_rate_limit(client_ip(request))

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
