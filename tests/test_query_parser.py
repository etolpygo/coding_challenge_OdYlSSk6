import pytest
from app.services.query_parser import parse


def test_recommend_intent():
    q = parse("recommend some good action movies")
    assert q.intent == "recommend"
    assert "action" in q.genres


def test_lookup_intent():
    q = parse("tell me about Inception")
    assert q.intent == "lookup"
    assert q.title_hint is not None
    assert "inception" in q.title_hint.lower()


def test_search_intent_default():
    q = parse("horror movies from 2010")
    assert q.intent == "search"
    assert "horror" in q.genres
    assert q.year == 2010


def test_decade_parsing():
    q = parse("best movies from the 1990s")
    assert q.year_from == 1990
    assert q.year_to == 1999


def test_year_range():
    q = parse("movies between 2000 and 2005")
    assert q.year_from == 2000
    assert q.year_to == 2005


def test_min_rating():
    q = parse("action movies rated above 8")
    assert q.min_rating == 8.0


def test_genre_alias_sci_fi():
    q = parse("great sci-fi films")
    assert "science fiction" in q.genres


def test_director_extraction():
    q = parse("movies directed by Christopher Nolan")
    assert q.director is not None
    assert "nolan" in q.director.lower()


def test_multiple_genres():
    q = parse("action comedy movies")
    assert "action" in q.genres
    assert "comedy" in q.genres


def test_empty_message_returns_defaults():
    q = parse("")
    assert q.intent == "search"
    assert q.genres == []
    assert q.year is None
