"""Glossary service operations."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GlossaryEntry, GlossaryStatus

_ALIAS_SPLIT_RE = re.compile(r"[;,|]")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "utf-16", "cp1252")


@dataclass(frozen=True)
class GlossaryEntryData:
    """Validated glossary entry input."""

    source_term_en: str
    approved_term_zh: str
    aliases_en: str | None = None
    entity_type: str | None = None
    notes: str | None = None
    status: GlossaryStatus = GlossaryStatus.draft


@dataclass(frozen=True)
class ImportSummary:
    """Summary of glossary import changes."""

    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: tuple[str, ...] = ()


class GlossaryService:
    """Manages glossary storage, import, and lookup."""

    def list_entries(self, db: Session, search: str | None = None) -> list[GlossaryEntry]:
        """Return glossary entries, optionally filtered by a simple text search."""
        statement = select(GlossaryEntry).order_by(GlossaryEntry.source_term_en.asc())
        entries = list(db.scalars(statement))
        query = self.normalize_text(search or "")
        if not query:
            return entries
        return [entry for entry in entries if self._entry_matches_query(entry, query)]

    def get_entry(self, db: Session, entry_id: int) -> GlossaryEntry | None:
        """Return one glossary entry by id."""
        return db.get(GlossaryEntry, entry_id)

    def create_entry(self, db: Session, data: GlossaryEntryData) -> GlossaryEntry:
        """Create a glossary entry or update the duplicate source term."""
        existing = self.lookup_exact(db, data.source_term_en)
        if existing is not None:
            self._apply_entry_data(existing, data)
            db.commit()
            db.refresh(existing)
            return existing

        entry = GlossaryEntry(**self._entry_kwargs(data))
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def update_entry(
        self, db: Session, entry_id: int, data: GlossaryEntryData
    ) -> GlossaryEntry | None:
        """Update an existing glossary entry."""
        entry = self.get_entry(db, entry_id)
        if entry is None:
            return None
        self._apply_entry_data(entry, data)
        db.commit()
        db.refresh(entry)
        return entry

    def lookup_exact(self, db: Session, source_term: str) -> GlossaryEntry | None:
        """Find an entry by exact normalized English source term."""
        wanted = self.normalize_text(source_term)
        if not wanted:
            return None
        for entry in db.scalars(select(GlossaryEntry)):
            if self.normalize_text(entry.source_term_en) == wanted:
                return entry
        return None

    def lookup_alias(self, db: Session, alias: str) -> GlossaryEntry | None:
        """Find an entry by exact normalized alias."""
        wanted = self.normalize_text(alias)
        if not wanted:
            return None
        for entry in db.scalars(select(GlossaryEntry)):
            if wanted in {
                self.normalize_text(item) for item in self.split_aliases(entry.aliases_en)
            }:
                return entry
        return None

    def find_matches_for_passage(self, db: Session, passage: str) -> list[GlossaryEntry]:
        """Return glossary entries whose term or alias appears in source passage."""
        normalized_passage = f" {self.normalize_text(passage)} "
        if not normalized_passage.strip():
            return []

        matches: list[GlossaryEntry] = []
        for entry in db.scalars(select(GlossaryEntry).order_by(GlossaryEntry.source_term_en.asc())):
            candidates = [entry.source_term_en, *self.split_aliases(entry.aliases_en)]
            if any(
                self._contains_normalized_phrase(normalized_passage, candidate)
                for candidate in candidates
            ):
                matches.append(entry)
        return matches

    def import_csv_file(self, db: Session, path: Path) -> ImportSummary:
        """Import glossary entries from a CSV file path using common CSV encodings."""
        last_error: UnicodeDecodeError | None = None
        for encoding in CSV_ENCODINGS:
            try:
                with path.open("r", encoding=encoding, newline="") as file_obj:
                    return self.import_csv(db, file_obj)
            except UnicodeDecodeError as exc:
                db.rollback()
                last_error = exc

        message = (
            f"Could not decode {path.name} with supported encodings: {', '.join(CSV_ENCODINGS)}"
        )
        if last_error is not None:
            message = f"{message}. Last error: {last_error}"
        raise ValueError(message)

    def import_csv(self, db: Session, file_obj: TextIO) -> ImportSummary:
        """Import glossary entries from a CSV file object."""
        reader = csv.DictReader(file_obj)
        if reader.fieldnames is None:
            return ImportSummary(skipped=1, errors=("CSV file has no header row.",))

        inserted = 0
        updated = 0
        skipped = 0
        errors: list[str] = []
        existing_by_term = {
            self.normalize_text(entry.source_term_en): entry
            for entry in db.scalars(select(GlossaryEntry))
        }

        for row_number, row in enumerate(reader, start=2):
            try:
                data = self.row_to_entry_data(row)
            except ValueError as exc:
                skipped += 1
                errors.append(f"Row {row_number}: {exc}")
                continue

            key = self.normalize_text(data.source_term_en)
            existing = existing_by_term.get(key)
            if existing is None:
                entry = GlossaryEntry(**self._entry_kwargs(data))
                db.add(entry)
                db.flush()
                existing_by_term[key] = entry
                inserted += 1
            else:
                self._apply_entry_data(existing, data)
                updated += 1

        db.commit()
        return ImportSummary(
            inserted=inserted, updated=updated, skipped=skipped, errors=tuple(errors)
        )

    def row_to_entry_data(self, row: dict[str, str | None]) -> GlossaryEntryData:
        """Map a CSV row to glossary entry data using tolerant column names."""
        source_term = self._get_row_value(
            row,
            "source_term_en",
            "source_term",
            "term_en",
            "english_name",
            "english",
            "en",
        )
        approved_term = self._get_row_value(
            row,
            "approved_term_zh",
            "target_term_zh",
            "term_zh",
            "cn_translation",
            "translation",
            "chinese",
            "zh",
        )
        if not source_term:
            raise ValueError("source_term_en is required")
        if not approved_term:
            raise ValueError("approved_term_zh is required")

        return GlossaryEntryData(
            source_term_en=source_term,
            approved_term_zh=approved_term,
            aliases_en=self._get_row_value(row, "aliases_en", "aliases", "alias_en", "alias"),
            entity_type=self._get_row_value(row, "entity_type", "type", "category", "tags"),
            notes=self._get_row_value(
                row,
                "notes",
                "note",
                "comment",
                "comments",
                "comments_brief_explanation",
            ),
            status=self.parse_status(self._get_row_value(row, "status")),
        )

    def parse_status(self, status: str | None) -> GlossaryStatus:
        """Parse a glossary status string with a draft fallback."""
        normalized = (status or GlossaryStatus.draft.value).strip().lower()
        try:
            return GlossaryStatus(normalized)
        except ValueError:
            return GlossaryStatus.draft

    def split_aliases(self, aliases: str | None) -> list[str]:
        """Split the stored alias text into individual alias strings."""
        if not aliases:
            return []
        return [item.strip() for item in _ALIAS_SPLIT_RE.split(aliases) if item.strip()]

    def normalize_text(self, value: str) -> str:
        """Normalize English matching text for simple lookup."""
        return _NON_WORD_RE.sub(" ", value.lower()).strip()

    def _contains_normalized_phrase(self, normalized_passage: str, phrase: str) -> bool:
        normalized_phrase = self.normalize_text(phrase)
        return bool(normalized_phrase) and f" {normalized_phrase} " in normalized_passage

    def _entry_matches_query(self, entry: GlossaryEntry, normalized_query: str) -> bool:
        fields = [
            entry.source_term_en,
            entry.approved_term_zh,
            entry.aliases_en or "",
            entry.entity_type or "",
            entry.notes or "",
            entry.status.value if isinstance(entry.status, GlossaryStatus) else str(entry.status),
        ]
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

    def _entry_kwargs(self, data: GlossaryEntryData) -> dict[str, object]:
        return {
            "source_term_en": data.source_term_en,
            "approved_term_zh": data.approved_term_zh,
            "aliases_en": data.aliases_en,
            "entity_type": data.entity_type,
            "notes": data.notes,
            "status": data.status,
        }

    def _apply_entry_data(self, entry: GlossaryEntry, data: GlossaryEntryData) -> None:
        entry.source_term_en = data.source_term_en
        entry.approved_term_zh = data.approved_term_zh
        entry.aliases_en = data.aliases_en
        entry.entity_type = data.entity_type
        entry.notes = data.notes
        entry.status = data.status
