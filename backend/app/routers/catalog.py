from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import require_any_signed_in_role
from ..database import get_db

# Read-only. Any signed-in identity (viewer, judge, or admin) can browse
# events/tracks/teams -- judges need it to fill the scoring form,
# spectators need it to filter the leaderboard. Mutating this data is
# admin-only and lives under /api/admin instead.
router = APIRouter(
    prefix="/api/catalog",
    tags=["catalog"],
    dependencies=[Depends(require_any_signed_in_role)],
)


@router.get("/events", response_model=list[schemas.EventOut])
def get_events(db: Session = Depends(get_db)):
    return crud.list_events(db)


@router.get("/tracks", response_model=list[schemas.TrackOut])
def get_tracks(event_id: int | None = None, db: Session = Depends(get_db)):
    return crud.list_tracks(db, event_id)


@router.get("/teams", response_model=list[schemas.TeamOut])
def get_teams(track_id: int | None = None, db: Session = Depends(get_db)):
    return crud.list_teams(db, track_id)
