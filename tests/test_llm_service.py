from unittest.mock import MagicMock, patch
import pytest
from app.models import Movie
from app.services import llm_service


SAMPLE_MOVIE = Movie(
    id=1, title="The Matrix", year=1999,
    overview=None, rating_avg=4.2, rating_count=341,
    director=None, cast=None, genres=["Action", "Sci-Fi"],
)


def _mock_ollama(text: str):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": text}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@patch("app.services.llm_service.httpx.Client")
def test_generate_response_returns_text(mock_client_cls):
    mock_client_cls.return_value.__enter__.return_value.post.return_value = (
        _mock_ollama("Here are some great action films!")
    )
    result = llm_service.generate_response("recommend action movies", [SAMPLE_MOVIE])
    assert result == "Here are some great action films!"


@patch("app.services.llm_service.httpx.Client")
def test_generate_response_no_movies(mock_client_cls):
    mock_client_cls.return_value.__enter__.return_value.post.return_value = (
        _mock_ollama("I recommend checking out The Godfather.")
    )
    result = llm_service.generate_response("recommend a classic movie", [])
    assert "Godfather" in result


@patch("app.services.llm_service.httpx.Client")
def test_generate_response_strips_whitespace(mock_client_cls):
    mock_client_cls.return_value.__enter__.return_value.post.return_value = (
        _mock_ollama("  Great movie!  ")
    )
    result = llm_service.generate_response("tell me about it", [SAMPLE_MOVIE])
    assert result == "Great movie!"


@patch("app.services.llm_service.httpx.Client")
def test_connect_error_raises_runtime_error(mock_client_cls):
    import httpx
    mock_client_cls.return_value.__enter__.return_value.post.side_effect = (
        httpx.ConnectError("refused")
    )
    with pytest.raises(RuntimeError, match="Ollama is not running"):
        llm_service.generate_response("any query", [])


@patch("app.services.llm_service.httpx.Client")
def test_http_error_raises_runtime_error(mock_client_cls):
    import httpx
    mock_resp = MagicMock()
    mock_resp.text = "model not found"
    mock_client_cls.return_value.__enter__.return_value.post.return_value.raise_for_status.side_effect = (
        httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)
    )
    with pytest.raises(RuntimeError, match="LLM error"):
        llm_service.generate_response("any query", [])


def test_prompt_includes_data_note_without_metadata():
    prompt = llm_service._build_prompt("recommend something", [SAMPLE_MOVIE])
    assert "not available" in prompt


def test_prompt_no_movies_uses_general_knowledge():
    prompt = llm_service._build_prompt("recommend something", [])
    assert "general knowledge" in prompt
