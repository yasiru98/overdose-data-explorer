import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import fetch_death_series

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("app")

# main.py lives at backend/app/main.py, so going up 2 parents lands on the
# project root (epidemic/) where index.html, main.js, main.css etc already
# live. keeping the frontend files where they are instead of moving them
# into backend/, this just points at them from here
FRONTEND_DIR = Path(__file__).resolve().parents[2]

app = FastAPI(title="Drug Overdose Epidemic API")


@app.get("/health")
def health():
    # just a quick "is this thing even up" check, handy for a container
    # healthcheck or just poking it manually to sanity check the server's alive
    return {"status": "ok"}


@app.get("/api/deaths")
def get_deaths():
    """returns the full overdose death time series across every state and
    month we've got loaded, so the frontend can pull it once and scrub
    through months locally instead of hitting the api on every slider move"""
    return fetch_death_series()


# this has to be mounted LAST. StaticFiles with html=True acts as a catch-all
# for any path that doesn't match a route above it, so if this went first it'd
# swallow /health and /api/deaths before they ever got a chance to run
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
