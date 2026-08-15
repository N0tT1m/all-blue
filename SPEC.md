# All Blue — spec

An anime library you can talk to. Semantic search over episodes, a recommender
trained on what you actually watch, and an agent that can queue and play — with
a grammar router so the model stays out of the hot path.

Named for the sea where every fish from all four seas gathers — one library
holding everything. Nothing in the code depends on the name; rename freely.

---

## Why this exists

This is a portfolio and skills project. That changes what "done" means, so it's
worth being explicit:

**The goal is not a working app. The goal is that you can explain every layer of
a working app.** An app you can't explain is worth less than a smaller one you
can, because the thing being evaluated in an interview is your understanding,
not your repo.

Three rules that follow from that:

1. **Don't commit code you can't explain line by line.** Not "roughly what it
   does" — why that structure, what happens when it fails, what you'd change at
   10x the data.
2. **Build the naive version first, then the good one.** Cosine similarity in
   numpy before pgvector. A `for` loop before a query optimiser. You can't
   appreciate what an abstraction buys you until you've felt its absence.
3. **Every slice ships end to end.** No half-built layers waiting on each other.
   You should be able to demo something after every slice.

Use AI as a tutor and reviewer here, not as an author. Ask it why, ask it to
critique, ask it what breaks — but type the implementation yourself.

---

## Non-goals

Writing these down because scope creep is the failure mode that killed the last
attempt at learning this properly.

- **Not a general media server.** No movies, no live TV, no transcoding, no
  mobile app. Plex already does that and you're not competing with it.
- **Not multi-user.** One user. No auth beyond a shared token. Adding users
  later is a schema change, not a rewrite.
- **Not a microservice fleet.** One API process, one database, one worker. Split
  it only when something actually hurts.
- **Not fine-tuning.** Retrieval, routing and evaluation are the employable
  skills and they're where the real engineering is. Training a model is a
  different job and you don't need it to prove this competence.
- **Not real-time anything.** Batch jobs are fine. Streaming is a distraction.

---

## Stack

| | choice | why |
|---|---|---|
| language | Python 3.12 | slices 2+ are embeddings and ML; Python removes friction where you'll be learning the most. Go is a fine choice for ingest if you'd rather, but you'd be swimming upstream later. |
| API | FastAPI | async, typed, auto docs at `/docs` you'll use constantly |
| DB | Postgres 16 + pgvector | pgvector comes in slice 2 — install the extension now, use it later |
| migrations | plain numbered `.sql` files + a tiny runner | you have first-hand evidence of what untracked migrations cost. Record what's applied in a `schema_migrations` table from day one. |
| deps | `uv` | already on your machine, fast, no venv ceremony |
| tests | pytest | from commit one, not bolted on later |

Run Postgres in Docker locally. Don't point this at the existing platform's
database — a fresh one keeps the blast radius at zero and lets you drop and
rebuild freely while learning.

---

## Data sources

The app does **not** talk to Plex to work. Plex is where you watch; this is a
different thing that happens to be about the same shows. That decision makes the
whole project deployable, because everything it needs is public.

Three sources, split by what each is actually good at:

| source | gives you | key? | role |
|---|---|---|---|
| **TMDB** | per-episode title, overview, air date | free key | **primary** — the episode corpus |
| **AniList** | series description, genres, relations | none | enrichment — relations especially |
| **Plex** | *your* watch history | your token | optional, private layer |

### Why not AniList alone (verified 2026-08-14)

It has no episode-level synopses. A live query for One Piece returns a rich
series description, genres, and a clean relations graph — but `streamingEpisodes`
holds 69 entries for an 1,100-episode show, and they're titles from streaming
platforms, not summaries. Series-level metadata across your 11 franchises is
roughly 30 rows, which is far too small to be an interesting search problem.

