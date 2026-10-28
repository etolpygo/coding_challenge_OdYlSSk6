"""
Wraps the Ollama HTTP API to generate conversational responses.

Ollama must be running locally (default: http://localhost:11434).
Model: llama3.2 (configurable via OLLAMA_MODEL env var).
"""

import logging
import os
import httpx
from app.models import Movie

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
TIMEOUT = 60.0


def _format_movie(movie: Movie) -> str:
    parts = [f"Title: {movie.title}"]
    if movie.year:
        parts.append(f"Year: {movie.year}")
    if movie.genres:
        parts.append(f"Genres: {', '.join(movie.genres)}")
    if movie.director:
        parts.append(f"Director: {movie.director}")
    if movie.cast:
        parts.append(f"Cast: {movie.cast}")
    if movie.rating_avg:
        parts.append(f"Rating: {movie.rating_avg:.2f}/5 ({movie.rating_count} user ratings)")
    if movie.overview:
        parts.append(f"Overview: {movie.overview[:300]}")
    return "\n".join(parts)


def _build_prompt(user_message: str, movies: list[Movie]) -> str:
    if not movies:
        return (
            "You are a helpful movie expert assistant. "
            "Answer the following question as best you can using your general knowledge. "
            "If you are unsure, say so honestly.\n\n"
            f"User: {user_message}\nAssistant:"
        )

    movie_context = "\n\n---\n\n".join(_format_movie(m) for m in movies)

    # Note what metadata is actually available so the LLM doesn't invent missing fields
    has_overview = any(m.overview for m in movies)
    has_cast = any(m.cast for m in movies)
    data_note = (
        "Note: the dataset provides title, year, genres, and user ratings. "
        + ("Plot overviews are available. " if has_overview else "Plot overviews are not available in this dataset. ")
        + ("Cast information is available." if has_cast else "Cast and director information are not available in this dataset.")
    )

    return (
        "You are a helpful movie expert assistant. "
        "Use the following movie data to answer the user's question in a natural, "
        "conversational way. Be concise but informative. "
        "Only mention fields that are present in the data — do not invent cast, directors, or plot details.\n\n"
        f"{data_note}\n\n"
        f"Movie data:\n{movie_context}\n\n"
        f"User: {user_message}\nAssistant:"
    )


def generate_response(user_message: str, movies: list[Movie]) -> str:
    prompt = _build_prompt(user_message, movies)

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"].strip()

    except httpx.ConnectError:
        logger.error("Cannot connect to Ollama at %s", OLLAMA_BASE_URL)
        raise RuntimeError(
            "Ollama is not running. Start it with `ollama serve` and ensure "
            f"model '{OLLAMA_MODEL}' is pulled (`ollama pull {OLLAMA_MODEL}`)."
        )
    except httpx.HTTPStatusError as e:
        logger.error("Ollama returned error: %s", e.response.text)
        raise RuntimeError(f"LLM error: {e.response.text}")
    except Exception as e:
        logger.exception("Unexpected LLM error")
        raise RuntimeError(f"LLM error: {e}") from e
