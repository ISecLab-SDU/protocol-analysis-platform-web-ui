"""Artifact-backed fuzz job request handlers."""

from __future__ import annotations

import logging
import json
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
DEBUG_REPLAY_INSTRUMENTED_CODE_ZIP_RELATIVE_PATH = Path(
    "replay/fuzz-startup-failed-after-instrumentation/latest/"
    "assertion-output/instrumented_code.zip"
)


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
        fuzz_config_job_id: Optional[str] = None,
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
            "fuzzConfigJobId": fuzz_config_job_id,
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
        fuzz_config_job_id = str(data.get("fuzzConfigJobId") or "").strip()
        if not fuzz_config_job_id:
            return make_response(error_response("缺少 Fuzz 配置任务 ID"), 400)

        from .fuzz_config_routes import completed_fuzz_config_job

        config_snapshot = completed_fuzz_config_job(fuzz_config_job_id)
        if not config_snapshot:
            return make_response(error_response("Fuzz 配置任务尚未完成或产物不可用"), 409)
        if config_snapshot.get("assertGenerationJobId") != assert_generation_job_id:
            return make_response(error_response("Fuzz 配置任务与断言生成任务不匹配"), 409)

        assert_snapshot = get_assert_generation_job(assert_generation_job_id)
        if not assert_snapshot:
            return make_response(error_response("未找到断言生成任务"), 404)
        if assert_snapshot.get("status") != "completed":
            return make_response(
                error_response(
                    "断言生成任务尚未完成", {"status": assert_snapshot.get("status")}
                ),
                409,
            )

        config_artifacts = cast(Dict[str, Any], config_snapshot.get("artifacts") or {})
        configured_zip = config_artifacts.get("instrumentedCodeZipPath")
        if isinstance(configured_zip, str) and configured_zip:
            instrumented_zip = Path(configured_zip).expanduser()
        else:
            instrumented_zip = _instrumented_code_zip_path(
                get_assert_generation_result(assert_generation_job_id)
            )
        if instrumented_zip is None:
            return make_response(error_response("断言生成结果缺少插桩源码压缩包"), 400)
        if not instrumented_zip.exists() or not instrumented_zip.is_file():
            return make_response(
                error_response(f"插桩源码压缩包不存在：{instrumented_zip}"), 400
            )

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
            fuzz_config_job_id=fuzz_config_job_id,
        )
        _prepare_and_launch_fuzz(snapshot["jobId"], instrumented_zip, config_snapshot)
        return make_response(
            success_response(FUZZ_JOBS.snapshot(snapshot["jobId"])), 202
        )

    def start_dev_fuzz_job():
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json(silent=True) or {}
        requested_zip = data.get("instrumentedCodeZipPath")
        if isinstance(requested_zip, str) and requested_zip.strip():
            instrumented_zip = Path(requested_zip.strip()).expanduser()
        else:
            instrumented_zip = (
                _debug_replay_instrumented_code_zip()
                or _latest_instrumented_code_zip()
            )
            if instrumented_zip is None:
                return make_response(
                    error_response("未找到可复用的插桩源码压缩包"), 404
                )

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
        return make_response(
            success_response(FUZZ_JOBS.snapshot(snapshot["jobId"])), 202
        )

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
        _refresh_process_state(FUZZ_JOBS.snapshot(job_id) or snapshot)
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
    return Path(
        os.environ.get("PG_FUZZ_WORKSPACE_ROOT", _runtime_root() / "fuzz-workspaces")
    ).expanduser()


def _fuzz_output_root() -> Path:
    return Path(
        os.environ.get("PG_FUZZ_OUTPUT_ROOT", _runtime_root() / "fuzz-jobs")
    ).expanduser()


def _configured_output_root() -> Path:
    return Path(
        os.environ.get("PG_OUTPUT_ROOT", _runtime_root() / "outputs")
    ).expanduser()


def _repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


def _allowed_instrumented_zip_roots() -> list[Path]:
    roots = [
        _runtime_root(),
        _configured_output_root(),
        _fuzz_workspace_root(),
        _fuzz_output_root(),
    ]
    debug_replay_zip = _configured_debug_replay_zip_path()
    if debug_replay_zip is not None:
        roots.append(debug_replay_zip.parent)
    configured = os.environ.get("PG_FUZZ_DEBUG_ZIP_ROOTS")
    if configured:
        roots.extend(
            Path(item).expanduser()
            for item in configured.split(os.pathsep)
            if item.strip()
        )

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


