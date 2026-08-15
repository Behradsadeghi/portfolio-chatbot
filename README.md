# Portfolio Chatbot

A retrieval-augmented chat widget for [behradsadeghi.github.io](https://behradsadeghi.github.io).
Visitors ask questions about my background; the assistant answers from the
site's own content, with citations, and says "I don't know" when the answer
isn't there.

## How it works

```
index.html → extract → chunk → embed → index.json
                                          ↓
question → embed → cosine similarity → top-k → Gemini → answer + citations
```

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

**Measured, not assumed.** A 12-question golden set with hand-labelled
expected chunks, scored by recall@k.

## Experiments

| Change | Result | Kept? |
|---|---|---|
| Reword project copy to match question vocabulary | recall@3 87.5% → 95.8%, recall@8 → 100% | Yes |
| Split multi-bullet job entries into separate chunks | recall@3 95.8% → 87.5% | Reverted |
| Embedding dimension 768 → 3072 | recall@1 75.0% → 70.8% | Reverted |

The retrieval failures that mattered most turned out to be a *content*
problem, not a model problem. A project described as using "EfficientNet"
did not surface for "computer vision"; one describing "Gemini structured
outputs" did not surface for "LLM". No embedding model can retrieve a concept
the text never states.

Splitting long entries into focused chunks backfired: each fragment carried
the same job title as a prefix, so sibling chunks clustered together and
occupied multiple top-k slots, crowding out other results. Focus alone isn't
enough — diversity matters too.

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

## Deployment

The backend runs on Render (free tier); the widget is a single vanilla-JS file
loaded by the static site. The API key stays server-side — the browser never
sees it. The endpoint is public, so it is rate-limited per IP and CORS is
restricted to the site's origin.

## Stack

Python · FastAPI · NumPy · Gemini API (`gemini-embedding-001`, `gemini-2.5-flash`)
