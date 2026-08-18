from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ALLOWED_ORIGINS
from .database import Base, engine
from .routers import admin, auth, catalog, leaderboard, scores

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

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(admin.router)
app.include_router(scores.router)
app.include_router(leaderboard.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}