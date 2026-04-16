"""Settings route placeholders."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    """Render the settings placeholder page."""
    return templates.TemplateResponse(request, "settings.html")