So AniList is not the catalog. It **is** the best answer to the
Naruto→Shippuden→Boruto problem: its `relations` edges (`SEQUEL`, `PREQUEL`,
`SIDE_STORY`, `ALTERNATIVE`) are exactly the links Plex and TMDB don't have, and
`ALTERNATIVE` is how it distinguishes FMA from Brotherhood. Free, no key,
GraphQL at `https://graphql.anilist.co`. It's rate limited — read the response
headers rather than guessing, and cache aggressively since this data never
changes.

### TMDB is the episode corpus

Free API key from a TMDB account. TV endpoints give season and episode listings
with an `overview` per episode, which is what slice 2 embeds.

**Its coverage for very long anime is the biggest unknown in this project** and
is the first thing to check — see Open risks.

### Plex is optional and private

The only thing it has that public sources don't is *your* watch history, which
the slice-3 recommender wants and which can't be reconstructed later. Treat it as
a sync job that may be absent: the app must run fine with zero Plex
configuration, because the deployed instance will have exactly that.

---

## Environment (verified 2026-08-14)

| what | where | notes |
|---|---|---|
| TMDB | `api.themoviedb.org` | free key, **required** — the episode corpus |
| AniList | `graphql.anilist.co` | no key, verified answering 2026-08-14 |
| Plex server | `192.168.1.74:32400` | v1.43.3, claimed. **Optional** — watch history only. `/identity` answers unauthenticated; everything else 401s. |
| NAS shares | `192.168.1.66` | SMB open. Not used by this app — Plex reads them, you watch there. |

Keys live in `.env`, which is in `.gitignore` from the first commit, before any
key is pasted anywhere.

### Getting the optional Plex token

Only needed for watch-history sync; skip it entirely on the first pass if you
want. Open Plex Web, browse to any episode, "Get Info" → "View XML" — the URL
ends in `?X-Plex-Token=...`. Treat it as a password; it's full account access.

Verify before use:

```bash
curl -s -H "Accept: application/json" \
  "http://192.168.1.74:32400/library/sections?X-Plex-Token=$PLEX_TOKEN" | jq '.'
```

The endpoint that matters is `/status/sessions/history/all` — the actual view
log. The `viewCount` / `lastViewedAt` fields on an episode are aggregates and
lose everything but the most recent watch.

---

## Data model

The one design decision that's expensive to unwind, so it gets the most thought.

Anime is the only content today, but the shape is deliberately generic: `kind`
plus a self-referencing `parent_id`. Adding films or live-action TV later becomes
a new data source, not a schema rewrite.

```sql
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
    source            text NOT NULL,   -- 'plex'
    source_id         text NOT NULL,   -- plex ratingKey
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
```

### Why each decision

**`UNIQUE (source, source_id)`** is what makes ingest idempotent. Re-running the
job must update rows, not duplicate them. Write the upsert as
`ON CONFLICT (source, source_id) DO UPDATE` from the start — retrofitting
idempotency after you have duplicates is miserable.

**`absolute_ordinal` separate from `ordinal`** is an anime-specific problem worth
understanding now. One Piece episode 1015 is season 21 episode 43 depending on
who's counting, and different sources disagree. Storing both means you can answer
either question instead of picking a side.

**No file paths, no `media_file` table.** The app never opens a video — Plex does
that, and you watch there. Dropping files removes NAS mounts, SMB credentials,
path translation between Windows and macOS, and an entire class of bug from the
project. Ownership lives in `library.yaml` at franchise level, which is all the
recommender needs ("don't suggest something he doesn't have").

**A source going quiet is not a deletion.** Kept from the original draft because
the lesson generalises past files: if an ingest run sees far less than the last
one — API error, expired key, rate limit returning empty pages — that looks
identical to "everything was removed". A scan that acts on it destroys the
catalog, which has already happened once on the other platform via an unreachable
share. If a run would delete more than 10% of rows, it must refuse and say why.

**`watch_event` as an event log, not a `view_count` column.** The recommender in
slice 3 needs to know *when* and *how far*, not just how many times. Aggregates
are cheap to compute from events; events are impossible to recover from
aggregates.

---

## Your actual corpus — and what it will do to you

