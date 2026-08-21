-- Slice 1. Schema as specified in SPEC.md "Data model".

CREATE TABLE content (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind              text NOT NULL CHECK (kind IN ('series','season','episode','film')),
    parent_id         uuid REFERENCES content(id) ON DELETE CASCADE,

    title             text NOT NULL,
    original_title    text,            -- romaji vs english; anime needs both
    synopsis          text,
    year              int,

    ordinal           int,             -- episode number within its season
    absolute_ordinal  int,             -- episode number across the whole series

    runtime_seconds   int,

    -- provenance: which system said so, and what it called it
    source            text NOT NULL,   -- 'tmdb' for the catalog, 'plex' for watch data
    source_id         text NOT NULL,
    added_at          timestamptz,
    updated_at        timestamptz NOT NULL DEFAULT now(),

    UNIQUE (source, source_id)
);

CREATE INDEX content_parent_idx  ON content(parent_id);
CREATE INDEX content_kind_idx    ON content(kind);

CREATE TABLE watch_event (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id       uuid NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    watched_at       timestamptz NOT NULL,
    progress_seconds int,
    completed        boolean NOT NULL DEFAULT false,
    source           text NOT NULL DEFAULT 'plex'
);

CREATE INDEX watch_event_content_idx ON watch_event(content_id, watched_at DESC);
