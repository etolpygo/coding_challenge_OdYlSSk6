import logging
from fastapi import APIRouter, HTTPException
from app.models import ChatRequest, ChatResponse
from app.services import query_parser, movie_service, llm_service

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a natural language message about movies and receive a conversational response.

    The agent parses your intent, retrieves relevant movies from the database,
    and uses an LLM to generate a helpful answer.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    parsed = query_parser.parse(request.message)
    logger.info("Parsed query: intent=%s genres=%s year=%s", parsed.intent, parsed.genres, parsed.year)

    movies = movie_service.search_movies(parsed)

    had_filters = bool(parsed.genres or parsed.year or parsed.year_from or parsed.title_hint)
    if not movies and had_filters:
        return ChatResponse(
            answer="I couldn't find any movies matching your query in the database. Try broadening your search — for example, remove the year filter or try a different genre.",
            movies=[],
        )

    try:
        answer = llm_service.generate_response(request.message, movies)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return ChatResponse(answer=answer, movies=movies)
