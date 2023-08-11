# Fathom

Fathom is a plain-English research desk for Aurora Mobility Inc. (ticker AURM), an EV charging company. You ask a question the way you’d ask a colleague. Behind the scenes it grabs hard numbers from Postgres, pulls matching commentary from management memos, and stitches both into one briefing.

---

## Prerequisites

- Python 3.10+
- Local PostgreSQL (the default `DATABASE_URL` works with no password)
- HuggingFace API access for chat + embeddings
- A Pinecone account

---

## Setup

**1. Install packages**
```bash
pip install -r requirements.txt
```

**2. Configure secrets**
```bash
cp .env.example .env
# Fill in:
#   LLM_API_KEY       — HuggingFace token
#   PINECONE_API_KEY  — Pinecone token
#   DATABASE_URL      — Postgres connection string (local default is usually fine)
```

**3. Create and seed the database**
```bash
python setup_db.py
```
This builds `financial_db` and loads eleven quarters of Aurora Mobility figures from 2022–2024.

**4. Index the filings**
```bash
python ingest_docs.py
```
Chunks every `.txt` / `.pdf` under `data/reports/`, embeds them, and pushes the vectors into the `financial-docs` Pinecone index. Run this again whenever you drop in new reports.

---

## Running it

### In the browser
```bash
uvicorn app:app --port 8000
```
Open **http://localhost:8000**.

### In the terminal (interactive)
```bash
python main.py
```

### In the terminal (one-shot)
```bash
python main.py "What was Q3 2024 revenue and what drove growth?"
python main.py --verbose "Compare 2023 vs 2024 net income"   # prints LangChain debug traces
```

---

## What it does well

- **Parallel lookup** — SQL generation/execution and Pinecone search run together via `asyncio.gather`, so you’re not waiting on one before the other starts.
- **Numbers meet narrative** — Postgres gives you exact totals; the memos and annual reviews explain the “why”; an LLM writes one answer that uses both.
- **Browser desk** — question box, starter prompts, staged loading copy, a markdown briefing, plus expandable panels for the SQL, row results, and filing excerpts.
- **Modern LangChain SQL path** — uses `create_sql_query_chain` and `QuerySQLDataBaseTool` (the replacements for the old `SQLDatabaseChain`).

---

## Project layout

```
├── app.py              # FastAPI HTTP layer
├── main.py             # CLI entry point
├── setup_db.py         # Schema + seed data
├── ingest_docs.py      # Report → Pinecone pipeline
├── src/
│   ├── agent.py        # Orchestrates SQL, vectors, and synthesis
│   ├── sql_chain.py    # Natural language → SQL → execute
│   ├── vector_store.py # Embeddings + similarity search
│   └── config.py       # Env loading / validation
├── static/
│   └── index.html      # Single-page research desk
├── data/
│   ├── reports/        # Source filings for retrieval
│   └── schema.sql      # Table definitions
└── docs/
    └── flows.md        # How the pipelines fit together
```

### Debug mode

Pass `--verbose` if you want to see LangChain internals, including the SQL the model wrote:

```bash
python main.py --verbose "Compare 2023 vs 2024 revenue"
```
