#!/usr/bin/env python3
"""Seed ProtocolGuard static analysis history entries without running Docker."""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

# Make the protocol_compliance package importable when executed as a script.
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from protocol_compliance import analysis  # type: ignore  # noqa: E402
from protocol_compliance.state_repository import (  # type: ignore  # noqa: E402
    AnalysisStateRepository,
    analysis_state_repository,
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def synthesize_job(
    repo: AnalysisStateRepository,
    *,
    protocol_name: str,
    protocol_version: Optional[str],
    rules_file: str,
    code_file_name: str,
    builder_file: str,
    config_file: str,
    notes: Optional[str],
    rules_summary: Optional[str],
    database_path: Optional[Path],
    start_time: datetime,
) -> str:
    """Insert a completed job plus its progress events."""
    job_id = str(uuid.uuid4())
    t0 = start_time
    t1 = t0 + timedelta(seconds=1)
    t2 = t0 + timedelta(seconds=2)
    t3 = t0 + timedelta(seconds=3)

    repo.record_progress(
        job_id=job_id,
        status="queued",
        stage="queued",
        message="Job queued",
        created_at=_iso(t0),
        updated_at=_iso(t0),
    )
    repo.add_event(job_id=job_id, timestamp=_iso(t0), stage="queued", message="Job queued")

    repo.record_progress(
        job_id=job_id,
        status="running",
        stage="init",
        message="Preparing analysis inputs",
        updated_at=_iso(t1),
    )
    repo.add_event(job_id=job_id, timestamp=_iso(t1), stage="init", message="Preparing analysis inputs")

    repo.record_progress(
        job_id=job_id,
        status="running",
        stage="inputs",
        message="Persisting uploaded artefacts",
        updated_at=_iso(t2),
    )
    repo.add_event(job_id=job_id, timestamp=_iso(t2), stage="inputs", message="Persisting uploaded artefacts")

    result = analysis.build_mock_analysis(
        code_file_name=code_file_name,
        rules_file_name=rules_file,
        protocol_name=protocol_name,
        notes=notes,
        rules_summary=rules_summary,
    )
    if isinstance(result, dict):
        inputs = result.setdefault("inputs", {})
        if isinstance(inputs, dict):
            inputs["codeFileName"] = code_file_name
    metadata = result.get("modelResponse", {}).get("metadata")
    if isinstance(metadata, dict) and protocol_version:
        metadata.setdefault("protocolVersion", protocol_version)
    artifacts = _build_artifacts(job_id, database_path, builder_file, config_file)
    if artifacts:
        result["artifacts"] = artifacts

    repo.record_completion(
        job_id=job_id,
        status="completed",
        stage="completed",
        message="Static analysis completed successfully",
        updated_at=_iso(t3),
        result=result,
    )
    repo.add_event(
        job_id=job_id,
        timestamp=_iso(t3),
        stage="completed",
        message="Static analysis completed successfully",
    )
    return job_id


def _build_artifacts(
    job_id: str,
    database_path: Optional[Path],
    builder_file: str,
    config_file: str,
) -> Optional[dict]:
    if not database_path:
        return None
    database = database_path.expanduser().resolve()
    return {
        "database": str(database),
        "workspace": None,
        "output": None,
        "config": None,
        "logs": None,
        "workspaceSnapshots": [
            {
                "path": str(database),
                "label": "ProtocolGuard SQLite results",
            }
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create static-analysis history rows and events without executing ProtocolGuard.",
    )
    parser.add_argument("--db-path", type=Path, default=analysis_state_repository.db_path, help="SQLite file to seed")
    parser.add_argument("--count", type=int, default=1, help="How many completed jobs to insert")
    parser.add_argument("--protocol-name", default="TLS 1.3 handshake", help="Protocol name recorded in metadata")
    parser.add_argument("--protocol-version", default=None, help="Optional protocol version")
    parser.add_argument("--rules-file", default="protocol-guard-rules.yaml", help="Rules file name stored in inputs")
    parser.add_argument(
        "--code-file-name",
        default=None,
        help="Compressed source archive name stored in inputs.codeFileName",
    )
    parser.add_argument("--code-file", default="handler.c", help="Source file name stored in inputs")
    parser.add_argument("--builder-file", default="protocol-builder.zip", help="Builder file name for inputs/artifacts")
    parser.add_argument("--config-file", default="protocol-config.yml", help="Config file name for inputs/artifacts")
    parser.add_argument("--notes", default="Seeded via synth script", help="Notes stored in the analysis input payload")
    parser.add_argument("--rules-summary", default="Mock rule set summary", help="Optional rules summary text")
    parser.add_argument(
        "--database",
        type=Path,
        action="append",
        help="Path to an existing ProtocolGuard SQLite result database (workspace not required). "
        "Specify multiple times to insert multiple jobs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = AnalysisStateRepository(db_path=args.db_path)

    start = datetime.now(timezone.utc)
    job_ids: List[str] = []
    database_paths = args.database or []

    code_file_name = args.code_file_name or args.code_file

    if database_paths:
        pairs = list(enumerate(database_paths))
    else:
        pairs = [(offset, None) for offset in range(max(args.count, 1))]

    for offset, db_path in pairs:
        job_ids.append(
            synthesize_job(
                repo,
                protocol_name=args.protocol_name,
                protocol_version=args.protocol_version,
                rules_file=args.rules_file,
                code_file_name=code_file_name,
                builder_file=args.builder_file,
                config_file=args.config_file,
                notes=args.notes,
                rules_summary=args.rules_summary,
                database_path=db_path,
                start_time=start + timedelta(minutes=offset),
            )
        )

    print(f"Inserted {len(job_ids)} completed job(s) into {args.db_path}")
    for job_id in job_ids:
        print(f"- {job_id}")


if __name__ == "__main__":
    main()
