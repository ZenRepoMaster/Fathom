"""
SQL chain — functional equivalent of LangChain SQLDatabaseChain.

SQLDatabaseChain was removed in langchain-community 0.4+.  The recommended
migration is create_sql_query_chain (SQL generation) + QuerySQLDataBaseTool
(execution), chained with LCEL.  This module wraps that pattern and exposes
the same interface the rest of the project expects.

The custom prompt enforces STRICTLY CAPITALIZED SQL keywords while keeping
table/column names lowercase as defined in the schema.
"""

import re
from langchain_classic.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

from .config import DATABASE_URL, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, VERBOSE

# Prompt variables must be: input, dialect, table_info, top_k
# (create_sql_query_chain maps question→input internally)
_SQL_PROMPT = PromptTemplate(
    input_variables=["input", "dialect", "table_info", "top_k"],
    template="""You are a senior financial data analyst with deep {dialect} expertise.

Given a user question, produce a single STRICTLY CAPITALIZED SQL query.

STRICT RULES — follow every one:
1. ALL SQL keywords MUST be UPPERCASE: SELECT, FROM, WHERE, GROUP BY, ORDER BY,
   HAVING, JOIN, LEFT JOIN, INNER JOIN, ON, AS, AND, OR, NOT, IN, BETWEEN, LIKE,
   DISTINCT, COUNT, SUM, AVG, MAX, MIN, ROUND, CAST, COALESCE, NULLIF, LIMIT,
   OFFSET, WITH, UNION, CASE, WHEN, THEN, ELSE, END.
2. Table and column names stay lowercase exactly as shown in the schema.
3. String literals MUST use the EXACT case shown in the sample rows
   (e.g. 'Aurora Mobility Inc.' not 'aurora mobility inc.', 'Q3' not 'q3').
4. Never SELECT *. Prefer the pnl_summary view for combined P&L queries.
5. Add LIMIT {top_k} unless the user asks for all records.
6. Output ONLY the SQL statement ending with a semicolon.
   Do NOT write any explanation, commentary, or alternative queries after it.

Schema:
{table_info}

Question: {input}
SQLQuery:""",
)


def _clean_sql(raw: str) -> str:
    """
    Extract a clean SQL statement from raw LLM output.
    Handles markdown fences, 'SQLQuery:' prefixes, and trailing prose
    that instruction-tuned models sometimes add after the semicolon.
    """
    sql = raw.strip()
    # Strip any markdown fences wherever they appear
    sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE)
    # Strip 'SQLQuery:' prefix
    sql = re.sub(r"^SQLQuery:\s*", "", sql, flags=re.IGNORECASE)
    # Find the first SQL keyword and start there
    match = re.search(r"\b(SELECT|WITH|INSERT|UPDATE|DELETE)\b", sql, re.IGNORECASE)
    if match:
        sql = sql[match.start():]
    # Truncate at the FIRST semicolon — discard any trailing prose or second example queries
    first_semi = sql.find(";")
    if first_semi != -1:
        sql = sql[: first_semi + 1]
    return sql.strip()


class SQLQueryChain:
    """Wraps create_sql_query_chain + QuerySQLDataBaseTool into one object."""

    def __init__(self):
        self.db = SQLDatabase.from_uri(
            DATABASE_URL,
            include_tables=["companies", "financial_metrics", "segments", "pnl_summary"],
            sample_rows_in_table_info=2,
            view_support=True,
        )
        llm = ChatOpenAI(
            model=LLM_MODEL,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            temperature=0,
            max_tokens=2048,
        )
        self._sql_generator = create_sql_query_chain(llm, self.db, prompt=_SQL_PROMPT, k=50)
        self._executor = QuerySQLDataBaseTool(db=self.db)

        # LCEL chain: question → {question, query, result}
        self._chain = (
            RunnablePassthrough.assign(query=self._sql_generator)
            .assign(result=lambda x: self._executor.invoke(_clean_sql(x["query"])))
        )

    def invoke(self, question: str) -> dict:
        """
        Run the full SQL pipeline for a natural-language question.
        Returns {"sql_query": str, "sql_result": str}.
        """
        raw = self._chain.invoke({"question": question})
        sql = _clean_sql(raw.get("query", ""))
        result = raw.get("result", "")
        if VERBOSE:
            print(f"\n[SQL] Generated:\n{sql}\n[SQL] Result:\n{result}\n")
        return {"sql_query": sql, "sql_result": result}


def create_sql_chain() -> SQLQueryChain:
    return SQLQueryChain()


def run_sql_query(chain: SQLQueryChain, question: str) -> dict:
    return chain.invoke(question)

# Return empty result set instead of raising on no rows
