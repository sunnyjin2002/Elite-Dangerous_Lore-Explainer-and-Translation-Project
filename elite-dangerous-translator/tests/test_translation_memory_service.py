"""Translation memory service tests."""

from io import StringIO

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.services.translation_memory_service import TranslationMemoryService


def test_translation_memory_import_and_lexical_retrieval() -> None:
    """CSV import updates duplicates and retrieval ranks lexical matches."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    service = TranslationMemoryService()

    csv_data = StringIO(
        "source_text,translated_text,source_reference,tags\n"
        "Frame Shift Drive charging,????????,Codex A,ship;fsd\n"
        "Thargoid interceptor detected,???????????,Codex B,alien;combat\n"
        "Frame Shift Drive charging,???????,Codex A,ship;updated\n"
    )

    with session_factory() as db:
        summary = service.import_csv(db, csv_data)

        assert summary.inserted == 2
        assert summary.updated == 1
        assert summary.skipped == 0

        matches = service.retrieve_similar_passages(
            db,
            "The pilot waited for the frame shift drive to finish charging.",
        )

        assert matches[0].entry.source_text == "Frame Shift Drive charging"
        assert matches[0].entry.translated_text == "???????"
        assert matches[0].score > 0

        tag_matches = service.retrieve_similar_passages(db, "alien contact", limit=1)
        assert tag_matches[0].entry.source_text == "Thargoid interceptor detected"
