"""Article routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/articles", tags=["articles"])
templates = Jinja2Templates(directory="app/templates")
ingestion_service = IngestionService()


@router.get("", response_class=HTMLResponse)
def manual_submit_alias() -> RedirectResponse:
    """Redirect the legacy article entry point to the manual submission form."""
    return RedirectResponse(url="/articles/manual/new", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/manual/new", response_class=HTMLResponse)
def manual_submit(request: Request) -> HTMLResponse:
    """Render the manual article submission form."""
    return templates.TemplateResponse(
        request,
        "manual_submit.html",
        {
            "errors": [],
            "form": {"target_language": "zh-CN"},
        },
    )


@router.post("/manual", response_class=HTMLResponse)
def submit_manual_article(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    title: Annotated[str | None, Form()] = None,
    source_url: Annotated[str | None, Form()] = None,
    source_text: Annotated[str | None, Form()] = None,
    target_language: Annotated[str, Form()] = "zh-CN",
) -> HTMLResponse | RedirectResponse:
    """Validate and persist a manual lore submission."""
    submission, errors = ingestion_service.validate_manual_submission(
        title=title,
        source_url=source_url,
        source_text=source_text,
        target_language=target_language,
    )
    if errors or submission is None:
        return templates.TemplateResponse(
            request,
            "manual_submit.html",
            {
                "errors": errors,
                "form": {
                    "title": title or "",
                    "source_url": source_url or "",
                    "source_text": source_text or "",
                    "target_language": target_language or "zh-CN",
                },
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    result = ingestion_service.submit_manual_article(db, submission)
    return RedirectResponse(
        url=f"/jobs/{result.job.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{article_id}", response_class=HTMLResponse)
def article_detail(
    request: Request,
    article_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """Render article metadata, source text, and related jobs."""
    article = ingestion_service.get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return templates.TemplateResponse(
        request,
        "article_detail.html",
        {"article": article},
    )
