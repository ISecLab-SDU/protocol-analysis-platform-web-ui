"""CLI helper to manually seed assertion history records.

Usage examples:
    python -m protocol_compliance.assertion_history_util \
        --diff-file ./instrumentation.diff \
        --job-id manual-001 \
        --code-filename sample.tar.gz \
        --database-filename sqlite_sample.db
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path
from typing import Optional

# Support running as a module or as a standalone script.
try:  # noqa: SIM105 - explicit guard for script execution
    from .assertion_history_repository import AssertionHistoryRepository, ASSERTION_HISTORY_REPOSITORY
except Exception:  # pragma: no cover - fallback for direct execution
    import sys
    from pathlib import Path

    CURRENT_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = CURRENT_DIR.parent
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))
    from protocol_compliance.assertion_history_repository import (  # type: ignore
        AssertionHistoryRepository,
        ASSERTION_HISTORY_REPOSITORY,
    )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("limit must be >= 1")
    return parsed


def _resolve_repo(db_path: Optional[str], storage_dir: Optional[str]) -> AssertionHistoryRepository:
    if not db_path and not storage_dir:
        return ASSERTION_HISTORY_REPOSITORY
    db = Path(db_path).expanduser() if db_path else None
    storage = Path(storage_dir).expanduser() if storage_dir else None
    return AssertionHistoryRepository(db_path=db, storage_dir=storage)


def seed_history(
    *,
    diff_file: Path,
    job_id: str,
    code_filename: Optional[str],
    database_filename: Optional[str],
    created_at: Optional[str],
    copy_diff: bool,
    db_path: Optional[str],
    storage_dir: Optional[str],
) -> Path:
    repo = _resolve_repo(db_path, storage_dir)
    return repo.insert_manual_entry(
        job_id=job_id,
        diff_file=diff_file,
        code_filename=code_filename,
        database_filename=database_filename,
        created_at=created_at,
        copy_diff=copy_diff,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Seed assertion history with a manual record")
    parser.add_argument(
        "--diff-file",
        required=True,
        help="Path to the instrumentation diff file to record",
    )
    parser.add_argument(
        "--job-id",
        default=None,
        help="Job ID to record (default: random UUID)",
    )
    parser.add_argument(
        "--code-filename",
        default=None,
        help="Original code archive filename to store alongside the record",
    )
    parser.add_argument(
        "--database-filename",
        default=None,
        help="Original SQLite filename to store alongside the record",
    )
    parser.add_argument(
        "--created-at",
        default=None,
        help="ISO8601 timestamp for record creation (default: now, UTC)",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Do not copy diff into history storage; reference the source file directly",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Override database path (default: ASSERT_HISTORY_DB_NAME within PROTOCOLGUARD_STATE_DIR)",
    )
    parser.add_argument(
        "--storage-dir",
        default=None,
        help="Override diff storage directory (default: assertion_history under PROTOCOLGUARD_STATE_DIR)",
    )

    parsed = parser.parse_args(argv)

    diff_file = Path(parsed.diff_file).expanduser().resolve()
    if not diff_file.exists():
        parser.error(f"Diff file does not exist: {diff_file}")

    job_id = parsed.job_id or str(uuid.uuid4())
    try:
        destination = seed_history(
            diff_file=diff_file,
            job_id=job_id,
            code_filename=parsed.code_filename,
            database_filename=parsed.database_filename,
            created_at=parsed.created_at,
            copy_diff=not parsed.no_copy,
            db_path=parsed.db_path,
            storage_dir=parsed.storage_dir,
        )
    except Exception as exc:  # pragma: no cover - CLI helper
        parser.error(str(exc))
        return 1

    print(f"Recorded job {job_id}")
    if destination:
        print(f"Diff stored at: {destination}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
