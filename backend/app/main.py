from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import admin, scores, leaderboard, auth, catalog

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
    allow_origins=[
        "https://imaginative-custard-ef8c4b.netlify.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "*"
    ],
    allow_credentials=True,
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