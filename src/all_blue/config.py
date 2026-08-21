"""Environment config. Loads .env; PLEX_* are optional and may be absent."""


def load():
    """Return settings: TMDB_API_KEY, DATABASE_URL, PLEX_BASE_URL, PLEX_TOKEN.

    PLEX_TOKEN unset is a supported mode, not an error — the deployed demo runs
    that way. Fail loudly only on a missing TMDB_API_KEY or DATABASE_URL.
    """
    raise NotImplementedError
