"""SQLite-backed persistence for ProtocolGuard static analysis jobs."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence

LOGGER = logging.getLogger(__name__)


def _default_state_directory() -> Path:
    raw_dir = os.environ.get("PROTOCOLGUARD_STATE_DIR")
    if raw_dir:
        try:
            base_dir = Path(raw_dir).expanduser().resolve()
        except (OSError, RuntimeError):
            LOGGER.warning("Invalid PROTOCOLGUARD_STATE_DIR %s; falling back to package directory", raw_dir)
            base_dir = Path(__file__).resolve().parent / "_state"
    else:
        base_dir = Path(__file__).resolve().parent / "_state"
    return base_dir


def _default_db_path() -> Path:
    raw_name = os.environ.get("PROTOCOLGUARD_STATE_DB_NAME", "analysis_state.sqlite3")
    base_dir = _default_state_directory()
    return (base_dir / raw_name).resolve()


def _normalize_path(value: Optional[Any]) -> Optional[str]:
    if isinstance(value, (str, Path)):
        try:
            return str(Path(value).expanduser().resolve())
        except (OSError, RuntimeError):
            return str(value)
    return None


def _dump_json(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        LOGGER.warning("Failed to serialize JSON payload for persistence: %s", exc)
        return None


def _load_json(value: Optional[str]) -> Optional[Any]:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError) as exc:
        LOGGER.warning("Failed to deserialize JSON payload from persistence: %s", exc)
        return None


class AnalysisStateRepository:
    """Persist static analysis job metadata and artefact locations."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path).resolve() if db_path else _default_db_path()
        self._lock = threading.Lock()
        self._initialized = False

    @property
    def db_path(self) -> Path:
        return self._db_path

    def record_progress(
        self,
        *,
        job_id: str,
        status: str,
        stage: str,
        message: str,
        updated_at: str,
        created_at: Optional[str] = None,
    ) -> None:
        payload = {
            "job_id": job_id,
            "status": status,
            "stage": stage,
            "message": message,
            "workspace_path": None,
            "output_path": None,
            "config_path": None,
            "logs_path": None,
            "database_path": None,
            "result_json": None,
            "error_text": None,
            "details_json": None,
            "docker_logs_json": None,
            "workspace_snapshots_json": None,
            "created_at": created_at or updated_at,
            "updated_at": updated_at,
            "completed_at": None,
        }
        self._upsert(payload)

    def record_completion(
        self,
        *,
        job_id: str,
        status: str,
        stage: str,
        message: str,
        updated_at: str,
        result: Mapping[str, Any],
    ) -> None:
        artifacts = result.get("artifacts") if isinstance(result, Mapping) else None
        workspace_path = None
        output_path = None
        config_path = None
        logs_path = None
        database_path = None
        workspace_snapshots: Optional[Sequence[Mapping[str, Any]]] = None

        if isinstance(artifacts, Mapping):
            workspace_path = _normalize_path(artifacts.get("workspace"))
            output_path = _normalize_path(artifacts.get("output"))
            config_path = _normalize_path(artifacts.get("config"))
            logs_path = _normalize_path(artifacts.get("logs"))
            database_path = _normalize_path(artifacts.get("database"))
            snapshots = artifacts.get("workspaceSnapshots")
            if isinstance(snapshots, Sequence):
                workspace_snapshots = [entry for entry in snapshots if isinstance(entry, Mapping)]  # type: ignore[arg-type]

        payload = {
            "job_id": job_id,
            "status": status,
            "stage": stage,
            "message": message,
            "workspace_path": workspace_path,
            "output_path": output_path,
            "config_path": config_path,
            "logs_path": logs_path,
            "database_path": database_path,
            "result_json": _dump_json(result),
            "error_text": None,
            "details_json": None,
            "docker_logs_json": None,
            "workspace_snapshots_json": _dump_json(workspace_snapshots),
            "created_at": updated_at,
            "updated_at": updated_at,
            "completed_at": updated_at,
        }
        self._upsert(payload)

    def record_failure(
        self,
        *,
        job_id: str,
        status: str,
        stage: str,
        message: str,
        updated_at: str,
        error: Optional[str],
        details: Optional[Mapping[str, Any]],
    ) -> None:
        payload = {
            "job_id": job_id,
            "status": status,
            "stage": stage,
            "message": message,
            "workspace_path": None,
            "output_path": None,
            "config_path": None,
            "logs_path": None,
            "database_path": None,
            "result_json": None,
            "error_text": error or message,
            "details_json": _dump_json(details),
            "docker_logs_json": None,
            "workspace_snapshots_json": None,
            "created_at": updated_at,
            "updated_at": updated_at,
            "completed_at": None,
        }
        self._upsert(payload)

    def add_event(self, *, job_id: str, timestamp: str, stage: str, message: str) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO analysis_job_events (job_id, timestamp, stage, message)
                    VALUES (:job_id, :timestamp, :stage, :message)
                    """,
                    {
                        "job_id": job_id,
                        "timestamp": timestamp,
                        "stage": stage,
                        "message": message,
                    },
                )
        except sqlite3.DatabaseError as exc:
            LOGGER.warning("Failed to persist analysis job event for %s: %s", job_id, exc)

    def fetch_jobs(self, *, limit: int = 50) -> List[dict[str, Any]]:
        self._ensure_initialized()
        query = (
            """
            SELECT
                job_id,
                status,
                stage,
                message,
                workspace_path,
                output_path,
                config_path,
                logs_path,
                database_path,
                result_json,
                error_text,
                details_json,
                docker_logs_json,
                workspace_snapshots_json,
                created_at,
                updated_at,
                completed_at
            FROM analysis_jobs
            ORDER BY COALESCE(completed_at, updated_at, created_at) DESC
            """
        )
        params: tuple[Any, ...]
        if limit and limit > 0:
            query += " LIMIT ?"
            params = (int(limit),)
        else:
            params = tuple()

        connection: Optional[sqlite3.Connection] = None
        try:
            connection = sqlite3.connect(self._db_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON;")
            rows = connection.execute(query, params).fetchall()
        except sqlite3.DatabaseError as exc:
            LOGGER.warning("Failed to read analysis job history: %s", exc)
            return []
        finally:
            if connection is not None:
                with suppress(Exception):
                    connection.close()

        history: List[dict[str, Any]] = []
        for row in rows:
            history.append(
                {
                    "job_id": row["job_id"],
                    "status": row["status"],
                    "stage": row["stage"],
                    "message": row["message"],
                    "workspace_path": row["workspace_path"],
                    "output_path": row["output_path"],
                    "config_path": row["config_path"],
                    "logs_path": row["logs_path"],
                    "database_path": row["database_path"],
                    "result": _load_json(row["result_json"]),
                    "error": row["error_text"],
                    "details": _load_json(row["details_json"]),
                    "docker_logs": _load_json(row["docker_logs_json"]),
                    "workspace_snapshots": _load_json(row["workspace_snapshots_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "completed_at": row["completed_at"],
                }
            )
        return history

    def _ensure_initialized(self) -> None:
        if self._initialized and self._db_path.exists():
            return
        with self._lock:
            if self._initialized and self._db_path.exists():
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS analysis_jobs (
                            job_id TEXT PRIMARY KEY,
                            status TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            message TEXT NOT NULL,
                            workspace_path TEXT,
                            output_path TEXT,
                            config_path TEXT,
                            logs_path TEXT,
                            database_path TEXT,
                            result_json TEXT,
                            error_text TEXT,
                            details_json TEXT,
                            docker_logs_json TEXT,
                            workspace_snapshots_json TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            completed_at TEXT
                        );

                        CREATE TABLE IF NOT EXISTS analysis_job_events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            job_id TEXT NOT NULL,
                            timestamp TEXT NOT NULL,
                            stage TEXT NOT NULL,
                            message TEXT NOT NULL,
                            FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id) ON DELETE CASCADE
                        );
                        """
                    )
                    conn.commit()
            except sqlite3.DatabaseError as exc:
                LOGGER.error("Unable to initialize analysis state database at %s: %s", self._db_path, exc)
            self._initialized = True

    @contextmanager
    def _connect(self):
        self._ensure_initialized()
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
            conn.commit()
        except sqlite3.DatabaseError:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _upsert(self, payload: Mapping[str, Optional[Any]]) -> None:
        self._ensure_initialized()
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO analysis_jobs (
                        job_id,
                        status,
                        stage,
                        message,
                        workspace_path,
                        output_path,
                        config_path,
                        logs_path,
                        database_path,
                        result_json,
                        error_text,
                        details_json,
                        docker_logs_json,
                        workspace_snapshots_json,
                        created_at,
                        updated_at,
                        completed_at
                    ) VALUES (
                        :job_id,
                        :status,
                        :stage,
                        :message,
                        :workspace_path,
                        :output_path,
                        :config_path,
                        :logs_path,
                        :database_path,
                        :result_json,
                        :error_text,
                        :details_json,
                        :docker_logs_json,
                        :workspace_snapshots_json,
                        :created_at,
                        :updated_at,
                        :completed_at
                    )
                    ON CONFLICT(job_id) DO UPDATE SET
                        status = excluded.status,
                        stage = excluded.stage,
                        message = excluded.message,
                        workspace_path = COALESCE(excluded.workspace_path, analysis_jobs.workspace_path),
                        output_path = COALESCE(excluded.output_path, analysis_jobs.output_path),
                        config_path = COALESCE(excluded.config_path, analysis_jobs.config_path),
                        logs_path = COALESCE(excluded.logs_path, analysis_jobs.logs_path),
                        database_path = COALESCE(excluded.database_path, analysis_jobs.database_path),
                        result_json = COALESCE(excluded.result_json, analysis_jobs.result_json),
                        error_text = COALESCE(excluded.error_text, analysis_jobs.error_text),
                        details_json = COALESCE(excluded.details_json, analysis_jobs.details_json),
                        docker_logs_json = COALESCE(excluded.docker_logs_json, analysis_jobs.docker_logs_json),
                        workspace_snapshots_json = COALESCE(excluded.workspace_snapshots_json, analysis_jobs.workspace_snapshots_json),
                        updated_at = excluded.updated_at,
                        completed_at = COALESCE(excluded.completed_at, analysis_jobs.completed_at)
                    """,
                    payload,
                )
        except sqlite3.DatabaseError as exc:
            LOGGER.warning("Failed to persist analysis job state for %s: %s", payload.get("job_id"), exc)


def _create_repository() -> AnalysisStateRepository:
    return AnalysisStateRepository()


analysis_state_repository = _create_repository()
