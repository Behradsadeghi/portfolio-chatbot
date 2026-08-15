# Portfolio Chatbot

A retrieval-augmented chat widget for [behradsadeghi.github.io](https://behradsadeghi.github.io).
Visitors ask questions about my background; the assistant answers from the
site's own content and says "I don't know" when the answer isn't there.

**Live:** ask a question in the bar at the bottom of the site.

## How it works

```
index.html → extract → chunk → embed → index.json               (build time)
                                          ↓
question (+ recent turns) → embed → cosine → top-8 → Gemini → answer + sources
```

Two repositories: this one holds the backend and the widget source; the static
site holds a copy of the widget and one `<script>` tag. GitHub Pages serves
files only — it cannot run Python — so the retrieval service lives elsewhere
and the page talks to it over HTTP.

The browser never sees the API key. It stays on the server, along with the
index.

## Design decisions

**No vector database.** 26 chunks fits in a NumPy array. FAISS and Chroma do
*approximate* search because exact search is infeasible at scale — at this
scale exact search takes under a millisecond. The threshold to revisit is a
few thousand chunks.

**Structural chunking, not fixed-size.** Character-based chunking with overlap
exists to handle continuous prose with no natural boundaries. This site has
boundaries: each job, project, and skill category is one semantic unit. Fixed
windows would merge the end of one job with the start of the next.

**Build-time indexing.** Embeddings are computed once and committed. The
server loads a JSON file at startup instead of making 26 API calls on every
restart.

**Temperature 0.** Not for determinism's own sake — without it, evaluation is
meaningless. You can't tell whether a change improved the system if the same
input produces different output each run.

**Stateless server, client-held history.** The widget shows past conversations
and a "Continue conversation" prompt, but nothing is stored server-side. The
client replays the last few turns with each request. Two reasons: a portfolio
site has no business retaining visitors' chat logs, and a stateless service
survives restarts and horizontal scaling without a session store.

Follow-ups drove this. Once the UI implies continuity, someone asks "what about
the second one?" — and a server with no history answers something unrelated,
which reads as a broken bot rather than a missing feature.

**Query rewriting before retrieval.** Passing history to the generation step
alone was not enough, and the failure was instructive. Asked "from when?" after
a question about the current role, the assistant replied that it didn't have
that information — while the retrieved passage plainly read
`(May 2026 - Present)`. The model was not the problem. Retrieval was embedding
the literal string "from when", which carries no semantic content and matches
nothing, so the relevant chunk never reached the model at all.

Follow-ups are now rewritten into standalone queries before embedding —
"from when?" becomes "When did Behrad start working at Softlab?" — at the cost
of one extra call, and only when history exists. First questions, which are most
sessions, are untouched. If the rewrite fails the original question is used;
a helper step should not be able to take down the endpoint.

**Measured, not assumed.** A 12-question golden set with hand-labelled
expected chunks, scored by recall@k.

**Recall over precision.** Extra retrieved chunks cost tokens; the model
ignores them. A *missing* chunk is unrecoverable — the model can't cite what it
never received. So `k=8`, and the model does the filtering.

## Experiments

| Change | Result | Kept? |
|---|---|---|
| Reword project copy to match question vocabulary | recall@3 87.5% → 95.8%, recall@8 → 100% | Yes |
| Split multi-bullet job entries into separate chunks | recall@3 95.8% → 87.5% | Reverted |
| Embedding dimension 768 → 3072 | recall@1 75.0% → 70.8% | Reverted |
| Cross-encoder reranker | Not attempted — see below | No |

The failures that mattered most turned out to be a *content* problem, not a
model problem. A project described as using "EfficientNet" did not surface for
"computer vision"; one describing "Gemini structured outputs" did not surface
for "LLM". No embedding model retrieves a concept the text never states.

Splitting long entries into focused chunks backfired: each fragment carried the
same job title as a prefix, so sibling chunks clustered and occupied multiple
top-k slots, crowding out other results. Focus alone isn't enough — diversity
matters too.

A reranker was the obvious next lever and was deliberately skipped. Reranking
fixes *ordering* within the retrieved set, but recall@8 was already 100% — the
right chunks were reaching the model. The cost would have been `torch` and
`sentence-transformers`, roughly 2 GB of dependencies, on a 512 MB instance.
Worth revisiting if `k` ever needs to shrink for latency.

## Serving

The endpoint is public and spends a personal API quota, so abuse costs real
money and real availability.

**Rate limiting, two layers.** Per-IP (10/min) stops one person spamming. A
global cap (200/hr) stops one person rotating through proxies — against IP
rotation the per-IP limit does nothing, because every address looks fresh. The
global cap is the only thing standing there.

**Real client IPs.** Behind a proxy, `request.client.host` is the *proxy's*
address. Left alone, every visitor collapses into one bucket and the limiter
either throttles innocent users or never fires at all. The client IP is read
from `X-Forwarded-For` instead. That header is spoofable in general; it is
trusted here only because the platform sets it and clients cannot override it —
an assumption to recheck if the host ever changes, and one reason the global
cap exists as a backstop that trusts nothing.

**Bounded memory.** The per-IP table is swept periodically. Without that, IP
rotation grows it without limit on a 512 MB instance — the denial of service
the rate limiter was supposed to prevent.

**Input validation at the edge.** Message length is capped, conversation
history is capped in both turn count and per-turn length, and history roles are
constrained by regex to `user` or `assistant`. That last one matters: without
it, a crafted `system` turn would be a channel for injecting instructions
through what looks like ordinary chat history.

**CORS pinned to the site's origin**, not `*`, so the endpoint isn't a free
Gemini proxy for anyone who finds the URL.

**Errors are generic to the client** and detailed in the logs. Internal
exceptions leak paths, configuration, and sometimes fragments of secrets.

**Model output is rendered as text, never HTML.** `textContent`, not
`innerHTML`. Answers are grounded in site content, but treating any model output
as markup is the classic XSS path, and grounding is not a security boundary.

**Client-side storage is fail-open.** `localStorage` can be disabled or full;
the widget degrades to working without history rather than throwing.

Citation markers are stripped before display. The model still emits them: they
force each claim to be attributed, they identify which of the 8 chunks were
actually used, and they make wrong answers traceable to a chunk. But `[3]`
points at a passage the visitor never sees, so it renders as a source list
instead — the data is kept, only the display is cleaned.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your Gemini API key

python -m scripts.extract_chunks    # index.html  → chunks.json
python -m scripts.embed_chunks      # chunks.json → index.json
python -m scripts.eval_retrieval    # recall@k against the golden set
python -m scripts.answer "does he know Docker?"

uvicorn scripts.api:app --reload    # serve the API locally
```

`scripts/list_models.py` lists the model names the API key can currently reach.
Model IDs get deprecated — `text-embedding-004` was removed in January 2026 —
so it's worth asking the API rather than trusting a constant.

Content changes require rerunning the full chain: `extract → embed → eval`.
The index is a build artifact of `index.html`, and stale embeddings answer
questions about a site that no longer exists.

## Stack

Python · FastAPI · Pydantic · NumPy · Gemini API (`gemini-embedding-001`,
`gemini-2.5-flash`) · vanilla JS, no build step · deployed on Render
