"""
Parses free-text movie queries into structured intent + filters.

Intents:
  - recommend   : user wants suggestions ("recommend", "suggest", "what should I watch")
  - lookup      : user asks about a specific movie ("tell me about Inception")
  - search      : generic search with filters ("action movies from 2010")
"""

import re
from dataclasses import dataclass, field

GENRES = {
    "action", "adventure", "animation", "comedy", "crime", "documentary",
    "drama", "fantasy", "film-noir", "horror", "imax", "musical", "mystery",
    "romance", "sci-fi", "scifi", "science fiction", "thriller", "war", "western",
    "children",
}

# Maps user-friendly terms to the exact genre names stored in the DB (MovieLens conventions)
GENRE_ALIASES = {
    "science fiction": "Sci-Fi",
    "sci fi": "Sci-Fi",
    "scifi": "Sci-Fi",
    "sci-fi": "Sci-Fi",
    "rom-com": "Romance",
    "romcom": "Romance",
    "romance": "Romance",
    "action": "Action",
    "adventure": "Adventure",
    "animation": "Animation",
    "comedy": "Comedy",
    "crime": "Crime",
    "documentary": "Documentary",
    "drama": "Drama",
    "fantasy": "Fantasy",
    "film-noir": "Film-Noir",
    "horror": "Horror",
    "imax": "IMAX",
    "musical": "Musical",
    "mystery": "Mystery",
    "thriller": "Thriller",
    "war": "War",
    "western": "Western",
    "children": "Children",
}

RECOMMEND_PATTERNS = re.compile(
    r"\b(recommend|suggest|what should i watch|good movies?|best movies?|"
    r"top movies?|similar to|like .+)\b",
    re.IGNORECASE,
)

LOOKUP_PATTERNS = re.compile(
    r"\b(tell me about|what is|who (directed|starred in|made)|"
    r"when was .+ (made|released)|cast of|director of|plot of|synopsis of)\b",
    re.IGNORECASE,
)

YEAR_PATTERN = re.compile(r"\b(19[0-9]{2}|20[0-2][0-9])\b")
DECADE_PATTERN = re.compile(r"\b(19[0-9]0|20[0-2]0)s\b", re.IGNORECASE)
MIN_RATING_PATTERN = re.compile(r"\brated?\s+(above|over|at least|higher than)?\s*([0-9.]+)\b", re.IGNORECASE)


@dataclass
class ParsedQuery:
    intent: str = "search"
    title_hint: str | None = None
    genres: list[str] = field(default_factory=list)
    year: int | None = None
    year_from: int | None = None
    year_to: int | None = None
    min_rating: float | None = None
    director: str | None = None
    limit: int = 5
    raw: str = ""


def parse(text: str) -> ParsedQuery:
    q = ParsedQuery(raw=text)
    lower = text.lower()

    # Intent
    if RECOMMEND_PATTERNS.search(lower):
        q.intent = "recommend"
    elif LOOKUP_PATTERNS.search(lower):
        q.intent = "lookup"
    else:
        q.intent = "search"

    # Genres — check user text against all known terms, map to DB-canonical names
    for term in GENRES:
        if term in lower:
            canonical = GENRE_ALIASES.get(term, term.title())
            if canonical not in q.genres:
                q.genres.append(canonical)

    # Year / decade
    decade_match = DECADE_PATTERN.search(text)
    if decade_match:
        decade_start = int(decade_match.group(1))
        q.year_from = decade_start
        q.year_to = decade_start + 9
    else:
        year_matches = YEAR_PATTERN.findall(text)
        if len(year_matches) == 1:
            q.year = int(year_matches[0])
        elif len(year_matches) >= 2:
            years = sorted(int(y) for y in year_matches)
            if years[-1] - years[0] <= 9 and years[0] % 10 == 0:
                # looks like a decade expressed as two years e.g. "2000 to 2009"
                q.year_from, q.year_to = years[0], years[-1]
            else:
                q.year_from, q.year_to = years[0], years[-1]

    # Minimum rating
    rating_match = MIN_RATING_PATTERN.search(text)
    if rating_match:
        try:
            q.min_rating = float(rating_match.group(2))
        except ValueError:
            pass

    # Director
    director_match = re.search(
        r"(?:directed by|director[:\s]+)\s*([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
        text,
        re.IGNORECASE,
    )
    if director_match:
        q.director = director_match.group(1).strip()

    # Title hint for lookup intent
    title_patterns = [
        r"(?:tell me about|about the movie|about)\s+[\"']?([^\"'?]+)[\"']?",
        r"(?:plot of|synopsis of|cast of|director of)\s+[\"']?([^\"'?]+)[\"']?",
        r"(?:who directed|who made|who starred in)\s+[\"']?([^\"'?]+)[\"']?",
        r"(?:when was)\s+[\"']?([^\"'?]+?)\s+(?:made|released)[\"']?",
    ]
    for pattern in title_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            q.title_hint = m.group(1).strip().rstrip("?.,")
            break

    return q
