# Elite Dangerous Translation System — MVP Technical Specification

## 1. Purpose

Build a local, web-accessed MVP that translates **Elite Dangerous** English lore/news text into **Chinese**, using:

* a custom glossary of approved vocabulary
* prior human-translated passages as translation memory/reference material
* an LLM-based translation step
* an LLM-assisted review step
* keyword extraction and tagging
* wiki publishing support
* notification support

The MVP should run locally through a web server and be usable from a browser. It should support both:

1. **Automatic intake** of new official articles from a monitored website
2. **Manual intake** where a user pastes text or supplies a source URL

The system should prioritize **translation consistency, glossary enforcement, and operational simplicity** over full agent autonomy.

---

## 2. MVP Scope

### In scope

* Local web app with browser UI
* Hourly polling of source website for new articles
* Manual submission of source text and/or source URL
* Article ingestion and storage
* Glossary-aware translation
* Retrieval of similar prior translated passages
* LLM-based review/verification
* Keyword extraction and tagging
* Draft management
* Publishing to wiki via a controlled programmatic publishing layer
* Email notification on completion
* Job status tracking and logs

### Out of scope for MVP

* Full autonomous multi-agent architecture
* Complex workflow orchestration frameworks
* Multi-user authentication
* Cloud deployment
* Full multilingual support beyond designing with future extensibility in mind
* Real-time push/webhook monitoring if the source site does not support it
* Fully automatic categorization independent of source metadata

---

## 3. Product Goals

### Primary goals

* Produce Chinese translations that are more consistent than generic machine translation
* Reuse approved terminology and prior translations
* Reduce manual effort for translating new and old lore/news content
* Provide a clean local UI for running and inspecting jobs
* Create a portfolio-quality project with clear architecture and practical LLM integration

### Non-functional goals

* Easy to run locally
* Easy to debug
* Modular enough to extend later
* Safe publishing flow
* Reproducible processing pipeline

---

## 4. Users and Usage Modes

### User roles for MVP

* **Primary operator**: the project owner using the local web UI
* Optional future role: subscribers receiving email notifications

### Usage modes

#### A. Automatic news workflow

1. Poll source site hourly
2. Detect new article
3. Ingest content
4. Translate
5. Review
6. Extract tags
7. Save result
8. Publish automatically to predefined wiki destination if allowed
9. Send notification

#### B. Manual translation workflow

1. User opens local web UI
2. User pastes text and/or source URL
3. User optionally provides title
4. System ingests content
5. Translate
6. Review
7. Extract tags
8. Save as draft by default
9. User may later publish manually or provide exact destination URL/path
10. Send notification/status update

---

## 5. Recommended Architecture

Use a **modular monolith** for the MVP.

### Why

* simpler than microservices
* easier local setup
* easier for Codex to scaffold
* still supports clear module boundaries

### Architecture style

* Backend API server
* Background job worker
* Local relational database
* Browser-based frontend
* LLM provider integration
* Optional vector or lexical retrieval for translation memory

### High-level components

1. **Frontend Web UI**
2. **Backend API**
3. **Scheduler / Poller**
4. **Job Processor**
5. **Glossary Service**
6. **Translation Memory Retrieval Service**
7. **Translation Service**
8. **Review Service**
9. **Tag Extraction Service**
10. **Publishing Service**
11. **Notification Service**
12. **Persistence Layer**

---

## 6. Recommended Tech Stack

## Backend

* **Python 3.11+**
* **FastAPI** for backend API and local web server
* **Uvicorn** as ASGI server
* **Pydantic** for request/response schemas and config validation
* **SQLAlchemy 2.x** for ORM/database access
* **Alembic** for schema migrations

## Frontend

Choose one of these:

### Option A: Simplest MVP

* **Jinja2 server-rendered HTML templates**
* HTMX optional for lightweight interactivity

### Option B: Slightly richer UI

* **React + Vite** frontend
* FastAPI backend serving API only

**Recommendation for first MVP:**

* Start with **FastAPI + Jinja2 + minimal JavaScript**
* Upgrade later if needed

## Database

* **SQLite** for MVP local persistence

## Background jobs / scheduling

### Simplest

