"""Translation memory routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.translation_memory_service import TranslationMemoryService

router = APIRouter(prefix="/translation-memory", tags=["translation-memory"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
translation_memory_service = TranslationMemoryService()
TRANSLATION_MEMORY_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "references" / "translation_memory"
)


@router.get("", response_class=HTMLResponse)
def translation_memory_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    imported: str | None = None,
) -> HTMLResponse:
    """Render translation memory browse and search UI."""
    entries = translation_memory_service.list_entries(db, q)
    matches = translation_memory_service.retrieve_similar_passages(db, q, limit=10) if q else []
    return templates.TemplateResponse(
        request,
        "translation_memory.html",
        {
            "entries": entries,
            "matches": matches,
            "query": q or "",
            "message": imported,
            "errors": [],
        },
    )


@router.post("/import", response_class=HTMLResponse, response_model=None)
async def import_translation_memory(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    memory_file: Annotated[UploadFile | None, File()] = None,
    file_name: Annotated[str | None, Form()] = None,
) -> Response:
    """Import translation memory CSV data from upload or reference directory."""
    try:
        path = await _resolve_import_file(memory_file, file_name)
        summary = translation_memory_service.import_csv_file(db, path)
    except ValueError as exc:
        entries = translation_memory_service.list_entries(db)
        return templates.TemplateResponse(
            request,
            "translation_memory.html",
            {
                "entries": entries,
                "matches": [],
                "query": "",
                "message": None,
                "errors": [str(exc)],
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    details = f"Imported {path.name}: {summary.inserted} inserted, {summary.updated} updated"
    if summary.skipped:
        details += f", {summary.skipped} skipped"
    if summary.errors:
        details += f". First error: {summary.errors[0]}"
    return RedirectResponse(
        url=f"/translation-memory?imported={details}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


async def _resolve_import_file(memory_file: UploadFile | None, file_name: str | None) -> Path:
    """Resolve an uploaded or existing translation memory CSV file."""
    TRANSLATION_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if memory_file is not None and memory_file.filename:
        if not memory_file.filename.lower().endswith(".csv"):
            raise ValueError("Only CSV translation memory imports are supported right now.")
        path = TRANSLATION_MEMORY_DIR / Path(memory_file.filename).name
        path.write_bytes(await memory_file.read())
        return path

    clean_name = (file_name or "").strip()
    if not clean_name:
        raise ValueError(
            "Choose a CSV file or enter a file name under data/references/translation_memory/."
        )
    path = TRANSLATION_MEMORY_DIR / Path(clean_name).name
    if path.suffix.lower() != ".csv":
        raise ValueError("Only CSV translation memory imports are supported right now.")
    if not path.exists():
        raise ValueError(f"Translation memory file not found: {path.name}")
    return path
