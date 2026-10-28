import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from app.services.query_parser import ParsedQuery
from app.services import movie_service
from app import database


SAMPLE_MOVIES = [
    {"id": 1, "title": "The Dark Knight", "year": 2008, "overview": "Batman fights the Joker.",
     "rating_avg": 9.0, "rating_count": 10000, "director": "Christopher Nolan", "cast": "Christian Bale"},
    {"id": 2, "title": "Inception", "year": 2010, "overview": "Dreams within dreams.",
     "rating_avg": 8.8, "rating_count": 9000, "director": "Christopher Nolan", "cast": "Leonardo DiCaprio"},
    {"id": 3, "title": "The Notebook", "year": 2004, "overview": "A love story.",
     "rating_avg": 7.5, "rating_count": 5000, "director": "Nick Cassavetes", "cast": "Ryan Gosling"},
]

SAMPLE_GENRES = [
    {"movie_id": 1, "name": "Action"},
    {"movie_id": 1, "name": "Crime"},
    {"movie_id": 2, "name": "Action"},
    {"movie_id": 2, "name": "Science Fiction"},
    {"movie_id": 3, "name": "Romance"},
    {"movie_id": 3, "name": "Drama"},
]


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", db_file)

    database.init_db()
    with database.db_connection() as conn:
        conn.executemany(
            "INSERT INTO movies (id, title, year, overview, rating_avg, rating_count, director, cast) "
            "VALUES (:id, :title, :year, :overview, :rating_avg, :rating_count, :director, :cast)",
            SAMPLE_MOVIES,
        )
        conn.executemany(
            "INSERT INTO genres (movie_id, name) VALUES (:movie_id, :name)",
            SAMPLE_GENRES,
        )


def test_get_movie_by_id():
    movie = movie_service.get_movie_by_id(1)
    assert movie is not None
    assert movie.title == "The Dark Knight"
    assert "Action" in movie.genres


def test_get_movie_by_id_not_found():
    assert movie_service.get_movie_by_id(999) is None


def test_search_by_genre():
    q = ParsedQuery(genres=["romance"], limit=10)
    results = movie_service.search_movies(q)
    assert len(results) == 1
    assert results[0].title == "The Notebook"


def test_search_by_year():
    q = ParsedQuery(year=2010, limit=10)
    results = movie_service.search_movies(q)
    assert len(results) == 1
    assert results[0].title == "Inception"


def test_search_by_min_rating():
    q = ParsedQuery(min_rating=8.9, limit=10)
    results = movie_service.search_movies(q)
    assert len(results) == 1
    assert results[0].title == "The Dark Knight"


def test_search_by_director():
    q = ParsedQuery(director="Christopher Nolan", limit=10)
    results = movie_service.search_movies(q)
    assert len(results) == 2


def test_search_by_title_hint():
    q = ParsedQuery(title_hint="Inception", limit=10)
    results = movie_service.search_movies(q)
    assert len(results) == 1
    assert results[0].title == "Inception"


def test_list_movies_no_filters():
    results = movie_service.list_movies(limit=10)
    assert len(results) == 3


def test_list_movies_genre_filter():
    results = movie_service.list_movies(genre="action", limit=10)
    assert len(results) == 2


def test_list_movies_pagination():
    first = movie_service.list_movies(limit=1, offset=0)
    second = movie_service.list_movies(limit=1, offset=1)
    assert len(first) == 1
    assert len(second) == 1
    assert first[0].id != second[0].id
