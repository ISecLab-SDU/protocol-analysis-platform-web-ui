"""SQLite-backed history store for instrumentation diff artefacts."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional

LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state_directory() -> Path:
    raw_dir = os.environ.get("PROTOCOLGUARD_STATE_DIR")
    if raw_dir:
        try:
            return Path(raw_dir).expanduser().resolve()
        except (OSError, RuntimeError):
            LOGGER.warning("Invalid PROTOCOLGUARD_STATE_DIR %s; using package _state directory", raw_dir)
    return Path(__file__).resolve().parent / "_state"


def _default_db_path() -> Path:
    raw_name = os.environ.get("ASSERT_HISTORY_DB_NAME", "assertion_history.sqlite3")
    return (_default_state_directory() / raw_name).resolve()


def _default_storage_dir() -> Path:
    raw_dir = os.environ.get("ASSERT_HISTORY_STORAGE_DIR")
    if raw_dir:
        try:
            return Path(raw_dir).expanduser().resolve()
        except (OSError, RuntimeError):
            LOGGER.warning("Invalid ASSERT_HISTORY_STORAGE_DIR %s; falling back to default location", raw_dir)
    return (_default_state_directory() / "assertion_history").resolve()


@dataclass
class AssertionHistoryEntry:
    job_id: str
    code_filename: Optional[str]
    database_filename: Optional[str]
    diff_path: Optional[str]
    diff_filename: Optional[str]
    created_at: str
    updated_at: str
    source: str

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "jobId": self.job_id,
            "codeFilename": self.code_filename,
            "databaseFilename": self.database_filename,
            "diffPath": self.diff_path,
            "diffFilename": self.diff_filename,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "source": self.source,
        }


class AssertionHistoryRepository:
    """Persist instrumentation diff metadata for later retrieval."""

    def __init__(
        self,
        *,
        db_path: Optional[Path] = None,
        storage_dir: Optional[Path] = None,
    ) -> None:
        self._db_path = (db_path or _default_db_path()).resolve()
        self._storage_dir = (storage_dir or _default_storage_dir()).resolve()
        self._lock = threading.Lock()
        self._initialized = False

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    def record_job(
        self,
        *,
        job_id: str,
        diff_source_path: Path,
        code_filename: Optional[str],
        database_filename: Optional[str],
        created_at: Optional[str] = None,
        source: str = "auto",
        copy_diff: bool = True,
    ) -> Optional[Path]:
        """Copy the diff file into storage and persist metadata."""

        if not job_id:
            raise ValueError("job_id is required")
        if not diff_source_path:
            raise ValueError("diff_source_path is required")

        if not diff_source_path.exists():
            LOGGER.warning("Diff file %s missing while recording job %s", diff_source_path, job_id)
            diff_storage_path: Optional[Path] = None
        else:
            diff_storage_path = (
                self._persist_diff_file(job_id, diff_source_path) if copy_diff else diff_source_path.resolve()
            )

        timestamp = created_at or _now_iso()
        self._upsert_entry(
            job_id=job_id,
            code_filename=code_filename,
            database_filename=database_filename,
            diff_path=str(diff_storage_path) if diff_storage_path else None,
            diff_filename=diff_source_path.name,
            created_at=timestamp,
            updated_at=timestamp,
            source=source or "auto",
        )
        return diff_storage_path

    def insert_manual_entry(
        self,
        *,
        job_id: str,
        diff_file: Path,
        code_filename: Optional[str],
        database_filename: Optional[str],
        created_at: Optional[str] = None,
        copy_diff: bool = True,
    ) -> Optional[Path]:
        """Helper for manual seeding via Python scripts."""

        return self.record_job(
            job_id=job_id,
            diff_source_path=diff_file,
            code_filename=code_filename,
            database_filename=database_filename,
            created_at=created_at,
            source="manual",
            copy_diff=copy_diff,
        )

    def list_history(self, *, limit: int = 50) -> List[Dict[str, Optional[str]]]:
        """Return the newest history entries."""

        limit = max(1, min(limit, 500))
        self._ensure_initialized()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_id, code_filename, database_filename, diff_path, diff_filename, created_at, updated_at, source
                FROM assertion_history
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_entry(row).as_dict() for row in rows]

    def get_entry(self, job_id: str) -> Optional[Dict[str, Optional[str]]]:
        if not job_id:
            return None
        self._ensure_initialized()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT job_id, code_filename, database_filename, diff_path, diff_filename, created_at, updated_at, source
                FROM assertion_history
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_entry(row).as_dict()

    def resolve_diff_path(self, job_id: str) -> Optional[Path]:
        entry = self.get_entry(job_id)
        if not entry:
            return None
        raw_path = entry.get("diffPath")
        if not raw_path:
            return None
        path = Path(raw_path)
        return path if path.exists() else None

    # Internal helpers -----------------------------------------------------

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assertion_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL UNIQUE,
                        code_filename TEXT,
                        database_filename TEXT,
                        diff_path TEXT,
                        diff_filename TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        source TEXT NOT NULL DEFAULT 'auto'
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_assertion_history_job ON assertion_history(job_id)")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_assertion_history_created ON assertion_history(created_at DESC)"
                )
            self._initialized = True

    def _upsert_entry(
        self,
        *,
        job_id: str,
        code_filename: Optional[str],
        database_filename: Optional[str],
        diff_path: Optional[str],
        diff_filename: Optional[str],
        created_at: str,
        updated_at: str,
        source: str,
    ) -> None:
        self._ensure_initialized()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assertion_history (
                    job_id,
                    code_filename,
                    database_filename,
                    diff_path,
                    diff_filename,
                    created_at,
                    updated_at,
                    source
                )
                VALUES (:job_id, :code_filename, :database_filename, :diff_path, :diff_filename, :created_at, :updated_at, :source)
                ON CONFLICT(job_id) DO UPDATE SET
                    code_filename = excluded.code_filename,
                    database_filename = excluded.database_filename,
                    diff_path = excluded.diff_path,
                    diff_filename = excluded.diff_filename,
                    updated_at = excluded.updated_at,
                    source = excluded.source
                """,
                {
                    "job_id": job_id,
                    "code_filename": code_filename,
                    "database_filename": database_filename,
                    "diff_path": diff_path,
                    "diff_filename": diff_filename,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "source": source,
                },
            )
            conn.commit()

    def _persist_diff_file(self, job_id: str, source_path: Path) -> Path:
        self._ensure_initialized()
        target_dir = self._storage_dir / job_id
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / source_path.name
        try:
            shutil.copy2(source_path, destination)
        except OSError as exc:
            LOGGER.error("Failed to copy diff file %s -> %s: %s", source_path, destination, exc)
            raise
        return destination.resolve()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._ensure_initialized()
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> AssertionHistoryEntry:
        return AssertionHistoryEntry(
            job_id=row["job_id"],
            code_filename=row["code_filename"],
            database_filename=row["database_filename"],
            diff_path=row["diff_path"],
            diff_filename=row["diff_filename"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            source=row["source"],
        )


ASSERTION_HISTORY_REPOSITORY = AssertionHistoryRepository()

