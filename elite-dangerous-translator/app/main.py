"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.routes_articles import router as articles_router
from app.api.routes_glossary import router as glossary_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_publish import router as publish_router
from app.api.routes_settings import router as settings_router
from app.api.routes_translation_memory import router as translation_memory_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.scheduler import create_scheduler
from app.db.session import create_database_tables, get_db
from app.services.job_service import JobService

APP_DIR = Path(__file__).resolve().parent
settings = get_settings()
templates = Jinja2Templates(directory=APP_DIR / "templates")
job_service = JobService()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure process-level resources for the application lifetime."""
    configure_logging(settings.log_level)
    create_database_tables()
    scheduler = create_scheduler(settings)
    app.state.scheduler = scheduler
    scheduler.start(paused=True)
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

    app.include_router(articles_router)
    app.include_router(jobs_router)
    app.include_router(glossary_router)
    app.include_router(translation_memory_router)
    app.include_router(publish_router)
    app.include_router(settings_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return a lightweight health check response."""
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
        """Render the local dashboard shell with recent jobs."""
        recent_jobs = job_service.list_recent_jobs(db)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"app_name": settings.app_name, "recent_jobs": recent_jobs},
        )

    return app


app = create_app()