* **APScheduler** for hourly polling
* **FastAPI BackgroundTasks** or a simple async task runner for small jobs

### Slightly more robust

* **Celery + Redis** or **RQ + Redis**

**Recommendation for MVP:**

* Start with **APScheduler + database-backed job records**
* Process jobs in the app process or a simple worker process

## Web scraping / ingestion

* **httpx** for HTTP requests
* **BeautifulSoup4** or **selectolax** for HTML parsing
* **trafilatura** optional for article text extraction

## LLM / NLP

* **OpenAI API** or another LLM provider accessible from Python
* Direct SDK/API integration first
* Optional later: LangChain only if explicitly desired for learning

## Retrieval / search

### MVP retrieval options

1. **Simple lexical retrieval** using SQLite + SQL LIKE / FTS
2. **Embeddings-based retrieval** using local vectors

**Recommendation:**

* Start with **SQLite FTS5** for translation memory retrieval
* Add embeddings later if needed

## Wiki publishing

* **httpx** or **requests** to call the target wiki API
* Controlled publishing module using stored credentials from environment variables

## Email notifications

* **SendGrid**, **Amazon SES**, or SMTP
* For local MVP, SMTP or a transactional API is enough

## Config and secrets

* **python-dotenv** for local `.env`
* Pydantic settings model

## Testing

* **pytest**
* **pytest-asyncio** if async is used
* **respx** or request mocking for HTTP integrations

## Dev tooling

* **ruff** for linting
* **black** for formatting
* **mypy** optional
* **pre-commit** optional

---

## 7. Should LangChain or MCP be used?

### For the MVP

Not required.

### Recommendation

Build the MVP first with:

* direct LLM API calls
* explicit prompt templates
* explicit Python modules for retrieval, translation, review, and publishing

### Why

* fewer abstractions
* easier debugging
* easier prompt and data control
* easier for Codex to scaffold accurately

### When to add LangChain later

Only if you want to experiment with:

* reusable chains
* prompt/template management across many steps
* tool-using workflows
* more agentic iterative refinement

### MCP note

MCP is not needed for this MVP unless you intentionally want to expose parts of the system as tools to another AI client. It adds complexity without helping the core local translation workflow.

---

## 8. Data Flow Overview

### Flow A: Automatic source monitoring

1. Scheduler triggers polling job hourly
2. Poller fetches article list from source website
3. System extracts article URLs/IDs and compares against stored records
4. New article found
5. Article content is fetched and stored
6. Translation job record is created
7. Job processor runs translation pipeline
8. Result stored as translation draft/result
9. Optional auto-publish for known article type/path
10. Notification sent

### Flow B: Manual submission

1. User submits source text and/or URL through web UI
2. Backend stores submission record
3. Translation job record is created
4. Job processor runs translation pipeline
5. Result stored as draft
6. User reviews result in web UI
7. User either leaves as draft or provides exact destination path/URL for publishing
8. Publishing job runs
9. Notification/status sent

---

## 9. Core Modules

## 9.1 Ingestion Module

Responsibilities:

* fetch source content from monitored site
* accept manual text submission
* normalize raw input into a standard internal representation

Inputs:

* source URL
* manual title
* manual body text
* source type metadata

Outputs:

* article record
* source content record
* job record

Key functions:

* `poll_source_site()`
* `fetch_article(url)`
* `parse_article(html)`
* `create_manual_submission(payload)`

---

## 9.2 Source Metadata / Intake Classification Module

Responsibilities:

* determine article source type from origin/path
* set publishing defaults based on source

Examples:

* official news URL -> `official_news`
* manual pasted text -> `manual_lore`

For MVP, source metadata can be deterministic based on trigger/input rather than ML classification.

---

## 9.3 Glossary Module

Responsibilities:

* load and manage approved terminology
* expose lookup APIs for relevant term retrieval
* validate that output follows required terminology where applicable

Suggested glossary fields:

* `id`
* `source_term_en`
* `approved_term_zh`
* `aliases_en`
* `aliases_zh`
* `entity_type`
* `notes`
* `example_usage`
* `status` (approved / review / deprecated)
* `created_at`
* `updated_at`

MVP glossary source:

