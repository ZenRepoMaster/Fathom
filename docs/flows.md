# How Fathom’s pipelines work

## 1. What happens when you ask a question

```
Your question comes in
    │
    ├──► Numbers path (asyncio.to_thread)
    │       create_sql_query_chain (LangChain)
    │         → model writes a SQL query
    │         → QuerySQLDataBaseTool runs it against Postgres
    │         → you get back { sql_query, sql_result }
    │
    └──► Narrative path (asyncio.to_thread)
            HFRouterEmbeddings.embed_query(question)
              → Pinecone nearest-neighbor search (k=5, drop scores under 0.25)
              → you get back Documents plus source metadata

Both sides run at the same time with asyncio.gather().

    │
    ▼
Composer model (Llama-3.3-70B via HuggingFace Router)
    Sees: system brief + your question + sql_result + vector_context
    Writes: final_answer as markdown

    │
    ▼
Response payload: { question, sql_query, sql_result, vector_context, final_answer }
```

---

## 2. The SQL path (`src/sql_chain.py`)

LangChain retired `SQLDatabaseChain` after 0.4. We rebuild the same job with three pieces:

- `create_sql_query_chain` — asks the LLM for a SELECT
- `QuerySQLDataBaseTool` — runs that SELECT on PostgreSQL
- `_clean_sql()` — strips markdown fences, chatter, and prefixes before execution

Tables the model can see: `companies`, `financial_metrics`, `segments`, `pnl_summary`.

---

## 3. The vector path (`src/vector_store.py`)

**Loading (`ingest_docs.py`):**
- Picks up `.txt` and `.pdf` files under `data/reports/`
- Splits them into 800-character chunks with 120 characters of overlap
- Embeds with HuggingFace Inference (`BAAI/bge-small-en-v1.5`, 384 dims)
- Upserts into a Pinecone serverless index (`financial-docs`, us-east-1)

**At query time:**
- Embeds the question with the same model
- Calls `PineconeVectorStore.similarity_search_with_relevance_scores()`
- Throws away anything scoring below 0.25

---

## 4. The browser path (`app.py` + `static/index.html`)

```
Browser
  POST /api/query  { question: "..." }
       │
  FastAPI handler
       │
  await FinancialAgent.query_async(question)
       │   (blocking work jumps to threads via asyncio.to_thread —
       │    so we don’t nest event loops)
       │
  JSON lands in the UI as:
    - Briefing     → marked.js markdown
    - SQL text     → dark <pre>
    - Tabular rows → monospace wrap block
    - Narrative    → pre-wrapped filing excerpts
    Detail panels start collapsed so the brief stays front and center.
```

`static/` mounts as `StaticFiles`. `/api/*` is registered first so those routes win.

`FinancialAgent` is built once inside the FastAPI `lifespan` hook and reused for every request.

---

## 5. Bootstrap scripts

**`setup_db.py`** — creates `financial_db` and loads eleven quarters of Aurora Mobility Inc. (AURM) into the four tables.

**`ingest_docs.py`** — runs the load steps in §3. Re-run it after you add files under `data/reports/`.

## Agent Orchestration

The agent runs SQL generation and vector search in parallel via `asyncio.gather`,
then synthesises both results into a single markdown briefing.

## Async Parallel Search

SQL generation and Pinecone search run concurrently via `asyncio.gather`.
Set `ENABLE_PARALLEL_SEARCH=false` to run them sequentially for debugging.
