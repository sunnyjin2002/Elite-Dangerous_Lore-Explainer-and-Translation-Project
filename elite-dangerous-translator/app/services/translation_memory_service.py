"""Translation memory service operations."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TranslationMemoryEntry

_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class TranslationMemoryData:
    """Validated translation memory input."""

    source_text: str
    translated_text: str
    source_reference: str | None = None
    tags: str | None = None


@dataclass(frozen=True)
class TranslationMemoryImportSummary:
    """Summary of translation memory import changes."""

    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class TranslationMemoryMatch:
    """Retrieved translation memory entry with lexical score details."""

    entry: TranslationMemoryEntry
    score: float
    matched_terms: tuple[str, ...]


class TranslationMemoryService:
    """Imports, browses, and retrieves reusable translation memory passages."""

    def list_entries(
        self,
        db: Session,
        search: str | None = None,
        limit: int = 100,
    ) -> list[TranslationMemoryEntry]:
        """Return translation memory entries, optionally filtered by lexical search."""
        statement = (
            select(TranslationMemoryEntry)
            .order_by(TranslationMemoryEntry.created_at.desc(), TranslationMemoryEntry.id.desc())
            .limit(limit)
        )
        entries = list(db.scalars(statement))
        query = self.normalize_text(search or "")
        if not query:
            return entries
        query_tokens = set(self.tokenize(query))
        return [
            entry for entry in entries if self._entry_has_query_match(entry, query, query_tokens)
        ]

    def retrieve_similar_passages(
        self,
        db: Session,
        source_text: str,
        limit: int = 5,
    ) -> list[TranslationMemoryMatch]:
        """Retrieve similar passages using simple lexical token overlap scoring."""
        query = self.normalize_text(source_text)
        query_tokens = set(self.tokenize(query))
        if not query_tokens:
            return []

        matches: list[TranslationMemoryMatch] = []
        for entry in db.scalars(select(TranslationMemoryEntry)):
            score, matched_terms = self.score_entry(entry, query, query_tokens)
            if score > 0:
                matches.append(
                    TranslationMemoryMatch(
                        entry=entry,
                        score=score,
                        matched_terms=tuple(sorted(matched_terms)),
                    )
                )

        return sorted(
            matches,
            key=lambda match: (match.score, match.entry.created_at, match.entry.id),
            reverse=True,
        )[:limit]

    def score_entry(
        self,
        entry: TranslationMemoryEntry,
        normalized_query: str,
        query_tokens: set[str],
    ) -> tuple[float, set[str]]:
        """Score one entry against normalized query text.

        Scoring is intentionally transparent:
        - source token overlap is worth 2 points per token
        - tag token overlap is worth 1 point per token
        - source phrase containment gets a 10 point bonus
        """
        source = self.normalize_text(entry.source_text)
        tag_text = self.normalize_text(entry.tags or "")
        source_tokens = set(self.tokenize(source))
        tag_tokens = set(self.tokenize(tag_text))

        source_overlap = query_tokens & source_tokens
        tag_overlap = query_tokens & tag_tokens
        score = float((len(source_overlap) * 2) + len(tag_overlap))
        matched_terms = set(source_overlap | tag_overlap)

        if normalized_query and (normalized_query in source or source in normalized_query):
            score += 10.0
            matched_terms.add("phrase")

        return score, matched_terms

    def import_csv_file(self, db: Session, path: Path) -> TranslationMemoryImportSummary:
        """Import translation memory rows from a CSV file path."""
        with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            return self.import_csv(db, file_obj)

    def import_csv(self, db: Session, file_obj: TextIO) -> TranslationMemoryImportSummary:
        """Import translation memory rows from a CSV file object."""
        reader = csv.DictReader(file_obj)
        if reader.fieldnames is None:
            return TranslationMemoryImportSummary(
                skipped=1, errors=("CSV file has no header row.",)
            )

        inserted = 0
        updated = 0
        skipped = 0
        errors: list[str] = []
        existing_by_key = {
            self.dedupe_key(entry.source_text, entry.source_reference): entry
            for entry in db.scalars(select(TranslationMemoryEntry))
        }

        for row_number, row in enumerate(reader, start=2):
            try:
                data = self.row_to_memory_data(row)
            except ValueError as exc:
                skipped += 1
                errors.append(f"Row {row_number}: {exc}")
                continue

            key = self.dedupe_key(data.source_text, data.source_reference)
            existing = existing_by_key.get(key)
            if existing is None:
                entry = TranslationMemoryEntry(**self._entry_kwargs(data))
                db.add(entry)
                db.flush()
                existing_by_key[key] = entry
                inserted += 1
            else:
                existing.translated_text = data.translated_text
                existing.source_reference = data.source_reference
                existing.tags = data.tags
                updated += 1

        db.commit()
        return TranslationMemoryImportSummary(
            inserted=inserted,
            updated=updated,
            skipped=skipped,
            errors=tuple(errors),
        )

    def row_to_memory_data(self, row: dict[str, str | None]) -> TranslationMemoryData:
        """Map a CSV row to translation memory input using tolerant column names."""
        source_text = self._get_row_value(row, "source_text", "source", "english", "en")
        translated_text = self._get_row_value(
            row,
            "translated_text",
            "translation",
            "target_text",
            "chinese",
            "zh",
        )
        if not source_text:
            raise ValueError("source_text is required")
        if not translated_text:
            raise ValueError("translated_text is required")

        return TranslationMemoryData(
            source_text=source_text,
            translated_text=translated_text,
            source_reference=self._get_row_value(
                row, "source_reference", "reference", "source_ref"
            ),
            tags=self._get_row_value(row, "tags", "tag", "keywords"),
        )

    def dedupe_key(self, source_text: str, source_reference: str | None) -> tuple[str, str]:
        """Return a stable duplicate key for import updates."""
        return (self.normalize_text(source_text), self.normalize_text(source_reference or ""))

    def normalize_text(self, value: str) -> str:
        """Normalize lexical matching text."""
        return _NON_WORD_RE.sub(" ", value.lower()).strip()

    def tokenize(self, value: str) -> list[str]:
        """Tokenize normalized text and drop tiny noise tokens."""
        return [token for token in self.normalize_text(value).split() if len(token) > 1]

    def _entry_has_query_match(
        self,
        entry: TranslationMemoryEntry,
        normalized_query: str,
        query_tokens: set[str],
    ) -> bool:
        score, _ = self.score_entry(entry, normalized_query, query_tokens)
        if score > 0:
            return True
        fields = [entry.translated_text, entry.source_reference or ""]
        return any(normalized_query in self.normalize_text(field) for field in fields)

    def _get_row_value(self, row: dict[str, str | None], *names: str) -> str | None:
        normalized_row = {
            self.normalize_text(key).replace(" ", "_"): value
            for key, value in row.items()
            if key is not None
        }
        for name in names:
            value = normalized_row.get(self.normalize_text(name).replace(" ", "_"))
            if value is not None and value.strip():
                return value.strip()
        return None

    def _entry_kwargs(self, data: TranslationMemoryData) -> dict[str, object]:
        return {
            "source_text": data.source_text,
            "translated_text": data.translated_text,
            "source_reference": data.source_reference,
            "tags": data.tags,
        }
