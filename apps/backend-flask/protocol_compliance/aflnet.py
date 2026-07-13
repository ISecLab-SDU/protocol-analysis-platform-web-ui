"""AFLNet/ProtocolGuard filesystem and command helpers."""

from __future__ import annotations

import json
import os
import shlex
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, cast


# SOL配置 - ProtocolGuard配置
RTSP_CONFIG = {
    "script_path": None,  # 不再需要脚本文件
    "container_output_dir": "/out/fuzz-output",
    "log_file_name": "plot_data",
    "image": "protocolguard:latest",
    "command": "fuzz",
}


def _is_path_inside(path: Path, allowed_roots: list[Path]) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False

    for root in allowed_roots:
        try:
            resolved.relative_to(root.expanduser().resolve())
            return True
        except (OSError, RuntimeError, ValueError):
            continue
    return False


def _aflnet_output_root() -> Path:
    configured = os.environ.get("AFLNET_OUTPUT_ROOT")
    if configured:
        return Path(configured).expanduser()
    runtime_root = Path(
        os.environ.get("PG_RUNTIME_ROOT", "/tmp/protocolguard")
    ).expanduser()
    output_root = Path(
        os.environ.get("PG_OUTPUT_ROOT", runtime_root / "outputs")
    ).expanduser()
    return output_root.parent / "fuzz-output"


def _aflnet_log_file_name() -> str:
    return cast(str, RTSP_CONFIG["log_file_name"])


def _aflnet_container_output_dir() -> str:
    return cast(str, RTSP_CONFIG["container_output_dir"])


def _process_identity_value(env_name: str, fallback: int) -> str:
    configured = os.environ.get(env_name)
    if configured and configured.isdigit():
        return configured
    return str(fallback)


def _aflnet_container_host_identity_flags() -> str:
    uid = _process_identity_value("PG_HOST_UID", os.getuid())
    gid = _process_identity_value("PG_HOST_GID", os.getgid())
    return f"-e PG_HOST_UID={uid} -e PG_HOST_GID={gid}"


def _aflnet_shell_command(
    instrumented_code_dir: Optional[Path] = None,
    *,
    bundle_dir: Optional[Path] = None,
    runtime_env: Optional[Dict[str, str]] = None,
    output_root: Optional[Path] = None,
) -> str:
    output_root = output_root or _aflnet_output_root()
    output_root.mkdir(parents=True, exist_ok=True)
    mount = f"{output_root}:{_aflnet_container_output_dir()}"
    command = [
        "docker",
        "run",
        "-d",
        "--privileged",
        _aflnet_container_host_identity_flags(),
        "-v",
        shlex.quote(mount),
    ]
    if instrumented_code_dir is not None:
        command.extend(
            [
                "-e",
                "PG_FUZZ_INSTRUMENTED_CODE_DIR=/workspace/instrumented_code",
                "-v",
                shlex.quote(f"{instrumented_code_dir}:/workspace/instrumented_code:ro"),
            ]
        )
    if bundle_dir is not None:
        command.extend(["-v", shlex.quote(f"{bundle_dir}:/workspace:ro")])
    for key, value in (runtime_env or {}).items():
        command.extend(["-e", shlex.quote(f"{key}={value}")])
    command.extend(
        [
            shlex.quote(cast(str, RTSP_CONFIG["image"])),
            shlex.quote(cast(str, RTSP_CONFIG["command"])),
        ]
    )
    return " ".join(command)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _aflnet_fallback_output_root() -> Path:
    configured = os.environ.get("AFLNET_FALLBACK_OUTPUT_ROOT")
    if configured:
        return Path(configured).expanduser()

    filename = os.environ.get("AFLNET_FALLBACK_LOG_FILE_NAME", "plot_data")
    candidates = [
        _repo_root() / "fuzz-output",
        _repo_root().parent / "fuzz-output",
        Path.cwd() / "fuzz-output",
        Path("/tmp/protocolguard/fuzz-output"),
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / filename).exists():
            return resolved

    for candidate in candidates:
        expanded = candidate.expanduser()
        if expanded.exists():
            return expanded

    fallback = _repo_root() / "fuzz-output"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _aflnet_output_root_for_source(source: str = "primary") -> Path:
    if source == "fallback":
        return _aflnet_fallback_output_root()
    return _aflnet_output_root()


def _aflnet_log_file_for_source(source: str = "primary") -> Path:
    if source == "fallback":
        filename = os.environ.get("AFLNET_FALLBACK_LOG_FILE_NAME", "plot_data")
        return _aflnet_fallback_output_root() / filename
    return _aflnet_output_root() / _aflnet_log_file_name()


