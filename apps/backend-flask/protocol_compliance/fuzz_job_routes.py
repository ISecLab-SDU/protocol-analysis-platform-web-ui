"""Artifact-backed fuzz job request handlers."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, cast

from flask import make_response, request

from utils.responses import error_response, success_response

from .assertion import get_assert_generation_job, get_assert_generation_result
from .aflnet import _aflnet_result_path_info, _aflnet_shell_command

LOGGER = logging.getLogger(__name__)


class FuzzJobRegistry:
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create(
        self,
        *,
        assert_generation_job_id: str,
        debug_source: Optional[str] = None,
        instrumented_code_zip_path: Path,
        notes: Optional[str],
        protocol: str,
        protocol_implementations: list[str],
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        workspace = _fuzz_workspace_root() / job_id
        output = _fuzz_output_root() / job_id
        job: Dict[str, Any] = {
            "jobId": job_id,
            "assertGenerationJobId": assert_generation_job_id,
            "status": "queued",
            "stage": "queued",
            "message": "Fuzz job queued",
            "createdAt": now,
            "updatedAt": now,
            "protocol": protocol,
            "protocolImplementations": protocol_implementations,
            "debugSource": debug_source,
            "notes": notes,
            "inputs": {
                "instrumentedCodeZipPath": str(instrumented_code_zip_path),
                "instrumentedCodeZipFileName": instrumented_code_zip_path.name,
            },
            "artifacts": {
                "fuzzWorkspacePath": str(workspace),
                "fuzzerLogFilePath": None,
                "outputPath": str(output),
                "logFilePath": str(output / "fuzz.log"),
            },
            "process": None,
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


FUZZ_JOBS = FuzzJobRegistry()


def create_fuzz_job_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
) -> Dict[str, Callable[..., Any]]:
    def start_fuzz_job():
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json(silent=True) or {}
        assert_generation_job_id = str(data.get("assertGenerationJobId") or "").strip()
        if not assert_generation_job_id:
            return make_response(error_response("缺少断言生成任务 ID"), 400)

        assert_snapshot = get_assert_generation_job(assert_generation_job_id)
        if not assert_snapshot:
            return make_response(error_response("未找到断言生成任务"), 404)
        if assert_snapshot.get("status") != "completed":
            return make_response(
                error_response("断言生成任务尚未完成", {"status": assert_snapshot.get("status")}),
                409,
            )

        assert_result = get_assert_generation_result(assert_generation_job_id)
        instrumented_zip = _instrumented_code_zip_path(assert_result)
        if instrumented_zip is None:
            return make_response(error_response("断言生成结果缺少插桩源码压缩包"), 400)
        if not instrumented_zip.exists() or not instrumented_zip.is_file():
            return make_response(error_response(f"插桩源码压缩包不存在：{instrumented_zip}"), 400)

        protocol = str(data.get("protocol") or "UNKNOWN").strip() or "UNKNOWN"
        protocol_implementations_raw = data.get("protocolImplementations") or []
        protocol_implementations = [
            str(item)
            for item in protocol_implementations_raw
            if isinstance(item, (int, str)) and str(item).strip()
        ]
        notes = data.get("notes")
        notes_text = notes.strip() if isinstance(notes, str) and notes.strip() else None

        snapshot = FUZZ_JOBS.create(
            assert_generation_job_id=assert_generation_job_id,
            instrumented_code_zip_path=instrumented_zip,
            notes=notes_text,
            protocol=protocol,
            protocol_implementations=protocol_implementations,
        )
        _prepare_and_launch_fuzz(snapshot["jobId"], instrumented_zip)
        return make_response(success_response(FUZZ_JOBS.snapshot(snapshot["jobId"])), 202)

    def start_dev_fuzz_job():
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json(silent=True) or {}
        requested_zip = data.get("instrumentedCodeZipPath")
        if isinstance(requested_zip, str) and requested_zip.strip():
            instrumented_zip = Path(requested_zip.strip()).expanduser()
        else:
            instrumented_zip = _latest_instrumented_code_zip()
            if instrumented_zip is None:
                return make_response(error_response("未找到可复用的插桩源码压缩包"), 404)

        zip_error = _validate_instrumented_code_zip(instrumented_zip)
        if zip_error:
            return make_response(error_response(zip_error), 400)

        protocol = str(data.get("protocol") or "MQTT").strip() or "MQTT"
        protocol_implementations = _parse_protocol_implementations(data)
        notes = data.get("notes")
        notes_text = notes.strip() if isinstance(notes, str) and notes.strip() else None
        assert_generation_job_id = str(data.get("assertGenerationJobId") or "").strip()
        if not assert_generation_job_id:
            assert_generation_job_id = _infer_assert_generation_job_id(instrumented_zip)

        snapshot = FUZZ_JOBS.create(
            assert_generation_job_id=assert_generation_job_id,
            debug_source="instrumentedCodeZipPath",
            instrumented_code_zip_path=instrumented_zip,
            notes=notes_text,
            protocol=protocol,
            protocol_implementations=protocol_implementations,
        )
        _prepare_and_launch_fuzz(snapshot["jobId"], instrumented_zip)
        return make_response(success_response(FUZZ_JOBS.snapshot(snapshot["jobId"])), 202)

    def get_fuzz_job(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error
        snapshot = FUZZ_JOBS.snapshot(job_id)
        if not snapshot:
            return make_response(error_response("未找到 Fuzz 任务"), 404)
        _refresh_process_state(snapshot)
        return make_response(success_response(FUZZ_JOBS.snapshot(job_id)), 200)

    def read_fuzz_logs(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error
        snapshot = FUZZ_JOBS.snapshot(job_id)
        if not snapshot:
            return make_response(error_response("未找到 Fuzz 任务"), 404)
        from_position_raw = request.args.get("fromPosition", "0")
        try:
            from_position = max(0, int(from_position_raw))
        except (TypeError, ValueError):
            from_position = 0
        payload = _read_job_log(snapshot, from_position)
        _refresh_process_state(snapshot)
        return make_response(success_response(payload), 200)

    def stop_fuzz_job(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error
        snapshot = FUZZ_JOBS.snapshot(job_id)
        if not snapshot:
            return make_response(error_response("未找到 Fuzz 任务"), 404)
        process = snapshot.get("process")
        if isinstance(process, dict):
            container_id = process.get("containerId")
            if isinstance(container_id, str) and container_id:
                _stop_container(container_id)
        FUZZ_JOBS.update(
            job_id,
            status="stopped",
            stage="stopped",
            message="Fuzz job stopped",
        )
        return make_response(success_response(FUZZ_JOBS.snapshot(job_id)), 200)

    return {
        "start_fuzz_job": start_fuzz_job,
        "start_dev_fuzz_job": start_dev_fuzz_job,
        "get_fuzz_job": get_fuzz_job,
        "read_fuzz_logs": read_fuzz_logs,
        "stop_fuzz_job": stop_fuzz_job,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_root() -> Path:
    return Path(os.environ.get("PG_RUNTIME_ROOT", "/tmp/protocolguard")).expanduser()


def _fuzz_workspace_root() -> Path:
    return Path(os.environ.get("PG_FUZZ_WORKSPACE_ROOT", _runtime_root() / "fuzz-workspaces")).expanduser()


def _fuzz_output_root() -> Path:
    return Path(os.environ.get("PG_FUZZ_OUTPUT_ROOT", _runtime_root() / "fuzz-jobs")).expanduser()


def _configured_output_root() -> Path:
    return Path(os.environ.get("PG_OUTPUT_ROOT", _runtime_root() / "outputs")).expanduser()


def _allowed_instrumented_zip_roots() -> list[Path]:
    roots = [
        _runtime_root(),
        _configured_output_root(),
        _fuzz_workspace_root(),
        _fuzz_output_root(),
    ]
    configured = os.environ.get("PG_FUZZ_DEBUG_ZIP_ROOTS")
    if configured:
        roots.extend(Path(item).expanduser() for item in configured.split(os.pathsep) if item.strip())

    deduped: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        try:
            resolved = root.expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def _instrumented_zip_discovery_roots() -> list[Path]:
    roots = [_configured_output_root()]
    configured = os.environ.get("PG_FUZZ_DEBUG_ZIP_ROOTS")
    if configured:
        roots.extend(Path(item).expanduser() for item in configured.split(os.pathsep) if item.strip())

    deduped: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        try:
            resolved = root.expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def _is_path_inside(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _latest_instrumented_code_zip() -> Optional[Path]:
    candidates: list[Path] = []
    for root in _instrumented_zip_discovery_roots():
        if not root.exists():
            continue
        candidates.extend(path for path in root.rglob("instrumented_code.zip") if path.is_file())
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _instrumented_code_zip_path(result: Optional[Dict[str, object]]) -> Optional[Path]:
    if not isinstance(result, dict):
        return None
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    raw_path = cast(Dict[str, object], artifacts).get("instrumentedCodeZipPath")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    return Path(raw_path).expanduser()


def _validate_instrumented_code_zip(path: Path) -> Optional[str]:
    if not _is_path_inside(path, _allowed_instrumented_zip_roots()):
        roots = ", ".join(str(root) for root in _allowed_instrumented_zip_roots())
        return f"插桩源码压缩包不在允许的调试目录内：{path}；允许目录：{roots}"
    if not path.exists() or not path.is_file():
        return f"插桩源码压缩包不存在：{path}"
    if path.name != "instrumented_code.zip":
        return f"插桩源码压缩包文件名应为 instrumented_code.zip：{path}"
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        return f"插桩源码压缩包不是有效 ZIP：{path}"
    if not any(name.startswith("instrumented_code/") and not name.endswith("/") for name in names):
        return f"插桩源码压缩包缺少 instrumented_code/ 内容：{path}"
    return None


def _infer_assert_generation_job_id(path: Path) -> str:
    parent_name = path.parent.name.strip()
    if parent_name:
        return f"debug:{parent_name}"
    return "debug:instrumented-code"


def _parse_protocol_implementations(data: Dict[str, Any]) -> list[str]:
    protocol_implementations_raw = data.get("protocolImplementations") or []
    return [
        str(item)
        for item in protocol_implementations_raw
        if isinstance(item, (int, str)) and str(item).strip()
    ]


def _prepare_and_launch_fuzz(job_id: str, instrumented_zip: Path) -> None:
    snapshot = FUZZ_JOBS.snapshot(job_id)
    if not snapshot:
        return
    artifacts = cast(Dict[str, str], snapshot["artifacts"])
    workspace = Path(artifacts["fuzzWorkspacePath"])
    output = Path(artifacts["outputPath"])
    inputs = workspace / "inputs"
    instrumented_dir = inputs / "instrumented_code"
    log_file = Path(artifacts["logFilePath"])

    try:
        FUZZ_JOBS.update(job_id, status="running", stage="workspace", message="Preparing fuzz workspace")
        inputs.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)
        staged_zip = inputs / "instrumented_code.zip"
        shutil.copy2(instrumented_zip, staged_zip)
        if instrumented_dir.exists():
            shutil.rmtree(instrumented_dir)
        instrumented_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(staged_zip) as archive:
            archive.extractall(instrumented_dir)

        FUZZ_JOBS.update(
            job_id,
            artifacts={
                **artifacts,
                "instrumentedCodeZipPath": str(staged_zip),
                "instrumentedCodePath": str(instrumented_dir),
            },
            message="Instrumented source package staged for fuzzing",
        )
        _append_log(log_file, f"Staged instrumented source zip: {staged_zip}")
        _append_log(log_file, f"Extracted instrumented source: {instrumented_dir}")

        command = _aflnet_shell_command(instrumented_dir)
        _append_log(log_file, f"Launching fuzzer command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or "Fuzzer command failed"
            raise RuntimeError(message)

        container_id = result.stdout.strip()
        result_info = _aflnet_result_path_info("primary")
        fuzzer_log_file = result_info.pop("logFilePath", None)
        FUZZ_JOBS.update(
            job_id,
            status="running",
            stage="running",
            message="Fuzz job running",
            process={"containerId": container_id or None, "pid": None, "command": command},
            artifacts={
                **cast(Dict[str, Any], FUZZ_JOBS.snapshot(job_id)["artifacts"]),
                **result_info,
                "fuzzerLogFilePath": fuzzer_log_file,
            },
        )
        _append_log(log_file, f"Fuzzer container started: {container_id or 'unknown'}")
    except Exception as exc:
        LOGGER.exception("Fuzz job %s failed to start", job_id)
        _append_log(log_file, f"ERROR: {exc}")
        FUZZ_JOBS.update(
            job_id,
            status="failed",
            stage="error",
            message="Fuzz job failed",
            error=str(exc),
        )


def _refresh_process_state(snapshot: Dict[str, Any]) -> None:
    if snapshot.get("status") != "running":
        return
    process = snapshot.get("process")
    if not isinstance(process, dict):
        return
    container_id = process.get("containerId")
    if not isinstance(container_id, str) or not container_id:
        return
    result = subprocess.run(
        f"docker ps -q --filter id={container_id}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return
    FUZZ_JOBS.update(
        str(snapshot["jobId"]),
        status="completed",
        stage="completed",
        message="Fuzz job container stopped",
    )


def _read_job_log(snapshot: Dict[str, Any], from_position: int) -> Dict[str, Any]:
    artifacts = snapshot.get("artifacts")
    artifact_data = cast(Dict[str, Any], artifacts)
    fuzzer_log = artifact_data.get("fuzzerLogFilePath")
    job_log = artifact_data.get("logFilePath")
    log_file = Path(str(fuzzer_log or job_log or ""))
    content = ""
    position = from_position
    if log_file.exists():
        with log_file.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(from_position)
            content = handle.read()
            position = handle.tell()
    payload = {
        "content": content,
        "position": position,
        "fileSize": log_file.stat().st_size if log_file.exists() else 0,
        "job": snapshot,
    }
    for key in (
        "fuzzerLogFilePath",
        "instrumentedCodePath",
        "instrumentedCodeZipPath",
        "logFilePath",
        "outputRoot",
        "pocPath",
        "outputSource",
        "isFallbackOutput",
    ):
        if key in artifact_data:
            payload[key] = artifact_data[key]
    payload["logFilePath"] = str(log_file) if str(log_file) else payload.get("logFilePath")
    return payload


def _append_log(log_file: Path, message: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%H:%M:%S")
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _stop_container(container_id: str) -> None:
    subprocess.run(
        ["docker", "stop", container_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
    )
