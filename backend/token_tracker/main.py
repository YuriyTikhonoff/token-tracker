"""FastAPI app: the JSON API under /api, the widget page, and, when it has been
built, the web dashboard itself.

Run with `token-tracker serve`, or for development from backend/:
`.venv/bin/uvicorn token_tracker.main:app --reload --port 8765`.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import queries, schema
from .routes import accounts, data, refresh, widget

STATIC_DIR = Path(__file__).parent / "static"



@asynccontextmanager
async def lifespan(_app):
    # A first run has no tables yet; create them so an empty install answers
    # with zeros instead of an error.
    connection = queries.connect(queries.DEFAULT_DB_PATH)
    try:
        schema.migrate(connection)
    finally:
        connection.close()
    yield


app = FastAPI(title="Token Tracker API", lifespan=lifespan)

app.state.pricing = queries.load_pricing()

# The Vite dev server runs on its own port (5173, or the next free one), so
# match any localhost port rather than hardcoding one.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_origins=["tauri://localhost"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(data.router)
app.include_router(refresh.router)
app.include_router(widget.router)

# Last, so it never shadows the routes above.
if (STATIC_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")
else:

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def get_root() -> str:
        return (
            "<h1>Token Tracker API</h1>"
            "<p>The web dashboard is not bundled in this checkout. Run <code>npm run dev</code> "
            "in <code>frontend/</code>, or <code>npm run build:package</code> there and restart. "
            "The data is at <a href='/api/data'>/api/data</a>.</p>"
        )
