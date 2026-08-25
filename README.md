# All Blue

An anime library you can talk to — semantic search over episodes, a recommender trained on what you actually watch, and an agent that can queue and play. A grammar router keeps the model out of the hot path.

Named for the sea where fish from all four seas gather: one library holding everything.

## Why it exists

This is a portfolio and skills project, which changes what "done" means. **The goal is not a working app — it's being able to explain every layer of one.** An app you can't explain is worth less than a smaller one you can.

Three rules follow:

1. **No code I can't explain line by line** — not roughly what it does, but why that structure, what happens when it fails, what changes at 10x the data.
2. **Naive version first, then the good one** — cosine similarity in numpy before pgvector, a `for` loop before a query optimiser. You can't appreciate what an abstraction buys until you've felt its absence.
3. **Every slice ships end to end** — no half-built layers waiting on each other.

## Stack

Python 3.12 · FastAPI · Postgres (psycopg) · uv · pytest

## Layout

```
src/all_blue/
  api.py         HTTP surface
  ingest.py      library ingestion
  db.py          Postgres access
  config.py      env-driven settings
  sources/       anilist · plex · tmdb
migrations/       001_content.sql
library.yaml      library definition
```

## Running

```bash
cp .env.example .env      # fill in source credentials
docker compose up -d      # Postgres
uv sync
uv run uvicorn all_blue.api:app --reload
uv run pytest
```

See `SPEC.md` for the full design and the reasoning behind each slice.
