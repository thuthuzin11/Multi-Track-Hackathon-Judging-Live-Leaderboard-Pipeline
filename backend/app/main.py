from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ALLOWED_ORIGINS
from .database import Base, engine
from .routers import admin, scores, leaderboard, auth, catalog

# Create tables if they don't exist yet (fine for a school project;
# use Alembic migrations for anything production-grade).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multi-Track Hackathon Judging & Live Leaderboard Pipeline",
    description=(
        "Distributed score-processing pipeline: FastAPI ingest -> "
        "Redis track buffers -> parallel worker processes -> Map-Reduce "
        "aggregation -> PostgreSQL (authoritative) -> Redis (fast leaderboard reads)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Judges authenticate with a Bearer token in the Authorization header,
    # not cookies, so credentialed CORS isn't needed -- this also lets us
    # keep allow_origins=["*"] for easy multi-location access without
    # violating the browser's "no wildcard + credentials" rule.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(admin.router)
app.include_router(scores.router)
app.include_router(leaderboard.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
