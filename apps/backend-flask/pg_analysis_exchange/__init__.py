"""Portable, source-bound analysis documents shared by producers and consumers."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import stat
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

FORMAT = "protocolguard.analysis"
SCHEMA = json.loads(Path(__file__).with_name("schema.json").read_text(encoding="utf-8"))


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(value: str) -> str:
    if (
        not value
        or "\\" in value
        or ":" in value
        or "\x00" in value
        or value.startswith("/")
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise ValueError(f"Invalid source-relative path: {value!r}")
    return value


def source_root(directory: Path) -> Path:
    """Remove archive wrapper directories, without interpreting project build markers."""
    root = directory.resolve()
    while True:
        entries = list(root.iterdir())
        if len(entries) != 1 or not entries[0].is_dir() or entries[0].is_symlink():
            return root
        root = entries[0]


def extract_archive(archive: Path, directory: Path) -> Path:
    """Extract source archives without allowing member/link escapes or special files."""
    directory.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()

    def target(name: str) -> Path:
        # TAR permits conventional './' prefixes and directory trailing slashes.
        name = name.removeprefix("./").rstrip("/")
        if not name:
            return directory
        safe_path(name)
        path = directory / name
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Archive member escapes source root")
        return path

    def register(path: Path) -> None:
        key = str(path)
        if key in seen or path.is_symlink():
            raise ValueError("Duplicate archive file")
        seen.add(key)
        path.parent.mkdir(parents=True, exist_ok=True)

    links = []
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                path = target(member.filename)
                mode = member.external_attr >> 16
                if member.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                elif stat.S_ISLNK(mode):
                    register(path)
                    links.append((path, source.read(member).decode("utf-8"), False))
                else:
                    register(path)
                    with source.open(member) as content, path.open("wb") as output:
                        shutil.copyfileobj(content, output)
                    path.chmod(0o755 if mode & 0o111 else 0o644)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive) as source:
            for member in source:
                path = target(member.name)
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    register(path)
                    with (
                        source.extractfile(member) as content,
                        path.open("wb") as output,
                    ):
                        shutil.copyfileobj(content, output)
                    path.chmod(0o755 if member.mode & 0o111 else 0o644)
                elif member.issym() or member.islnk():
                    register(path)
                    links.append((path, member.linkname, member.islnk()))
                else:
                    raise ValueError("Unsupported archive member")
    else:
        raise ValueError("Source upload must be a tar or ZIP archive")
    for path, name, hard in links:
        if "\\" in name or ":" in name or Path(name).is_absolute():
            raise ValueError("Unsafe archive link")
        destination = (directory if hard else path.parent) / name
        if not destination.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Archive link escapes source root")
        if hard:
            if not destination.is_file():
                raise ValueError("Unresolved archive hard link")
            shutil.copyfile(destination, path)
        else:
            path.symlink_to(name)
    root = source_root(directory)
    manifest(root)  # Validate dangling links, directory links and empty sources now.
    return root


def manifest(root: Path) -> dict[str, Any]:
    files = []
    root = root.resolve()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            if not path.resolve().is_relative_to(root) or not path.is_file():
                raise ValueError(
                    "Source links must resolve to regular files inside source root"
                )
        if path.is_file():
            files.append(
                {
                    "path": safe_path(path.relative_to(root).as_posix()),
                    "sha256": digest(path.read_bytes()),
                }
            )
    if not files:
        raise ValueError("Source tree is empty")
    files.sort(key=lambda f: f["path"])
    return {"files": files, "treeSha256": digest(canonical(files))}


def validate_document(document: Any, root: Path | None = None) -> dict[str, Any]:
    errors = sorted(
        Draft202012Validator(SCHEMA, format_checker=FormatChecker()).iter_errors(
            document
        ),
        key=lambda e: str(e.path),
    )
    if errors:
        raise ValueError(
            f"Invalid analysis document at {list(errors[0].path)}: {errors[0].message}"
        )
    try:
        timestamp = datetime.fromisoformat(
            document["generatedAt"].replace("Z", "+00:00")
        )
        if timestamp.tzinfo is None:
            raise ValueError("Timezone required")
    except ValueError as exc:
        raise ValueError("Invalid generatedAt timestamp") from exc
    files = document["source"]["files"]
    if files != sorted(files, key=lambda f: f["path"]) or len(
        {f["path"] for f in files}
    ) != len(files):
        raise ValueError("Source manifest must contain unique sorted paths")
    for entry in files:
        safe_path(entry["path"])
    if (
        digest(canonical([{"path": f["path"], "sha256": f["sha256"]} for f in files]))
        != document["source"]["treeSha256"]
    ):
        raise ValueError("Source manifest hash does not match")
    if root is not None:
        actual = manifest(root)
        if actual["treeSha256"] != document["source"]["treeSha256"]:
            raise ValueError(
                "Source tree does not match analysis; upload the original source archive"
            )
    ids: set[str] = set()
    paths = {f["path"] for f in files}
    for result in document["results"]:
        if result["id"] in ids:
            raise ValueError("Duplicate result ID")
        ids.add(result["id"])
        location_ids = set()
        for location in result["locations"]:
            if location["id"] in location_ids:
                raise ValueError("Duplicate location ID")
            location_ids.add(location["id"])
            if safe_path(location["path"]) not in paths:
                raise ValueError("Location is absent from source manifest")
            start, end = location["startLine"], location["endLine"]
            if start > end or any(
                n < start or n > end for n in location["relevantLines"]
            ):
                raise ValueError("Invalid location line range")
            if root is not None:
                lines = (
                    (root / location["path"])
                    .read_bytes()
                    .decode("utf-8")
                    .splitlines(keepends=True)
                )
                if (
                    end > len(lines)
                    or "".join(lines[start - 1 : end]) != location["code"]
                ):
                    raise ValueError("Location evidence does not match original source")
        for diagnostic in result["diagnostics"]:
            if diagnostic.get("resultId", result["id"]) != result["id"]:
                raise ValueError("Diagnostic references an unknown result")
    for diagnostic in document["diagnostics"]:
        if "resultId" in diagnostic and diagnostic["resultId"] not in ids:
            raise ValueError("Diagnostic references an unknown result")
    return document


def eligible_results(document: dict[str, Any]) -> list[dict[str, Any]]:
    if any(
        d["severity"] == "blocking" and not d.get("resultId")
        for d in document["diagnostics"]
    ):
        return []
    blocked = {
        d.get("resultId")
        for d in document["diagnostics"]
        if d["severity"] == "blocking"
    }
    return [
        r
        for r in document["results"]
        if r["verdict"] == "non_compliant"
        and r["locations"]
        and r["id"] not in blocked
        and not any(d["severity"] == "blocking" for d in r["diagnostics"])
    ]


def _diagnostic(code: str, message: str, severity: str = "blocking") -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _list(value: Any) -> list[str]:
    return [str(x) for x in (value if isinstance(value, list) else [value]) if x]


def _rules(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        if "rules" in payload:
            return _rules(payload["rules"])
        return [
            r
            for group in payload.values()
            if isinstance(group, list)
            for r in group
            if isinstance(r, dict)
        ]
    return []


def export_database(
    database: Path,
    original: Path,
    *,
    analysis_id: str,
    archive_name: str,
    protocol: str,
    protocol_version: str | None = None,
    rules: Any = None,
    analyzed_root: Path | None = None,
    legacy: bool = False,
) -> dict[str, Any]:
    """Adapt producer-private SQLite/model output into the public contract once."""
    source = {"archiveName": Path(archive_name).name, **manifest(original)}
    paths = [f["path"] for f in source["files"]]
    rules_by_text = {
        str(r.get("rule", r.get("description", ""))).strip(): r for r in _rules(rules)
    }
    with sqlite3.connect(
        f"file:{database.resolve().as_posix()}?mode=ro", uri=True
    ) as conn:
        rows = conn.execute(
            "SELECT rule_desc, code_snippet, call_graph, llm_response FROM rule_code_snippet ORDER BY rule_desc"
        ).fetchall()
    results = []
    for description, snippet, graph, raw in rows:
        rid = "result-" + digest(str(description).encode())[:24]
        metadata = rules_by_text.get(str(description).strip(), {})
        diagnostics = []
        try:
            response = json.loads(raw)
            if not isinstance(response, dict):
                raise ValueError("Not an object")
        except (TypeError, ValueError):
            response = {}
        verdict = {
            "violation found!": "non_compliant",
            "no violation found!": "compliant",
        }.get(str(response.get("result", "")).strip().lower(), "needs_review")
        if verdict == "needs_review":
            diagnostics.append(
                _diagnostic(
                    "evaluation_unavailable",
                    "The evaluation is missing or unrecognized",
                )
            )
        locations = []
        for index, violation in enumerate(
            response.get("violations", [])
            if isinstance(response.get("violations", []), list)
            else []
        ):
            try:
                if not isinstance(violation, dict):
                    raise ValueError("Invalid location")
                reported = str(violation.get("filename", "")).replace("\\", "/")
                # Prefer exact relative path, then unique path-component suffix matches.
                reported = re.sub(r":\d+(?::\d+)?$", "", reported)
                candidates = [
                    p for p in paths if reported == p or reported.endswith("/" + p)
                ]
                if len(candidates) != 1:
                    raise ValueError("Ambiguous or unavailable source location")
                path = candidates[0]
                if analyzed_root is None:
                    raise ValueError("Original analyzed source identity is unavailable")
                built = analyzed_root / path
                if not built.is_file():
                    matches = [
                        p
                        for p in analyzed_root.rglob(Path(path).name)
                        if p.as_posix().endswith("/" + path)
                    ]
                    if len(matches) != 1:
                        raise ValueError("Ambiguous analyzed source file")
                    built = matches[0]
                if not built.is_file() or digest(built.read_bytes()) != digest(
                    (original / path).read_bytes()
                ):
                    raise ValueError("Analyzed file differs from the original source")
                numbers = violation.get("code_lines", [])
                if (
                    not isinstance(numbers, list)
                    or not numbers
                    or any(type(n) is not int or n < 1 for n in numbers)
                ):
                    raise ValueError("Missing or invalid source lines")
                start, end = min(numbers), max(numbers)
                function = violation.get("function_name") or None
                # Enrich with producer-private AST data while it is still available.
                ast = built.with_name(".cf_" + built.stem + ".json")
                if function and ast.is_file():
                    try:
                        functions = json.loads(ast.read_text()).get("functions", [])
                        matches = [
                            f
                            for f in functions
                            if f.get("name") == function
                            and f.get("overall", {}).get("start", end + 1) <= start
                            and f.get("overall", {}).get("end", 0) >= end
                        ]
                        if len(matches) == 1:
                            start, end = (
                                matches[0]["overall"]["start"],
                                matches[0]["overall"]["end"],
                            )
                    except (ValueError, TypeError, AttributeError):
                        pass
                lines = (
                    (original / path)
                    .read_bytes()
                    .decode("utf-8")
                    .splitlines(keepends=True)
                )
                if (
                    type(start) is not int
                    or type(end) is not int
                    or start < 1
                    or end > len(lines)
                ):
                    raise ValueError("Source lines are outside the original file")
                locations.append(
                    {
                        "id": f"location-{index + 1}",
                        "path": path,
                        "function": function,
                        "startLine": start,
                        "endLine": end,
                        "relevantLines": sorted(set(numbers)),
                        "code": "".join(lines[start - 1 : end]),
                    }
                )
            except (ValueError, OSError) as exc:
                diagnostics.append(_diagnostic("location_unresolved", str(exc)))
        if verdict == "non_compliant" and not locations and not diagnostics:
            diagnostics.append(
                _diagnostic(
                    "location_unresolved", "No verified source location was produced"
                )
            )
        results.append(
            {
                "id": rid,
                "rule": {
                    "id": str(metadata.get("id") or "rule-" + rid[7:]),
                    "description": str(description),
                    "reference": metadata.get("reference"),
                    "requestTypes": _list(metadata.get("req_type")),
                    "requestFields": _list(metadata.get("req_fields")),
                    "responseTypes": _list(metadata.get("res_type")),
                    "responseFields": _list(metadata.get("res_fields")),
                },
                "verdict": verdict,
                "reason": str(
                    response.get("reason") or "No valid evaluation available"
                ),
                "locations": locations,
                "context": {"codeSlice": snippet or None, "callGraph": graph or None},
                "diagnostics": diagnostics,
            }
        )
    document = {
        "format": FORMAT,
        "schemaVersion": "1.0",
        "analysisId": analysis_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "producer": {"name": "ProtocolGuard", "version": "1.0.0"},
        "protocol": {"name": protocol or "unknown", "version": protocol_version},
        "source": source,
        "results": results,
        "diagnostics": [],
    }
    if legacy:
        document["diagnostics"].append(
            _diagnostic(
                "legacy_source_identity_unavailable",
                "Legacy database has no original source manifest; rerun analysis or supply a previously exported JSON document",
            )
        )
    return validate_document(document, original)


def read_database_document(database: Path, root: Path) -> dict[str, Any]:
    """Resolve legacy input only when its producer supplied a source-bound companion."""
    database_hash = digest(database.read_bytes())
    for parent in [database.parent, database.parent.parent]:
        candidate = parent / "analysis-exchange.json"
        binding = parent / "analysis-exchange-origin.json"
        if candidate.is_file() and binding.is_file():
            provenance = json.loads(binding.read_text(encoding="utf-8"))
            if provenance.get("databaseSha256") == database_hash:
                return validate_document(
                    json.loads(candidate.read_text(encoding="utf-8")), root
                )
    raise ValueError(
        "Legacy database has no verifiable source identity. Upload the exported analysis JSON or rerun static analysis."
    )
