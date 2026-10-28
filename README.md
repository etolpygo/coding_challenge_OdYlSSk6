# Movie AI Agent

A conversational REST API that answers natural language questions about movies. It combines structured SQL queries against the MovieLens dataset with LLM-generated responses via [Ollama](https://ollama.com) (llama3.2).

## Dataset choice

MovieLens (small, ~9k movies, ~100k ratings) was chosen over TMDB 5000 because it is freely downloadable without any login — the ingestion script fetches it automatically from grouplens.org. It also has real user ratings rather than aggregated vote scores, which makes rating-based queries more meaningful.

The tradeoff is that MovieLens has sparse movie metadata: no plot overviews, cast, or director. TMDB 5000 would be the better choice if those fields were a priority (the LLM gives richer answers when it has an overview to work from), but it requires a Kaggle account to download. For a self-contained proof of concept, MovieLens wins on accessibility.

## How it works

```
User message
     │
     ▼
query_parser   → extracts intent (recommend / lookup / search),
                 genre, year, rating filters, title hint, director
     │
     ▼
movie_service  → builds a parameterised SQL query, returns matching movies
     │
     ▼
llm_service    → sends retrieved movie data + original question to llama3.2,
                 returns a natural conversational answer
     │
     ▼
ChatResponse   → { answer: "...", movies: [...] }
```

### Why structure-first, then LLM?

The key design decision is to do structured retrieval before calling the LLM, rather than giving the raw question to the LLM and letting it figure everything out.

**Accuracy and reliability.** If a user asks for "horror movies rated above 4 from the 1990s", a pure-LLM approach would either hallucinate film titles or require a very large context window stuffed with the entire dataset. SQL handles filters precisely and instantly — the LLM only sees the handful of movies that actually match.

**Separation of concerns.** The query parser and movie service are deterministic and testable: you can write unit tests that assert exact SQL results. The LLM is only responsible for the one thing it's good at — turning structured data into natural, readable prose. This makes the system easier to debug: if the answer is wrong about facts, it's a retrieval problem; if the tone is off, it's a prompt problem.

**Handling missing metadata.** Because MovieLens doesn't include plot overviews, cast, or director, the LLM prompt explicitly tells the model what fields are and aren't available. This prevents hallucination of plausible-sounding but invented details — the model is instructed to only discuss what the data actually contains.

**Trade-offs.** The regex-based query parser is intentionally simple — it's fast and transparent but won't handle complex or ambiguous phrasings well. A production system would replace it with an LLM-based intent classifier or a more sophisticated NLP pipeline. The current approach is a deliberate POC choice: easy to understand, easy to test, zero extra latency.

---

## Setup

### 1. Install Python 3.11 via pyenv

```bash
curl https://pyenv.run | bash
# Add pyenv to your shell — follow the printed instructions, then restart your shell

pyenv install 3.11.9
```

### 2. Create a virtual environment

```bash
cd coding_challenge
pyenv local 3.11.9          # pins this directory to Python 3.11.9
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start Ollama via Docker

For platform compatibility, the recommended approach is to run Ollama via Docker:

```bash
docker compose up -d                                      # start Ollama in the background
docker exec ollama ollama pull llama3.2                   # download the model (~2 GB, requires ~4 GB RAM)
```

Ollama will be available at `http://localhost:11434`. To stop it: `docker compose down`.

> **Native install:** download from [ollama.com/download](https://ollama.com/download), then run `ollama pull llama3.2 && ollama serve`.

### 4. Ingest the data

The script downloads the MovieLens dataset automatically — no login required.

```bash
python scripts/ingest.py
# Ingested 9742 movies and 22050 genre records.
```

### 5. Run the API

```bash
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send a natural language question, get a conversational answer |
| `GET` | `/movies` | List/filter movies (genre, year, min_rating, limit, offset) |
| `GET` | `/movies/{id}` | Get a single movie by TMDB ID |
| `GET` | `/health` | Health check |

---

## Example requests & responses

### Chat — recommend movies

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "recommend some great sci-fi movies from the 1990s"}'
```

```json
{
  "answer": "Here are some great sci-fi picks from the 1990s! The Matrix (1999) is rated 4.2/5 by MovieLens users — a genre-defining classic. Dark City (1998) is a visually striking neo-noir worth tracking down, and Twelve Monkeys (1995) is a tense time-travel thriller. All three are highly rated and well worth your time.",
  "movies": [
    {
      "id": 2571,
      "title": "The Matrix",
      "year": 1999,
      "overview": null,
      "rating_avg": 4.19,
      "rating_count": 341,
      "director": null,
      "cast": null,
      "genres": ["Action", "Sci-Fi", "Thriller"]
    }
  ]
}
```

### Chat — look up a specific movie

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "tell me about Inception"}'
```

```json
{
  "answer": "Inception (2010) is a Science Fiction and Thriller that's very well regarded by MovieLens users, with an average rating of 4.07 out of 5 from 196 ratings. It's one of the more highly rated films in the dataset — definitely worth a watch if you haven't seen it.",
  "movies": [{ "id": 79132, "title": "Inception", "year": 2010, "rating_avg": 4.07, ... }]
}
```

### Chat — filter by rating

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "action movies rated above 8"}'
```

### List movies with filters

```bash
curl "http://localhost:8000/movies?genre=horror&min_rating=7&limit=5"
```

### Get a single movie

```bash
curl http://localhost:8000/movies/27205
```

---

## Running tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

---

## Configuration

| Environment variable | Default | Description |
|----------------------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model name to use |

```bash
OLLAMA_MODEL=llama3.1:8b uvicorn app.main:app --reload
```
