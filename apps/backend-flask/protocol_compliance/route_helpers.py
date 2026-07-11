"""Shared helpers used by protocol-compliance route handlers."""

from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import Iterable
from typing import Optional, cast

import toml
from werkzeug.datastructures import FileStorage

from .store import TaskStatus

LOGGER = logging.getLogger(__name__)


def _to_int(value: object, fallback: int) -> int:
    if value is None:
        return fallback
    try:
        parsed = int(str(value))
    except ValueError:
        return fallback
    return parsed if parsed > 0 else fallback


def _normalize_status(raw: object) -> Optional[list[TaskStatus]]:
    if not raw:
        return None
    if isinstance(raw, str):
        raw_items: Iterable[str] = [raw]
    elif isinstance(raw, Iterable):
        raw_items = (str(item) for item in raw)
    else:
        return None
    statuses: set[TaskStatus] = set()
    allowed: set[TaskStatus] = {"completed", "failed", "processing", "queued"}

    for item in raw_items:
        if not item:
            continue
        segments = [segment.strip() for segment in item.split(",")]
        for segment in segments:
            if segment in allowed:
                statuses.add(cast(TaskStatus, segment))

    return list(statuses) if statuses else None


def _parse_tags(raw: Optional[str]) -> Optional[list[str]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, list):
        tags = [item for item in parsed if isinstance(item, str)]
        return tags or None
    return None


def _read_upload(upload: FileStorage) -> tuple[str, Optional[bytes]]:
    filename = upload.filename or "upload.bin"
    data = upload.read() if upload else None
    if upload:
        with contextlib.suppress(Exception):
            upload.stream.seek(0)
    return filename, data


def _extract_protocol_metadata_from_config(
    raw: Optional[bytes], source_label: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    source = source_label or "config.toml"
    if not raw:
        LOGGER.debug("Config payload %s is empty; skipping protocol metadata extraction", source)
        return None, None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        LOGGER.warning("Failed to decode %s as UTF-8 while extracting protocol metadata: %s", source, exc)
        return None, None
    try:
        parsed = toml.loads(text)
    except toml.TomlDecodeError as exc:
        LOGGER.warning("Failed to parse %s as TOML while extracting protocol metadata: %s", source, exc)
        return None, None

    project = parsed.get("project")
    if isinstance(project, dict):
        raw_name = project.get("protocol_name") or project.get("protocol")
        raw_version = project.get("protocol_version") or project.get("version")
        name = raw_name.strip() if isinstance(raw_name, str) else None
        version = raw_version.strip() if isinstance(raw_version, str) else None
        return (name or None, version or None)

    LOGGER.debug(
        "Config %s does not define a [project] section when extracting protocol metadata", source
    )
    return None, None


def _collect_exception_details(exc: Exception, *, max_logs: int = 40) -> dict[str, object]:
    details: dict[str, object] = {"message": str(exc)}
    extra = getattr(exc, "details", None)
    if isinstance(extra, dict) and extra:
        details.update(extra)

    logs = getattr(exc, "logs", None)
    if isinstance(logs, list) and logs:
        details["logs"] = logs[-max_logs:]

    excerpt = getattr(exc, "log_excerpt", None)
    if excerpt and "logExcerpt" not in details:
        details["logExcerpt"] = excerpt

    return details


def _strip_extension(filename: str) -> str:
    if "." not in filename:
        return filename
    return filename.rsplit(".", 1)[0]
