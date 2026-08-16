from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import get_current_admin
from ..database import get_db
from ..redis_client import get_redis
from ..config import ACTIVE_TRACKS_SET

# Every route in this router requires a logged-in admin -- enforced once
# here via dependencies=[...] rather than repeating Depends(get_current_admin)
# on each endpoint.
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


# ==================== Events ====================

@router.post("/events", response_model=schemas.EventOut)
def create_event(payload: schemas.EventCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_event(db, payload)
    except crud.ConflictError as e:
        raise HTTPException(409, str(e))
    except crud.InvalidScheduleError as e:
        raise HTTPException(400, str(e))


@router.get("/events", response_model=list[schemas.EventOut])
def get_events(db: Session = Depends(get_db)):
    return crud.list_events(db)


@router.put("/events/{event_id}", response_model=schemas.EventOut)
def edit_event(event_id: int, payload: schemas.EventUpdate, db: Session = Depends(get_db)):
    try:
        event = crud.update_event(db, event_id, payload)
    except crud.ConflictError as e:
        raise HTTPException(409, str(e))
    except crud.InvalidScheduleError as e:
        raise HTTPException(400, str(e))
    if not event:
        raise HTTPException(404, "Event not found")
    return event


@router.delete("/events/{event_id}", status_code=204)
def remove_event(event_id: int, db: Session = Depends(get_db)):
    try:
        found = crud.delete_event(db, event_id)
    except crud.InUseError as e:
        raise HTTPException(409, str(e))
    if not found:
        raise HTTPException(404, "Event not found")


# ==================== Tracks ====================

@router.post("/tracks", response_model=schemas.TrackOut)
def create_track(payload: schemas.TrackCreate, db: Session = Depends(get_db)):
    if not crud.get_event(db, payload.event_id):
        raise HTTPException(404, "Event not found")
    try:
        track = crud.create_track(db, payload.name, payload.event_id)
    except crud.ConflictError as e:
        raise HTTPException(409, str(e))

    # Register with Redis so the worker manager spawns a process for it.
    get_redis().sadd(ACTIVE_TRACKS_SET, track.id)
    return track


@router.get("/tracks", response_model=list[schemas.TrackOut])
def get_tracks(event_id: int | None = None, db: Session = Depends(get_db)):
    return crud.list_tracks(db, event_id)


@router.put("/tracks/{track_id}", response_model=schemas.TrackOut)
def edit_track(track_id: int, payload: schemas.TrackUpdate, db: Session = Depends(get_db)):
    if payload.event_id is not None and not crud.get_event(db, payload.event_id):
        raise HTTPException(404, "Event not found")
    try:
        track = crud.update_track(db, track_id, payload)
    except crud.ConflictError as e:
        raise HTTPException(409, str(e))
    if not track:
        raise HTTPException(404, "Track not found")
    return track


@router.delete("/tracks/{track_id}", status_code=204)
def remove_track(track_id: int, db: Session = Depends(get_db)):
    try:
        found = crud.delete_track(db, track_id)
    except crud.InUseError as e:
        raise HTTPException(409, str(e))
    if not found:
        raise HTTPException(404, "Track not found")


# ==================== Teams ====================

@router.post("/teams", response_model=schemas.TeamOut)
def create_team(payload: schemas.TeamCreate, db: Session = Depends(get_db)):
    if not crud.get_track(db, payload.track_id):
        raise HTTPException(404, "Track not found")
    try:
        return crud.create_team(db, payload.name, payload.track_id)
    except crud.ConflictError as e:
        raise HTTPException(409, str(e))


@router.get("/teams", response_model=list[schemas.TeamOut])
def get_teams(track_id: int | None = None, db: Session = Depends(get_db)):
    return crud.list_teams(db, track_id)


@router.put("/teams/{team_id}", response_model=schemas.TeamOut)
def edit_team(team_id: int, payload: schemas.TeamUpdate, db: Session = Depends(get_db)):
    if payload.track_id is not None and not crud.get_track(db, payload.track_id):
        raise HTTPException(404, "Track not found")
    try:
        team = crud.update_team(db, team_id, payload)
    except crud.ConflictError as e:
        raise HTTPException(409, str(e))
    if not team:
        raise HTTPException(404, "Team not found")
    return team


@router.delete("/teams/{team_id}", status_code=204)
def remove_team(team_id: int, db: Session = Depends(get_db)):
    try:
        found = crud.delete_team(db, team_id)
    except crud.InUseError as e:
        raise HTTPException(409, str(e))
    if not found:
        raise HTTPException(404, "Team not found")


# ==================== Judges ====================

@router.post("/judges", response_model=schemas.JudgeOut)
def create_judge(payload: schemas.JudgeCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_judge(db, payload.name, payload.username, payload.password)
    except crud.ConflictError as e:
        raise HTTPException(409, str(e))


@router.get("/judges", response_model=list[schemas.JudgeOut])
def get_judges(db: Session = Depends(get_db)):
    return crud.list_judges(db)


@router.put("/judges/{judge_id}", response_model=schemas.JudgeOut)
def edit_judge(judge_id: int, payload: schemas.JudgeUpdate, db: Session = Depends(get_db)):
    try:
        judge = crud.update_judge(db, judge_id, payload)
    except crud.ConflictError as e:
        raise HTTPException(409, str(e))
    if not judge:
        raise HTTPException(404, "Judge not found")
    return judge


@router.delete("/judges/{judge_id}", status_code=204)
def remove_judge(judge_id: int, db: Session = Depends(get_db)):
    try:
        found = crud.delete_judge(db, judge_id)
    except crud.InUseError as e:
        raise HTTPException(409, str(e))
    if not found:
        raise HTTPException(404, "Judge not found")


# ==================== Results (read-only) ====================

@router.get("/results", response_model=list[schemas.ResultOut])
def get_results(db: Session = Depends(get_db)):
    """Raw authoritative results straight from PostgreSQL (for the demo:
    'Show calculated team results in PostgreSQL')."""
    return crud.list_results(db)
