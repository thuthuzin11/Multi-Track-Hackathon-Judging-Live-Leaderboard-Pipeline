from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .auth import hash_password
from .config import EVENT_START_PAST_TOLERANCE_SECONDS
from .models import utcnow


class ConflictError(Exception):
    """Raised when a create/update would collide with an existing unique
    value, e.g. an event/track/team/judge name or username already taken."""


class InUseError(Exception):
    """Raised when trying to delete something that other records still
    depend on (a track with teams, a team/judge with scores, etc.)."""


class InvalidScheduleError(Exception):
    """Raised when an event's start/end times don't make sense -- start
    time in the past, or end time not after start time."""


def _as_aware_utc(dt: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC for comparison. If
    it's naive, assume it's already UTC (matches how this codebase
    always produces naive datetimes -- see models.utcnow) rather than
    stripping tzinfo off an aware one, which is what caused values to
    silently drift by the viewer's UTC offset."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _validate_schedule(start_date, end_date, *, check_start_not_past: bool):
    """Shared validation for creating/editing an event. `check_start_not_past`
    is False when an update doesn't actually change start_date -- so
    renaming an event that already started doesn't get rejected for a
    start time that was valid when the event was created."""
    if start_date and check_start_not_past:
        start = _as_aware_utc(start_date)
        earliest_allowed = utcnow() - timedelta(seconds=EVENT_START_PAST_TOLERANCE_SECONDS)
        if start < earliest_allowed:
            raise InvalidScheduleError(
                "Start time can't be in the past. Pick the current time or later."
            )
    if start_date and end_date and _as_aware_utc(end_date) <= _as_aware_utc(start_date):
        raise InvalidScheduleError("End time must be after the start time.")


# ---------------- Events ----------------

def create_event(db: Session, data) -> models.Event:
    _validate_schedule(data.start_date, data.end_date, check_start_not_past=True)
    event = models.Event(
        name=data.name,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f'An event named "{data.name}" already exists.')
    db.refresh(event)
    return event


def update_event(db: Session, event_id: int, data) -> models.Event | None:
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        return None

    updates = data.model_dump(exclude_unset=True)
    new_start = updates.get("start_date", event.start_date)
    new_end = updates.get("end_date", event.end_date)
    # Only require "not in the past" if start_date is actually being
    # changed to something new -- otherwise editing an event that's
    # already underway (e.g. just fixing a typo in the name) would fail
    # every time on its own valid-when-created start time. Compare via
    # _as_aware_utc() on both sides so this is robust even if either
    # value happens to be naive.
    incoming_start = updates.get("start_date")
    start_changed = "start_date" in updates and (
        (incoming_start is None) != (event.start_date is None)
        or (
            incoming_start is not None
            and event.start_date is not None
            and _as_aware_utc(incoming_start) != _as_aware_utc(event.start_date)
        )
    )
    _validate_schedule(new_start, new_end, check_start_not_past=start_changed)

    for field, value in updates.items():
        setattr(event, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("An event with that name already exists.")
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: int) -> bool:
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        return False
    if db.query(models.Track).filter(models.Track.event_id == event_id).count() > 0:
        raise InUseError(
            "This event still has tracks assigned to it. Delete or reassign "
            "those tracks first."
        )
    db.delete(event)
    db.commit()
    return True


def list_events(db: Session):
    return db.query(models.Event).order_by(models.Event.id).all()


def get_event(db: Session, event_id: int):
    return db.query(models.Event).filter(models.Event.id == event_id).first()


def get_current_event(db: Session) -> models.Event | None:
    """The 'current' event the live leaderboard defaults to: whichever
    event was created most recently. As soon as an admin creates a new
    event, this flips to it and the leaderboard/track picker follow --
    by design, per how this system is meant to be used (one event live
    at a time)."""
    return db.query(models.Event).order_by(models.Event.id.desc()).first()


# ---------------- Tracks ----------------

def create_track(db: Session, name: str, event_id: int) -> models.Track:
    track = models.Track(name=name, event_id=event_id)
    db.add(track)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f'Track "{name}" already exists in this event.')
    db.refresh(track)
    return track


