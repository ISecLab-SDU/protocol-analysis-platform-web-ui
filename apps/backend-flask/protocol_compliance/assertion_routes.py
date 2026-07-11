"""Assertion-generation request handlers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Dict, Optional, cast

from flask import make_response, request, send_file
from werkzeug.datastructures import FileStorage

from utils.responses import error_response, success_response

from .assertion import (
    get_assert_generation_job,
    get_assert_generation_result,
    get_assert_generation_zip_path,
    get_diff_parsing_job,
    get_diff_parsing_result,
    submit_assert_generation_job,
    submit_diff_parsing_job,
)

LOGGER = logging.getLogger(__name__)


def create_assertion_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
    expand_path: Callable[[Optional[str]], Optional[Path]],
    read_upload: Callable[[FileStorage], tuple[str, Optional[bytes]]],
    resolve_assertion_database_path: Callable[[Path], tuple[Optional[Path], list[str]]],
) -> Dict[str, Callable[..., object]]:
    def assertion_generation():
        _, error = ensure_authenticated()
        if error:
            return error

        if not request.files:
            return make_response(error_response("请上传源码压缩包"), 400)

        code_upload_raw = request.files.get("codeArchive")
        if not isinstance(code_upload_raw, FileStorage):
            return make_response(error_response("请上传完整文件：源码压缩包"), 400)

        code_name, code_data = read_upload(code_upload_raw)

        database_path_requested = request.form.get("databasePath")
        database_source = "upload"
        if database_path_requested:
            database_path = expand_path(database_path_requested)
            if database_path is None:
                return make_response(error_response("分析结果数据路径无效"), 400)
            resolved_database_path, database_warnings = resolve_assertion_database_path(database_path)
            if resolved_database_path is None:
                return make_response(
                    error_response(f"分析结果数据不存在：{database_path}"),
                    400,
                )
            if database_warnings:
                LOGGER.warning(
                    "Resolved assertion analysis data with fallback",
                    extra={
                        "requestedDatabasePath": str(database_path),
                        "resolvedDatabasePath": str(resolved_database_path),
                        "warnings": database_warnings,
                    },
                )
            database_path = resolved_database_path
            try:
                database_data = database_path.read_bytes()
            except OSError as exc:
                LOGGER.exception("Failed to read assertion analysis data: %s", database_path)
                return make_response(error_response(f"读取分析结果数据失败：{exc}"), 500)
            database_name = database_path.name
            database_source = str(database_path)
        else:
            database_upload_raw = request.files.get("database")
            if not isinstance(database_upload_raw, FileStorage):
                return make_response(error_response("请上传完整文件：分析结果数据文件"), 400)
            database_name, database_data = read_upload(database_upload_raw)

        if not code_data or not database_data:
            return make_response(error_response("上传的文件内容为空，请重新上传"), 400)

        build_instructions_raw = request.form.get("buildInstructions", "")
        notes = request.form.get("notes")

        LOGGER.info(
            "Assertion generation job requested",
            extra={
                "codeArchive": code_name,
                "database": database_name,
                "databaseSource": database_source,
                "hasBuildInstructions": bool(build_instructions_raw.strip()),
                "notesLength": len(notes.strip()) if isinstance(notes, str) else 0,
            },
        )

        snapshot = submit_assert_generation_job(
            code_payload=(code_name, code_data),
            database_payload=(database_name, database_data),
            build_instructions=build_instructions_raw,
            notes=notes,
        )
        return make_response(success_response(snapshot), 202)

    def assertion_generation_progress(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        snapshot = get_assert_generation_job(job_id)
        if not snapshot:
            return make_response(error_response("未找到断言生成任务"), 404)
        return make_response(success_response(snapshot), 200)

    def assertion_generation_result(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        result = get_assert_generation_result(job_id)
        if result is None:
            snapshot = get_assert_generation_job(job_id)
            if not snapshot:
                return make_response(error_response("未找到断言生成任务"), 404)
            status = snapshot.get("status")
            return make_response(
                error_response("断言生成任务尚未完成", {"status": status}),
                409,
            )
        return make_response(success_response(result), 200)

    def assertion_generation_download(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        snapshot = get_assert_generation_job(job_id)
        if not snapshot:
            return make_response(error_response("未找到断言生成任务"), 404)

        if snapshot.get("status") != "completed":
            return make_response(
                error_response("断言生成任务尚未完成", {"status": snapshot.get("status")}),
                409,
            )

        zip_path = get_assert_generation_zip_path(job_id)
        if not zip_path:
            return make_response(error_response("未找到断言生成结果压缩包"), 404)

        download_name = f"assertion-generation-{job_id}.zip"
        return send_file(
            zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=download_name,
            max_age=0,
        )

    def assertion_generation_instrumentation_diff(job_id: str):
        """Fetch the instrumentation diff for a completed assertion generation job."""
        _, error = ensure_authenticated()
        if error:
            return error

        result = get_assert_generation_result(job_id)
        if result is None:
            snapshot = get_assert_generation_job(job_id)
            if not snapshot:
                return make_response(error_response("未找到断言生成任务"), 404)
            status = snapshot.get("status")
            return make_response(
                error_response("断言生成任务尚未完成", {"status": status}),
                409,
            )

        instrumentation = result.get("instrumentation")
        if not instrumentation or not isinstance(instrumentation, dict):
            return make_response(error_response("未找到 instrumentation 数据"), 404)

        instrumentation_data = cast(Dict[str, object], instrumentation)
        artifacts = instrumentation_data.get("artifacts")
        if not artifacts or not isinstance(artifacts, dict):
            return make_response(error_response("未找到 instrumentation artifacts"), 404)

        artifact_data = cast(Dict[str, object], artifacts)
        diff_output = artifact_data.get("diffOutput")
        if not diff_output or not isinstance(diff_output, dict):
            return make_response(error_response("未找到 instrumentation diff 输出"), 404)

        return make_response(success_response(diff_output), 200)

    def start_diff_parsing(assert_job_id: str):
        """Start diff parsing for a completed assertion generation job."""
        _, error = ensure_authenticated()
        if error:
            return error

        assert_snapshot = get_assert_generation_job(assert_job_id)
        if not assert_snapshot:
            return make_response(error_response("未找到断言生成任务"), 404)

        if assert_snapshot.get("status") != "completed":
            return make_response(
                error_response(
                    "断言生成任务尚未完成，无法开始差异解析",
                    {"status": assert_snapshot.get("status")},
                ),
                409,
            )

        LOGGER.info(
            "Diff parsing job requested",
            extra={
                "parentJobId": assert_job_id,
            },
        )

        snapshot = submit_diff_parsing_job(assert_job_id)
        return make_response(success_response(snapshot), 202)

    def diff_parsing_progress(assert_job_id: str, diff_job_id: str):
        """Get progress of a diff parsing job."""
        _, error = ensure_authenticated()
        if error:
            return error

        snapshot = get_diff_parsing_job(diff_job_id)
        if not snapshot:
            return make_response(error_response("未找到差异解析任务"), 404)

        if snapshot.get("parentJobId") != assert_job_id:
            return make_response(
                error_response("差异解析任务与指定的断言生成任务不匹配"),
                400,
            )

        return make_response(success_response(snapshot), 200)

    def diff_parsing_result(assert_job_id: str, diff_job_id: str):
        """Get result of a completed diff parsing job."""
        _, error = ensure_authenticated()
        if error:
            return error

        result = get_diff_parsing_result(diff_job_id)
        if result is None:
            snapshot = get_diff_parsing_job(diff_job_id)
            if not snapshot:
                return make_response(error_response("未找到差异解析任务"), 404)

            if snapshot.get("parentJobId") != assert_job_id:
                return make_response(
                    error_response("差异解析任务与指定的断言生成任务不匹配"),
                    400,
                )

            status = snapshot.get("status")
            return make_response(
                error_response("差异解析任务尚未完成", {"status": status}),
                409,
            )

        return make_response(success_response(result), 200)

    return {
        "assertion_generation": assertion_generation,
        "assertion_generation_progress": assertion_generation_progress,
        "assertion_generation_result": assertion_generation_result,
        "assertion_generation_download": assertion_generation_download,
        "assertion_generation_instrumentation_diff": assertion_generation_instrumentation_diff,
        "start_diff_parsing": start_diff_parsing,
        "diff_parsing_progress": diff_parsing_progress,
        "diff_parsing_result": diff_parsing_result,
    }
