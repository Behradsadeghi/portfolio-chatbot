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
    FALLBACK_MODEL,
    GENERATION_MODEL,
    REWRITE_MODEL,
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
# Chand turn-e akhar be model dade beshe. Bishtar = context-e behtar
# vali token-e bishtar; kamtar = arzun-tar vali follow-up ha mishkanan.
# 6 ya'ni 3 ta rad-o-badl - baraye chatbot-e ye site kafie.
MAX_HISTORY_TURNS = 6

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


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    text: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    # max_length ye guardrail-e sade-st: jelo-ye prompt-e 100 hezar
    # kalame-i ro migire ke faghat token misuzune.
    message: str = Field(min_length=1, max_length=500)

    # CHERA HISTORY LAZEM SHOD
    # ------------------------
    # Ta hala har request mostaghel bud. Vali ta vaghti UI neshun mide
    # goftogu edame dare, user follow-up miporse: "un dovomi chi bud?"
    # Bedun-e tariche, model nemidune "dovomi" chie va javab-e bi-rabt
    # mide - va bazdid-konande fekr mikone bot ahmagh-e, na inke
    # feature nadare.
    #
    # Server tariche ro NEGAH NEMIDARE. Client har bar mifreste. In
    # ya'ni server stateless mimune (chand instance, restart, hich
    # kodum moshkeli nist) va ma hich chat-i ro zakhire nemikonim.
    history: list[Turn] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS)


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


def is_quota_error(exc: Exception) -> bool:
    """
    CHERA MATNI VA NA BA TYPE-E EXCEPTION
    -------------------------------------
    SDK hame-ye khataye 4xx ro be onvan ye ClientError mide - 429-e
    quota ba 400-e bad request yek type daran. Pas bayad be mohtava
    negah konim.

    In shekannde-st (age Google matn ro avaz kone, mishkane) - vali
    natije-ye shekastan-esh faghat ine ke fallback nemizanad va
    error-e adi bar migarde. Fail-safe.
    """
    text = str(exc)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def generate_with_fallback(contents, config):
    """
    Aval model-e asli, va age quota-sh tamum shod, model-e fallback.

    CHERA IN KAR MIKONE
    -------------------
    Quota-ye free tier BE EZAYE HAR MODEL hesab mishe. Pas vaghti
    gemini-2.5-flash tamum mishe, gemini-2.5-flash-lite hanuz budget-e
    DAST-NAKHORDE-ye khodesh ro dare. Fallback ya'ni do barabar zarfiat,
    na tekrar-e hamun.

    Faghat rooye khataye QUOTA fallback mizanim. Age prompt-e ma kharab
    bashe (400) ya key eshtebah bashe (403), model-e digeh ham hamun
    khata ro mide - retry faghat vaght va budget talaf mikone.
    """
    try:
        return _client.models.generate_content(
            model=GENERATION_MODEL, contents=contents, config=config
        )
    except Exception as exc:
        if not is_quota_error(exc):
            raise
        print(f"[fallback] {GENERATION_MODEL} quota hit -> {FALLBACK_MODEL}")
        return _client.models.generate_content(
            model=FALLBACK_MODEL, contents=contents, config=config
        )


REWRITE_PROMPT = """You rewrite a follow-up question into a standalone search \
query, using the conversation that came before it.

Output only the rewritten query. No explanation, no quotes.

If the question is already self-contained, output it unchanged.

Conversation:
{history}

Follow-up question: {question}

Standalone search query:"""


