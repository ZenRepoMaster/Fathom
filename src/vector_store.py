"""
Pinecone vector store for unstructured management commentary.

Documents (PDF reports, executive memos) are chunked, embedded via the
HuggingFace Inference router, and stored in a Pinecone serverless index.

The HF router exposes embeddings at:
  POST {EMBEDDING_BASE_URL}/models/{EMBEDDING_MODEL}
with body {"inputs": ["text1", "text2"]} → [[float, ...], [float, ...]]
"""

import time
from pathlib import Path
from typing import List

import requests
from langchain_core.embeddings import Embeddings
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec

from .config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_REGION,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_API_KEY,
    EMBEDDING_DIMENSIONS,
)


class HFRouterEmbeddings(Embeddings):
    """
    Calls the HuggingFace Inference router's feature-extraction endpoint.
    Endpoint: {base_url}/models/{model}
    Request:  {"inputs": ["text1", "text2"]}
    Response: [[float, ...], [float, ...]]
    """

    def __init__(self, base_url: str, model: str, api_key: str, timeout: int = 30):
        # Strip any /v1 suffix — the HF router model path doesn't use it
        clean_base = base_url.rstrip("/").removesuffix("/v1")
        self.api_url = f"{clean_base}/models/{model}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.timeout = timeout

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        r = requests.post(
            self.api_url,
            headers=self.headers,
            json={"inputs": texts},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


def get_embeddings() -> HFRouterEmbeddings:
    return HFRouterEmbeddings(
        base_url=EMBEDDING_BASE_URL,
        model=EMBEDDING_MODEL,
        api_key=EMBEDDING_API_KEY,
    )


def _ensure_index(pc: Pinecone) -> None:
    existing = {idx.name for idx in pc.list_indexes()}
    if PINECONE_INDEX_NAME not in existing:
        print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}' (dim={EMBEDDING_DIMENSIONS})…")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSIONS,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=PINECONE_REGION),
        )
        while not pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
            time.sleep(1)
        print("Index ready.")


def get_vector_store() -> PineconeVectorStore:
    _ensure_index(Pinecone(api_key=PINECONE_API_KEY))
    return PineconeVectorStore(
        index_name=PINECONE_INDEX_NAME,
        embedding=get_embeddings(),
        pinecone_api_key=PINECONE_API_KEY,
    )


def load_documents(reports_dir: str) -> list[Document]:
    """Load .txt and .pdf files from reports_dir."""
    docs: list[Document] = []
    p = Path(reports_dir)

    for txt_file in p.glob("**/*.txt"):
        loader = TextLoader(str(txt_file), encoding="utf-8")
        loaded = loader.load()
        for doc in loaded:
            doc.metadata["source"] = txt_file.name
        docs.extend(loaded)

    for pdf_file in p.glob("**/*.pdf"):
        loader = PyPDFLoader(str(pdf_file))
        loaded = loader.load()
        for doc in loaded:
            doc.metadata["source"] = pdf_file.name
        docs.extend(loaded)

    return docs


def ingest_documents(reports_dir: str, chunk_size: int = 800, chunk_overlap: int = 120) -> int:
    """Chunk and upsert all documents in reports_dir into Pinecone.

    Clears the existing index first so prior demo corpora (e.g. NovaTech)
    do not mix with the current knowledge base.
    """
    docs = load_documents(reports_dir)
    if not docs:
        raise FileNotFoundError(f"No .txt or .pdf files found in: {reports_dir}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"Loaded {len(docs)} document(s) → {len(chunks)} chunks.")

    pc = Pinecone(api_key=PINECONE_API_KEY)
    _ensure_index(pc)
    index = pc.Index(PINECONE_INDEX_NAME)
    print(f"Clearing existing vectors in '{PINECONE_INDEX_NAME}'…")
    try:
        index.delete(delete_all=True)
    except Exception as exc:
        print(f"Index clear skipped ({exc}); continuing with upsert.")

    vs = get_vector_store()
    vs.add_documents(chunks)
    print(f"Upserted {len(chunks)} chunks to Pinecone index '{PINECONE_INDEX_NAME}'.")
    return len(chunks)


def semantic_search(query: str, k: int = 5, score_threshold: float = 0.25) -> list[Document]:
    """Return the top-k most relevant document chunks for query."""
    vs = get_vector_store()
    results_with_scores = vs.similarity_search_with_score(query, k=k)
    return [doc for doc, score in results_with_scores if score >= score_threshold]

# Chunk configuration for document ingestion
CHUNK_SIZE    = int(os.environ.get("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "50"))

# Maximum results returned from similarity search
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "5"))
