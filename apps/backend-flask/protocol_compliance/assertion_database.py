"""Assertion database path resolution helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Callable, Optional


def _candidate_sqlite_roots_for_job(
    job_id: str,
    *,
    expand_path: Callable[[Optional[str]], Optional[Path]],
    get_static_analysis_job: Callable[[str], Optional[dict[str, Any]]],
) -> list[Path]:
    runtime_root = Path(os.environ.get("PG_RUNTIME_ROOT", "/tmp/protocolguard")).expanduser()
    output_root = Path(os.environ.get("PG_OUTPUT_ROOT", runtime_root / "outputs")).expanduser()
    workspace_root = Path(os.environ.get("PG_WORKSPACE_ROOT", runtime_root / "workspaces")).expanduser()

    roots = [
        output_root / job_id / "database",
        output_root / job_id,
        workspace_root / job_id / "database",
        workspace_root / job_id,
    ]

    snapshot = get_static_analysis_job(job_id)
    if snapshot:
        for key in ("database_path", "databasePath"):
            raw_database_path = snapshot.get(key)
            database_path = expand_path(str(raw_database_path)) if raw_database_path else None
            if database_path:
                roots.append(database_path.parent if database_path.suffix else database_path)
        for key in ("output_path", "outputPath"):
            raw_output_path = snapshot.get(key)
            output_path = expand_path(str(raw_output_path)) if raw_output_path else None
            if output_path:
                roots.extend([output_path / "database", output_path])
        for key in ("workspace_path", "workspacePath"):
            raw_workspace_path = snapshot.get(key)
            workspace_path = expand_path(str(raw_workspace_path)) if raw_workspace_path else None
            if workspace_path:
                roots.extend([workspace_path / "database", workspace_path])

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        marker = str(root.resolve(strict=False))
        if marker in seen:
            continue
        seen.add(marker)
        unique_roots.append(root)
    return unique_roots


def _resolve_assertion_database_path(
    database_path: Path,
    *,
    candidate_sqlite_roots_for_job: Callable[[str], list[Path]],
) -> tuple[Optional[Path], list[str]]:
    warnings: list[str] = []
    if database_path.is_file():
        return database_path, warnings

    warnings.append(f"指定的分析结果数据不存在：{database_path}")
    job_id = next(
        (
            part
            for part in database_path.parts
            if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", part)
        ),
        None,
    )
    if not job_id:
        return None, warnings

    expected_name = database_path.name
    for root in candidate_sqlite_roots_for_job(job_id):
        if not root.exists() or not root.is_dir():
            continue
        named_candidate = root / expected_name
        if named_candidate.is_file():
            return named_candidate, warnings
        matches = sorted(root.glob("*.db"))
        if matches:
            return matches[0], warnings

    return None, warnings