Attack on Titan · One Piece · Fullmetal Alchemist (both) · Naruto + Shippuden +
Boruto · Dragon Ball (all) · Frieren · Hunter x Hunter · Demon Slayer · Pokémon
(all) · Spy x Family.

Roughly **4,500–5,000 episodes** across ~11 franchises. That's a good size: big
enough that semantic search is a real problem worth solving, small enough that
embedding the whole thing is cheap.

It also contains, by luck, most of the classic catalog-modeling landmines. Here
they are in order of how much they'll hurt, so none of them surprises you.

**1. Two adaptations of the same source.** FMA (2003) vs Brotherhood. Hunter x
Hunter (1999) vs (2011). Separate series that retell the same early arcs, so
their episode synopses are near-identical. In slice 2 these will come back as
duplicate search results and you will think your embeddings are broken. They
aren't — the data really is that similar. Fix it at search time by grouping
results per series, never by deleting rows.

**2. An alternate cut of the same show.** Dragon Ball Z vs Kai: same story,
recut, different episode boundaries. Worse than #1, because it isn't merely
similar — it's the same scenes renumbered. Plex will treat them as separate
series, which is correct. Expect Kai to dominate any "similar episodes" result
against Z.

**3. Pokémon's numbering.** ~1,300 episodes across ~25 regional series. Depending
on your Plex agent and folder naming, it's either one show with 25 seasons or 25
separate shows. Either way `ordinal` and `absolute_ordinal` will diverge
dramatically. **This is the best test case you have for that column pair** — get
Pokémon right and the rest of the library is easy.

**4. Split-cour and arc-named seasons.** AoT's Final Season Parts 1/2/3. Demon
Slayer's seasons named by arc (Mugen Train, Entertainment District, Swordsmith
Village). Spy x Family Part 1/2. Plex's season numbers will not match what anyone
actually calls these. Put Plex's number in `ordinal` and the human name in
`title`, and don't try to reconcile them in slice 1.

**5. Continuations filed as separate series.** Naruto → Shippuden → Boruto.
Dragon Ball → Z → Super. One story, three unrelated `content` rows. "What should
I watch next" can't work across that gap until they're linked — and Plex has no
idea they're related, while AniList does. That's a `series_relation` table in a
later slice. Don't build it now; just don't be surprised when you hit it.

**The schema above already handles all of this.** No change to migration `001`
is needed — `kind` + `parent_id` + the two ordinals covers every case, and
relations and dedup are additive later. That's the payoff for spending the
thought on the content model up front.

### Sanity numbers

Ballparks to check your ingest against. **Verify against Plex; don't trust
these** — they're from memory of the franchises, not from your server.

| | eps | | eps |
|---|---|---|---|
| Pokémon (all) | ~1,300 | Hunter x Hunter (both) | ~210 |
| One Piece | ~1,100 | FMA (both) | ~115 |
| Naruto + Shippuden + Boruto | ~1,000 | Attack on Titan | ~94 |
| Dragon Ball (all, incl. Kai) | ~800 | Demon Slayer | ~63 |
| | | Spy x Family | ~37 |
| | | Frieren | ~28 |

**If ingest returns a few hundred episodes, you've hit pagination.** Every API
here pages, and none of them shout about it — TMDB returns a `page` /
`total_pages` pair that's easy to ignore, and AniList caps `perPage` at 50. Walk
the pages until they run out; don't assume one request is the whole answer.
Against a ~5,000-episode corpus this is the most likely slice-1 bug and it fails
*silently*, which is exactly why the acceptance criteria compare per-series
counts against the source's own reported totals instead of just checking that
rows appeared.

---

## Open risks — read before writing code

Three things this spec doesn't fully answer. Two of them can invalidate work
you've already done, so they get checked in slice 1 even though they pay off
later.

### 1. ~~Episode synopsis coverage~~ — RESOLVED 2026-08-14

