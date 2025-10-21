"""Filesystem helpers for ProtocolGuard Docker jobs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["JobPaths"]


@dataclass
class JobPaths:
    job_id: str
    workspace: Path
    output: Path
    config_dir: Path
    config_file: Path
    log_file: Path
