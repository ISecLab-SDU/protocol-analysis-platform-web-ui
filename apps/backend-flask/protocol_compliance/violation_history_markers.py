"""Timestamp and delete-marker helpers for violation history."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, cast

from .violation_history_state import (
    _load_violation_history_timestamps,
    _save_violation_history_timestamps,
)


def _history_database_path_marker(value: Any) -> str:
    if not value:
        return ""
    try:
        return str(Path(str(value)).expanduser().resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return str(value)


def _history_database_name_marker(
    value: Any,
    *,
    dedupe_key: Callable[[Any], str],
) -> str:
    name = Path(str(value or "")).name
    if re.fullmatch(r"[0-9a-f]{12}-.+", name):
        name = name.split("-", 1)[1]
    return dedupe_key(name)


def _database_history_time_marker(db_path: Path) -> str:
    return _history_database_path_marker(db_path)


def _row_history_time_marker(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    dedupe_key: Callable[[Any], str],
    rule_desc: Any,
) -> str:
    stable_key = "|".join(
        [
            _database_history_time_marker(db_path),
            dedupe_key(rule_desc),
            hashlib.sha1(str(code_snippet or "").encode("utf-8")).hexdigest(),
            hashlib.sha1(str(call_graph or "").encode("utf-8")).hexdigest(),
        ]
    )
    return hashlib.sha1(stable_key.encode("utf-8")).hexdigest()


def _candidate_database_history_times(
    db_path: Path,
    *,
    package_dir: Path,
) -> List[str]:
    candidates: List[str] = []
    for candidate in [
        db_path,
        package_dir / "databases" / db_path.name,
        Path.cwd() / "database" / db_path.name,
    ]:
        try:
            if candidate.is_file():
                candidates.append(
                    datetime.fromtimestamp(
                        candidate.stat().st_mtime,
                        timezone.utc,
                    ).isoformat()
                )
        except OSError:
            continue
    return candidates


def _database_history_display_time(
    db_path: Path,
    *,
    package_dir: Path,
    persist_if_missing: bool = True,
) -> str:
    marker = _database_history_time_marker(db_path)
    timestamps = _load_violation_history_timestamps()
    databases = cast(Dict[str, Any], timestamps["databases"])
    stored = databases.get(marker)
    if isinstance(stored, str) and stored.strip():
        return stored

    candidate_times = _candidate_database_history_times(
        db_path,
        package_dir=package_dir,
    )
    display_time = (
        min(candidate_times)
        if candidate_times
        else datetime.now(timezone.utc).isoformat()
    )
    if persist_if_missing:
        databases[marker] = display_time
        _save_violation_history_timestamps(timestamps)
    return display_time


def _row_history_display_time(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    dedupe_key: Callable[[Any], str],
    fallback: str,
    persist_if_missing: bool = True,
    rule_desc: Any,
) -> str:
    marker = _row_history_time_marker(
        db_path,
        call_graph=call_graph,
        code_snippet=code_snippet,
        dedupe_key=dedupe_key,
        rule_desc=rule_desc,
    )
    timestamps = _load_violation_history_timestamps()
    rows = cast(Dict[str, Any], timestamps["rows"])
    stored = rows.get(marker)
    if isinstance(stored, str) and stored.strip():
        return stored
    if persist_if_missing:
        rows[marker] = fallback
        _save_violation_history_timestamps(timestamps)
    return fallback


def _remember_row_history_display_time(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    dedupe_key: Callable[[Any], str],
    rule_desc: Any,
    timestamp: str,
) -> None:
    timestamps = _load_violation_history_timestamps()
    marker = _row_history_time_marker(
        db_path,
        call_graph=call_graph,
        code_snippet=code_snippet,
        dedupe_key=dedupe_key,
        rule_desc=rule_desc,
    )
    rows = cast(Dict[str, Any], timestamps["rows"])
    rows[marker] = timestamp
    _save_violation_history_timestamps(timestamps)


def _history_delete_marker_payload(value: Any) -> str:
    return hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()


def _history_item_delete_markers(
    item: Dict[str, Any],
    *,
    dedupe_key: Callable[[Any], str],
    violation_match_keys: Callable[[Any], set[str]],
) -> set[str]:
    markers: set[str] = set()
    item_id = item.get("id")
    if isinstance(item_id, str) and item_id.strip():
        markers.add(f"id:{item_id.strip()}")

    database_key = dedupe_key(
        item.get("databaseName")
        or Path(str(item.get("databasePath") or "")).name
    )
    rule_key = dedupe_key(item.get("ruleDesc"))
    reason_key = dedupe_key(item.get("reason"))
    code_snippet = str(item.get("codeSnippet") or "")
    call_graph = str(item.get("callGraph") or "")
    code_key = _history_delete_marker_payload(code_snippet) if code_snippet else ""
    call_graph_key = _history_delete_marker_payload(call_graph) if call_graph else ""
    violation_key = ";".join(sorted(violation_match_keys(item.get("violations"))))

    if database_key and rule_key:
        if violation_key:
            markers.add(f"location:{database_key}:{rule_key}:{violation_key}")
        if reason_key and violation_key:
            markers.add(
                f"semantic:{database_key}:{rule_key}:{reason_key}:{violation_key}"
            )
        if code_key or call_graph_key:
            markers.add(
                f"body:{database_key}:{rule_key}:{code_key}:{call_graph_key}"
            )
        if reason_key:
            markers.add(f"reason:{database_key}:{rule_key}:{reason_key}")
    return markers


def _deleted_violation_history_markers() -> Dict[str, Any]:
    timestamps = _load_violation_history_timestamps()
    deleted = cast(Dict[str, Any], timestamps["deleted"])
    return deleted


def _is_violation_history_deleted(
    item: Dict[str, Any],
    *,
    dedupe_key: Callable[[Any], str],
    violation_match_keys: Callable[[Any], set[str]],
) -> bool:
    deleted = _deleted_violation_history_markers()
    item_markers = _history_item_delete_markers(
        item,
        dedupe_key=dedupe_key,
        violation_match_keys=violation_match_keys,
    )
    return any(marker in deleted for marker in item_markers)


def _remember_deleted_violation_history(
    item: Dict[str, Any],
    *,
    dedupe_key: Callable[[Any], str],
    violation_match_keys: Callable[[Any], set[str]],
) -> None:
    markers = _history_item_delete_markers(
        item,
        dedupe_key=dedupe_key,
        violation_match_keys=violation_match_keys,
    )
    if not markers:
        return
    timestamps = _load_violation_history_timestamps()
    deleted = cast(Dict[str, Any], timestamps["deleted"])
    deleted_at = datetime.now(timezone.utc).isoformat()
    for marker in markers:
        deleted[marker] = deleted_at
    _save_violation_history_timestamps(timestamps)


def _forget_deleted_violation_history(
    item: Dict[str, Any],
    *,
    dedupe_key: Callable[[Any], str],
    violation_match_keys: Callable[[Any], set[str]],
) -> None:
    markers = _history_item_delete_markers(
        item,
        dedupe_key=dedupe_key,
        violation_match_keys=violation_match_keys,
    )
    if not markers:
        return
    timestamps = _load_violation_history_timestamps()
    deleted = cast(Dict[str, Any], timestamps["deleted"])
    changed = False
    for marker in markers:
        if marker in deleted:
            changed = True
            deleted.pop(marker, None)
    if changed:
        _save_violation_history_timestamps(timestamps)
