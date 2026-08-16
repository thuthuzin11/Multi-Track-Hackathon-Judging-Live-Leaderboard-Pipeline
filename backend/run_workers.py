"""
Run this in its own terminal (separate from `uvicorn app.main:app`):

    python run_workers.py

It spawns one OS process per hackathon track, each independently draining
and aggregating that track's Redis buffer. New tracks created later via
the Admin dashboard are picked up automatically within a few seconds.
"""
from app.worker import run_manager

if __name__ == "__main__":
    run_manager()
