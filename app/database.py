import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "movies.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS movies (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    year        INTEGER,
    overview    TEXT,
    rating_avg  REAL,
    rating_count INTEGER,
    director    TEXT,
    cast        TEXT
);

CREATE TABLE IF NOT EXISTS genres (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER NOT NULL REFERENCES movies(id),
    name     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ratings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id  INTEGER NOT NULL REFERENCES movies(id),
    user_id   INTEGER NOT NULL,
    rating    REAL NOT NULL,
    timestamp INTEGER
);

CREATE INDEX IF NOT EXISTS idx_movies_year    ON movies(year);
CREATE INDEX IF NOT EXISTS idx_movies_rating  ON movies(rating_avg);
CREATE INDEX IF NOT EXISTS idx_genres_movie   ON genres(movie_id);
CREATE INDEX IF NOT EXISTS idx_genres_name    ON genres(name);
CREATE INDEX IF NOT EXISTS idx_ratings_movie  ON ratings(movie_id);
CREATE INDEX IF NOT EXISTS idx_ratings_user   ON ratings(user_id);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def db_connection():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_connection() as conn:
        conn.executescript(SCHEMA)
    logger.info("Database initialised at %s", DB_PATH)
