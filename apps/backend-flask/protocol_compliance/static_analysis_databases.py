"""Static-analysis database path and writable-copy helpers."""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .violation_history_state import (
    _violation_history_writable_database_path,
    _violation_history_writable_database_root,
)


def _expand_path(raw: Optional[str]) -> Optional[Path]:
    if not raw or not isinstance(raw, str):
        return None
    try:
        return Path(raw).expanduser()
    except (OSError, ValueError):
        return None


def _find_sqlite_file(
    database_path: Optional[str],
    workspace_path: Optional[str],
    *,
    collect_warnings: bool = True,
) -> tuple[Optional[Path], list[str]]:
    """Resolve the SQLite database path, collecting warnings."""
    warnings: list[str] = []

    candidate = _expand_path(database_path)
    if candidate and candidate.is_file():
        return candidate, warnings
    if collect_warnings and candidate and not candidate.exists():
        warnings.append(f"指定的数据库路径不存在：{candidate}")

    workspace = _expand_path(workspace_path)
    if workspace:
        if workspace.is_dir():
            matches = sorted(workspace.glob("sqlite_*.db"))
            if matches:
                return matches[0], warnings
            if collect_warnings:
                warnings.append(
                    f"在工作目录 {workspace} 中未找到 sqlite_*.db 文件"
                )
        else:
            if collect_warnings:
                warnings.append(f"工作目录不存在或不可访问：{workspace}")

    return None, warnings


def _is_sqlite_database_writable(db_path: Path) -> bool:
    if not db_path.is_file():
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "CREATE TABLE __protocolguard_write_probe__ "
                "(id INTEGER PRIMARY KEY)"
            )
            conn.execute("DROP TABLE __protocolguard_write_probe__")
            conn.rollback()
        return True
    except sqlite3.Error:
        return False


def _copy_sqlite_database_for_violation_history(
    source_path: Path,
    *,
    job_id: Optional[str],
) -> Path:
    destination = _violation_history_writable_database_path(source_path, job_id=job_id)
    if destination.is_file() and _is_sqlite_database_writable(destination):
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)
    os.chmod(destination, 0o600)
    return destination


def _ensure_writable_violation_history_database(
    db_path: Path,
    *,
    job_id: Optional[str],
    warnings: List[str],
) -> Path:
    if _is_sqlite_database_writable(db_path):
        return db_path

    writable_copy = _copy_sqlite_database_for_violation_history(db_path, job_id=job_id)
    warnings.append(
        f"数据库 {db_path} 不可写，已使用后端状态目录中的可写副本：{writable_copy}"
    )
    return writable_copy


def _iter_violation_history_writable_database_copies() -> List[Dict[str, Any]]:
    copy_root = _violation_history_writable_database_root()
    if not copy_root.is_dir():
        return []

    sources: List[Dict[str, Any]] = []
    for db_path in sorted(copy_root.glob("*/*.db")):
        name = db_path.name
        if "-" not in name:
            continue
        original_hash, _ = name.split("-", 1)
        if not re.fullmatch(r"[0-9a-f]{12}", original_hash):
            continue
        job_id = db_path.parent.name if db_path.parent.name != "manual" else None
        sources.append(
            {
                "path": db_path,
                "sourceType": "job" if job_id else "builtin",
                "jobId": job_id,
                "protocolName": None,
                "createdAt": None,
                "updatedAt": None,
                "originalPathHash": original_hash,
            }
        )
    return sources