def _configured_debug_replay_zip_path() -> Optional[Path]:
    configured = os.environ.get("PG_FUZZ_DEBUG_REPLAY_ZIP_PATH")
    if configured is not None:
        if not configured.strip():
            return None
        return Path(configured.strip()).expanduser()
    sample_input_root = os.environ.get("PG_PROTOCOLGUARD_SAMPLE_INPUT_ROOT")
    if sample_input_root is not None and sample_input_root.strip():
        root = Path(sample_input_root.strip()).expanduser()
    else:
        root = _repository_root() / ".sample-input"
    return root / DEBUG_REPLAY_INSTRUMENTED_CODE_ZIP_RELATIVE_PATH


def _debug_replay_instrumented_code_zip() -> Optional[Path]:
    path = _configured_debug_replay_zip_path()
    if path is None:
        return None
    if not path.exists() or not path.is_file():
        return None
    return path


def _instrumented_zip_discovery_roots() -> list[Path]:
    roots = [_configured_output_root()]
    configured = os.environ.get("PG_FUZZ_DEBUG_ZIP_ROOTS")
    if configured:
        roots.extend(
            Path(item).expanduser()
            for item in configured.split(os.pathsep)
            if item.strip()
        )

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
        candidates.extend(
            path for path in root.rglob("instrumented_code.zip") if path.is_file()
        )
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
    if not any(
        name.startswith("instrumented_code/") and not name.endswith("/")
        for name in names
    ):
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


