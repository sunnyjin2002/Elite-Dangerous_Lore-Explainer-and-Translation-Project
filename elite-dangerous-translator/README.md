# Elite Dangerous Translator

Local MVP web app for managing an Elite Dangerous EN-CN article translation workflow.

This phase provides the project scaffold, initial SQLite persistence model, and a browser-based manual lore submission workflow. The app can create draft-oriented article and job records without running translation or publishing.

## Requirements

- Python 3.11+

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Update `.env` with any provider, wiki, SMTP, or source polling values you want to test later.

## Run

```powershell
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. Use **Submit manual lore draft** to create an article and queued manual submission job.

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```




## Translation Memory

Translation memory CSV files live under `data/references/translation_memory/`. Supported columns are:

- `source_text`
- `translated_text`
- `source_reference`
- `tags`

Import one file from the command line:

```powershell
python scripts/import_translation_memory.py data/references/translation_memory/example.csv
```

Import every CSV file under `data/references/translation_memory/`:

```powershell
python scripts/import_translation_memory.py
```

The browser translation memory page at `/translation-memory` can import CSV files, browse passages, and run lexical retrieval over source text and tags.

## Glossary

Glossary CSV files live under `data/glossary/`. Supported columns are:

- `source_term_en`
- `approved_term_zh`
- `aliases_en`
- `entity_type`
- `notes`
- `status`

Import one file from the command line:

```powershell
python scripts/import_glossary.py data/glossary/example.csv
```

Import every CSV file under `data/glossary/`:

```powershell
python scripts/import_glossary.py
```

The browser glossary page at `/glossary` can search, import CSV files, add entries, and edit existing entries.

## Manual Submission Flow

The browser workflow supports:

- `GET /articles/manual/new` to open the form
- `POST /articles/manual` to create a `manual_lore` article and `manual_submission` job
- `GET /jobs/{job_id}` to inspect job status and logs
- `GET /articles/{article_id}` to inspect source article metadata and text
- `GET /jobs` to list queued and historical jobs

Manual jobs are draft-oriented. They are queued for a later translation phase; no translation or publishing is run by this workflow.

## Database

The default database URL is `sqlite:///./data/app.db`.

Apply the initial schema migration:

```powershell
alembic upgrade head
```

Create a future migration after changing ORM models:

```powershell
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

The initial migration creates tables for articles, jobs, translations, glossary entries, translation memory, tags, article/tag links, publish records, and job logs.

## Quality Checks

```powershell
pytest
ruff check .
black --check .
```

## Current Scope

Included:

- FastAPI application factory and `/health` endpoint
- Jinja-rendered dashboard at `/` with recent jobs
- Manual submission form, article detail page, job list, and job detail page
- Service-backed route modules for manual articles and jobs, with placeholders for glossary, translation memory, publishing, and settings
- Settings loaded from `.env`
- SQLAlchemy 2.x engine/session setup for SQLite
- ORM models for the MVP persistence layer
- Alembic configuration and initial migration
- Placeholder services, clients, scripts, templates, static assets, and prompts

Not included yet:

- Automated source ingestion and parsing
- Translation, review, tagging, and publishing workflows
- Provider API integrations
- Authentication or authorization
