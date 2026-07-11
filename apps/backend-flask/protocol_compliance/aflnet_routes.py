"""AFLNet artifact request handlers."""

from __future__ import annotations

import contextlib
import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from flask import make_response, request, send_file

from utils.responses import error_response, success_response

from .aflnet import (
    _aflnet_artifact_root,
    _aflnet_output_root_for_source,
    _is_path_inside,
    _resolve_aflnet_archive_source,
    _write_aflnet_poc_archive,
)


def create_aflnet_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
) -> Dict[str, Callable[..., Any]]:
    def download_aflnet_result():
        """Download AFLNET crash/queue artefacts as a zip bundle."""
        _, error = ensure_authenticated()
        if error:
            return error

        protocol = request.args.get("protocol") or "MQTT"
        implementation = request.args.get("implementation") or "SOL"
        crash_log_path = request.args.get("crashLogPath")
        output_source = _resolve_aflnet_archive_source(
            crash_log_path,
            request.args.get("outputSource"),
        )

        output_root = _aflnet_output_root_for_source(output_source).expanduser()
        if not output_root.exists() or not output_root.is_dir():
            return make_response(
                error_response(f"AFLNET 输出目录不存在：{output_root}"),
                404,
            )

        buffer = io.BytesIO()
        added = _write_aflnet_poc_archive(
            buffer,
            artifact_id=None,
            crash_log_path=crash_log_path,
            implementation=implementation,
            output_root=output_root,
            protocol=protocol,
        )

        if added <= 1:
            return make_response(error_response("AFLNET 输出目录中没有可打包的 POC 文件"), 404)

        buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_impl = re.sub(r"[^A-Za-z0-9_.-]+", "-", implementation).strip("-") or "aflnet"
        return send_file(
            buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{safe_impl}-aflnet-poc-{timestamp}.zip",
            max_age=0,
        )

    def snapshot_aflnet_result():
        """Persist the current AFLNET POC bundle for history downloads."""
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json(silent=True) or {}
        protocol = data.get("protocol") or "MQTT"
        implementation = data.get("implementation") or "SOL"
        crash_log_path = data.get("crashLogPath")
        output_source = _resolve_aflnet_archive_source(
            crash_log_path,
            data.get("outputSource") or data.get("output_source"),
        )

        output_root = _aflnet_output_root_for_source(output_source).expanduser()
        if not output_root.exists() or not output_root.is_dir():
            return make_response(
                error_response(f"AFLNET 输出目录不存在：{output_root}"),
                404,
            )

        artifact_id = f"aflnet-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        artifact_dir = (_aflnet_artifact_root() / artifact_id).resolve()
        artifact_dir.mkdir(parents=True, exist_ok=False)
        zip_path = artifact_dir / "poc.zip"

        added = _write_aflnet_poc_archive(
            zip_path,
            artifact_id=artifact_id,
            crash_log_path=crash_log_path,
            implementation=implementation,
            output_root=output_root,
            protocol=protocol,
        )

        if added <= 1:
            with contextlib.suppress(OSError):
                zip_path.unlink()
            with contextlib.suppress(OSError):
                artifact_dir.rmdir()
            return make_response(error_response("AFLNET 输出目录中没有可归档的 POC 文件"), 404)

        file_size = zip_path.stat().st_size
        return success_response({
            "artifactId": artifact_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "downloadUrl": f"/protocol-compliance/fuzzing/aflnet-result/artifacts/{artifact_id}/download",
            "fileSize": file_size,
        })

    def download_aflnet_result_artifact(artifact_id: str):
        """Download a persisted AFLNET POC artifact."""
        _, error = ensure_authenticated()
        if error:
            return error

        if not re.fullmatch(r"[A-Za-z0-9_.-]+", artifact_id):
            return make_response(error_response("POC artifact id 非法"), 400)

        artifact_root = _aflnet_artifact_root().resolve()
        zip_path = (artifact_root / artifact_id / "poc.zip").resolve()
        if not _is_path_inside(zip_path, [artifact_root]) or not zip_path.is_file():
            return make_response(error_response("POC artifact 不存在或已过期"), 404)

        return send_file(
            zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{artifact_id}.zip",
            max_age=0,
        )

    return {
        "download_aflnet_result": download_aflnet_result,
        "snapshot_aflnet_result": snapshot_aflnet_result,
        "download_aflnet_result_artifact": download_aflnet_result_artifact,
    }
