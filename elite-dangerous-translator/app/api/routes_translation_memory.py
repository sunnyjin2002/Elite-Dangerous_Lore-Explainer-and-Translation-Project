"""Translation memory route placeholders."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/translation-memory", tags=["translation-memory"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def translation_memory_page(request: Request) -> HTMLResponse:
    """Render the translation memory placeholder page."""
    return templates.TemplateResponse(request, "translation_memory.html")