def _prepare_and_launch_fuzz(
    job_id: str,
    instrumented_zip: Path,
    config_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    snapshot = FUZZ_JOBS.snapshot(job_id)
    if not snapshot:
        return
    artifacts = cast(Dict[str, str], snapshot["artifacts"])
    workspace = Path(artifacts["fuzzWorkspacePath"])
    output = Path(artifacts["outputPath"])
    aflnet_output = output / "aflnet-output"
    inputs = workspace / "inputs"
    instrumented_dir = inputs / "instrumented_code"
    log_file = Path(artifacts["logFilePath"])

    try:
        FUZZ_JOBS.update(
            job_id,
            status="running",
            stage="workspace",
            message="Preparing fuzz workspace",
        )
        inputs.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)
        _append_log(log_file, f"Fuzz job {job_id} accepted")
        _append_log(log_file, f"Protocol: {snapshot.get('protocol') or 'UNKNOWN'}")
        _append_log(
            log_file,
            "Protocol implementations: "
            + ", ".join(cast(list[str], snapshot.get("protocolImplementations") or [])),
        )
        _append_log(log_file, f"Workspace: {workspace}")
        _append_log(log_file, f"Job output: {output}")
        _append_log(log_file, f"Job AFLNet output: {aflnet_output}")
        _append_log(log_file, f"Input instrumented source zip: {instrumented_zip}")
        _append_log(
            log_file,
            f"Input zip size: {_format_bytes(instrumented_zip.stat().st_size)}",
        )
        if aflnet_output.exists():
            shutil.rmtree(aflnet_output)
        aflnet_output.mkdir(parents=True, exist_ok=True)
        staged_zip = inputs / "instrumented_code.zip"
        shutil.copy2(instrumented_zip, staged_zip)
        if instrumented_dir.exists():
            shutil.rmtree(instrumented_dir)
        instrumented_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(staged_zip) as archive:
            archive_names = archive.namelist()
            archive.extractall(instrumented_dir)
        file_count = sum(1 for name in archive_names if name and not name.endswith("/"))

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
        _append_log(log_file, f"Extracted file count: {file_count}")
        _append_log(log_file, "Extracted source preview:")
        for line in _path_preview_lines(instrumented_dir, limit=24):
            _append_log(log_file, f"  {line}")

        bundle_dir: Optional[Path] = None
        runtime_env: Dict[str, str] = {}
        if config_snapshot:
            config_artifacts = cast(Dict[str, Any], config_snapshot.get("artifacts") or {})
            bundle_dir = Path(str(config_artifacts.get("bundlePath") or "")).expanduser()
            env_path = Path(str(config_artifacts.get("envPath") or "")).expanduser()
            if not bundle_dir.is_dir():
                raise RuntimeError(f"Fuzz configuration bundle missing: {bundle_dir}")
            if not env_path.is_file():
                raise RuntimeError(f"Fuzz configuration env missing: {env_path}")
            runtime_env = {
                str(key): str(value)
                for key, value in json.loads(env_path.read_text(encoding="utf-8")).items()
            }
            FUZZ_JOBS.update(
                job_id,
                artifacts={
                    **cast(Dict[str, Any], (FUZZ_JOBS.snapshot(job_id) or snapshot)["artifacts"]),
                    "fuzzBundlePath": str(bundle_dir),
                    "fuzzConfigManifestPath": str(config_artifacts.get("manifestPath") or ""),
                    "fuzzConfigEnvPath": str(env_path),
                },
            )
            _append_log(log_file, f"Using fuzz configuration job: {config_snapshot.get('jobId')}")
            _append_log(log_file, f"Fuzz bundle: {bundle_dir}")
            for key in sorted(runtime_env):
                _append_log(log_file, f"Runtime {key}: {runtime_env[key]}")

        command = _aflnet_shell_command(
            instrumented_dir if bundle_dir is None else None,
            bundle_dir=bundle_dir,
            runtime_env=runtime_env,
            output_root=aflnet_output,
        )
        _append_log(log_file, f"Launching fuzzer command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if result.stdout.strip():
            _append_log(log_file, f"docker run stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            _append_log(log_file, f"docker run stderr: {result.stderr.strip()}")
        if result.returncode != 0:
            message = result.stderr.strip() or "Fuzzer command failed"
            raise RuntimeError(message)

        container_id = result.stdout.strip()
        result_info = _aflnet_result_path_info("primary", output_root=aflnet_output)
        fuzzer_log_file = result_info.pop("logFilePath", None)
        _append_log(log_file, f"AFLNet output root: {result_info.get('outputRoot')}")
        _append_log(log_file, f"AFLNet plot_data path: {fuzzer_log_file}")
        _append_log(log_file, f"AFLNet POC path: {result_info.get('pocPath')}")
        FUZZ_JOBS.update(
            job_id,
            status="running",
            stage="running",
            message="Fuzz job running",
            process={
                "containerId": container_id or None,
                "dockerLogSeenEntries": [],
                "dockerLogSince": snapshot.get("createdAt"),
                "lastContainerStatus": None,
                "lastOutputSummary": None,
                "pid": None,
                "command": command,
            },
            artifacts={
                **cast(Dict[str, Any], (FUZZ_JOBS.snapshot(job_id) or snapshot)["artifacts"]),
                **result_info,
                "fuzzerLogFilePath": fuzzer_log_file,
                "fuzzerLogReadPosition": 0,
            },
        )
        _append_log(log_file, f"Fuzzer container started: {container_id or 'unknown'}")
        _append_log(log_file, "Waiting for Docker logs and AFLNet plot_data...")
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
    _sync_runtime_log_sources(snapshot)
    refreshed_snapshot = FUZZ_JOBS.snapshot(str(snapshot["jobId"])) or snapshot
    if refreshed_snapshot.get("status") != "running":
        return
    snapshot = refreshed_snapshot
    process = snapshot.get("process")
    if not isinstance(process, dict):
        return
    container_id = process.get("containerId")
    if not isinstance(container_id, str) or not container_id:
        return
    log_file = _job_log_file(snapshot)
    result = subprocess.run(
        f"docker ps -q --filter id={container_id}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return
    status = _container_status_line(container_id)
    _append_log(
        log_file, f"Fuzzer container is no longer running: {status or container_id}"
    )
    FUZZ_JOBS.update(
        str(snapshot["jobId"]),
        status="completed",
        stage="completed",
        message="Fuzz job container stopped",
    )


def _read_job_log(snapshot: Dict[str, Any], from_position: int) -> Dict[str, Any]:
    _sync_runtime_log_sources(snapshot)
    refreshed_snapshot = FUZZ_JOBS.snapshot(str(snapshot["jobId"])) or snapshot
    artifacts = refreshed_snapshot.get("artifacts")
    artifact_data = cast(Dict[str, Any], artifacts)
    job_log = artifact_data.get("logFilePath")
    log_file = Path(str(job_log or ""))
    content = ""
    position = from_position
    if log_file.exists():
        with log_file.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(from_position)
            content = handle.read()
            position = handle.tell()
    payload: Dict[str, Any] = {
        "content": content,
        "position": position,
        "fileSize": log_file.stat().st_size if log_file.exists() else 0,
        "job": refreshed_snapshot,
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
    payload["logFilePath"] = (
        str(log_file) if str(log_file) else payload.get("logFilePath")
    )
    return payload


def _sync_runtime_log_sources(snapshot: Dict[str, Any]) -> None:
    artifacts = snapshot.get("artifacts")
    if not isinstance(artifacts, dict):
        return

    job_id = str(snapshot["jobId"])
    artifact_data = cast(Dict[str, Any], artifacts)
    log_file = _job_log_file(snapshot)
    updates: Dict[str, Any] = {}
    artifact_updates: Dict[str, Any] = dict(artifact_data)

    process = snapshot.get("process")
    if isinstance(process, dict):
        process_updates = dict(process)
        docker_sync = _sync_docker_logs(log_file, process_updates)
        docker_log_count = docker_sync["line_count"]
        if docker_log_count is not None:
            process_updates["dockerLogLineCount"] = docker_log_count
        startup_error = docker_sync["startup_error"]
        if startup_error:
            process_updates["startupError"] = startup_error
            updates["status"] = "failed"
            updates["stage"] = "error"
            updates["message"] = "AFLNet startup failed"
            updates["error"] = startup_error
            _append_log(log_file, f"ERROR: AFLNet startup failed: {startup_error}")
        output_summary = _sync_output_directory_summary(
            log_file, artifact_data, process_updates
        )
        if output_summary:
            process_updates["lastOutputSummary"] = output_summary
        if process_updates != process:
            updates["process"] = process_updates

    fuzzer_position = _sync_fuzzer_log_file(log_file, artifact_updates)
    if fuzzer_position is not None:
        artifact_updates["fuzzerLogReadPosition"] = fuzzer_position

    if artifact_updates != artifact_data:
        updates["artifacts"] = artifact_updates
    if updates:
        FUZZ_JOBS.update(job_id, **updates)


def _sync_docker_logs(log_file: Path, process: Dict[str, Any]) -> Dict[str, Any]:
    container_id = process.get("containerId")
    if not isinstance(container_id, str) or not container_id:
        return {"line_count": None, "startup_error": None}

    since = str(process.get("dockerLogSince") or "1970-01-01T00:00:00Z")
    sync_started_at = _docker_timestamp_now()
    result = subprocess.run(
        ["docker", "logs", "--timestamps", "--since", since, container_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        if message and process.get("lastDockerLogError") != message:
            _append_log(log_file, f"Docker log read failed: {message}")
            process["lastDockerLogError"] = message
        return {
            "line_count": _coerce_int(process.get("dockerLogLineCount")),
            "startup_error": None,
        }

    seen_entries = _coerce_str_list(process.get("dockerLogSeenEntries"))
    new_entries: list[tuple[str, str]] = []
    next_seen_entries = list(seen_entries)
    for stream, content in (("stdout", result.stdout), ("stderr", result.stderr)):
        for raw_line in _split_lines(content):
            if raw_line in seen_entries:
                continue
            new_entries.append((stream, raw_line))
            next_seen_entries.append(raw_line)

    if new_entries:
        stdout_count = sum(1 for stream, _line in new_entries if stream == "stdout")
        stderr_count = len(new_entries) - stdout_count
        _append_log(
            log_file,
            (
                "Synced Docker container logs: "
                f"{stdout_count} stdout line(s), {stderr_count} stderr line(s)"
            ),
        )
        for stream, raw_line in new_entries:
            _append_log(
                log_file, f"[container:{stream}] {_strip_docker_timestamp(raw_line)}"
            )

    startup_error = _detect_aflnet_startup_error(
        _strip_docker_timestamp(raw_line) for _stream, raw_line in new_entries
    )
    process["dockerLogSince"] = sync_started_at
    process["dockerLogSeenEntries"] = next_seen_entries[-200:]
    process["dockerLogLineCount"] = _coerce_int(
        process.get("dockerLogLineCount")
    ) + len(new_entries)
    return {
        "line_count": _coerce_int(process.get("dockerLogLineCount")),
        "startup_error": startup_error,
    }


def _detect_aflnet_startup_error(lines: Any) -> Optional[str]:
    for line in lines:
        normalized = str(line).strip()
        if not normalized:
            continue
        if (
            "PROGRAM ABORT" in normalized
            or "PG_FUZZ_INSTRUMENTED_CODE_DIR is set" in normalized
            or "The fuzzer cannot infer how to build or launch" in normalized
            or "Seed corpus directory" in normalized
            or "Target binary not found" in normalized
            or "AFLNet binary not found" in normalized
        ):
            return normalized
    return None


def _sync_fuzzer_log_file(
    log_file: Path, artifact_data: Dict[str, Any]
) -> Optional[int]:
    fuzzer_log = artifact_data.get("fuzzerLogFilePath")
    if not isinstance(fuzzer_log, str) or not fuzzer_log:
        return None
    fuzzer_log_path = Path(fuzzer_log)
    position = _coerce_int(artifact_data.get("fuzzerLogReadPosition"))
    if not fuzzer_log_path.exists():
        if not artifact_data.get("fuzzerLogMissingReported"):
            _append_log(
                log_file, f"AFLNet plot_data not created yet: {fuzzer_log_path}"
            )
            artifact_data["fuzzerLogMissingReported"] = True
        return position

    if artifact_data.get("fuzzerLogMissingReported"):
        _append_log(log_file, f"AFLNet plot_data detected: {fuzzer_log_path}")
        artifact_data["fuzzerLogMissingReported"] = False

    try:
        with fuzzer_log_path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(position)
            content = handle.read()
            new_position = handle.tell()
    except OSError as exc:
        _append_log(log_file, f"Failed to read AFLNet plot_data: {exc}")
        return position

    if content:
        lines = [line for line in content.splitlines() if line.strip()]
        if lines:
            _append_log(log_file, f"AFLNet plot_data emitted {len(lines)} new line(s)")
            for line in lines:
                _append_log(log_file, f"[plot_data] {line}")
    return new_position


def _sync_output_directory_summary(
    log_file: Path,
    artifact_data: Dict[str, Any],
    process: Dict[str, Any],
) -> Optional[str]:
    output_root = artifact_data.get("outputRoot")
    if not isinstance(output_root, str) or not output_root:
        return None
    output_path = Path(output_root)
    if not output_path.exists():
        return None

    entries = _interesting_output_entries(output_path)
    summary = ", ".join(entries) if entries else "empty"
    if process.get("lastOutputSummary") == summary:
        return summary
    _append_log(log_file, f"AFLNet output snapshot: {summary}")
    return summary


def _interesting_output_entries(output_root: Path) -> list[str]:
    names = [
        "plot_data",
        "fuzzer_stats",
        "replayable-crashes",
        "crashes",
        "crash",
        "crash_logs",
        "hangs",
        "queue",
    ]
    entries: list[str] = []
    for name in names:
        path = output_root / name
        if not path.exists():
            continue
        if path.is_dir():
            count = sum(1 for child in path.iterdir() if not child.name.startswith("."))
            entries.append(f"{name}/ ({count} item{'s' if count != 1 else ''})")
        else:
            entries.append(f"{name} ({_format_bytes(path.stat().st_size)})")
    return entries


def _job_log_file(snapshot: Dict[str, Any]) -> Path:
    artifacts = snapshot.get("artifacts")
    if isinstance(artifacts, dict):
        raw_path = artifacts.get("logFilePath")
        if isinstance(raw_path, str) and raw_path:
            return Path(raw_path)
    return _fuzz_output_root() / str(snapshot["jobId"]) / "fuzz.log"


def _append_log(log_file: Path, message: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%H:%M:%S")
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")
    _emit_backend_log(log_file, message)


def _emit_backend_log(log_file: Path, message: str) -> None:
    job_id = log_file.parent.name if log_file.name == "fuzz.log" else "unknown"
    level = logging.INFO
    if message.startswith("ERROR:") or " failed" in message.lower():
        level = logging.ERROR
    elif "warn" in message.lower() or "not created yet" in message.lower():
        level = logging.WARNING
    LOGGER.log(
        level,
        "[job %s][fuzz] %s",
        job_id,
        message,
        extra={
            "protocolguard_context": {
                "job_id": job_id,
                "stage": "fuzz",
                "log_file": str(log_file),
            }
        },
    )


def _split_lines(value: str) -> list[str]:
    return [line for line in value.splitlines() if line.strip()]


def _coerce_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _coerce_int(value: object) -> int:
    if value is None:
        return 0
    if not isinstance(value, (int, float, str)):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _docker_timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _strip_docker_timestamp(line: str) -> str:
    timestamp, separator, message = line.partition(" ")
    if separator and timestamp.endswith("Z") and "T" in timestamp:
        return message
    return line


def _format_bytes(size: int) -> str:
    units = ("B", "KB", "MB", "GB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _path_preview_lines(root: Path, *, limit: int) -> list[str]:
    if not root.exists():
        return ["<missing>"]
    lines: list[str] = []
    for child in sorted(root.rglob("*")):
        if len(lines) >= limit:
            lines.append("...")
            break
        try:
            relative = child.relative_to(root)
        except ValueError:
            continue
        suffix = "/" if child.is_dir() else f" ({_format_bytes(child.stat().st_size)})"
        lines.append(f"{relative.as_posix()}{suffix}")
    return lines or ["<empty>"]


def _container_status_line(container_id: str) -> Optional[str]:
    result = subprocess.run(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"id={container_id}",
            "--format",
            "{{.ID}} {{.Status}}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        message = result.stderr.strip()
        return message or None
    return result.stdout.strip() or None


def _stop_container(container_id: str) -> None:
    subprocess.run(
        ["docker", "stop", container_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
    )
