import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import fetch_death_series

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("app")

# main.py lives at backend/app/main.py, so going up 1 parent lands on
# backend/, where the static/ folder holds index.html, main.js, etc.
# these live inside backend/ (not the project root) specifically because
# railway's deploy only includes whatever's under its configured Root
# Directory (backend/) - anything outside that never makes it into the
# deployed container, which is exactly what broke this the first time
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "static"

# the frontend loads Vue/Vuetify/D3 from a handful of different CDNs and
# embeds a YouTube video, and Vue's standalone build compiles its templates
# at runtime (needs 'unsafe-eval'). without sending our own CSP header,
# whatever's in front of this in production (railway's proxy, in our case)
# sends a stricter default that blocks that runtime compile and the whole
# vue app silently fails to render - this header is what actually fixes that
CSP_HEADER = (
    "default-src 'self' https:; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
    "style-src 'self' 'unsafe-inline' https:; "
    "font-src 'self' https: data:; "
    "img-src 'self' https: data:; "
    "frame-src https:; "
    "connect-src 'self' https:;"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP_HEADER
        return response


app = FastAPI(title="Drug Overdose Epidemic API")
app.add_middleware(SecurityHeadersMiddleware)


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
