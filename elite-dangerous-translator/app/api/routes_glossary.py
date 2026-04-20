"""Glossary routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.models import GlossaryStatus
from app.db.session import get_db
from app.services.glossary_service import GlossaryEntryData, GlossaryService

router = APIRouter(prefix="/glossary", tags=["glossary"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
glossary_service = GlossaryService()
GLOSSARY_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "glossary"


@router.get("", response_class=HTMLResponse)
def glossary_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    edit_id: int | None = None,
    imported: str | None = None,
    message: str | None = None,
) -> HTMLResponse:
    """Render glossary browsing, search, import, and edit UI."""
    entries = glossary_service.list_entries(db, q)
    edit_entry = glossary_service.get_entry(db, edit_id) if edit_id is not None else None
    return templates.TemplateResponse(
        request,
        "glossary.html",
        {
            "entries": entries,
            "query": q or "",
            "edit_entry": edit_entry,
            "statuses": [status.value for status in GlossaryStatus],
            "errors": [],
            "message": message or imported,
            "form": {},
        },
    )


@router.post("/import", response_class=HTMLResponse, response_model=None)
async def import_glossary(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    glossary_file: Annotated[UploadFile | None, File()] = None,
    file_name: Annotated[str | None, Form()] = None,
) -> Response:
    """Import glossary CSV data from an upload or data/glossary file name."""
    try:
        path = await _resolve_import_file(glossary_file, file_name)
        summary = glossary_service.import_csv_file(db, path)
    except ValueError as exc:
        entries = glossary_service.list_entries(db)
        return templates.TemplateResponse(
            request,
            "glossary.html",
            {
                "entries": entries,
                "query": "",
                "edit_entry": None,
                "statuses": [status.value for status in GlossaryStatus],
                "errors": [str(exc)],
                "message": None,
                "form": {},
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    details = f"Imported {path.name}: {summary.inserted} inserted, {summary.updated} updated"
    if summary.skipped:
        details += f", {summary.skipped} skipped"
    if summary.errors:
        details += f". First error: {summary.errors[0]}"
    return RedirectResponse(
        url=f"/glossary?imported={details}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("", response_class=HTMLResponse, response_model=None)
def create_glossary_entry(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    source_term_en: Annotated[str, Form()],
    approved_term_zh: Annotated[str, Form()],
    aliases_en: Annotated[str | None, Form()] = None,
    entity_type: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    entry_status: Annotated[str, Form()] = GlossaryStatus.draft.value,
) -> Response:
    """Create a glossary entry from the browser form."""
    data, errors = _entry_data_from_form(
        source_term_en,
        approved_term_zh,
        aliases_en,
        entity_type,
        notes,
        entry_status,
    )
    if errors or data is None:
        return _render_form_errors(request, db, errors, None, locals())

    entry = glossary_service.create_entry(db, data)
    return RedirectResponse(
        url=f"/glossary?message=Saved glossary entry {entry.source_term_en}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.put("/{entry_id}", response_class=HTMLResponse, response_model=None)
def update_glossary_entry(
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
    source_term_en: Annotated[str, Form()],
    approved_term_zh: Annotated[str, Form()],
    aliases_en: Annotated[str | None, Form()] = None,
    entity_type: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    entry_status: Annotated[str, Form()] = GlossaryStatus.draft.value,
) -> Response:
    """Update a glossary entry. Intended for API clients and progressive UI use."""
    data, errors = _entry_data_from_form(
        source_term_en,
        approved_term_zh,
        aliases_en,
        entity_type,
        notes,
        entry_status,
    )
    if errors or data is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)

    entry = glossary_service.update_entry(db, entry_id, data)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Glossary entry not found"
        )
    return RedirectResponse(url="/glossary", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{entry_id}", response_class=HTMLResponse, response_model=None)
def update_glossary_entry_from_form(
    request: Request,
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
    source_term_en: Annotated[str, Form()],
    approved_term_zh: Annotated[str, Form()],
    aliases_en: Annotated[str | None, Form()] = None,
    entity_type: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    entry_status: Annotated[str, Form()] = GlossaryStatus.draft.value,
) -> Response:
    """Update a glossary entry from the HTML form."""
    data, errors = _entry_data_from_form(
        source_term_en,
        approved_term_zh,
        aliases_en,
        entity_type,
        notes,
        entry_status,
    )
    if errors or data is None:
        return _render_form_errors(request, db, errors, entry_id, locals())

    entry = glossary_service.update_entry(db, entry_id, data)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Glossary entry not found"
        )
    return RedirectResponse(
        url=f"/glossary?message=Updated glossary entry {entry.source_term_en}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


async def _resolve_import_file(
    glossary_file: UploadFile | None,
    file_name: str | None,
) -> Path:
    """Resolve an uploaded or existing data/glossary CSV file."""
    GLOSSARY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if glossary_file is not None and glossary_file.filename:
        if not glossary_file.filename.lower().endswith(".csv"):
            raise ValueError("Only CSV glossary imports are supported right now.")
        path = GLOSSARY_DATA_DIR / Path(glossary_file.filename).name
        path.write_bytes(await glossary_file.read())
        return path

    clean_name = (file_name or "").strip()
    if not clean_name:
        raise ValueError("Choose a CSV file or enter a file name under data/glossary/.")
    path = GLOSSARY_DATA_DIR / Path(clean_name).name
    if path.suffix.lower() != ".csv":
        raise ValueError("Only CSV glossary imports are supported right now.")
    if not path.exists():
        raise ValueError(f"Glossary file not found: {path.name}")
    return path


def _entry_data_from_form(
    source_term_en: str,
    approved_term_zh: str,
    aliases_en: str | None,
    entity_type: str | None,
    notes: str | None,
    entry_status: str,
) -> tuple[GlossaryEntryData | None, list[str]]:
    """Validate glossary form input."""
    errors: list[str] = []
    source_term = source_term_en.strip()
    approved_term = approved_term_zh.strip()
    if not source_term:
        errors.append("English source term is required.")
    if not approved_term:
        errors.append("Approved Chinese term is required.")
    if len(source_term) > 255:
        errors.append("English source term must be 255 characters or fewer.")
    if len(approved_term) > 255:
        errors.append("Approved Chinese term must be 255 characters or fewer.")
    if entity_type and len(entity_type.strip()) > 100:
        errors.append("Entity type must be 100 characters or fewer.")

    status_value = glossary_service.parse_status(entry_status)
    if errors:
        return None, errors
    return (
        GlossaryEntryData(
            source_term_en=source_term,
            approved_term_zh=approved_term,
            aliases_en=(aliases_en or "").strip() or None,
            entity_type=(entity_type or "").strip() or None,
            notes=(notes or "").strip() or None,
            status=status_value,
        ),
        [],
    )


def _render_form_errors(
    request: Request,
    db: Session,
    errors: list[str],
    edit_id: int | None,
    form_values: dict[str, object],
) -> HTMLResponse:
    """Render glossary page with validation errors."""
    edit_entry = glossary_service.get_entry(db, edit_id) if edit_id is not None else None
    return templates.TemplateResponse(
        request,
        "glossary.html",
        {
            "entries": glossary_service.list_entries(db),
            "query": "",
            "edit_entry": edit_entry,
            "statuses": [status.value for status in GlossaryStatus],
            "errors": errors,
            "message": None,
            "form": form_values,
        },
        status_code=status.HTTP_400_BAD_REQUEST,
    )
