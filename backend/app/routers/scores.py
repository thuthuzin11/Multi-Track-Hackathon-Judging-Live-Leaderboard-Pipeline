import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import get_current_judge
from ..database import get_db
from ..redis_client import get_redis
from ..config import track_buffer_key, ACTIVE_TRACKS_SET

router = APIRouter(prefix="/api/scores", tags=["scores"])


@router.post("", response_model=schemas.ScoreAccepted, status_code=202)
def submit_score(
    payload: schemas.ScoreSubmission,
    db: Session = Depends(get_db),
    current_judge=Depends(get_current_judge),
):
    """
    Judges must be logged in to call this. The judge identity comes ONLY
    from the verified access token (current_judge) -- never from the
    request body -- so one judge account can never submit a score under
    another judge's name.

    This does NOT touch PostgreSQL directly. It pushes the raw
    submission onto the track's Redis buffer (list) and returns
    immediately; a worker process picks it up asynchronously. That's
    what keeps concurrent judge submissions from becoming direct,
    contended database writes.
    """
    team = crud.get_team(db, payload.team_id)
    if not team:
        raise HTTPException(404, "Team not found")
    if team.track_id != payload.track_id:
        raise HTTPException(400, "team_id does not belong to track_id")

    status = crud.track_event_status(db, payload.track_id)
    if status == "finished":
        raise HTTPException(403, "This event has ended. Scoring is closed.")

    r = get_redis()
    r.sadd(ACTIVE_TRACKS_SET, payload.track_id)  # make sure a worker exists

    raw = {
        "judge_id": current_judge.id,
        "team_id": payload.team_id,
        "technical": payload.technical,
        "innovation": payload.innovation,
        "presentation": payload.presentation,
        "impact": payload.impact,
    }
    r.rpush(track_buffer_key(payload.track_id), json.dumps(raw))

    return schemas.ScoreAccepted(
        status="accepted",
        message="Score queued for processing",
        track_id=payload.track_id,
    )


@router.get("/mine", response_model=list[schemas.MyScoreOut])
def my_scores(db: Session = Depends(get_db), current_judge=Depends(get_current_judge)):
    """Every score this judge has submitted so far, for the 'My Scores'
    view and for prefilling the form when they pick a team they've
    already scored (so re-submitting edits the existing row instead of
    piling up a second one)."""
    return crud.list_my_scores(db, current_judge.id)
