import os
from dotenv import load_dotenv

load_dotenv()

# LLM — HuggingFace Router (OpenAI-compatible)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://router.huggingface.co/v1")
LLM_MODEL    = os.getenv("LLM_MODEL",    "meta-llama/Llama-3.3-70B-Instruct")
LLM_API_KEY  = os.getenv("LLM_API_KEY",  "")

# Embeddings — HuggingFace Inference API (OpenAI-compatible)
EMBEDDING_BASE_URL   = os.getenv("EMBEDDING_BASE_URL",   "https://router.huggingface.co/hf-inference")
EMBEDDING_MODEL      = os.getenv("EMBEDDING_MODEL",      "BAAI/bge-small-en-v1.5")
EMBEDDING_API_KEY    = os.getenv("EMBEDDING_API_KEY",    "")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))

# Pinecone
PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY",    "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "financial-docs")
PINECONE_REGION     = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")

# PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/financial_db")
VERBOSE      = os.getenv("VERBOSE", "false").lower() == "true"


def validate():
    missing = []
    if not LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if not PINECONE_API_KEY:
        missing.append("PINECONE_API_KEY")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your credentials."
        )

LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.1"))

# Database connection pool
DB_POOL_SIZE    = int(os.environ.get("DB_POOL_SIZE", "5"))
DB_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "30"))

# LLM token limit for SQL chain prompts
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "2048"))

# CORS configuration
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# Async parallel search configuration
PARALLEL_TIMEOUT     = int(os.environ.get("PARALLEL_TIMEOUT", "45"))
ENABLE_PARALLEL      = os.environ.get("ENABLE_PARALLEL_SEARCH", "true").lower() == "true"
SEARCH_CONCURRENCY   = int(os.environ.get("SEARCH_CONCURRENCY", "5"))

# UI theme configuration
UI_THEME = os.environ.get("UI_THEME", "light")

# Query response cache
CACHE_ENABLED  = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL      = int(os.environ.get("CACHE_TTL", "300"))
CACHE_MAX_SIZE = int(os.environ.get("CACHE_MAX_SIZE", "100"))

# Logging configuration
LOG_LEVEL  = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = os.environ.get("LOG_FORMAT", "json")
