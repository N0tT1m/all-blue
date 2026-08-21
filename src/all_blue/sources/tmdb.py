"""TMDB client. HTTP only, returns plain dicts, no knowledge of the schema.

v4 bearer token: send as `Authorization: Bearer <token>`, not as an api_key
query param. Cache raw responses to cache/tmdb/{...}.json so tests run offline.
"""


def get_series(tmdb_id: int) -> dict:
    raise NotImplementedError


def get_season(tmdb_id: int, season_number: int) -> dict:
    raise NotImplementedError
