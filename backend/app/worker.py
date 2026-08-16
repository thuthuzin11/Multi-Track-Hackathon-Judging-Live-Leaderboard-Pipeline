"""
Parallel worker processes.

Each track gets its own OS process (Python multiprocessing). A worker:

  1. Blocks on its track's Redis list ("track buffer") waiting for new
     raw score submissions -- this is the partition it alone owns.
  2. MAP: turns the raw submission into a weighted score for one judge/team pair.
  3. Writes the raw Score row to PostgreSQL (durable, authoritative).
  4. REDUCE: re-aggregates all of that team's scores into a single
     final_score / num_scores in the `results` table.
  5. Recomputes the ranking for the track (and for the whole event that
     track belongs to) and pushes it into Redis sorted sets so spectator
     reads never hit PostgreSQL.

Because step 1 is decoupled from the FastAPI request handler, score
submission returns immediately (fast writes) and the leaderboard becomes
*eventually consistent* a few hundred milliseconds later once a worker
gets to it.
"""

import json
import multiprocessing as mp
import signal
import time

from sqlalchemy.orm import Session

from .config import (
    SCORE_WEIGHTS,
    WORKER_BLPOP_TIMEOUT,
    track_buffer_key,
    leaderboard_track_key,
    leaderboard_event_key,
    ACTIVE_TRACKS_SET,
)
from .database import SessionLocal
from .redis_client import get_redis
from . import models
from .models import utcnow


def compute_weighted_score(technical: float, innovation: float,
                            presentation: float, impact: float) -> float:
    return (
        technical * SCORE_WEIGHTS["technical"]
        + innovation * SCORE_WEIGHTS["innovation"]
        + presentation * SCORE_WEIGHTS["presentation"]
        + impact * SCORE_WEIGHTS["impact"]
    )


def _reduce_team(db: Session, team_id: int) -> float:
    """REDUCE: recompute one team's aggregate final score from every
    Score row on record for them, and upsert the `results` row."""
    scores = db.query(models.Score).filter(models.Score.team_id == team_id).all()
    if not scores:
        return 0.0

    avg = sum(s.weighted_score for s in scores) / len(scores)

    result = (
        db.query(models.Result).filter(models.Result.team_id == team_id).first()
    )
    if result is None:
        result = models.Result(team_id=team_id)
        db.add(result)

    result.final_score = round(avg, 4)
    result.num_scores = len(scores)
    result.updated_at = utcnow()
    db.commit()
    return result.final_score


def _rerank_track(db: Session, r, track_id: int):
    """Recompute the ranking within a track and push it into Redis."""
    teams = db.query(models.Team).filter(models.Team.track_id == track_id).all()
    team_ids = [t.id for t in teams]
    if not team_ids:
        return

    results = (
        db.query(models.Result)
        .filter(models.Result.team_id.in_(team_ids))
        .all()
    )
    results.sort(key=lambda x: x.final_score, reverse=True)

    pipe = r.pipeline()
    pipe.delete(leaderboard_track_key(track_id))
    for idx, res in enumerate(results, start=1):
        res.rank = idx
        pipe.zadd(leaderboard_track_key(track_id), {str(res.team_id): res.final_score})
    db.commit()
    pipe.execute()


def _rerank_event(db: Session, r, event_id: int):
    """Recompute the combined ranking across every track in one event
    and push it into Redis. This -- not a lifetime-global mix of every
    event ever run -- is what the live leaderboard shows by default, so
    an old event's results stop appearing the moment a new event exists."""
    team_ids = [
        t.id
        for t in db.query(models.Team)
        .join(models.Track, models.Team.track_id == models.Track.id)
        .filter(models.Track.event_id == event_id)
        .all()
    ]
    pipe = r.pipeline()
    pipe.delete(leaderboard_event_key(event_id))
    if team_ids:
        results = db.query(models.Result).filter(models.Result.team_id.in_(team_ids)).all()
        for res in results:
            pipe.zadd(leaderboard_event_key(event_id), {str(res.team_id): res.final_score})
    pipe.execute()


