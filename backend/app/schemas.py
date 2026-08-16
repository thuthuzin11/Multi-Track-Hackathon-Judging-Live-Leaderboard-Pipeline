from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr


# ---------- Events ----------

class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "upcoming"  # "upcoming" | "ongoing" | "finished", computed server-side


# ---------- Tracks ----------

class TrackCreate(BaseModel):
    name: str
    event_id: int


class TrackUpdate(BaseModel):
    name: Optional[str] = None
    event_id: Optional[int] = None


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    event_id: int


# ---------- Teams ----------

class TeamCreate(BaseModel):
    name: str
    track_id: int


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    track_id: Optional[int] = None


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    track_id: int


# ---------- Judges (accounts) ----------

class JudgeCreate(BaseModel):
    name: str
    username: str
    password: str = Field(min_length=6)

    @field_validator("username")
    @classmethod
    def username_no_spaces(cls, v: str) -> str:
        v = v.strip()
        if " " in v:
            raise ValueError("Username cannot contain spaces")
        return v.lower()


class JudgeUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)


class JudgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    username: str


# ---------- Auth ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class ViewerSignup(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class ViewerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: Optional[str] = None


class AdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    profile: dict  # JudgeOut | AdminOut | ViewerOut, shape depends on role


class MeOut(BaseModel):
    role: str
    profile: dict


# ---------- Score submission ----------
# Note: judge_id is intentionally NOT part of this payload. The judge is
# identified from the Authorization: Bearer <token> header, so one judge
# can never submit a score as another judge.

class ScoreSubmission(BaseModel):
    team_id: int
    track_id: int
    technical: float = Field(ge=0, le=10)
    innovation: float = Field(ge=0, le=10)
    presentation: float = Field(ge=0, le=10)
    impact: float = Field(ge=0, le=10)


class ScoreAccepted(BaseModel):
    status: str
    message: str
    track_id: int


class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    judge_id: int
    team_id: int
    track_id: int
    technical: float
    innovation: float
    presentation: float
    impact: float
    weighted_score: float
    created_at: datetime


class MyScoreOut(BaseModel):
    """A judge's own submission, enriched with team/track names for
    display so the frontend doesn't need extra lookups."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: int
    team_name: str
    track_id: int
    track_name: str
    event_status: str
    technical: float
    innovation: float
    presentation: float
    impact: float
    weighted_score: float
    updated_at: datetime


# ---------- Leaderboard / results ----------

class LeaderboardEntry(BaseModel):
    rank: int
    team_id: int
    team_name: str
    track_id: Optional[int] = None
    track_name: Optional[str] = None
    final_score: float
    num_scores: int


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    team_id: int
    final_score: float
    num_scores: int
    rank: Optional[int]
    updated_at: datetime
