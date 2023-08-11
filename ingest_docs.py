#!/usr/bin/env python3
"""
Load management commentary (PDF reports, executive memos) into Pinecone.

Reads every .txt and .pdf under data/reports/, splits into chunks,
embeds them, and upserts into Pinecone.

Run: python ingest_docs.py
     python ingest_docs.py --dir /path/to/custom/reports
"""

import argparse
from pathlib import Path
from src.config import validate
from src.vector_store import ingest_documents

DEFAULT_REPORTS_DIR = str(Path(__file__).parent / "data" / "reports")


def main():
    parser = argparse.ArgumentParser(description="Ingest financial reports into Pinecone.")
    parser.add_argument(
        "--dir",
        default=DEFAULT_REPORTS_DIR,
        help=f"Directory containing .txt/.pdf reports (default: {DEFAULT_REPORTS_DIR})",
    )
    parser.add_argument("--chunk-size",    type=int, default=800,  help="Token chunk size (default: 800)")
    parser.add_argument("--chunk-overlap", type=int, default=120,  help="Chunk overlap (default: 120)")
    args = parser.parse_args()

    validate()

    print(f"Loading documents from: {args.dir}")
    n = ingest_documents(args.dir, chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    print(f"\nDone. {n} chunks are now searchable in Pinecone.")


if __name__ == "__main__":
    main()
