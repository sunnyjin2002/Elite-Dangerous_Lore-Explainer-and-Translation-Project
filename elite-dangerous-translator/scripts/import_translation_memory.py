"""Import translation memory CSV files into the local database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal, create_database_tables  # noqa: E402
from app.services.translation_memory_service import TranslationMemoryService  # noqa: E402

DEFAULT_MEMORY_DIR = PROJECT_ROOT / "data" / "references" / "translation_memory"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Import translation memory CSV data.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        help=(
            "CSV path or file name under data/references/translation_memory/. "
            "Defaults to all CSV files there."
        ),
    )
    return parser.parse_args()


def resolve_paths(csv_path: str | None) -> list[Path]:
    """Resolve one explicit CSV path or all CSV files in the reference directory."""
    if csv_path:
        candidate = Path(csv_path)
        if not candidate.is_absolute():
            direct = PROJECT_ROOT / candidate
            candidate = direct if direct.exists() else DEFAULT_MEMORY_DIR / candidate.name
        if candidate.suffix.lower() != ".csv":
            raise ValueError("Only CSV translation memory imports are supported right now.")
        if not candidate.exists():
            raise FileNotFoundError(f"Translation memory CSV not found: {candidate}")
        return [candidate]

    paths = sorted(DEFAULT_MEMORY_DIR.glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"No CSV files found in {DEFAULT_MEMORY_DIR}")
    return paths


def main() -> None:
    """Run translation memory CSV import."""
    args = parse_args()
    paths = resolve_paths(args.csv_path)
    service = TranslationMemoryService()
    create_database_tables()

    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    with SessionLocal() as db:
        for path in paths:
            summary = service.import_csv_file(db, path)
            total_inserted += summary.inserted
            total_updated += summary.updated
            total_skipped += summary.skipped
            print(
                f"{path.name}: {summary.inserted} inserted, "
                f"{summary.updated} updated, {summary.skipped} skipped"
            )
            for error in summary.errors[:10]:
                print(f"  - {error}")
            if len(summary.errors) > 10:
                print(f"  - ... {len(summary.errors) - 10} more errors")

    print(f"Done: {total_inserted} inserted, " f"{total_updated} updated, {total_skipped} skipped")


if __name__ == "__main__":
    main()
