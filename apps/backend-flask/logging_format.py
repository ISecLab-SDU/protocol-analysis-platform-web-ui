"""Logging formatters for backend application output."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class ContextFormatter(logging.Formatter):
    """Append structured LogRecord context as stable key=value fields."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        context = _get_context(record)
        if not context:
            return message
        return f"{message}\t{_format_context(context)}"


def _get_context(record: logging.LogRecord) -> Mapping[str, object] | None:
    context = getattr(record, "protocolguard_context", None)
    if isinstance(context, Mapping):
        return context
    return None


def _format_context(context: Mapping[str, object]) -> str:
    return " ".join(
        f"{key}={_format_value(value)}"
        for key, value in sorted(context.items())
        if value is not None
    )


def _format_value(value: object) -> str:
    text = _CONTROL_CHARS_RE.sub("?", str(value))
    if not text:
        return '""'
    if any(char.isspace() for char in text) or '"' in text or "\\" in text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text
