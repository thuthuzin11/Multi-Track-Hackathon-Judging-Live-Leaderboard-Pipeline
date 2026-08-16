# Multi-Track Hackathon Judging & Live Leaderboard Pipeline

A distributed score-processing pipeline for university hackathons with
multiple judging tracks, three account types, and a scheduled event
lifecycle. Built to match the project slide deck:

```
Judges (own accounts) -> FastAPI -> Redis Track Buffers -> Parallel Workers ->
Map-Reduce -> PostgreSQL (authoritative) -> Redis (fast reads) -> Leaderboard
```

**No Docker.** Everything runs as plain local processes: PostgreSQL,
Redis, the FastAPI server, the worker manager, and the React frontend,
each in its own terminal. To let judges and spectators join from their
own devices on different WiFi networks, see [`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

## Who can do what

| | Sign-up / login | Can do |
|---|---|---|
| **Viewer** | Email only, no password | View the live leaderboard. Nothing else. |
| **Judge** | Username + password (admin creates the account) | Pick a track/team, submit scores, view their own past scores and edit them, view the leaderboard. |
| **Admin** | Username + password | Create/edit/delete events, tracks, teams, and judge accounts. Set each event's start/end time. View the leaderboard and the raw results table at any time, including after an event ends. |

Landing on the site shows three tabs — **View Results**, **Judge**,
**Admin** — so each kind of user lands on exactly the login/signup they
need.

---

## Key behaviors this version adds

- **Editing a score doesn't double-count it.** Each judge can only ever
  have one score on record per team (enforced with a database unique
  constraint on `judge_id + team_id`). Re-scoring a team you've already
  judged overwrites your previous numbers — `num_scores` on the
  leaderboard always equals the number of *distinct judges*, never the
  number of submissions.
- **Events have a schedule, and can't be started in the past.** An
  admin sets a start time and end time per event; the start time must
  be now or later (enforced server-side, not just in the date picker).
  The system computes a live status — `Upcoming`, `Ongoing`, or
  `Finished` — shown as a badge everywhere the event appears.
- **Scoring locks automatically when an event ends.** Once the end time
  passes, `POST /api/scores` is rejected server-side (not just hidden
  in the UI) with a clear "this event has ended" message. Judges and
  viewers can still see the leaderboard; they just can't change it.
- **The leaderboard is scoped to one event at a time.** "Current event"
  = whichever event was created most recently. The Live Leaderboard,
  the countdown banner, and the judge's track picker all follow it
  automatically — the previous event's results and tracks quietly stop
  appearing the moment a new event is created, with nothing to delete
  or archive by hand. See "How 'current event' works" below for the
  exact rule and its trade-offs.
- **A live countdown banner** shows the current event's name, start
  time, end time, and status everywhere it's relevant (Live
  Leaderboard, Judge dashboard, Admin dashboard) — "Starts in 2h 15m",
  "Ends in 42m 10s", or "Ended 1h ago", ticking every second, always in
  the viewer's own local time.
- **Judges only ever see the current event's tracks.** Tracks that
  belonged to a past event never appear in the scoring form's track
  picker, even if that judge scored them before a newer event existed.
  Their scoring history still shows those old scores (for their own
  reference) but marks them "Past event" instead of offering to edit.
- **Full admin CRUD with safety rails.** Deleting an event/track/team/
  judge that's still referenced elsewhere (a track with teams, a judge
  who's already scored something) is blocked with an explanation
  instead of silently corrupting data.

### How "current event" works

The rule is intentionally simple: **the most recently created event is
current**, full stop — regardless of its own start/end times. Creating
event B while event A is still ongoing immediately switches the
leaderboard and judges' track picker to B, even if B hasn't started
yet (it'll just show "no scores yet" until it does).

This matches "one event live at a time," which is how most hackathons
actually run. If your use case needs two events genuinely running
side-by-side, or the ability to flip back to an older event without
creating a new one, see the **Ideas for extending this** section below
— the data model already keeps every event's results separately
(`leaderboard:event:{id}` in Redis), so that's a UI/API change, not a
redesign.

---

## Ideas for extending this

A few things worth considering as your next steps, roughly in order of
how much they'd change:

- **An explicit "make this the current event" toggle**, instead of
  "most recent wins." Useful if you ever prep next month's event while
  this month's is still running, or want to switch back to an older
  one to show final results without touching Admin. Backend-wise this
  is small: an `is_current` boolean on `Event` (unique-true via a
  partial index or just enforced in `crud.py`), and swap
  `get_current_event()`'s "order by id desc" for "where is_current".
- **An event archive/history view** for spectators — a dropdown to
  browse *any* past event's final leaderboard, not just the current
  one. The per-event Redis keys already exist for this
  (`/api/leaderboard?event_id=...` already works); it's mostly a
  frontend addition (an "Archive" tab with an event picker).
- **Let an admin end an event early** with one click ("End Now")
  instead of having to edit the end time — small addition to
  `routers/admin.py`, sets `end_date = now`.
- **WebSocket push** instead of the 2-second leaderboard poll and
  1-second countdown tick, for a slightly snappier feel at large
  screen displays / venue projectors.
- **Judges assigned to specific tracks**, if your event ever has judges
  who shouldn't score every track — right now any judge can score any
  track in the current event.
- **Prevent overlapping events** (reject creating a new event whose
  start time falls inside an existing un-finished event's window) if
  "one event at a time" should be enforced rather than just assumed.

None of these are needed for what's built now — just worth having on
the radar as the project grows.

---

## How it demonstrates distributed programming

| Slide concept          | Where it lives in the code |
|-------------------------|-----------------------------|
| Concurrency              | Many judges can `POST /api/scores` at once; FastAPI + async Redis writes handle it without blocking |
| Partitioning              | Each track gets its own Redis list: `track_buffer:{track_id}` (`backend/app/config.py`) |
| Parallel processing       | `run_workers.py` spawns one **OS process** per track via `multiprocessing` (`backend/app/worker.py`) |
| Map-Reduce                | MAP: turn a raw submission into a weighted score. REDUCE: re-aggregate a team's scores into `final_score` (`worker.py`) |
| Write buffering           | The API never writes to Postgres directly — it only pushes to Redis and returns 202 immediately (`backend/app/routers/scores.py`) |
| Caching                   | Redis sorted sets (`ZADD`) power `GET /api/leaderboard` so spectator traffic never touches Postgres |
| Eventual consistency      | There's a small delay between "score accepted" and "leaderboard reflects it" while a worker processes the buffer |

---

## Prerequisites (install once)

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL** (14+) running locally
- **Redis** (6+) running locally

Quick local installs:

- macOS: `brew install postgresql redis` then `brew services start postgresql` and `brew services start redis`
- Ubuntu/Debian: `sudo apt install postgresql redis-server`
- Windows: install PostgreSQL from postgresql.org, and Redis via [Memurai](https://www.memurai.com/) or WSL

Create the database once:

```bash
createdb hackathon
# or: psql -U postgres -c "CREATE DATABASE hackathon;"
```

> **Upgrading from an earlier version of this project?** This version
> added new tables/columns (Viewers, Admins, event start/end times, the
> unique constraint on scores). There's no migration tool set up, so
> the simplest path is a fresh database: `dropdb hackathon && createdb hackathon`.

---

## 1. Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # set JWT_SECRET to a random string
```

**Terminal A — API server:**

```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal B — worker manager:**

```bash
python run_workers.py
```

**Terminal C — create your first admin login** (required once; there's
no other way to get an admin account, since creating one normally
requires already being logged in as an admin):

```bash
python seed.py
```

This only creates the database tables and one admin account (username
`admin` / password `adminpass1` by default — override with
`ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars, recommended). It does
**not** create any demo events, tracks, teams, or judges — you create
all of that yourself from the Admin dashboard after logging in. Safe to
re-run; it won't overwrite an existing admin.

