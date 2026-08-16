from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    """Timezone-AWARE current UTC time. Used everywhere instead of the
    naive datetime.utcnow() -- paired with DateTime(timezone=True)
    columns below, this is what makes a stored time unambiguous. A plain
    'timestamp without time zone' column is the classic source of a
    fixed-offset display bug (e.g. everything off by exactly a UTC+6:30
    Myanmar-sized gap): depending on the driver/session, a timezone-aware
    value going in can get silently reinterpreted using the server's
    session timezone instead of UTC. timestamptz + aware Python
    datetimes throughout removes that ambiguity entirely."""
    return datetime.now(timezone.utc)


class Event(Base):
    """A hackathon event. Tracks belong to an event, so the same system
    can host multiple hackathons over time without the data mixing."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    tracks = relationship("Track", back_populates="event")

    @property
    def status(self) -> str:
        """upcoming / ongoing / finished, computed from start/end times.
        An event with no end_date is treated as never finishing. This is
        a plain Python property (not a DB column) so schemas.EventOut
        picks it up automatically via from_attributes."""
        now = utcnow()
        if self.start_date and now < self.start_date:
            return "upcoming"
        if self.end_date and now > self.end_date:
            return "finished"
        return "ongoing"


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    event = relationship("Event", back_populates="tracks")
    teams = relationship("Team", back_populates="track")

    __table_args__ = (UniqueConstraint("name", "event_id", name="uq_track_per_event"),)


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)

    track = relationship("Track", back_populates="teams")
    scores = relationship("Score", back_populates="team")
    result = relationship("Result", back_populates="team", uselist=False)

    __table_args__ = (UniqueConstraint("name", "track_id", name="uq_team_per_track"),)


class Judge(Base):
    """Each judge has their own login account. Admins create the account
    (name + username + initial password); the judge then logs in and
    scores are always submitted as that authenticated judge -- never
    picked from a dropdown -- so one judge can't submit as another."""

    __tablename__ = "judges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    scores = relationship("Score", back_populates="judge")


class Admin(Base):
    """An organizer account. Admins manage events, tracks, teams and
    judge accounts, and can always view results -- including after an
    event has ended."""

    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Viewer(Base):
    """A spectator account. Signing up only requires an email -- there's
    no password -- and a viewer can only ever read the leaderboard."""

    __tablename__ = "viewers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Score(Base):
    """
    Authoritative, durable record of one judge's scoring of one team.
    UNIQUE on (judge_id, team_id): a judge can only ever have ONE row per
    team. Re-submitting (editing) the same team overwrites this row in
    place rather than inserting a new one, so num_scores always equals
    the number of DISTINCT judges who scored a team, never the number of
    submissions. Written by a worker process AFTER it has popped the raw
    submission off the track's Redis buffer. criteria scores are 0-10.
    """

    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    judge_id = Column(Integer, ForeignKey("judges.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)

    technical = Column(Float, nullable=False)
    innovation = Column(Float, nullable=False)
    presentation = Column(Float, nullable=False)
    impact = Column(Float, nullable=False)
    weighted_score = Column(Float, nullable=False)  # computed at write time

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    judge = relationship("Judge", back_populates="scores")
    team = relationship("Team", back_populates="scores")

    __table_args__ = (UniqueConstraint("judge_id", "team_id", name="uq_score_per_judge_team"),)


class Result(Base):
    """
    One row per team: the REDUCE output. Recomputed by the worker every
    time a new score lands for that team's track partition.
    """

    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), unique=True, nullable=False)
    final_score = Column(Float, nullable=False, default=0.0)
    num_scores = Column(Integer, nullable=False, default=0)
    rank = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    team = relationship("Team", back_populates="result")