This was the risk that could have invalidated the plan. It's answered: **4,789
episodes across your 18 series, 99% with a non-empty overview.** Measured
directly against TMDB, every season of every show.

| show | tmdb | episodes | coverage |
|---|---|---|---|
| Pokémon | 60572 | 1,235 | 100% |
| One Piece | 37854 | 1,181 | 99% |
| Naruto Shippūden | 31910 | 500 | 100% |
| Boruto | 70881 | 293 | 100% |
| Dragon Ball Z | 12971 | 291 | 100% |
| Naruto | 46260 | 220 | 100% |
| Dragon Ball Z Kai | 61709 | 158 | 100% |
| Dragon Ball | 12609 | 153 | 100% |
| Hunter x Hunter (2011) | 46298 | 148 | 100% |
| Dragon Ball Super | 62715 | 131 | 100% |
| Attack on Titan | 1429 | 87 | 100% |
| Dragon Ball GT / FMA:B / Demon Slayer / HxH '99 / Spy x Family / FMA / Frieren | — | 64 / 64 / 63 / 62 / 50 / 51 / 38 | 100% |

Slice 2 is viable exactly as written. The ids are resolved in `library.yaml`.

Two things that fell out of the measurement and are worth keeping:

**Pokémon is ONE show with 25 seasons**, not 25 separate shows. That was an open
question in the corpus section; it's now settled, and it makes Pokémon the
sharpest test of `ordinal` vs `absolute_ordinal`.

**A title search for "One Piece" returns the 2023 Netflix live-action first**
(id 111110, not 37854). Hunter x Hunter returns two ids under an identical
title. This is exactly why `library.yaml` is hand-written, and it's the concrete
justification if anyone asks why you didn't automate the matching.

### 2. Your own watch history is the private half

Public sources know everything about the shows and nothing about you. The
slice-3 recommender needs your history, and Plex is the only place it exists.

VPN or Tailscale means *you* can reach Plex from anywhere, which is real — but
it doesn't help a stranger opening your demo, so the app can never require it.
Structure it so Plex is a sync job that fills `watch_event` when configured and
is simply absent when it isn't. The deployed instance runs with no Plex at all
and everything except personalised recommendations still works.

### 3. Watch history cannot be backfilled

Everything else re-derives by re-running ingest. Watch history can't: Plex prunes
it, and once a view falls off the end it's gone forever.

So **capture it early even though nothing uses it until slice 3.** The
`viewCount` / `lastViewedAt` fields on an episode are lossy aggregates — the last
time you watched, not the twelve times before. The real log is
`/status/sessions/history/all`. Start collecting now and you'll reach slice 3
with months of signal instead of a snapshot.

This is the one piece of Plex work worth doing in slice 1, and it's the only
reason the token appears in this spec at all.

### 4. Matching your library to TMDB

Public sources don't know what you own. You need a link between "the shows I
have" and their TMDB ids, and matching by title string is where this gets ugly —
"Fullmetal Alchemist" matches two different series, Pokémon's regional seasons
are filed inconsistently, and romaji vs English titles rarely agree.

With ~11 franchises, **resolve them by hand.** A checked-in `library.yaml`
mapping your shows to TMDB (and AniList) ids is fifteen minutes of work and
removes an entire category of bug. Fuzzy title matching is a fine engineering
problem, but it's not one that teaches you anything about AI, and at this scale
it's pure cost. Automate it only if the library grows past what you'll hand-edit.

That file is also what makes the public demo honest: it's the seed list, it's
public data, and it contains nothing personal.

### Smaller things worth knowing

**If you publish the repo, your watch history is in it.** Not sensitive, but
decide deliberately rather than discovering it later. The public demo should seed
from `library.yaml` with no watch data at all.

**Cache every API response to disk during development.** TMDB and AniList are
rate limited and your corpus is thousands of episodes. A dumb
`cache/{source}/{id}.json` layer will save you hours and makes your tests
runnable offline.

**Budget.** Slice 1 is a weekend. If it's taking two weeks, the scope grew —
re-read the non-goals.

