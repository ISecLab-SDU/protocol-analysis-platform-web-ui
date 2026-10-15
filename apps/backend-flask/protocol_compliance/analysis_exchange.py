"""Web boundary for portable analysis artifacts and legacy database inputs."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any

from pg_analysis_exchange import (
    digest,
    eligible_results,
    extract_archive,
    read_database_document,
    validate_document,
    export_database,
    source_root,
)


def _write_json(path: Path, value: Any) -> None:
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def persist_exchange(document: dict[str, Any], output: Path, database: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "analysis-exchange.json"
    _write_json(path, document)
    _write_json(
        output / "analysis-exchange-origin.json",
        {"databaseSha256": digest(database.read_bytes())},
    )
    return path


def prepare_assertion_document(
    code_name: str,
    code_data: bytes,
    *,
    document_data: bytes | None = None,
    database_data: bytes | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    with TemporaryDirectory(prefix="pg-analysis-input-") as temp:
        directory = Path(temp)
        archive = directory / "source.archive"
        archive.write_bytes(code_data)
        root = extract_archive(archive, directory / "source")
        if document_data is not None:
            document = json.loads(document_data)
        else:
            if database_data is None:
                raise ValueError("No analysis document supplied")
            if database_path is None:
                database_path = directory / "legacy.db"
                database_path.write_bytes(database_data)
            document = read_database_document(database_path, root)
        validate_document(document, root)
        if not eligible_results(document):
            raise ValueError(
                "No eligible violations: results are compliant, inconclusive, or blocked by unresolved evidence"
            )
        return document


def resolve_exchange_artifact(result: dict[str, Any]) -> Path:
    """Retry export from persisted producer inputs without rerunning analysis."""
    artifacts = result.get("artifacts") or {}
    existing = artifacts.get("exchange")
    if existing and Path(existing).is_file():
        return Path(existing)
    workspace_path, database_path = (
        artifacts.get("workspace"),
        artifacts.get("database"),
    )
    if not workspace_path or not database_path:
        raise ValueError(
            "Original source snapshot or analysis database is unavailable; rerun analysis"
        )
    workspace, database = Path(workspace_path), Path(database_path)
    output = Path(artifacts.get("output") or workspace / "exchange-output")
    existing = output / "analysis-exchange.json"
    if existing.is_file():
        return existing
    metadata = result.get("modelResponse", {}).get("metadata", {})
    inputs = result.get("inputs") or {}
    document = export_database(
        database,
        source_root(workspace / "exchange-source"),
        analysis_id=result["analysisId"],
        archive_name=inputs.get("codeFileName", "source-archive"),
        protocol=metadata.get("protocol") or inputs.get("protocolName") or "unknown",
        protocol_version=metadata.get("protocolVersion"),
        rules=json.loads((workspace / "inputs/rules.json").read_text(encoding="utf-8")),
        analyzed_root=source_root(workspace / "project"),
    )
    return persist_exchange(document, output, database)