def rewrite_query(message: str, history: list[Turn]) -> str:
    """
    CHERA IN LAZEM SHOD
    -------------------
    Tariche faghat be marhale-ye GENERATION mirasid, na RETRIEVAL. Ya'ni
    vaghti user minevise "from when", ma hamun do kalame ro embed
    mikardim. "from when" hich mohtava-ye ma'naii nadare - vector-esh be
    hich chunk-e khasi nazdik nist, pas 8 ta chunk-e bi-rabt barmigasht.

    Natije: model migoft "I don't have that information" - dar hali ke
    chunk-e Softlab daghighan "(May 2026 - Present)" ro dasht. Model
    eshtebah nemikard; chizi ke lazem dasht behesh NEMIRESID.

    Pas ghabl az retrieval, soal ro mostaghel mikonim:
        "from when"  ->  "When did Behrad start working at Softlab?"

    HAZINE: ye API call-e ezafi, VALI faghat vaghti tariche vojud dare.
    Soal-e aval - ke aksar-e session-ha faghat hamun-e - dast nakhorde
    mimune.

    Age rewrite fail she, be soal-e asli barmigardim. Ye laye-ye komaki
    nabayad kol-e endpoint ro bendaze.
    """
    if not history:
        return message

    transcript = "\n".join(
        f"{'Visitor' if t.role == 'user' else 'Assistant'}: {t.text}"
        for t in history[-MAX_HISTORY_TURNS:]
    )

    try:
        response = _client.models.generate_content(
            model=REWRITE_MODEL,
            contents=REWRITE_PROMPT.format(history=transcript, question=message),
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=128,
                # THINKING RO KHAMUSH MIKONIM
                # ---------------------------
                # Model-haye 2.5 ghabl az javab token kharj-e "fekr kardan"
                # mikonan. Ba saghf-e 64 token, thinking hame-ye budget ro
                # khord va rewrite NESFE birun umad:
                #     'from when' -> 'When did'
                # Un ham az soal-e asli badtar bud.
                #
                # Rewrite estedlal nemikhad - jaygozini-ye zamir ba esm-e.
                # Pas thinking khamush, saghf balatar.
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        rewritten = (response.text or "").strip()
    except Exception as exc:
        print(f"[rewrite failed] {type(exc).__name__}: {exc}")
        return message

    # Guardrail: age khoruji khali ya bi-ma'ni bud, asl ro negah midarim.
    if not rewritten or len(rewritten) > 300:
        return message

    print(f"[rewrite] {message!r} -> {rewritten!r}")
    return rewritten


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
        # Ba tariche, soal-e kootah ro be ye soal-e MOSTAGHEL tabdil
        # mikonim ghabl az retrieval. (Tozih-e kamel tuye rewrite_query.)
        search_query = rewrite_query(body.message, body.history)

        embed_response = _client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=search_query,
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

        # CHERA CONTEXT HAR BAR DOBARE FERESTADE MISHE
        # -------------------------------------------
        # Retrieval baraye HAR soal jodagane ejra mishe, pas chunk-haye
        # marbut be soal-e feli miad - na un-haii ke 3 soal ghabl lazem
        # budan. Tariche faghat baraye fahmidan-e ejara'at ("un dovomi",
        # "chera?") be kar mire, na be onvan-e manba'-e vaghayeh.
        contents = []
        for turn in body.history[-MAX_HISTORY_TURNS:]:
            contents.append(
                types.Content(
                    role="user" if turn.role == "user" else "model",
                    parts=[types.Part(text=turn.text)],
                )
            )
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            f"Context passages:\n\n{context}\n\n"
                            f"Visitor's question: {body.message}"
                        )
                    )
                ],
            )
        )

        response = generate_with_fallback(
            contents,
            types.GenerateContentConfig(
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

    except HTTPException:
        raise
    except Exception as exc:
        # CHERA PAYAM-E VAGHEI RO BE USER NEMIDIM
        # ---------------------------------------
        # Error-e dakheli momkene shamel-e etela'at-e hassas bashe
        # (masir-e file, bakhshi az key, sakhtar-e system). Be user ye
        # payam-e omumi midim, va asl-e error ro log mikonim.
        print(f"[ERROR] {type(exc).__name__}: {exc}")

        # QUOTA-YE UPSTREAM RO JODA MIKONIM
        # ---------------------------------
        # Vaghti quota-ye rooz-e Gemini tamum mishe, in ye khataye ma
        # nist - ye mahdudiyat-e movaghat-e. "Something went wrong" be
        # user mige barnamash kharab-e, dar hali ke faghat bayad farda
        # biad. Va MA ham vaghti log ro mibinim donbal-e bug migardim
        # ke vojud nadare.
        # Injaa residan ya'ni HAR DO model quota-shun tamum shode.
        if is_quota_error(exc):
            raise HTTPException(
                status_code=503,
                detail="The assistant has hit its daily limit. Please try again tomorrow.",
            )

        raise HTTPException(
            status_code=500,
            detail="Something went wrong. Please try again.",
        )
