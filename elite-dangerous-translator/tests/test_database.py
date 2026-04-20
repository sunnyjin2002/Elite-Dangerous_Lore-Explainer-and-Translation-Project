"""Database model smoke tests."""

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base


def test_models_create_expected_tables() -> None:
    """All MVP ORM tables can be created in SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    table_names = set(inspect(engine).get_table_names())
    assert table_names == {
        "article_tags",
        "articles",
        "glossary_entries",
        "job_logs",
        "jobs",
        "publish_records",
        "tags",
        "translation_memory",
        "translations",
    }
