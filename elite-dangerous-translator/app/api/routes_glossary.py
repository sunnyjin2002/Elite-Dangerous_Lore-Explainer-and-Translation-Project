"""Glossary route placeholders."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/glossary", tags=["glossary"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def glossary_page(request: Request) -> HTMLResponse:
    """Render the glossary placeholder page."""
    return templates.TemplateResponse(request, "glossary.html")