---

## Slice 1 — ingest (no AI at all)

Get clean data in and query it. This is the foundation everything else stands on,
and it's the layer most people building AI apps are weakest at.

**Build:**

1. `schema_migrations` table and a migration runner (~30 lines).
2. Migration `001` creating the tables above.
3. `library.yaml` — your shows mapped to TMDB ids, resolved by hand.
4. A TMDB client: seasons and episodes for a series. HTTP only, returns plain
   dicts, no knowledge of your schema, responses cached to disk.
5. An ingest job: upsert series, seasons, episodes.
6. Watch-history sync from Plex into `watch_event`, **skipped cleanly when
   `PLEX_TOKEN` is unset**. Nothing consumes it until slice 3; capture it now
   because it's unrecoverable (Open risks #3).
7. `GET /content?q=` — substring title search, paginated.
8. `GET /content/{id}` — one item plus its children.
9. `GET /series/{id}/episodes` — ordered correctly.
10. A coverage report: how many episodes have a non-empty overview, overall and
    per series. This is the number Open risk #1 turns on.

**Acceptance criteria** — these are the spec, not suggestions:

- [ ] Running ingest twice in a row leaves the row count unchanged.
- [ ] Series episode counts match TMDB's own reported season/episode counts.
      **Per series, not in total** — a plausible total hides one truncated show.
- [ ] Total episode count is in the thousands, not the hundreds. If it isn't,
      you're being paginated (see above).
- [ ] Pokémon and One Piece both ingest completely, and their episodes come back
      in the right order. They're the two that will break first.
- [ ] Every episode resolves to a series through `parent_id`.
- [ ] Episodes come back in correct order, including across season boundaries.
- [ ] Every series in `library.yaml` resolved to a real TMDB id and ingested.
- [ ] Ingest **refuses to run** if it would remove more than 10% of existing
      rows, and says why.
- [ ] `pytest` passes, covering: the upsert is idempotent, ordering is right,
      and the mass-deletion guard actually trips.
- [ ] **Synopsis coverage is reported and you've read it.** Not a pass/fail —
      the number decides whether slice 2 starts with embeddings or with AniList
      enrichment. Below ~70% and the plan changes.
- [ ] `watch_event` has rows, and re-running ingest doesn't duplicate them.
- [ ] The whole app runs with `PLEX_TOKEN` unset — catalog, search, everything
      except watch history. That's the mode the public demo runs in, so it can't
      be an afterthought.

**Deliberately not in this slice:** embeddings, any model, a frontend, auth,
AniList enrichment.

---

## Later slices — the arc, not the plan

Sketched so you can see where it goes. **Don't build these yet.** Each gets its
own spec when you reach it, informed by what slice 1 taught you.

**Slice 2 — embeddings and semantic search.** Embed episode synopses. Compute
cosine similarity in numpy by hand first, then move to pgvector and confirm you
get the same answers. Hand-label ~20 queries with their expected episodes and
measure recall@5. That test set is your first eval and the habit that matters
most.

**Slice 3 — the recommender.** From `watch_event`, not from ratings. Start with
"more like what you finished", measure it, then get fancier. This is the slice
that proves you can do ML that isn't an LLM.

**Slice 4 — the agent loop, written from scratch.** No LangChain. Roughly 200
lines: send messages plus tool schemas, parse tool calls, dispatch to handlers,
feed results back, loop until it stops. This is the single most valuable thing
here to have written yourself, and it's much smaller than it looks. Tools:
search, queue, play, "what should I watch".

**Slice 5 — the router, evals, and deploy.** A grammar handles "play the next
episode of X" without a model; the model handles the rest. Instrument cost and
latency per path. Publish it with a README that leads with those numbers.

---

## What "finished" looks like

Portfolio projects sprawl because nobody defines the end. This one is done when:

- [ ] A public repo with a README that opens with **numbers** — corpus size,
      search recall, router hit rate, p95 latency and cost per request — not a
      feature list.
