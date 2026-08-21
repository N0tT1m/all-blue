"""Plex client — watch history only. Optional; may be absent.

/status/sessions/history/all is the real view log. viewCount / lastViewedAt are
lossy aggregates. A missing token is a skipped step, never a crash.
"""


def history(base_url: str, token: str) -> list[dict]:
    raise NotImplementedError
