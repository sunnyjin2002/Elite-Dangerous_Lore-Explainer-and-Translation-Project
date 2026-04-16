"""Job service operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Article, Job, JobLog, JobStatus, JobType


class JobService:
    """Creates and reads job records and structured job logs."""

    def create_manual_submission_job(
        self,
        db: Session,
        article: Article,
        target_language: str,
    ) -> Job:
        """Create a draft-oriented manual submission job for an article."""
        job = Job(
            article=article,
            job_type=JobType.manual_submission,
            status=JobStatus.queued,
            target_language=target_language,
        )
        db.add(job)
        db.flush()
        return job

    def add_log(self, db: Session, job: Job, stage: str, message: str) -> JobLog:
        """Append a structured log entry to a job."""
        log = JobLog(job=job, stage=stage, message=message)
        db.add(log)
        db.flush()
        return log

    def list_recent_jobs(self, db: Session, limit: int = 10) -> list[Job]:
        """Return recent jobs with article metadata for dashboard display."""
        statement = (
            select(Job)
            .options(selectinload(Job.article))
            .order_by(Job.created_at.desc(), Job.id.desc())
            .limit(limit)
        )
        return list(db.scalars(statement))

    def get_job(self, db: Session, job_id: int) -> Job | None:
        """Return one job with article and logs loaded."""
        statement = (
            select(Job)
            .where(Job.id == job_id)
            .options(selectinload(Job.article), selectinload(Job.logs))
        )
        return db.scalar(statement)

    def list_jobs(self, db: Session) -> list[Job]:
        """Return all jobs ordered newest first."""
        statement = (
            select(Job)
            .options(selectinload(Job.article))
            .order_by(Job.created_at.desc(), Job.id.desc())
        )
        return list(db.scalars(statement))
