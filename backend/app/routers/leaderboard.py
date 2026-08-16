from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import require_any_signed_in_role
from ..database import get_db
from ..redis_client import get_redis
from ..config import leaderboard_track_key, leaderboard_event_key

# Any signed-in identity can read the leaderboard: a viewer who signed
# up with just an email, a logged-in judge, or an admin. Anonymous
# (no token) requests are rejected -- viewers must sign up first.
router = APIRouter(
    prefix="/api/leaderboard",
    tags=["leaderboard"],
    dependencies=[Depends(require_any_signed_in_role)],
)


def _build_entries(db: Session, redis_key: str) -> list[schemas.LeaderboardEntry]:
    r = get_redis()
    # ZREVRANGE: highest score first
    raw = r.zrevrange(redis_key, 0, -1, withscores=True)
    if not raw:
        return []

    team_ids = [int(team_id) for team_id, _ in raw]
    teams = {
        t.id: t
        for t in db.query(models.Team).filter(models.Team.id.in_(team_ids)).all()
    }
    tracks = {t.id: t.name for t in db.query(models.Track).all()}

    entries = []
    for idx, (team_id_str, score) in enumerate(raw, start=1):
        team_id = int(team_id_str)
        team = teams.get(team_id)
        if not team:
            continue
        result = team.result
        entries.append(
            schemas.LeaderboardEntry(
                rank=idx,
                team_id=team_id,
                team_name=team.name,
                track_id=team.track_id,
                track_name=tracks.get(team.track_id),
                final_score=round(float(score), 4),
                num_scores=result.num_scores if result else 0,
            )
        )
    return entries


@router.get("", response_model=list[schemas.LeaderboardEntry])
def get_event_leaderboard(event_id: int | None = None, db: Session = Depends(get_db)):
    """Fast, cache-backed leaderboard for one event (spectator's default
    view). Scoped to `event_id` if given, otherwise the CURRENT event --
    whichever was created most recently -- so an old event's results
    stop showing here the moment a new event exists, without needing to
    delete anything."""
    event = crud.get_event(db, event_id) if event_id is not None else crud.get_current_event(db)
    if not event:
        return []
    return _build_entries(db, leaderboard_event_key(event.id))


@router.get("/track/{track_id}", response_model=list[schemas.LeaderboardEntry])
def get_track_leaderboard(track_id: int, db: Session = Depends(get_db)):
    return _build_entries(db, leaderboard_track_key(track_id))
