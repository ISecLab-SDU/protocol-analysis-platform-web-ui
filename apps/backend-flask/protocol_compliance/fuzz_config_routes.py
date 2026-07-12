"""Fuzz runtime configuration job handlers."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, cast

from flask import make_response, request

from utils.responses import error_response, success_response

from .assertion import get_assert_generation_job, get_assert_generation_result
from .fuzz_job_routes import (
    _allowed_instrumented_zip_roots,
    _append_log,
    _debug_replay_instrumented_code_zip,
    _format_bytes,
    _instrumented_code_zip_path,
    _is_path_inside,
    _latest_instrumented_code_zip,
    _path_preview_lines,
    _validate_instrumented_code_zip,
)

LOGGER = logging.getLogger(__name__)


class FuzzConfigJobRegistry:
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create(
        self,
        *,
        assert_generation_job_id: str,
        instrumented_code_zip_path: Path,
        notes: Optional[str],
        protocol: str,
        protocol_implementations: list[str],
        runtime_overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        workspace = _config_workspace_root() / job_id
        output = _config_output_root() / job_id
        bundle = output / "fuzz-bundle"
        job: Dict[str, Any] = {
            "jobId": job_id,
            "assertGenerationJobId": assert_generation_job_id,
            "status": "queued",
            "stage": "queued",
            "message": "Fuzz configuration job queued",
            "createdAt": now,
            "updatedAt": now,
            "protocol": protocol,
            "protocolImplementations": protocol_implementations,
            "runtimeOverrides": runtime_overrides,
            "notes": notes,
            "inputs": {
                "instrumentedCodeZipPath": str(instrumented_code_zip_path),
                "instrumentedCodeZipFileName": instrumented_code_zip_path.name,
            },
            "artifacts": {
                "workspacePath": str(workspace),
                "outputPath": str(output),
                "bundlePath": str(bundle),
                "manifestPath": str(bundle / "fuzz-runtime.json"),
                "envPath": str(bundle / "fuzz-env.json"),
                "logFilePath": str(output / "fuzz-config.log"),
                "eventsPath": str(bundle / "evidence" / "agent-events.jsonl"),
            },
            "process": None,
            "result": None,
            "error": None,
        }
        self._jobs[job_id] = job
        return self.snapshot(job_id) or job

    def update(self, job_id: str, **fields: Any) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updatedAt"] = _now_iso()

    def snapshot(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return dict(job)


FUZZ_CONFIG_JOBS = FuzzConfigJobRegistry()


def create_fuzz_config_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
) -> Dict[str, Callable[..., Any]]:
    def start_fuzz_config_job():
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json(silent=True) or {}
        assert_generation_job_id = str(data.get("assertGenerationJobId") or "").strip()
        instrumented_zip: Optional[Path] = None
        if assert_generation_job_id:
            assert_snapshot = get_assert_generation_job(assert_generation_job_id)
            if not assert_snapshot:
                return make_response(error_response("未找到断言生成任务"), 404)
            if assert_snapshot.get("status") != "completed":
                return make_response(
                    error_response("断言生成任务尚未完成", {"status": assert_snapshot.get("status")}),
                    409,
                )
            instrumented_zip = _instrumented_code_zip_path(
                get_assert_generation_result(assert_generation_job_id)
            )
            if instrumented_zip is None:
                return make_response(error_response("断言生成结果缺少插桩源码压缩包"), 400)
        else:
            requested_zip = data.get("instrumentedCodeZipPath")
            if isinstance(requested_zip, str) and requested_zip.strip():
                instrumented_zip = Path(requested_zip.strip()).expanduser()
                assert_generation_job_id = _infer_assert_generation_job_id(instrumented_zip)
            else:
                instrumented_zip = (
                    _debug_replay_instrumented_code_zip()
                    or _latest_instrumented_code_zip()
                )
                if instrumented_zip is None:
                    return make_response(
                        error_response("未找到可复用的插桩源码压缩包"), 404
                    )
                assert_generation_job_id = _infer_assert_generation_job_id(instrumented_zip)

        zip_error = _validate_or_existing_assert_zip(instrumented_zip)
        if zip_error:
            return make_response(error_response(zip_error), 400)

        protocol = str(data.get("protocol") or "UNKNOWN").strip() or "UNKNOWN"
        protocol_implementations = _parse_protocol_implementations(data)
        runtime_overrides, runtime_override_error = _parse_runtime_overrides(data)
        if runtime_override_error:
            return make_response(error_response(runtime_override_error), 400)
        notes = data.get("notes")
        notes_text = notes.strip() if isinstance(notes, str) and notes.strip() else None

        snapshot = FUZZ_CONFIG_JOBS.create(
            assert_generation_job_id=assert_generation_job_id,
            instrumented_code_zip_path=instrumented_zip,
            notes=notes_text,
            protocol=protocol,
            protocol_implementations=protocol_implementations,
            runtime_overrides=runtime_overrides,
        )
        thread = threading.Thread(
            target=_prepare_fuzz_config_job,
            args=(snapshot["jobId"], instrumented_zip),
            daemon=True,
        )
        thread.start()
        FUZZ_CONFIG_JOBS.update(
            snapshot["jobId"],
            process={"threadName": thread.name, "pid": None},
        )
        return make_response(success_response(FUZZ_CONFIG_JOBS.snapshot(snapshot["jobId"])), 202)

    def get_fuzz_config_job(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error
        snapshot = FUZZ_CONFIG_JOBS.snapshot(job_id)
        if not snapshot:
            return make_response(error_response("未找到 Fuzz 配置任务"), 404)
        return make_response(success_response(snapshot), 200)

    def read_fuzz_config_logs(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error
        snapshot = FUZZ_CONFIG_JOBS.snapshot(job_id)
        if not snapshot:
            return make_response(error_response("未找到 Fuzz 配置任务"), 404)
        from_position_raw = request.args.get("fromPosition", "0")
        try:
            from_position = max(0, int(from_position_raw))
        except (TypeError, ValueError):
            from_position = 0
        log_file = _job_log_file(snapshot)
        content = ""
        position = from_position
        if log_file.exists():
            with log_file.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(from_position)
                content = handle.read()
                position = handle.tell()
        return make_response(
            success_response(
                {
                    "content": content,
                    "position": position,
                    "fileSize": log_file.stat().st_size if log_file.exists() else 0,
                    "job": FUZZ_CONFIG_JOBS.snapshot(job_id) or snapshot,
                    "logFilePath": str(log_file),
                }
            ),
            200,
        )

    return {
        "start_fuzz_config_job": start_fuzz_config_job,
        "get_fuzz_config_job": get_fuzz_config_job,
        "read_fuzz_config_logs": read_fuzz_config_logs,
    }


def completed_fuzz_config_job(job_id: str) -> Optional[Dict[str, Any]]:
    snapshot = FUZZ_CONFIG_JOBS.snapshot(job_id)
    if not snapshot or snapshot.get("status") != "completed":
        return None
    artifacts = snapshot.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    manifest_path = Path(str(artifacts.get("manifestPath") or ""))
    env_path = Path(str(artifacts.get("envPath") or ""))
    bundle_path = Path(str(artifacts.get("bundlePath") or ""))
    if not manifest_path.is_file() or not env_path.is_file() or not bundle_path.is_dir():
        return None
    return snapshot


def _prepare_fuzz_config_job(job_id: str, instrumented_zip: Path) -> None:
    snapshot = FUZZ_CONFIG_JOBS.snapshot(job_id)
    if not snapshot:
        return
    artifacts = cast(Dict[str, str], snapshot["artifacts"])
    workspace = Path(artifacts["workspacePath"])
    output = Path(artifacts["outputPath"])
    bundle = Path(artifacts["bundlePath"])
    log_file = Path(artifacts["logFilePath"])
    inputs = workspace / "inputs"
    instrumented_dir = inputs / "instrumented_code"

    try:
        FUZZ_CONFIG_JOBS.update(
            job_id,
            status="running",
            stage="workspace",
            message="Preparing fuzz configuration workspace",
        )
        inputs.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)
        bundle.mkdir(parents=True, exist_ok=True)
        _append_log(log_file, f"Fuzz configuration job {job_id} accepted")
        _append_log(log_file, f"Protocol: {snapshot.get('protocol') or 'UNKNOWN'}")
        _append_log(log_file, f"Workspace: {workspace}")
        _append_log(log_file, f"Bundle: {bundle}")
        _append_log(log_file, f"Input instrumented source zip: {instrumented_zip}")
        _append_log(log_file, f"Input zip size: {_format_bytes(instrumented_zip.stat().st_size)}")

        staged_zip = inputs / "instrumented_code.zip"
        shutil.copy2(instrumented_zip, staged_zip)
        if instrumented_dir.exists():
            shutil.rmtree(instrumented_dir)
        instrumented_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(staged_zip) as archive:
            archive_names = archive.namelist()
            archive.extractall(instrumented_dir)
        file_count = sum(1 for name in archive_names if name and not name.endswith("/"))
        _append_log(log_file, f"Extracted instrumented source: {instrumented_dir}")
        _append_log(log_file, f"Extracted file count: {file_count}")
        for line in _path_preview_lines(instrumented_dir, limit=24):
            _append_log(log_file, f"  {line}")

        command = _fuzz_config_docker_command(snapshot, instrumented_dir, bundle)
        _append_log(log_file, f"Launching fuzz configuration command: {' '.join(command)}")
        FUZZ_CONFIG_JOBS.update(
            job_id,
            stage="agent",
            message="Fuzz configuration Agent running",
            process={"command": command, "pid": None},
        )
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        current_process = dict(cast(Dict[str, Any], FUZZ_CONFIG_JOBS.snapshot(job_id) or {}).get("process") or {})
        current_process["pid"] = process.pid
        FUZZ_CONFIG_JOBS.update(job_id, process=current_process)

        stdout_thread = threading.Thread(
            target=_pipe_process_stream,
            args=(process.stdout, log_file, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_pipe_process_stream,
            args=(process.stderr, log_file, "stderr"),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        return_code = process.wait()
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        if return_code != 0:
            raise RuntimeError(f"Fuzz configuration container exited with code {return_code}")

        manifest_path = Path(artifacts["manifestPath"])
        env_path = Path(artifacts["envPath"])
        if not manifest_path.is_file():
            raise RuntimeError(f"Fuzz configuration manifest was not produced: {manifest_path}")
        if not env_path.is_file():
            raise RuntimeError(f"Fuzz runtime environment file was not produced: {env_path}")
        result = {
            "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
            "runtimeEnv": json.loads(env_path.read_text(encoding="utf-8")),
        }
        _append_log(log_file, f"Fuzz configuration manifest: {manifest_path}")
        _append_log(log_file, f"Fuzz runtime env: {env_path}")
        FUZZ_CONFIG_JOBS.update(
            job_id,
            status="completed",
            stage="completed",
            message="Fuzz configuration completed",
            result=result,
            artifacts={
                **cast(Dict[str, Any], (FUZZ_CONFIG_JOBS.snapshot(job_id) or snapshot)["artifacts"]),
                "instrumentedCodeZipPath": str(staged_zip),
                "instrumentedCodePath": str(instrumented_dir),
            },
        )
    except Exception as exc:
        LOGGER.exception("Fuzz configuration job %s failed", job_id)
        _append_log(log_file, f"ERROR: {exc}")
        FUZZ_CONFIG_JOBS.update(
            job_id,
            status="failed",
            stage="error",
            message="Fuzz configuration failed",
            error=str(exc),
        )


def _fuzz_config_docker_command(
    snapshot: Dict[str, Any],
    instrumented_dir: Path,
    bundle: Path,
) -> list[str]:
    env = _docker_env_flags(snapshot)
    command = [
        "docker",
        "run",
        "--rm",
        "--privileged",
        *_host_identity_flags(),
        *env,
        "-v",
        f"{instrumented_dir}:/workspace/instrumented_code:rw",
        "-v",
        f"{bundle}:/out/fuzz-bundle:rw",
        "protocolguard:latest",
        "fuzz-config",
        "--target-dir",
        "/workspace/instrumented_code",
        "--bundle-dir",
        "/out/fuzz-bundle",
        "--protocol",
        str(snapshot.get("protocol") or "UNKNOWN"),
    ]
    for implementation in snapshot.get("protocolImplementations") or []:
        if str(implementation).strip():
            command.extend(["--implementation", str(implementation)])
    return command


def _docker_env_flags(snapshot: Dict[str, Any]) -> list[str]:
    flags: list[str] = []
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "PG_CLAUDE_MODEL", "ANTHROPIC_MODEL"):
        value = os.environ.get(key)
        if value:
            flags.extend(["-e", f"{key}={value}"])
    implementations = snapshot.get("protocolImplementations") or []
    if isinstance(implementations, list) and implementations:
        flags.extend(["-e", "PG_FUZZ_IMPLEMENTATIONS=" + ",".join(str(item) for item in implementations)])
    notes = snapshot.get("notes")
    if isinstance(notes, str) and notes:
        flags.extend(["-e", f"PG_FUZZ_CONFIG_NOTES={notes}"])
    overrides = snapshot.get("runtimeOverrides")
    if isinstance(overrides, dict):
        env_names = {
            "targetArgs": "PG_FUZZ_TARGET_ARGS",
            "transport": "PG_FUZZ_TRANSPORT",
            "host": "PG_FUZZ_HOST",
            "port": "PG_FUZZ_PORT",
            "netSpec": "PG_FUZZ_NETSPEC",
        }
        for key, env_name in env_names.items():
            value = overrides.get(key)
            if value is not None and str(value).strip():
                flags.extend(["-e", f"{env_name}={value}"])
    return flags


def _pipe_process_stream(stream: Any, log_file: Path, stream_name: str) -> None:
    if stream is None:
        return
    for raw_line in stream:
        line = raw_line.rstrip("\n")
        if line:
            _append_log(log_file, f"[container:{stream_name}] {line}")


def _host_identity_flags() -> list[str]:
    return [
        "-e",
        f"PG_HOST_UID={_process_identity_value('PG_HOST_UID', os.getuid())}",
        "-e",
        f"PG_HOST_GID={_process_identity_value('PG_HOST_GID', os.getgid())}",
    ]


def _process_identity_value(env_name: str, fallback: int) -> str:
    configured = os.environ.get(env_name)
    if configured and configured.isdigit():
        return configured
    return str(fallback)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_root() -> Path:
    return Path(os.environ.get("PG_RUNTIME_ROOT", "/tmp/protocolguard")).expanduser()


def _config_workspace_root() -> Path:
    return Path(
        os.environ.get("PG_FUZZ_CONFIG_WORKSPACE_ROOT", _runtime_root() / "fuzz-config-workspaces")
    ).expanduser()


def _config_output_root() -> Path:
    return Path(
        os.environ.get("PG_FUZZ_CONFIG_OUTPUT_ROOT", _runtime_root() / "fuzz-config-jobs")
    ).expanduser()


def _job_log_file(snapshot: Dict[str, Any]) -> Path:
    artifacts = snapshot.get("artifacts")
    if isinstance(artifacts, dict):
        raw_path = artifacts.get("logFilePath")
        if isinstance(raw_path, str) and raw_path:
            return Path(raw_path)
    return _config_output_root() / str(snapshot["jobId"]) / "fuzz-config.log"


def _validate_or_existing_assert_zip(path: Path) -> Optional[str]:
    if path.exists() and path.is_file() and _is_path_inside(path, _allowed_instrumented_zip_roots()):
        return _validate_instrumented_code_zip(path)
    if path.exists() and path.is_file():
        try:
            with zipfile.ZipFile(path) as archive:
                if any(name.startswith("instrumented_code/") and not name.endswith("/") for name in archive.namelist()):
                    return None
        except zipfile.BadZipFile:
            return f"插桩源码压缩包不是有效 ZIP：{path}"
    return f"插桩源码压缩包不存在：{path}"


def _parse_protocol_implementations(data: Dict[str, Any]) -> list[str]:
    raw = data.get("protocolImplementations") or []
    return [
        str(item)
        for item in raw
        if isinstance(item, (int, str)) and str(item).strip()
    ]


def _parse_runtime_overrides(data: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[str]]:
    overrides: Dict[str, Any] = {}

    target_args = data.get("targetArgs")
    if target_args is not None:
        if not isinstance(target_args, list) or not all(
            isinstance(item, (int, str)) and str(item).strip() for item in target_args
        ):
            return {}, "targetArgs 必须是非空字符串数组"
        overrides["targetArgs"] = " ".join(str(item).strip() for item in target_args)

    for key in ("transport", "host", "netSpec"):
        value = data.get(key)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                return {}, f"{key} 必须是非空字符串"
            overrides[key] = value.strip()

    port = data.get("port")
    if port is not None:
        try:
            port_int = int(port)
        except (TypeError, ValueError):
            return {}, "port 必须是整数"
        if port_int <= 0 or port_int > 65535:
            return {}, "port 必须在 1 到 65535 之间"
        overrides["port"] = str(port_int)

    return overrides, None


def _infer_assert_generation_job_id(path: Path) -> str:
    parent_name = path.parent.name.strip()
    return f"debug:{parent_name}" if parent_name else "debug:instrumented-code"
