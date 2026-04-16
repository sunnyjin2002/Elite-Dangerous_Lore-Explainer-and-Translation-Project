"""Job routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])
templates = Jinja2Templates(directory="app/templates")
job_service = JobService()


@router.get("", response_class=HTMLResponse)
def list_jobs(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    """Render all jobs ordered newest first."""
    jobs = job_service.list_jobs(db)
    return templates.TemplateResponse(request, "jobs.html", {"jobs": jobs})


@router.get("/{job_id}", response_class=HTMLResponse)
def job_detail(
    request: Request,
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """Render job status, article metadata, and logs."""
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return templates.TemplateResponse(request, "job_detail.html", {"job": job})
