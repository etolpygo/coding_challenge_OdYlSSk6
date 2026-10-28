"""
Load the MovieLens small dataset into the local SQLite database.

Dataset is downloaded automatically from grouplens.org — no login required.
Alternatively, place the files manually:
  data/ml-latest-small/movies.csv
  data/ml-latest-small/ratings.csv

Usage:
  python scripts/ingest.py
"""

import logging
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.database import db_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ML_DIR = Path("data/ml-latest-small")
ML_ZIP = Path("data/ml-latest-small.zip")
ML_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"

YEAR_RE = re.compile(r"\((\d{4})\)\s*$")


def _ensure_dataset() -> None:
    if (ML_DIR / "movies.csv").exists():
        return
    logger.info("Downloading MovieLens small dataset...")
    ML_ZIP.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(ML_URL, ML_ZIP)
    with zipfile.ZipFile(ML_ZIP) as zf:
        zf.extractall("data/")
    logger.info("Download complete.")


def _extract_year(title: str) -> tuple[str, int | None]:
    m = YEAR_RE.search(title)
    if m:
        clean_title = title[: m.start()].strip()
        return clean_title, int(m.group(1))
    return title.strip(), None


def load() -> None:
    _ensure_dataset()
    init_db()

    logger.info("Reading CSV files...")
    movies_df = pd.read_csv(ML_DIR / "movies.csv")
    ratings_df = pd.read_csv(ML_DIR / "ratings.csv")

    logger.info("Aggregating ratings for %d movies...", len(movies_df))
    agg = ratings_df.groupby("movieId")["rating"].agg(
        rating_avg="mean", rating_count="count"
    ).reset_index()

    df = movies_df.merge(agg, on="movieId", how="left")

    movie_rows = []
    genre_rows = []

    for _, row in df.iterrows():
        clean_title, year = _extract_year(str(row["title"]))

        rating_avg = float(row["rating_avg"]) if pd.notna(row.get("rating_avg")) else None
        rating_count = int(row["rating_count"]) if pd.notna(row.get("rating_count")) else None

        movie_rows.append({
            "id": int(row["movieId"]),
            "title": clean_title,
            "year": year,
            "overview": None,
            "rating_avg": round(rating_avg, 2) if rating_avg else None,
            "rating_count": rating_count,
            "director": None,
            "cast": None,
        })

        raw_genres = str(row.get("genres", ""))
        for g in raw_genres.split("|"):
            g = g.strip()
            if g and g != "(no genres listed)":
                genre_rows.append({"movie_id": int(row["movieId"]), "name": g})

    # Build individual ratings rows from raw ratings.csv data
    valid_movie_ids = {r["id"] for r in movie_rows}
    rating_rows = [
        {
            "movie_id": int(r["movieId"]),
            "user_id": int(r["userId"]),
            "rating": float(r["rating"]),
            "timestamp": int(r["timestamp"]),
        }
        for _, r in ratings_df.iterrows()
        if int(r["movieId"]) in valid_movie_ids
    ]

    with db_connection() as conn:
        conn.execute("DELETE FROM ratings")
        conn.execute("DELETE FROM genres")
        conn.execute("DELETE FROM movies")

        conn.executemany(
            """
            INSERT OR REPLACE INTO movies
                (id, title, year, overview, rating_avg, rating_count, director, cast)
            VALUES
                (:id, :title, :year, :overview, :rating_avg, :rating_count, :director, :cast)
            """,
            movie_rows,
        )
        conn.executemany(
            "INSERT INTO genres (movie_id, name) VALUES (:movie_id, :name)",
            genre_rows,
        )
        conn.executemany(
            "INSERT INTO ratings (movie_id, user_id, rating, timestamp) "
            "VALUES (:movie_id, :user_id, :rating, :timestamp)",
            rating_rows,
        )

    logger.info(
        "Ingested %d movies, %d genre records, %d ratings.",
        len(movie_rows), len(genre_rows), len(rating_rows),
    )


if __name__ == "__main__":
    load()