* import from spreadsheet (CSV/XLSX)

Key functions:

* `import_glossary(file)`
* `lookup_terms(text)`
* `validate_translation_terms(source_text, translated_text)`

---

## 9.4 Translation Memory Module

Responsibilities:

* store prior source/translation passage pairs
* retrieve similar past examples to improve consistency

Suggested storage:

* source text chunks
* translated text chunks
* metadata: source article, date, tags, notes

MVP retrieval approach:

* SQLite FTS5 full-text search over English source text and optional tags

Key functions:

* `import_translation_memory(file_or_records)`
* `retrieve_similar_passages(source_text, limit=5)`

---

## 9.5 Translation Service

Responsibilities:

* assemble prompt context
* invoke LLM
* generate first-pass translation

Input context:

* source title/body
* glossary matches
* similar translated examples
* target language
* style guide
* source type metadata

Output:

* translated title
* translated body
* translation notes
* unresolved terms list

Prompt requirements:

* obey glossary mappings strictly where given
* maintain lore consistency
* preserve names/entities accurately
* do not invent lore
* produce natural Chinese
* flag uncertain terms instead of guessing silently

Key function:

* `translate_article(article_id)`

---

## 9.6 Review Service

Responsibilities:

* review source vs translated result
* identify omissions, mistranslations, glossary violations, awkward wording
* optionally produce corrected final version

Implementation strategy:

1. deterministic QA checks
2. LLM review pass
3. final corrected version assembly

Deterministic checks may include:

* untranslated English fragments remain?
* required glossary terms used?
* disallowed variants used?
* title missing?
* paragraph count abnormal?

Output:

* review status
* list of issues
* corrected translation
* confidence score (heuristic)

Key function:

* `review_translation(job_id)`

---

## 9.7 Keyword Extraction / Tagging Module

Responsibilities:

* extract tags from source and/or final translation
* support browsing, search, metadata, and future retrieval

Examples of tags:

* Thargoids
* Aegis
* Federation
* Shinrarta Dezhra
* Guardian technology
* Community Goal

Implementation options:

### MVP option A

* LLM-generated tags constrained by max tag count and formatting rules

### MVP option B

* hybrid of rule-based glossary/entity match + LLM cleanup

**Recommendation:**

* Use **hybrid tagging**:

  * glossary/entity matching first
  * LLM fills in high-level topical tags

Key function:

* `extract_tags(article_id, translated_text)`

---

## 9.8 Publishing Service

Responsibilities:

* publish reviewed content to the target wiki
* prevent uncontrolled edits
* support draft vs publish flows

Rules:

* official monitored news may auto-publish to predefined destination if enabled
* manual submissions default to draft only
* manual submissions publish only when exact destination URL/path is provided or manually approved

Inputs:

* translated title/body
* source metadata
* target destination
* tags

Security:

* credentials from environment variables only
* no credentials inside prompts or database plaintext if avoidable

Key functions:

* `publish_news_article(job_id)`
* `publish_manual_article(job_id, destination_url)`

---

## 9.9 Notification Service

Responsibilities:

* send email notifications on completion/failure/publication

Email content may include:

* article title
* source URL
* job status
* whether published or saved as draft
* destination/wiki URL if published
* unresolved terms if any

Key function:

* `send_job_notification(job_id)`

---

## 9.10 Web UI

Responsibilities:

* provide local browser interface
* show jobs, drafts, logs, and results
* support manual submission and publication

Recommended MVP pages:

1. **Dashboard**

   * recent jobs
   * status counts
   * latest detected articles

2. **Manual Submission Page**

   * title input (optional)
   * source URL input (optional)
   * raw text textarea
   * target language selector (default Chinese)
   * submit button

3. **Job Detail Page**

   * source text
   * translated output
   * review notes
   * extracted tags
   * job logs
   * publish controls

4. **Glossary Page**

   * view/search glossary entries
   * upload/import glossary file

5. **Translation Memory Page**

   * view/search imported translation references

6. **Settings Page**

   * LLM configuration
   * email configuration
   * source polling interval
   * wiki publishing toggle

---

## 10. Database Design

Recommended MVP tables:

### `articles`

