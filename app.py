"""
Fathom HTTP server.

Run:
    uvicorn app:app --reload --port 8000
Then open http://localhost:8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    from src.agent import FinancialAgent
    print("Initializing Fathom agent…")
    _agent = FinancialAgent()
    print("Agent ready.")
    yield


app = FastAPI(title="Fathom", lifespan=lifespan)


class QueryRequest(BaseModel):
    question: str


@app.post("/api/query")
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        result = await _agent.query_async(req.question)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Static files last so /api/* routes take precedence
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# API configuration
API_VERSION = "v1"
API_PREFIX  = "/api/v1"
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "60"))

# Input length limits
MAX_QUERY_LENGTH = int(os.environ.get("MAX_QUERY_LENGTH", "1000"))