def update_track(db: Session, track_id: int, data) -> models.Track | None:
    track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if not track:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(track, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A track with that name already exists in this event.")
    db.refresh(track)
    return track


def delete_track(db: Session, track_id: int) -> bool:
    track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if not track:
        return False
    if db.query(models.Team).filter(models.Team.track_id == track_id).count() > 0:
        raise InUseError(
            "This track still has teams assigned to it. Delete or reassign "
            "those teams first."
        )
    db.delete(track)
    db.commit()
    return True


def list_tracks(db: Session, event_id: int | None = None):
    q = db.query(models.Track)
    if event_id is not None:
        q = q.filter(models.Track.event_id == event_id)
    return q.order_by(models.Track.id).all()


def get_track(db: Session, track_id: int):
    return db.query(models.Track).filter(models.Track.id == track_id).first()


def track_event_status(db: Session, track_id: int) -> str | None:
    """The status of the event a track belongs to, or None if the track
    doesn't exist. Used to block score submission once an event ends."""
    track = get_track(db, track_id)
    if not track or not track.event:
        return None
    return track.event.status


# ---------------- Teams ----------------

def create_team(db: Session, name: str, track_id: int) -> models.Team:
    team = models.Team(name=name, track_id=track_id)
    db.add(team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f'Team "{name}" already exists in this track.')
    db.refresh(team)
    return team


def update_team(db: Session, team_id: int, data) -> models.Team | None:
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A team with that name already exists in this track.")
    db.refresh(team)
    return team


def delete_team(db: Session, team_id: int) -> bool:
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        return False
    if db.query(models.Score).filter(models.Score.team_id == team_id).count() > 0:
        raise InUseError(
            "This team already has judging scores recorded. Remove those "
            "scores first if you really need to delete the team."
        )
    db.query(models.Result).filter(models.Result.team_id == team_id).delete()
    db.delete(team)
    db.commit()
    return True


def list_teams(db: Session, track_id: int | None = None):
    q = db.query(models.Team)
    if track_id is not None:
        q = q.filter(models.Team.track_id == track_id)
    return q.order_by(models.Team.id).all()


def get_team(db: Session, team_id: int):
    return db.query(models.Team).filter(models.Team.id == team_id).first()


# ---------------- Judges ----------------

def create_judge(db: Session, name: str, username: str, password: str) -> models.Judge:
    judge = models.Judge(
        name=name, username=username, hashed_password=hash_password(password)
    )
    db.add(judge)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f'Username "{username}" is already taken.')
    db.refresh(judge)
    return judge


def update_judge(db: Session, judge_id: int, data) -> models.Judge | None:
    judge = db.query(models.Judge).filter(models.Judge.id == judge_id).first()
    if not judge:
        return None
    updates = data.model_dump(exclude_unset=True)
    password = updates.pop("password", None)
    for field, value in updates.items():
        setattr(judge, field, value)
    if password:
        judge.hashed_password = hash_password(password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("That username is already taken.")
    db.refresh(judge)
    return judge


def delete_judge(db: Session, judge_id: int) -> bool:
    judge = db.query(models.Judge).filter(models.Judge.id == judge_id).first()
    if not judge:
        return False
    if db.query(models.Score).filter(models.Score.judge_id == judge_id).count() > 0:
        raise InUseError(
            "This judge has already submitted scores. Remove those scores "
            "first if you really need to delete the account."
        )
    db.delete(judge)
    db.commit()
    return True


def list_judges(db: Session):
    return db.query(models.Judge).order_by(models.Judge.id).all()


def get_judge(db: Session, judge_id: int):
    return db.query(models.Judge).filter(models.Judge.id == judge_id).first()


def get_judge_by_username(db: Session, username: str):
    return db.query(models.Judge).filter(models.Judge.username == username.lower()).first()


# ---------------- Results (read-only here) ----------------

def list_results(db: Session):
    return db.query(models.Result).order_by(models.Result.final_score.desc()).all()


# ---------------- Viewers (signup-only spectator accounts) ----------------

def get_viewer_by_email(db: Session, email: str):
    return db.query(models.Viewer).filter(models.Viewer.email == email.lower()).first()


def get_or_create_viewer(db: Session, email: str, name: str | None) -> models.Viewer:
    """Signup is idempotent: re-'signing up' with the same email just
    logs that viewer back in rather than erroring."""
    email = email.lower()
    viewer = get_viewer_by_email(db, email)
    if viewer:
        return viewer
    viewer = models.Viewer(email=email, name=name)
    db.add(viewer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return get_viewer_by_email(db, email)
    db.refresh(viewer)
    return viewer


# ---------------- Admins (organizer accounts) ----------------

def get_admin_by_username(db: Session, username: str):
    return db.query(models.Admin).filter(models.Admin.username == username.lower()).first()


def create_admin(db: Session, name: str, username: str, password: str) -> models.Admin:
    admin = models.Admin(
        name=name, username=username.lower(), hashed_password=hash_password(password)
    )
    db.add(admin)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f'Username "{username}" is already taken.')
    db.refresh(admin)
    return admin


# ---------------- A judge's own submissions ----------------

def list_my_scores(db: Session, judge_id: int):
    """Every score this judge has on record, enriched with team/track
    names and the track's event status, for the 'My Scores' view and
    for prefilling the edit form."""
    rows = (
        db.query(models.Score, models.Team, models.Track, models.Event)
        .join(models.Team, models.Score.team_id == models.Team.id)
        .join(models.Track, models.Team.track_id == models.Track.id)
        .join(models.Event, models.Track.event_id == models.Event.id)
        .filter(models.Score.judge_id == judge_id)
        .order_by(models.Score.updated_at.desc())
        .all()
    )
    results = []
    for score, team, track, event in rows:
        results.append(
            {
                "id": score.id,
                "team_id": team.id,
                "team_name": team.name,
                "track_id": track.id,
                "track_name": track.name,
                "event_status": event.status,
                "technical": score.technical,
                "innovation": score.innovation,
                "presentation": score.presentation,
                "impact": score.impact,
                "weighted_score": score.weighted_score,
                "updated_at": score.updated_at,
            }
        )
    return results