* `id`
* `source_type`
* `source_url`
* `source_title`
* `source_body`
* `published_at_source`
* `discovered_at`
* `created_at`
* `updated_at`

### `jobs`

* `id`
* `article_id`
* `job_type` (auto_news / manual_submission / publish_only)
* `status`
* `target_language`
* `error_message`
* `created_at`
* `started_at`
* `finished_at`

### `translations`

* `id`
* `article_id`
* `job_id`
* `translated_title`
* `translated_body`
* `reviewed_title`
* `reviewed_body`
* `review_notes`
* `confidence_score`
* `is_final`
* `created_at`

### `glossary_entries`

* `id`
* `source_term_en`
* `approved_term_zh`
* `aliases_en`
* `entity_type`
* `notes`
* `status`
* `created_at`
* `updated_at`

### `translation_memory`

* `id`
* `source_text`
* `translated_text`
* `source_reference`
* `tags`
* `created_at`

### `tags`

* `id`
* `name`
* `tag_type`
* `created_at`

### `article_tags`

* `article_id`
* `tag_id`

### `publish_records`

* `id`
* `article_id`
* `job_id`
* `destination_url`
* `publish_status`
* `response_metadata`
* `published_at`

### `job_logs`

* `id`
* `job_id`
* `stage`
* `message`
* `created_at`

---

## 11. Job Status Model

Suggested statuses:

* `detected`
* `queued`
* `ingesting`
* `ready_for_translation`
* `translating`
* `reviewing`
* `tagging`
* `draft_saved`
* `awaiting_publish_instruction`
* `publishing`
* `published`
* `failed`
* `needs_human_review`

This should be visible in the UI.

---

## 12. API Design (FastAPI)

## Ingestion / articles

* `GET /articles`
* `GET /articles/{article_id}`
* `POST /articles/manual`
* `POST /articles/poll`

## Jobs

* `GET /jobs`
* `GET /jobs/{job_id}`
* `POST /jobs/{job_id}/run`
* `POST /jobs/{job_id}/retry`

## Translation

* `POST /jobs/{job_id}/translate`
* `POST /jobs/{job_id}/review`
* `POST /jobs/{job_id}/tags`

## Publishing

* `POST /jobs/{job_id}/publish`
* payload may include explicit destination URL/path for manual jobs

## Glossary

* `GET /glossary`
* `POST /glossary/import`
* `POST /glossary`
* `PUT /glossary/{entry_id}`

## Translation memory

* `GET /translation-memory`
* `POST /translation-memory/import`

## Settings / health

* `GET /health`
* `GET /settings`
* `POST /settings`

---

## 13. Suggested Project Structure

```text
elite-dangerous-translator/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ routes_articles.py
│  │  ├─ routes_jobs.py
│  │  ├─ routes_glossary.py
│  │  ├─ routes_translation_memory.py
│  │  ├─ routes_publish.py
│  │  └─ routes_settings.py
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ logging.py
│  │  └─ scheduler.py
│  ├─ db/
│  │  ├─ base.py
│  │  ├─ session.py
│  │  ├─ models.py
│  │  └─ migrations/
│  ├─ services/
│  │  ├─ ingestion_service.py
│  │  ├─ source_parser_service.py
│  │  ├─ glossary_service.py
│  │  ├─ translation_memory_service.py
│  │  ├─ translation_service.py
│  │  ├─ review_service.py
│  │  ├─ tagging_service.py
│  │  ├─ publish_service.py
│  │  ├─ notification_service.py
│  │  └─ job_service.py
│  ├─ clients/
│  │  ├─ llm_client.py
│  │  ├─ wiki_client.py
│  │  └─ email_client.py
│  ├─ templates/
│  │  ├─ dashboard.html
│  │  ├─ article_detail.html
│  │  ├─ manual_submit.html
│  │  ├─ glossary.html
│  │  └─ settings.html
│  ├─ static/
│  │  ├─ css/
│  │  └─ js/
│  └─ prompts/
│     ├─ translate_prompt.txt
│     ├─ review_prompt.txt
│     └─ tagging_prompt.txt
├─ data/
│  ├─ uploads/
│  ├─ imports/
│  └─ app.db
├─ tests/
├─ .env
├─ pyproject.toml
├─ README.md
└─ alembic.ini
```

