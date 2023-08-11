"""
Fathom hybrid routing agent.

For every question the agent fires BOTH branches in parallel:
  1. SQL branch  — drafts and runs a SQL query against PostgreSQL
                   for exact numerical data.
  2. Vector branch — Pinecone semantic search pulls relevant management
                     commentary / executive memos for narrative context.

Both results go to a synthesis LLM that writes one cohesive,
numbers-grounded financial answer.
"""

import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from .sql_chain import create_sql_chain, run_sql_query
from .vector_store import semantic_search

_SYNTHESIS_SYSTEM = """You are an elite financial analyst assistant with access to two data sources:

1. EXACT SQL RESULTS — precise numerical data retrieved directly from a relational database.
   These numbers are authoritative. Cite them exactly (revenue, margins, user counts, etc.).

2. MANAGEMENT COMMENTARY — excerpts from executive memos and annual reports retrieved via
   semantic search. These provide the strategic narrative and qualitative context behind the numbers.

Your job is to synthesize both sources into a single, cohesive financial analysis:
- Lead with the exact figures from the SQL results.
- Weave in the qualitative narrative from management commentary to explain the WHY.
- Flag any discrepancies or missing data explicitly.
- Use precise financial language (YoY growth, gross margin, EBITDA, net income, etc.).
- Never invent numbers — if the SQL result is empty, say so."""

_SYNTHESIS_HUMAN = """## User Question
{question}

## SQL Query Executed
```sql
{sql_query}
```

## SQL Result (Exact Numerical Data)
{sql_result}

## Management Commentary (Semantic Search Results)
{vector_context}

---
Provide a comprehensive financial analysis that integrates both the exact numbers and the management narrative."""


def _format_vector_context(docs) -> str:
    if not docs:
        return "No relevant management commentary found for this query."
    sections = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "Unknown")
        sections.append(f"[{i}] Source: {source}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(sections)


class FinancialAgent:
    def __init__(self):
        self._sql_chain = create_sql_chain()
        self._llm = ChatOpenAI(
            model=LLM_MODEL,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            temperature=0.15,
            max_tokens=4096,
        )
        self._synthesis_chain = (
            ChatPromptTemplate.from_messages([
                ("system", _SYNTHESIS_SYSTEM),
                ("human",  _SYNTHESIS_HUMAN),
            ])
            | self._llm
            | StrOutputParser()
        )

    async def _run_sql_async(self, question: str) -> dict:
        return await asyncio.to_thread(run_sql_query, self._sql_chain, question)

    async def _run_vector_async(self, question: str, k: int = 5):
        return await asyncio.to_thread(semantic_search, question, k)

    async def query_async(self, question: str) -> dict:
        """Fire SQL and vector search simultaneously, then synthesize."""
        print("\n[Agent] Executing SQL query and semantic search in parallel…")

        sql_result, vector_docs = await asyncio.gather(
            self._run_sql_async(question),
            self._run_vector_async(question),
        )

        vector_context = _format_vector_context(vector_docs)

        print("[Agent] Synthesizing results with LLM…")
        final_answer = await asyncio.to_thread(
            self._synthesis_chain.invoke,
            {
                "question":       question,
                "sql_query":      sql_result["sql_query"],
                "sql_result":     sql_result["sql_result"],
                "vector_context": vector_context,
            },
        )

        return {
            "question":       question,
            "sql_query":      sql_result["sql_query"],
            "sql_result":     sql_result["sql_result"],
            "vector_context": vector_context,
            "final_answer":   final_answer,
        }

    def query(self, question: str) -> dict:
        """Synchronous wrapper around query_async."""
        return asyncio.run(self.query_async(question))

# Both branches (SQL + vector) are fired concurrently via asyncio.gather
# to minimise wall-clock latency on every user query
