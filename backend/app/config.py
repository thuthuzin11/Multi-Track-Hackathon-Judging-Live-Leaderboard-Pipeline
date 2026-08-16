import os
from dotenv import load_dotenv

load_dotenv()

# --- Database (PostgreSQL) ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/hackathon",
)

# --- Redis ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# --- Auth (judge accounts) ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))  # 12 hours

# --- CORS ---
# Comma-separated list of allowed frontend origins, e.g.
#   ALLOWED_ORIGINS=https://myapp.vercel.app,https://myapp.com
# Defaults to "*" for easy local development.
_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = ["*"] if _origins_env.strip() == "*" else [
    o.strip() for o in _origins_env.split(",") if o.strip()
]

# --- Scoring weights (must sum to 1.0) ---
SCORE_WEIGHTS = {
    "technical": 0.40,
    "innovation": 0.30,
    "presentation": 0.20,
    "impact": 0.10,
}

# --- Worker tuning ---
# How long (seconds) a worker blocks waiting on its track buffer before
# looping again to check for shutdown / new tracks.
WORKER_BLPOP_TIMEOUT = 2

# Redis key helpers, centralized so producer (API) and consumer (workers) agree
def track_buffer_key(track_id: int) -> str:
    return f"track_buffer:{track_id}"

def leaderboard_track_key(track_id: int) -> str:
    return f"leaderboard:track:{track_id}"

def leaderboard_event_key(event_id: int) -> str:
    """Combined ranking across every track in one event -- what the
    live leaderboard shows by default (scoped to the CURRENT event,
    not a lifetime-global mix of every event ever run)."""
    return f"leaderboard:event:{event_id}"

ACTIVE_TRACKS_SET = "tracks:active"

# How far in the past a new/edited event start time is still allowed to
# be, to absorb the few seconds between the admin picking a time and the
# request reaching the server. Keep small -- this is slack, not a loophole.
EVENT_START_PAST_TOLERANCE_SECONDS = 120
