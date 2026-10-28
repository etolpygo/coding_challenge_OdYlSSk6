import logging
from app.database import db_connection
from app.models import Movie
from app.services.query_parser import ParsedQuery

logger = logging.getLogger(__name__)


def _row_to_movie(row, genres: list[str]) -> Movie:
    return Movie(
        id=row["id"],
        title=row["title"],
        year=row["year"],
        overview=row["overview"],
        rating_avg=row["rating_avg"],
        rating_count=row["rating_count"],
        director=row["director"],
        cast=row["cast"],
        genres=genres,
    )


def _fetch_genres(conn, movie_ids: list[int]) -> dict[int, list[str]]:
    if not movie_ids:
        return {}
    placeholders = ",".join("?" * len(movie_ids))
    rows = conn.execute(
        f"SELECT movie_id, name FROM genres WHERE movie_id IN ({placeholders})",
        movie_ids,
    ).fetchall()
    result: dict[int, list[str]] = {mid: [] for mid in movie_ids}
    for row in rows:
        result[row["movie_id"]].append(row["name"])
    return result


def search_movies(query: ParsedQuery) -> list[Movie]:
    clauses: list[str] = []
    params: list = []

    if query.title_hint:
        clauses.append("m.title LIKE ?")
        params.append(f"%{query.title_hint}%")

    if query.genres:
        genre_placeholders = ",".join("?" * len(query.genres))
        clauses.append(
            f"m.id IN (SELECT movie_id FROM genres WHERE LOWER(name) IN ({genre_placeholders}))"
        )
        params.extend(g.lower() for g in query.genres)

    if query.year:
        clauses.append("m.year = ?")
        params.append(query.year)
    elif query.year_from and query.year_to:
        clauses.append("m.year BETWEEN ? AND ?")
        params.extend([query.year_from, query.year_to])
    elif query.year_from:
        clauses.append("m.year >= ?")
        params.append(query.year_from)

    if query.min_rating:
        clauses.append("m.rating_avg >= ?")
        params.append(query.min_rating)

    if query.director:
        clauses.append("LOWER(m.director) LIKE ?")
        params.append(f"%{query.director.lower()}%")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    # For recommendations sort by rating; otherwise relevance (rating still a good proxy)
    order = "ORDER BY m.rating_avg DESC, m.rating_count DESC"

    sql = f"""
        SELECT m.*
        FROM movies m
        {where}
        {order}
        LIMIT ?
    """
    params.append(query.limit)

    with db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        movie_ids = [r["id"] for r in rows]
        genres_map = _fetch_genres(conn, movie_ids)
        return [_row_to_movie(r, genres_map.get(r["id"], [])) for r in rows]


def get_movie_by_id(movie_id: int) -> Movie | None:
    with db_connection() as conn:
        row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
        if not row:
            return None
        genres = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM genres WHERE movie_id = ?", (movie_id,)
            ).fetchall()
        ]
        return _row_to_movie(row, genres)


def list_movies(
    genre: str | None = None,
    year: int | None = None,
    min_rating: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Movie]:
    clauses: list[str] = []
    params: list = []

    if genre:
        clauses.append(
            "m.id IN (SELECT movie_id FROM genres WHERE LOWER(name) = ?)"
        )
        params.append(genre.lower())

    if year:
        clauses.append("m.year = ?")
        params.append(year)

    if min_rating:
        clauses.append("m.rating_avg >= ?")
        params.append(min_rating)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT m.*
        FROM movies m
        {where}
        ORDER BY m.rating_avg DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    with db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        movie_ids = [r["id"] for r in rows]
        genres_map = _fetch_genres(conn, movie_ids)
        return [_row_to_movie(r, genres_map.get(r["id"], [])) for r in rows]
