"""SQLAlchemy ORM models for the MVP persistence layer."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    """Return a naive UTC timestamp for SQLite-compatible defaults."""
    return datetime.utcnow()


class SourceType(StrEnum):
    """Supported article source categories."""

    official_news = "official_news"
    community = "community"
    manual = "manual"
    manual_lore = "manual_lore"


class JobType(StrEnum):
    """Supported background job categories."""

    ingest = "ingest"
    translate = "translate"
    review = "review"
    tag = "tag"
    publish = "publish"
    manual_submission = "manual_submission"


class JobStatus(StrEnum):
    """Lifecycle states for a queued unit of work."""

    pending = "pending"
    queued = "queued"
    ready_for_translation = "ready_for_translation"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class GlossaryStatus(StrEnum):
    """Approval states for glossary entries."""

    draft = "draft"
    approved = "approved"
    deprecated = "deprecated"


class TagType(StrEnum):
    """Tag categories used for article organization."""

    topic = "topic"
    entity = "entity"
    source = "source"


class PublishStatus(StrEnum):
    """Publishing states for outbound records."""

    pending = "pending"
    published = "published"
    failed = "failed"


source_type_enum = Enum(
    SourceType,
    name="source_type",
    native_enum=False,
    create_constraint=True,
)
job_type_enum = Enum(JobType, name="job_type", native_enum=False, create_constraint=True)
job_status_enum = Enum(JobStatus, name="job_status", native_enum=False, create_constraint=True)
glossary_status_enum = Enum(
    GlossaryStatus,
    name="glossary_status",
    native_enum=False,
    create_constraint=True,
)
tag_type_enum = Enum(TagType, name="tag_type", native_enum=False, create_constraint=True)
publish_status_enum = Enum(
    PublishStatus,
    name="publish_status",
    native_enum=False,
    create_constraint=True,
)


class Article(Base):
    """Source article discovered or submitted for translation."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[SourceType] = mapped_column(source_type_enum)
    source_url: Mapped[str | None] = mapped_column(String(1024))
    source_title: Mapped[str] = mapped_column(String(500))
    source_body: Mapped[str] = mapped_column(Text)
    published_at_source: Mapped[datetime | None] = mapped_column(DateTime)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    jobs: Mapped[list[Job]] = relationship(back_populates="article", cascade="all, delete-orphan")
    translations: Mapped[list[Translation]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )
    publish_records: Mapped[list[PublishRecord]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )
    tag_links: Mapped[list[ArticleTag]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list[Tag]] = relationship(
        secondary="article_tags",
        back_populates="articles",
        viewonly=True,
    )


class Job(Base):
    """Work item for ingestion, translation, review, tagging, or publishing."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    job_type: Mapped[JobType] = mapped_column(job_type_enum)
    status: Mapped[JobStatus] = mapped_column(job_status_enum, default=JobStatus.pending)
    target_language: Mapped[str] = mapped_column(String(16), default="zh-CN")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    article: Mapped[Article] = relationship(back_populates="jobs")
    translations: Mapped[list[Translation]] = relationship(back_populates="job")
    publish_records: Mapped[list[PublishRecord]] = relationship(back_populates="job")
    logs: Mapped[list[JobLog]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Translation(Base):
    """Translated and reviewed article content."""

    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    translated_title: Mapped[str | None] = mapped_column(String(500))
    translated_body: Mapped[str | None] = mapped_column(Text)
    reviewed_title: Mapped[str | None] = mapped_column(String(500))
    reviewed_body: Mapped[str | None] = mapped_column(Text)
    review_notes: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    article: Mapped[Article] = relationship(back_populates="translations")
    job: Mapped[Job | None] = relationship(back_populates="translations")


class GlossaryEntry(Base):
    """Approved or draft terminology mapping."""

    __tablename__ = "glossary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_term_en: Mapped[str] = mapped_column(String(255))
    approved_term_zh: Mapped[str] = mapped_column(String(255))
    aliases_en: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[GlossaryStatus] = mapped_column(
        glossary_status_enum,
        default=GlossaryStatus.draft,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class TranslationMemoryEntry(Base):
    """Reusable source and translated text pair."""

    __tablename__ = "translation_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    tags: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Tag(Base):
    """Article tag."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    tag_type: Mapped[TagType] = mapped_column(tag_type_enum, default=TagType.topic)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    article_links: Mapped[list[ArticleTag]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
    )
    articles: Mapped[list[Article]] = relationship(
        secondary="article_tags",
        back_populates="tags",
        viewonly=True,
    )


class ArticleTag(Base):
    """Association table linking articles and tags."""

    __tablename__ = "article_tags"

    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)

    article: Mapped[Article] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(back_populates="article_links")


class PublishRecord(Base):
    """Record of an attempt to publish translated content."""

    __tablename__ = "publish_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    destination_url: Mapped[str | None] = mapped_column(String(1024))
    publish_status: Mapped[PublishStatus] = mapped_column(
        publish_status_enum,
        default=PublishStatus.pending,
    )
    response_metadata: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    article: Mapped[Article] = relationship(back_populates="publish_records")
    job: Mapped[Job | None] = relationship(back_populates="publish_records")


class JobLog(Base):
    """Log message attached to a job stage."""

    __tablename__ = "job_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    stage: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    job: Mapped[Job] = relationship(back_populates="logs")


__all__ = [
    "Article",
    "ArticleTag",
    "Base",
    "GlossaryEntry",
    "Job",
    "JobLog",
    "PublishRecord",
    "Tag",
    "Translation",
    "JobStatus",
    "JobType",
    "SourceType",
    "TranslationMemoryEntry",
]