---

## 14. Prompting Strategy

Use plain prompt templates stored in files.

### Translation prompt should include

* system instructions for lore-aware translation
* glossary entries relevant to the current text
* similar prior translations
* formatting instructions
* target language
* requirement to list unresolved terms

### Review prompt should include

* source text
* translated text
* glossary entries
* review checklist
* instruction to produce corrected final text when needed

### Tagging prompt should include

* title/body
* glossary/entity matches
* maximum number of tags
* requirement for concise normalized tags

Avoid hidden prompt sprawl. Keep prompts versioned and inspectable.

---

## 15. Retrieval Strategy

### Glossary retrieval

* exact match first
* alias match second
* simple normalized string matching

### Translation memory retrieval

MVP recommendation:

* chunk source examples into passages
* store in SQLite FTS5
* retrieve top N by lexical relevance

Why not embeddings first:

* simpler
* less infra
* easier debugging
* likely sufficient for MVP scale

Embeddings can be added later if lexical recall is poor.

---

## 16. Security Considerations

* Store API keys and wiki credentials in environment variables
* Do not hardcode secrets
* Do not include secrets in prompts, logs, or frontend output
* Limit auto-publish behavior to deterministic source types
* Manual submissions should default to draft only
* Log publishing attempts and responses

---

## 17. Error Handling

The pipeline should fail safely.

Examples:

* source fetch failure -> retry later, log error
* translation failure -> mark job failed, allow retry
* review failure -> preserve first-pass translation, mark for human review
* publish failure -> preserve reviewed translation, mark publish_failed state or failed log
* notification failure -> do not roll back completed work

Each stage should write structured logs to `job_logs`.

---

## 18. MVP Milestones

## Milestone 1: Local foundation

* FastAPI app runs locally
* SQLite database connected
* basic dashboard page
* manual submission form works

## Milestone 2: Core translation pipeline

* glossary import works
* translation memory import works
* translation step works
* review step works
* results stored

## Milestone 3: Automatic intake

* hourly polling works
* new article detection works
* article ingestion works
* job records created automatically

## Milestone 4: Tagging and result management

* keyword extraction and tagging works
* job detail page shows tags and logs
* drafts visible in UI

## Milestone 5: Publishing + notification

* manual publish flow works
* auto-publish for monitored news works if enabled
* email notifications work

---

## 19. Suggested Codex Build Order

Ask Codex to scaffold in this order:

1. FastAPI app skeleton with Jinja templates
2. SQLAlchemy models + Alembic migrations
3. Manual submission endpoint + form
4. Job table and status model
5. Glossary import and lookup service
6. Translation memory import and retrieval service
7. LLM client wrapper
8. Translation service
9. Review service
10. Tagging service
11. Dashboard and job detail pages
12. Source site poller
13. Publishing service
14. Notification service
15. Tests for each service

This order minimizes integration pain.

---

## 20. Definition of Done for MVP

The MVP is complete when:

* local web app starts successfully
* user can submit manual text from browser
* system can poll source website and detect new article
* glossary and prior translations influence translation output
* translation is reviewed before finalization
* tags are extracted and stored
* manual jobs save as draft by default
* official monitored news can be published to known path via controlled publish flow
* completion email can be sent
* logs and statuses are visible in UI

---

## 21. Post-MVP Extensions

* React frontend
* embeddings-based retrieval
* approval queue / diff view
* richer glossary editor
* side-by-side translation comparison UI
* confidence scoring improvements
* multilingual target support
* LangChain-based orchestration experiments
* MCP wrapper for exposing internal tools

---

## 22. Final Recommendation Summary

For the first MVP:

* use **FastAPI + Jinja2 + SQLite**
* use **APScheduler** for polling
* use **direct LLM API calls**, not LangChain
* use **SQLite FTS5** for translation memory retrieval
* use **hybrid tagging** (glossary/entity matching + LLM)
* keep the system as a **modular monolith** running locally

This gives the best balance of:

* simplicity
* learning value
* reliability
* portfolio quality
* Codex friendliness
