import os
from dotenv import load_dotenv

load_dotenv()

# --- Database (PostgreSQL) ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/hackathon",
)

# --- Redis ---
REDIS_HOST = os.getenv("REDIS_HOST") or os.getenv("REDISHOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT") or os.getenv("REDISPORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or os.getenv("REDISPASSWORD", None)

# --- Auth (judge accounts) ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))  # 12 hours

# --- CORS ---
_origins_env = os.getenv("ALLOWED_ORIGINS", "")

DEFAULT_ORIGINS = [
    "https://imaginative-custard-ef8c4b.netlify.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

if _origins_env and _origins_env.strip() != "*":
    ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]
    for origin in DEFAULT_ORIGINS:
        if origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(origin)
else:
    ALLOWED_ORIGINS = DEFAULT_ORIGINS

# --- Scoring weights (must sum to 1.0) ---
SCORE_WEIGHTS = {
    "technical": 0.40,
    "innovation": 0.30,
    "presentation": 0.20,
    "impact": 0.10,
}

# --- Worker tuning ---
WORKER_BLPOP_TIMEOUT = 2

# Redis key helpers
def track_buffer_key(track_id: int) -> str:
    return f"track_buffer:{track_id}"

def leaderboard_track_key(track_id: int) -> str:
    return f"leaderboard:track:{track_id}"

def leaderboard_event_key(event_id: int) -> str:
    return f"leaderboard:event:{event_id}"

ACTIVE_TRACKS_SET = "tracks:active"

EVENT_START_PAST_TOLERANCE_SECONDS = 120