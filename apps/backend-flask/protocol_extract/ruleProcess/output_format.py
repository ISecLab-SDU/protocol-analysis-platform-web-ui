from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _normalize_strings(value: object) -> list[str]:
    if isinstance(value, str):
        values: Iterable[object] = [value]
    elif isinstance(value, list):
        values = value
    else:
        return []

    normalized: list[str] = []
    for item in values:
        if item is None:
            continue
        text = str(item).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def build_legacy_rules_payload(
    results: Iterable[object],
) -> dict[str, list[dict[str, Any]]]:
    """Convert model output to the grouped scalar schema consumed by ProtocolGuard."""
    grouped: dict[str, list[dict[str, Any]]] = {}

    for result in results:
        if not isinstance(result, dict):
            continue

        rule = str(result.get("rule") or "").strip()
        if not rule:
            continue

        request_types = _normalize_strings(result.get("req_type")) or [""]
        response_types = _normalize_strings(result.get("res_type")) or [""]
        request_fields = _normalize_strings(result.get("req_fields"))
        response_fields = _normalize_strings(result.get("res_fields"))

        for request_type in request_types:
            for response_type in response_types:
                group = request_type or response_type or "DEFAULT"
                grouped.setdefault(group, []).append(
                    {
                        "rule": rule,
                        "req_type": request_type,
                        "req_fields": request_fields,
                        "res_type": response_type,
                        "res_fields": response_fields,
                    }
                )

    return grouped
