"""GET /widget — a self-contained HTML page for the Hammerspoon floating
overlay (widgets/hammerspoon/). Served from the backend so the page is
same-origin with /api/data and needs no CORS entry."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

_WIDGET_HTML = Path(__file__).resolve().parent.parent / "widget.html"


@router.get("/widget")
def get_widget() -> FileResponse:
    return FileResponse(_WIDGET_HTML, media_type="text/html")
