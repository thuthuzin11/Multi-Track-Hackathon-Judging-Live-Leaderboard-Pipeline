from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ALLOWED_ORIGINS
from .database import Base, engine
from .routers import admin, auth, catalog, leaderboard, scores

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multi-Track Hackathon Judging & Live Leaderboard Pipeline",
    version="1.0.0",
)

# CORS Configuration (CORSMiddleware ကို Middleware တန်းစီဇယား၏ အပေါ်ဆုံးတွင် ထားရမည်)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unhandled Exception ဖြစ်သွားပါကလည်း CORS Headers ပါအောင် ပြုလုပ်ခြင်း
@app.middleware("http")
def catch_exceptions_middleware(request: Request, call_next):
    try:
        return call_next(request)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
                "Access-Control-Allow-Credentials": "true",
            },
        )

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(admin.router)
app.include_router(scores.router)
app.include_router(leaderboard.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}