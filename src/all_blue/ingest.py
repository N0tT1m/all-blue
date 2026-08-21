"""The ingest job: library.yaml -> TMDB -> upsert series, seasons, episodes.

Contract from SPEC.md slice 1:
  - Upsert via ON CONFLICT (source, source_id) DO UPDATE. Running twice must
    leave the row count unchanged.
  - Walk every page. A few hundred episodes means you got paginated.
  - Refuse to run if it would remove more than 10% of existing rows, and say why.
  - Plex watch-history sync is a separate step, skipped cleanly when PLEX_TOKEN
    is unset.
"""


def run():
    raise NotImplementedError


def sync_watch_history():
    """From /status/sessions/history/all into watch_event. No-op without a token."""
    raise NotImplementedError


def coverage_report():
    """Episodes with a non-empty synopsis, overall and per series."""
    raise NotImplementedError
