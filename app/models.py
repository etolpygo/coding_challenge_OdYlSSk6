from pydantic import BaseModel
from typing import Optional


class Movie(BaseModel):
    id: int
    title: str
    year: Optional[int]
    overview: Optional[str]
    rating_avg: Optional[float]
    rating_count: Optional[int]
    director: Optional[str]
    cast: Optional[str]
    genres: list[str] = []


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    movies: list[Movie] = []
