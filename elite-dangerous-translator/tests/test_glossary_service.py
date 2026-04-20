"""Glossary service tests."""

from io import StringIO

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.services.glossary_service import GlossaryService


def test_glossary_import_lookup_and_passage_matching() -> None:
    """CSV import supports duplicate updates and reusable lookup helpers."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    service = GlossaryService()

    csv_data = StringIO(
        "source_term_en,approved_term_zh,aliases_en,entity_type,notes,status\n"
        "Thargoid,????,Thargoids|Bug,Species,Hostile alien species,approved\n"
        "Thargoid,?????,Interceptor,Species,Updated term,approved\n"
        "Frame Shift Drive,????,FSD,Technology,,draft\n"
    )

    with session_factory() as db:
        summary = service.import_csv(db, csv_data)

        assert summary.inserted == 2
        assert summary.updated == 1
        assert summary.skipped == 0
        assert service.lookup_exact(db, "thargoid").approved_term_zh == "?????"
        assert service.lookup_alias(db, "fsd").source_term_en == "Frame Shift Drive"

        matches = service.find_matches_for_passage(
            db,
            "The commander escaped the Interceptor after the FSD came online.",
        )

        assert [entry.source_term_en for entry in matches] == ["Frame Shift Drive", "Thargoid"]
