#!/usr/bin/env python3
"""
Fathom — terminal research desk.

Ask a finance question in plain English. The agent will:
  1. Draft and run CAPITALIZED SQL against PostgreSQL
  2. Pull management narrative via Pinecone similarity search
  3. Merge both into one briefing

Usage:
    python main.py                         # interactive REPL
    python main.py "What was Q3 2024 revenue and what drove growth?"
    python main.py --verbose "Compare 2023 vs 2024 net income"
"""

import sys
import argparse
import textwrap
import warnings
warnings.filterwarnings("ignore")

from src.config import validate, VERBOSE
from src.agent import FinancialAgent

DIVIDER = "─" * 72

EXAMPLE_QUESTIONS = [
    "What was Aurora Mobility's revenue in Q3 2024 and what drove the growth?",
    "Compare total revenue and net income across all quarters in 2024.",
    "Which segment grew the fastest in Q1 2024 and what did management say about it?",
    "What is Aurora Mobility's gross margin trend from 2022 to 2024?",
    "How many network members did Aurora have in Q3 2024 and what was ARPM?",
    "Summarize the full-year 2023 financial performance.",
]


def _print_result(result: dict) -> None:
    print(f"\n{DIVIDER}")
    print("QUERY")
    print(DIVIDER)
    print(result["question"])

    print(f"\n{DIVIDER}")
    print("GENERATED SQL")
    print(DIVIDER)
    print(result["sql_query"])

    print(f"\n{DIVIDER}")
    print("LEDGER EXTRACT")
    print(DIVIDER)
    print(result["sql_result"])

    print(f"\n{DIVIDER}")
    print("FILING EXCERPTS")
    print(DIVIDER)
    # Trim long vector context for readability
    ctx = result["vector_context"]
    if len(ctx) > 2000:
        ctx = ctx[:2000] + "\n… [truncated — full context passed to LLM]"
    print(ctx)

    print(f"\n{DIVIDER}")
    print("BRIEFING")
    print(DIVIDER)
    for line in result["final_answer"].splitlines():
        print(textwrap.fill(line, width=72) if len(line) > 72 else line)
    print(f"\n{DIVIDER}\n")


def run_single(question: str, agent: FinancialAgent) -> None:
    result = agent.query(question)
    _print_result(result)


def run_repl(agent: FinancialAgent) -> None:
    print("\nFathom  |  type 'examples' for starter prompts, 'quit' to exit")
    print(DIVIDER)
    while True:
        try:
            question = input("\nYour question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break
        if question.lower() == "examples":
            print("\nExample questions:")
            for i, q in enumerate(EXAMPLE_QUESTIONS, 1):
                print(f"  {i}. {q}")
            continue

        run_single(question, agent)


def main():
    parser = argparse.ArgumentParser(
        description="Fathom: hybrid SQL + semantic search research agent."
    )
    parser.add_argument("question", nargs="?", help="Natural language research question (omit for REPL)")
    parser.add_argument("--verbose", action="store_true", help="Show LangChain debug output")
    args = parser.parse_args()

    if args.verbose:
        import os
        os.environ["VERBOSE"] = "true"

    validate()

    agent = FinancialAgent()

    if args.question:
        run_single(args.question, agent)
    else:
        run_repl(agent)


if __name__ == "__main__":
    main()
