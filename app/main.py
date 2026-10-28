import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routers import chat, movies

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Movie AI Agent",
    description=(
        "A conversational REST API that answers questions about movies "
        "using structured data retrieval and an LLM (Ollama llama3.2)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(chat.router)
app.include_router(movies.router)


@app.get("/health", tags=["meta"])
def health():
    """Check that the API is running."""
    return {"status": "ok"}