def worker_loop(track_id: int, stop_event):
    """Entry point run inside each worker process."""
    # Ignore SIGINT in child; the manager handles shutdown via stop_event.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    r = get_redis()
    buffer_key = track_buffer_key(track_id)
    print(f"[worker:{track_id}] started, watching '{buffer_key}'", flush=True)

    while not stop_event.is_set():
        item = r.blpop(buffer_key, timeout=WORKER_BLPOP_TIMEOUT)
        if item is None:
            continue  # timed out, loop again so we can check stop_event

        _, raw = item
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[worker:{track_id}] dropped malformed payload: {raw}", flush=True)
            continue

        db = SessionLocal()
        try:
            # ---- MAP ----
            weighted = compute_weighted_score(
                payload["technical"],
                payload["innovation"],
                payload["presentation"],
                payload["impact"],
            )

            # Upsert on (judge_id, team_id): a judge editing their score
            # for a team they already scored overwrites that one row in
            # place, rather than adding a second row. This is what keeps
            # "one judge = one number of judge" true even after edits --
            # num_scores below counts rows, and there's at most one row
            # per (judge, team) pair.
            existing = (
                db.query(models.Score)
                .filter(
                    models.Score.judge_id == payload["judge_id"],
                    models.Score.team_id == payload["team_id"],
                )
                .first()
            )
            if existing:
                existing.technical = payload["technical"]
                existing.innovation = payload["innovation"]
                existing.presentation = payload["presentation"]
                existing.impact = payload["impact"]
                existing.weighted_score = weighted
                existing.updated_at = utcnow()
                action = "updated"
            else:
                score = models.Score(
                    judge_id=payload["judge_id"],
                    team_id=payload["team_id"],
                    track_id=track_id,
                    technical=payload["technical"],
                    innovation=payload["innovation"],
                    presentation=payload["presentation"],
                    impact=payload["impact"],
                    weighted_score=weighted,
                )
                db.add(score)
                action = "created"
            db.commit()

            # ---- REDUCE ----
            _reduce_team(db, payload["team_id"])
            _rerank_track(db, r, track_id)

            track = db.query(models.Track).filter(models.Track.id == track_id).first()
            if track:
                _rerank_event(db, r, track.event_id)

            print(
                f"[worker:{track_id}] {action} score "
                f"(judge={payload['judge_id']}, team={payload['team_id']}, "
                f"weighted={weighted:.2f})",
                flush=True,
            )
        except Exception as exc:  # keep the worker alive on bad data
            db.rollback()
            print(f"[worker:{track_id}] ERROR: {exc}", flush=True)
        finally:
            db.close()

    print(f"[worker:{track_id}] shutting down", flush=True)


def run_manager(poll_interval: float = 3.0):
    """
    Manager process: discovers tracks (via the `tracks:active` Redis set,
    populated by the API whenever an admin creates a track) and keeps one
    worker process alive per track. New tracks created while the system
    is running get their own worker automatically.
    """
    r = get_redis()
    stop_event = mp.Event()
    workers: dict[int, mp.Process] = {}

    def shutdown(*_):
        print("\n[manager] stopping all workers...", flush=True)
        stop_event.set()
        for p in workers.values():
            p.join(timeout=5)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("[manager] started. Watching for tracks...", flush=True)

    while True:
        active_ids = {int(tid) for tid in r.smembers(ACTIVE_TRACKS_SET)}

        # start workers for any new tracks
        for track_id in active_ids - workers.keys():
            p = mp.Process(target=worker_loop, args=(track_id, stop_event), daemon=True)
            p.start()
            workers[track_id] = p
            print(f"[manager] spawned worker for track {track_id} (pid={p.pid})", flush=True)

        time.sleep(poll_interval)
