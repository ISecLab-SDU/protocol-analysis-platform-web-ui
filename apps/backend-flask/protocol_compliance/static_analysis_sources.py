"""Source discovery helpers for static-analysis database routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


HistoryLister = Callable[..., List[Dict[str, Any]]]
SqliteResolver = Callable[[Optional[str], Optional[str]], tuple[Optional[Path], List[str]]]
WritableCopyIterator = Callable[[], List[Dict[str, Any]]]
PathHasher = Callable[[Path], str]


def iter_static_analysis_database_sources(
    *,
    db_dir: Path,
    find_sqlite_file: SqliteResolver,
    job_limit: int,
    list_static_analysis_history: HistoryLister,
    sqlite_path_hash: PathHasher,
    iter_writable_database_copies: WritableCopyIterator,
    include_builtin: bool = True,
) -> tuple[List[Dict[str, Any]], List[str]]:
    sources: List[Dict[str, Any]] = []
    warnings: List[str] = []
    seen_database_paths: set[str] = set()
    shadowed_database_hashes: set[str] = set()

    for source in iter_writable_database_copies():
        db_path = source["path"]
        if not isinstance(db_path, Path):
            continue
        resolved = str(db_path.resolve())
        seen_database_paths.add(resolved)
        original_hash = source.get("originalPathHash")
        if isinstance(original_hash, str):
            shadowed_database_hashes.add(original_hash)
        sources.append(source)

    if include_builtin:
        if db_dir.is_dir():
            for db_path in sorted(db_dir.glob("sqlite_*.db")):
                resolved = str(db_path.resolve())
                if sqlite_path_hash(db_path) in shadowed_database_hashes:
                    continue
                seen_database_paths.add(resolved)
                sources.append(
                    {
                        "path": db_path,
                        "sourceType": "builtin",
                        "jobId": None,
                        "protocolName": None,
                        "createdAt": None,
                        "updatedAt": None,
                    }
                )
        else:
            warnings.append(f"数据库目录不存在：{db_dir}")

    for entry in list_static_analysis_history(limit=job_limit):
        if entry.get("status") != "completed":
            continue
        database_path_raw = entry.get("databasePath")
        workspace_path_raw = entry.get("workspacePath")
        resolved_path, resolve_warnings = find_sqlite_file(
            str(database_path_raw) if database_path_raw else None,
            str(workspace_path_raw) if workspace_path_raw else None,
        )
        warnings.extend(resolve_warnings)
        if not resolved_path:
            continue
        resolved = str(resolved_path.resolve())
        if (
            resolved in seen_database_paths
            or sqlite_path_hash(resolved_path) in shadowed_database_hashes
        ):
            continue
        seen_database_paths.add(resolved)
        sources.append(
            {
                "path": resolved_path,
                "sourceType": "job",
                "jobId": entry.get("jobId"),
                "protocolName": entry.get("protocolName"),
                "createdAt": entry.get("createdAt"),
                "updatedAt": entry.get("updatedAt"),
            }
        )

    return sources, warnings
