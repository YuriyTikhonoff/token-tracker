"""FastAPI app — replaces dashboard.py's http.server handler.

Run with: uvicorn main:app --reload --port 8000 (from backend/app/).
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

import queries
from routes import data, refresh

app = FastAPI(title="Token Tracker API")

app.state.pricing = queries.load_pricing()

# Vite dev server and the Tauri webview call this from a different origin
# during development. Vite falls back to the next free port (5174, 5175...)
# if 5173 is already taken by another project, so match any localhost port
# rather than hardcoding 5173.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_origins=["tauri://localhost"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(refresh.router)
