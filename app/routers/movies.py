import logging
from fastapi import APIRouter, HTTPException, Query
from app.models import Movie
from app.services import movie_service

router = APIRouter(prefix="/movies", tags=["movies"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[Movie])
def list_movies(
    genre: str | None = Query(None, description="Filter by genre (e.g. 'action')"),
    year: int | None = Query(None, description="Filter by release year"),
    min_rating: float | None = Query(None, description="Minimum average rating (0-10)"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """List and filter movies from the database."""
    return movie_service.list_movies(
        genre=genre, year=year, min_rating=min_rating, limit=limit, offset=offset
    )


@router.get("/{movie_id}", response_model=Movie)
def get_movie(movie_id: int):
    """Get full details for a single movie by its TMDB ID."""
    movie = movie_service.get_movie_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found.")
    return movie
