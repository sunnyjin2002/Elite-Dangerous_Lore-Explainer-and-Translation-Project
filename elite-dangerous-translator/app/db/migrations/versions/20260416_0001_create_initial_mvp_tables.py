"""create initial mvp tables

Revision ID: 20260416_0001
Revises:
Create Date: 2026-04-16 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260416_0001"
down_revision = None
branch_labels = None
depends_on = None

source_type = sa.Enum(
    "official_news",
    "community",
    "manual",
    "manual_lore",
    name="source_type",
    native_enum=False,
    create_constraint=True,
)
job_type = sa.Enum(
    "ingest",
    "translate",
    "review",
    "tag",
    "publish",
    "manual_submission",
    name="job_type",
    native_enum=False,
    create_constraint=True,
)
job_status = sa.Enum(
    "pending",
    "queued",
    "ready_for_translation",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    name="job_status",
    native_enum=False,
    create_constraint=True,
)
glossary_status = sa.Enum(
    "draft",
    "approved",
    "deprecated",
    name="glossary_status",
    native_enum=False,
    create_constraint=True,
)
tag_type = sa.Enum(
    "topic",
    "entity",
    "source",
    name="tag_type",
    native_enum=False,
    create_constraint=True,
)
publish_status = sa.Enum(
    "pending",
    "published",
    "failed",
    name="publish_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("source_title", sa.String(length=500), nullable=False),
        sa.Column("source_body", sa.Text(), nullable=False),
        sa.Column("published_at_source", sa.DateTime(), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )
    op.create_table(
        "glossary_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_term_en", sa.String(length=255), nullable=False),
        sa.Column("approved_term_zh", sa.String(length=255), nullable=False),
        sa.Column("aliases_en", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", glossary_status, server_default="draft", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("tag_type", tag_type, server_default="topic", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "translation_memory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )
    op.create_table(
        "article_tags",
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("article_id", "tag_id"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("status", job_status, server_default="pending", nullable=False),
        sa.Column("target_language", sa.String(length=16), server_default="zh-CN", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
    )
    op.create_table(
        "job_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
    )
    op.create_table(
        "publish_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("destination_url", sa.String(length=1024), nullable=True),
        sa.Column("publish_status", publish_status, server_default="pending", nullable=False),
        sa.Column("response_metadata", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
    )
    op.create_table(
        "translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("translated_title", sa.String(length=500), nullable=True),
        sa.Column("translated_body", sa.Text(), nullable=True),
        sa.Column("reviewed_title", sa.String(length=500), nullable=True),
        sa.Column("reviewed_body", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("is_final", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
    )


def downgrade() -> None:
    op.drop_table("translations")
    op.drop_table("publish_records")
    op.drop_table("job_logs")
    op.drop_table("jobs")
    op.drop_table("article_tags")
    op.drop_table("translation_memory")
    op.drop_table("tags")
    op.drop_table("glossary_entries")
    op.drop_table("articles")
