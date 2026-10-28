from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.models import Movie

client = TestClient(app)

SAMPLE_MOVIE = Movie(
    id=1, title="The Matrix", year=1999,
    overview=None, rating_avg=4.2, rating_count=341,
    director=None, cast=None, genres=["Action", "Sci-Fi"],
)


# --- /health ---

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- POST /chat ---

@patch("app.routers.chat.llm_service.generate_response", return_value="Great sci-fi picks!")
@patch("app.routers.chat.movie_service.search_movies", return_value=[SAMPLE_MOVIE])
def test_chat_success(mock_search, mock_llm):
    resp = client.post("/chat", json={"message": "recommend sci-fi movies"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Great sci-fi picks!"
    assert len(data["movies"]) == 1
    assert data["movies"][0]["title"] == "The Matrix"


def test_chat_empty_message():
    resp = client.post("/chat", json={"message": "   "})
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


@patch("app.routers.chat.llm_service.generate_response", side_effect=RuntimeError("Ollama is not running"))
@patch("app.routers.chat.movie_service.search_movies", return_value=[SAMPLE_MOVIE])
def test_chat_llm_unavailable(mock_search, mock_llm):
    resp = client.post("/chat", json={"message": "recommend something"})
    assert resp.status_code == 503
    assert "Ollama" in resp.json()["detail"]


@patch("app.routers.chat.movie_service.search_movies", return_value=[])
def test_chat_no_results_with_filters(mock_search):
    resp = client.post("/chat", json={"message": "horror movies from 1750"})
    assert resp.status_code == 200
    data = resp.json()
    assert "couldn't find" in data["answer"].lower()
    assert data["movies"] == []


# --- GET /movies ---

@patch("app.routers.movies.movie_service.list_movies", return_value=[SAMPLE_MOVIE])
def test_list_movies(mock_list):
    resp = client.get("/movies")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@patch("app.routers.movies.movie_service.list_movies", return_value=[])
def test_list_movies_empty(mock_list):
    resp = client.get("/movies?genre=nonexistent")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_movies_invalid_limit():
    resp = client.get("/movies?limit=999")
    assert resp.status_code == 422


# --- GET /movies/{id} ---

@patch("app.routers.movies.movie_service.get_movie_by_id", return_value=SAMPLE_MOVIE)
def test_get_movie(mock_get):
    resp = client.get("/movies/1")
    assert resp.status_code == 200
    assert resp.json()["title"] == "The Matrix"


@patch("app.routers.movies.movie_service.get_movie_by_id", return_value=None)
def test_get_movie_not_found(mock_get):
    resp = client.get("/movies/99999")
    assert resp.status_code == 404
