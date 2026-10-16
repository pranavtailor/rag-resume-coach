# RAG Résumé Coach

Upload your résumé and a job posting — get a **retrieval-grounded gap analysis**:
a match score, the keywords you're missing, the gaps that matter, and
before/after rewrites for your weakest bullets.

Built as a portfolio project to demonstrate **GenAI/RAG engineering**:
local embeddings, vector retrieval, and a provider-abstracted LLM layer with a
fully offline demo mode.

## Architecture

```
┌──────────────┐      ┌──────────────────────────────────────────────┐
│   React +    │      │                  FastAPI                      │
│   Vite + TS  │      │                                               │
│              │      │  POST /api/resume ──► parsing.py              │
│  1. Upload   │─────►│    (PDF/DOCX/TXT → clean text)               │
│     résumé   │      │                                               │
│              │      │  POST /api/analyze ─► rag/pipeline.py         │
│  2. Paste    │─────►│    1. chunk_text() → overlapping word windows │
│     job post │      │    2. embed() → local sentence-transformers   │
│              │      │    3. upsert → ChromaDB (per-request collection)│
│  3. View     │◄─────│    4. query: job chunks → top résumé chunks   │
│     results  │      │    5. llm provider → structured JSON analysis │
└──────────────┘      │                                               │
                      │  llm/base.py ──► LLMProvider (Protocol)       │
                      │     ├── openai_provider.py (OPENAI_API_KEY)   │
                      │     └── stub.py (heuristic, offline demo)     │
                      └──────────────────────────────────────────────┘
```

**The RAG loop, concretely:** both documents are chunked and embedded with a
local model (`all-MiniLM-L6-v2`), indexed in a short-lived ChromaDB collection,
and each job-posting chunk retrieves the most similar résumé chunks. Those
retrieved passages ("evidence") ground the analysis — the LLM (or the
heuristic stub in demo mode) reasons over the *retrieved* résumé passages
rather than the whole document, which keeps long résumés focused and makes the
evidence inspectable in the UI.

**Graceful degradation:** every heavy dependency is optional at runtime.
- `sentence-transformers` missing → deterministic hashing embedder
- `chromadb` missing → in-memory cosine-similarity store
- `OPENAI_API_KEY` missing → heuristic stub provider (UI labels it "demo mode")

So `pip install` the small deps and the demo runs anywhere; add the ML
packages and an API key for the full experience.

## Project structure

```
rag-resume-coach/
├── README.md
├── .env.example
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py            # FastAPI app: /api/health, /api/resume, /api/analyze
│       ├── schemas.py         # Pydantic request/response models
│       ├── parsing.py         # PDF/DOCX/TXT text extraction
│       ├── rag/
│       │   ├── chunking.py    # Overlapping word-window chunker
│       │   ├── embeddings.py  # sentence-transformers + hashing fallback
│       │   ├── store.py       # ChromaDB + in-memory fallback
│       │   └── pipeline.py    # Orchestrates chunk → embed → retrieve → analyze
│       └── llm/
│           ├── base.py            # LLMProvider protocol + LLMError
│           ├── openai_provider.py # OpenAI-compatible (key from env)
│           ├── stub.py            # Heuristic offline demo provider
│           └── factory.py         # Picks provider from environment
└── frontend/
    ├── package.json / vite.config.ts / tsconfig.json / index.html
    └── src/
        ├── main.tsx / App.tsx     # 3-step flow: upload → job post → results
        ├── api.ts / types.ts
        ├── styles.css
        └── components/
            ├── ResumeUpload.tsx   # Drag & drop + editable extracted text
            ├── JobPostingInput.tsx
            └── ResultsView.tsx    # Score ring, keyword chips, gaps, rewrites
```

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate

# Minimal install (demo mode — no torch, runs fully offline):
pip install fastapi "uvicorn[standard]" pydantic python-multipart \
    python-dotenv httpx numpy pypdf python-docx openai

# Full install (local embeddings + vector DB):
pip install -r requirements.txt

# Optional: enable the real LLM provider
cp ../.env.example ../.env   # then set OPENAI_API_KEY

uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs · health: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxies /api → :8000)
```

## How the RAG pipeline works

1. **Parse** — `parsing.py` extracts clean text from the uploaded PDF/DOCX/TXT.
2. **Chunk** — overlapping 120-word windows keep each chunk self-contained.
3. **Embed** — every chunk becomes a 384-dim vector, locally
   (`all-MiniLM-L6-v2`, L2-normalized).
4. **Index** — chunks go into a fresh ChromaDB collection per request, tagged
   with `source: resume | job`, then deleted after the analysis.
5. **Retrieve** — each job chunk queries for the most similar *résumé* chunks;
   the top hits are the evidence grounding the analysis.
6. **Analyze** — the provider receives résumé + job posting + evidence and
   returns structured JSON: `match_score`, `missing_keywords`, `gaps`,
   `bullet_rewrites`. The OpenAI provider enforces the schema with
   `response_format: json_object`; the stub computes the same shape
   heuristically (keyword overlap, skill-lexicon gaps, template rewrites).

## Roadmap ideas

- [ ] Persist analyses (SQLite) + history view
- [ ] Multi-job comparison: rank several postings against one résumé
- [ ] Hybrid retrieval (BM25 + vector) and reranking
- [ ] Export the tailored résumé as DOCX
- [ ] Auth + per-user document libraries
- [ ] Eval harness: score rewrite quality against human-rated examples

## Tech stack

Python · FastAPI · Pydantic · sentence-transformers · ChromaDB · OpenAI API ·
React · TypeScript · Vite