API docs: `http://localhost:8000/docs`

---

## 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## 3. Running the demo

1. Open the site — you'll land on the three-tab sign-in screen.
2. **Admin** tab: log in with the account from `seed.py`. Create an
   event (start time now/soon, end time later), a track, a team or
   two, and a judge login account — all from the Admin dashboard.
3. **Judge** tab: log in with the judge account you just created. Pick
   the track and team, set the sliders, submit. Notice **My Submitted
   Scores** on the right — pick "Edit" on one and re-submit; watch the
   leaderboard's `# Judges` column *not* increase.
4. **View Results** tab: sign up with any email — no password — and
   you're on the live leaderboard immediately.
5. Back on **Admin**: try editing the event's end time to a few
   seconds in the future, save, then flip back to the Judge tab and
   try submitting — scoring locks itself out once the badge flips to
   "Finished."
6. Watch `run_workers.py`'s terminal — you'll see `created` vs
   `updated` in the log lines depending on whether a submission was a
   new score or an edit.
7. Try deleting a track that still has teams on the Admin tab — it's
   refused with an explanation instead of silently breaking things.
8. Try creating a new event from Admin with a start time in the past —
   it's rejected with a clear message. Try a start time a few minutes
   from now instead — it's accepted, and the countdown banner on every
   tab starts counting down to it.