- [ ] A URL someone can click, running on public metadata, where search and
      recommendations work without access to your files.
- [ ] `pytest` green, including the eval suite, runnable by a stranger from a
      clean checkout.
- [ ] One written piece explaining a non-obvious decision you made and what it
      cost — the kind of thing you'd talk through in an interview.

That's the whole deliverable. Anything not serving one of those four is scope
creep, however fun it is.

---

## Repo layout

```
all-blue/
  SPEC.md
  README.md              # write this LAST — it's the portfolio artifact
  library.yaml           # your shows -> tmdb/anilist ids. public, hand-written
  .env.example           # TMDB_API_KEY, DATABASE_URL, optional PLEX_*
  docker-compose.yml     # postgres + pgvector
  migrations/
    001_content.sql
  cache/                 # gitignored — raw API responses during dev
  src/all_blue/
    config.py
    db.py
    sources/
      tmdb.py            # episodes — HTTP only, no business logic
      anilist.py         # relations — later slice
      plex.py            # watch history — optional, may be absent
    ingest.py            # the job
    api.py               # FastAPI
  tests/
    fixtures/            # real API responses, saved while exploring
    test_ingest.py
```

Everything under `sources/` speaks HTTP and returns plain dicts — no knowledge of
your schema, no business logic. That's what lets each source be tested against
saved fixtures instead of a live API, and what keeps a missing Plex token from
being a crash instead of a skipped step.

---

## First session checklist

Coverage is already answered (Open risk #1) and `library.yaml` is already
resolved, so slice 1 starts from a known-good position.

1. `git init`, `.gitignore` containing `.env`, first commit — **before** any key
   exists on disk.
2. TMDB key into `.env`. You already have one in
   `~/workspace/porn-projects/platform/nojiko/.env` (a v4 bearer token — send it
   as `Authorization: Bearer`, not as an `api_key` query param).
3. Sanity-check the key yourself against one show, so you've seen the response
   shape with your own eyes rather than trusting this document.
4. Postgres up in Docker; confirm you can connect.
5. **Probe Pokémon first, not Frieren.** The instinct is to start with something
   clean and small; resist it. Frieren is 28 episodes in one tidy season — it'll
   parse first try and give you false confidence in a parser that then falls
   apart on the real library. Pokémon is ~1,300 episodes across ~25 regional
   series and breaks every assumption at once: how TMDB splits the regional
   series, whether you're being paginated, and what `ordinal` vs
   `absolute_ordinal` actually has to hold. Design against your hardest case and
   the easy ones come free.
6. **Read the JSON properly** before writing a parser — which fields are present,
   which are missing, where reality disagrees with this document. Save real
   responses into `tests/fixtures/` as you go; that's what you'll test against,
   and it costs nothing at that moment.
7. Hand-write `library.yaml` for your 11 franchises.

Steps 3, 5 and 6 are the real work. Everything after them is typing.

### Verify each franchise landed

Once ingest runs, walk the list rather than trusting a total. One truncated show
hides easily inside a plausible-looking number.

- [ ] Attack on Titan — check the Final Season parts didn't collapse into one
- [ ] One Piece — the long-tail test; absolute numbering must be right
- [ ] Fullmetal Alchemist — **two** series present, not one merged
- [ ] Naruto, Shippuden, Boruto — three separate series, all complete
- [ ] Dragon Ball, Z, Super, GT, Kai — Kai present and distinct from Z
- [ ] Frieren
- [ ] Hunter x Hunter — **both** the 1999 and 2011 series
- [ ] Demon Slayer — arc-named seasons kept their names
- [ ] Pokémon — the hard one; every regional series accounted for
- [ ] Spy x Family — Part 1/2 handled however Plex filed them

---

## How to use me on this

Ask me to review your schema before you write the ingest, and your ingest before
you write the API. Ask me why something is slow, what breaks at scale, what a
reviewer would object to.

Don't ask me to write the implementation. You already have a repo full of code
you didn't write; the point of this one is that it's yours.
