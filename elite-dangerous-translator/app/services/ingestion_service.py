"""Ingestion service operations."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Article, Job, SourceType
from app.services.job_service import JobService


@dataclass(frozen=True)
class ManualSubmissionData:
    """Validated manual submission form data."""

    title: str | None
    source_url: str | None
    source_text: str
    target_language: str


@dataclass(frozen=True)
class ManualSubmissionResult:
    """Records created for a manual submission."""

    article: Article
    job: Job


class IngestionService:
    """Coordinates article ingestion entry points."""

    def __init__(self, job_service: JobService | None = None) -> None:
        self.job_service = job_service or JobService()


    def validate_manual_submission(
        self,
        title: str | None,
        source_url: str | None,
        source_text: str | None,
        target_language: str | None,
    ) -> tuple[ManualSubmissionData | None, list[str]]:
        """Validate and normalize manual submission form input."""
        errors: list[str] = []
        normalized_title = (title or "").strip() or None
        normalized_url = (source_url or "").strip() or None
        normalized_text = (source_text or "").strip()
        normalized_language = (target_language or "zh-CN").strip() or "zh-CN"

        if not normalized_text:
            errors.append("Source text is required.")
        if normalized_title is not None and len(normalized_title) > 500:
            errors.append("Title must be 500 characters or fewer.")
        if normalized_url is not None and len(normalized_url) > 1024:
            errors.append("Source URL must be 1024 characters or fewer.")
        if len(normalized_language) > 16:
            errors.append("Target language must be 16 characters or fewer.")

        if errors:
            return None, errors
        return (
            ManualSubmissionData(
                title=normalized_title,
                source_url=normalized_url,
                source_text=normalized_text,
                target_language=normalized_language,
            ),
            [],
        )

    def submit_manual_article(
        self,
        db: Session,
        submission: ManualSubmissionData,
    ) -> ManualSubmissionResult:
        """Persist a manual lore article and create its draft translation job."""
        source_text = submission.source_text.strip()
        title = (submission.title or "").strip() or self._derive_title(source_text)
        source_url = (submission.source_url or "").strip() or None
        target_language = submission.target_language.strip() or "zh-CN"

        article = Article(
            source_type=SourceType.manual_lore,
            source_url=source_url,
            source_title=title,
            source_body=source_text,
        )
        db.add(article)
        db.flush()

        job = self.job_service.create_manual_submission_job(db, article, target_language)
        self.job_service.add_log(
            db,
            job,
            "manual_submission",
            "Manual lore draft was submitted from the browser.",
        )
        self.job_service.add_log(
            db,
            job,
            "queued",
            "Job is queued and ready for a future translation phase.",
        )
        db.commit()
        db.refresh(article)
        db.refresh(job)
        return ManualSubmissionResult(article=article, job=job)

    def get_article(self, db: Session, article_id: int) -> Article | None:
        """Return one article with related jobs and logs loaded."""
        statement = (
            select(Article)
            .where(Article.id == article_id)
            .options(selectinload(Article.jobs).selectinload(Job.logs))
        )
        return db.scalar(statement)

    def _derive_title(self, source_text: str) -> str:
        """Derive a readable title from the first source text line."""
        first_line = source_text.splitlines()[0].strip() if source_text.splitlines() else ""
        if not first_line:
            return "Manual lore submission"
        return first_line[:120]