9. Create a second event (any name, starting soon). Flip to **Live
   Leaderboard** — it immediately switches to the new (empty) event;
   the old event's results are still in the database, just not shown
   here anymore. Flip to **Judge** — the track picker now only offers
   the new event's tracks.

---

## Judges and viewers on their own devices, from anywhere

See **[`DEPLOYMENT.md`](./DEPLOYMENT.md)** for a quick ngrok tunnel
(same-day event) or a proper free-tier deployment (Render + Vercel,
reusable next time) — no Docker in either path.

---

## Project structure

```
backend/
  app/
    main.py             FastAPI app, CORS, router registration
    config.py            env settings, Redis key naming, JWT settings, scoring weights
    database.py           SQLAlchemy engine/session (PostgreSQL)
    redis_client.py        Redis connection pool
    auth.py                 password hashing, JWT issue/verify, per-role dependencies
    models.py                Event (with computed .status), Track, Team, Judge, Admin,
                              Viewer, Score (unique per judge+team), Result
    schemas.py                 Pydantic request/response models
    crud.py                      create/update/delete helpers with referential-integrity guards
    worker.py                     multiprocessing workers: MAP-REDUCE, upserts scores by (judge, team)
    routers/
      auth.py                      viewer signup, judge login, admin login, unified /me
      catalog.py                    read-only events/tracks/teams for any signed-in role
      admin.py                       full CRUD: events, tracks, teams, judges (admin-only); raw results
      scores.py                       submit (blocked once event finished) + "my scores" (judge-only)
      leaderboard.py                   fast reads from Redis sorted sets (any signed-in role)
  run_workers.py          entrypoint: spawns/monitors one worker per track
  seed.py                   creates the DB tables + your first admin login (nothing else)
  requirements.txt
  .env.example

frontend/
  src/
    api.js                 fetch wrapper: session storage (role + token), all endpoint calls
    App.jsx                  session bootstrap, role-based tab navigation
    components/
      LandingAuth.jsx          three-tab entry: viewer signup / judge login / admin login
      JudgeDashboard.jsx         score form w/ edit-prefill + event-ended lock, "My Scores" list
      AdminDashboard.jsx          Events/Tracks/Teams/Judges CRUD w/ schedule + status badges
      EntityManager.jsx            reusable create/edit/delete list panel (supports datetime fields)
      SpectatorLeaderboard.jsx      live leaderboard (global + per-track), event status badge
    styles.css
  vite.config.js
  package.json

DEPLOYMENT.md             reaching judges/spectators on other networks, no Docker
```

---

## API summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/viewer/signup` | — | email-only signup/login for spectators |
| POST | `/api/auth/judge/login` | — | judge sign-in |
| POST | `/api/auth/admin/login` | — | admin sign-in |
| GET | `/api/auth/me` | any | validate a stored session, fetch fresh profile |
| GET | `/api/catalog/events` `/tracks` `/teams` | any | read-only browsing for judges/viewers |
| POST/GET/PUT/DELETE | `/api/admin/events[/{id}]` | admin | manage events (name, start/end time) |
| POST/GET/PUT/DELETE | `/api/admin/tracks[/{id}]` | admin | manage tracks |
| POST/GET/PUT/DELETE | `/api/admin/teams[/{id}]` | admin | manage teams |
| POST/GET/PUT/DELETE | `/api/admin/judges[/{id}]` | admin | manage judge login accounts |
| GET | `/api/admin/results` | admin | raw `results` rows from PostgreSQL |
| POST | `/api/scores` | judge | submit/edit a score → Redis buffer, `202`; `403` if event finished |
| GET | `/api/scores/mine` | judge | this judge's own submitted scores |
| GET | `/api/leaderboard?event_id=` (optional) | any | current event's leaderboard by default, or a specific event's |
| GET | `/api/leaderboard/track/{id}` | any | one track's leaderboard, from Redis |

Full interactive docs: `http://localhost:8000/docs`

---

## Scoring formula (from the slide deck)

```
Final Score = Technical×0.40 + Innovation×0.30 + Presentation×0.20 + Impact×0.10
```

Computed once per judge/team pair at write time
(`worker.py: compute_weighted_score`). A team's `final_score` is the
**average** of all weighted scores it has received — one per distinct
judge, recomputed every time a score is created or edited.

---

## Future improvements (from the slide deck, not yet implemented)

- WebSocket push instead of polling for the leaderboard
- Message queue (e.g. RabbitMQ/Kafka) instead of Redis lists for buffering
- Multiple API instances behind a load balancer
- Worker auto-scaling
- Fault tolerance, monitoring, and load/performance testing