def _resolve_aflnet_output_source(data: Optional[Dict[str, Any]] = None) -> str:
    requested = (data or {}).get("outputSource") or (data or {}).get("output_source")
    if requested == "fallback" or (data or {}).get("useFallbackOutput"):
        return "fallback"
    return "primary"


def _resolve_aflnet_archive_source(
    requested_path: Optional[str],
    requested_source: Optional[str],
) -> str:
    if requested_source == "fallback":
        return "fallback"
    if requested_path:
        path = Path(requested_path).expanduser()
        if path.exists() and _is_path_inside(path, [_aflnet_fallback_output_root()]):
            return "fallback"
    return "primary"


def _aflnet_artifact_root() -> Path:
    configured = os.environ.get("AFLNET_ARTIFACT_ROOT")
    if configured:
        return Path(configured).expanduser()
    pg_output_root = Path(
        os.environ.get("PG_OUTPUT_ROOT", "/tmp/protocolguard/outputs")
    ).expanduser()
    return pg_output_root.parent / "fuzz-artifacts"


def _aflnet_result_path_info(
    source: str = "primary",
    *,
    output_root: Optional[Path] = None,
) -> Dict[str, Any]:
    explicit_output_root = output_root
    output_root = (
        output_root.expanduser()
        if output_root is not None
        else _aflnet_output_root_for_source(source).expanduser()
    )
    log_file = (
        output_root / _aflnet_log_file_name()
        if explicit_output_root is not None
        else _aflnet_log_file_for_source(source).expanduser()
    )
    poc_path = output_root
    for name in ("replayable-crashes", "crashes", "crash", "crash_logs", "queue"):
        candidate = output_root / name
        if candidate.exists():
            poc_path = candidate
            break
    return {
        "isFallbackOutput": source == "fallback",
        "logFilePath": str(log_file),
        "outputSource": source,
        "outputRoot": str(output_root),
        "pocPath": str(poc_path),
    }


def _poc_artifact_candidates(
    output_root: Path, requested_path: Optional[str]
) -> list[Path]:
    allowed_roots = [output_root]
    candidates: list[Path] = []

    if requested_path:
        requested = Path(requested_path).expanduser()
        if requested.exists() and _is_path_inside(requested, allowed_roots):
            candidates.append(requested)

    for name in (
        "replayable-crashes",
        "crashes",
        "crash",
        "crash_logs",
        "queue",
        "hangs",
        "fuzzer_stats",
        "plot_data",
    ):
        candidate = output_root / name
        if candidate.exists():
            candidates.append(candidate)

    if not candidates and output_root.exists():
        candidates.append(output_root)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except (OSError, RuntimeError):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(candidate)
    return deduped


def _add_path_to_zip(archive: zipfile.ZipFile, path: Path, output_root: Path) -> int:
    if not path.exists() or not _is_path_inside(path, [output_root]):
        return 0

    added = 0
    if path.is_file():
        archive.write(path, path.relative_to(output_root).as_posix())
        return 1

    for child in sorted(path.rglob("*")):
        if not child.is_file() or child.is_symlink():
            continue
        if not _is_path_inside(child, [output_root]):
            continue
        archive.write(child, child.relative_to(output_root).as_posix())
        added += 1
    return added


def _manifest_path_for_candidate(path: Path, output_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(output_root.resolve())
    except (OSError, RuntimeError, ValueError):
        return str(path)
    text = relative.as_posix()
    return text or "."


def _aflnet_finding_verdict(candidates: list[Path]) -> str:
    crash_names = {"replayable-crashes", "crashes", "crash", "crash_logs"}
    return (
        "afl_crash_observed"
        if any(candidate.name in crash_names for candidate in candidates)
        else "afl_no_crash_observed"
    )


def _write_aflnet_poc_archive(
    target: Any,
    *,
    artifact_id: Optional[str],
    crash_log_path: Optional[str],
    implementation: str,
    output_root: Path,
    protocol: str,
) -> int:
    candidates = _poc_artifact_candidates(output_root, crash_log_path)
    if not candidates:
        return 0

    manifest = {
        "artifactType": "aflnet_finding_bundle",
        "artifactId": artifact_id,
        "protocol": protocol,
        "implementation": implementation,
        "verdict": _aflnet_finding_verdict(candidates),
        "disclaimer": (
            "This bundle reports AFLNet runtime findings only. It does not "
            "attribute crashes to a specific inserted assertion or protocol rule."
        ),
        "outputRoot": str(output_root),
        "includedPaths": [
            _manifest_path_for_candidate(candidate, output_root) for candidate in candidates
        ],
        "requestedCrashLogPath": crash_log_path,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    added = 0

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2)
        )
        added += 1
        for candidate in candidates:
            added += _add_path_to_zip(archive, candidate, output_root)

    return added
