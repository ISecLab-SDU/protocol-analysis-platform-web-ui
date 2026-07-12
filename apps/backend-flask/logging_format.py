"""Logging formatters for backend application output."""

from __future__ import annotations

import logging
import os
import re
import sys
from collections.abc import Mapping

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_RESET = "\x1b[0m"
_LEVEL_COLORS = {
    logging.DEBUG: "\x1b[2;37m",
    logging.INFO: "\x1b[32m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[1;31m",
}


class ContextFormatter(logging.Formatter):
    """Append structured LogRecord context as stable key=value fields."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        context = _get_context(record)
        if not context:
            return message
        return f"{message}\t{_format_context(context)}"


class ColorizedContextFormatter(ContextFormatter):
    """Colorize console log levels while preserving plain file output."""

    def __init__(
        self,
        *args: object,
        level_width: int = 8,
        use_color: bool | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._level_width = level_width
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        levelname = f"{original_levelname:<{self._level_width}}"
        color = _LEVEL_COLORS.get(record.levelno)
        if color is not None and self._should_color():
            levelname = f"{color}{levelname}{_RESET}"
        record.levelname = levelname
        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname

    def _should_color(self) -> bool:
        if self._use_color is not None:
            return self._use_color
        if os.environ.get("NO_COLOR") is not None:
            return False
        if os.environ.get("FORCE_COLOR"):
            return True
        return sys.stderr.isatty()


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
