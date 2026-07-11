"""Static-analysis submission and job history route registration."""

from __future__ import annotations

import json
import logging
from typing import Callable, Optional, cast

from flask import Blueprint, make_response, request
from werkzeug.datastructures import FileStorage

from utils.responses import error_response, success_response

from .analysis import (
    delete_static_analysis_job,
    extract_protocol_version,
    normalize_protocol_name,
    submit_static_analysis_job,
    try_extract_rules_summary,
)

LOGGER = logging.getLogger(__name__)


def register_static_analysis_submission_routes(
    bp: Blueprint,
    ensure_authenticated: Callable[[], tuple[object, object]],
    *,
    extract_protocol_metadata_from_config: Callable[
        [Optional[bytes], Optional[str]],
        tuple[Optional[str], Optional[str]],
    ],
    list_static_analysis_history: Callable[..., list[dict[str, object]]],
    read_upload: Callable[[FileStorage], tuple[str, Optional[bytes]]],
    strip_extension: Callable[[str], str],
    to_int: Callable[[object, int], int],
) -> dict[str, Callable[..., object]]:
    @bp.route("/static-analysis", methods=["POST"])
    def static_analysis():
        _, error = ensure_authenticated()
        if error:
            return error

        if not request.files:
            return make_response(
                error_response("请上传源码、协议规则和配置文件"), 400
            )

        uploads_map = {
            "codeArchive": request.files.get("codeArchive"),
            "rules": request.files.get("rules"),
            "config": request.files.get("config"),
        }

        required_missing = [
            key for key, value in uploads_map.items()
            if not isinstance(value, FileStorage)
        ]
        if required_missing:
            labels = {
                "codeArchive": "源码压缩包",
                "rules": "协议规则 JSON",
                "config": "分析配置 TOML",
            }
            readable = "、".join(labels.get(item, item) for item in required_missing)
            return make_response(
                error_response(f"请上传完整文件：{readable}"), 400
            )

        code_upload = cast(FileStorage, uploads_map["codeArchive"])
        rules_upload = cast(FileStorage, uploads_map["rules"])
        config_upload = cast(FileStorage, uploads_map["config"])

        code_name, code_data = read_upload(code_upload)
        rules_name, rules_data = read_upload(rules_upload)
        config_name, config_data = read_upload(config_upload)

        if code_data is None or config_data is None or rules_data is None:
            return make_response(error_response("上传的文件内容为空，请重新上传"), 400)

        parsed_rules = None
        if rules_data:
            try:
                parsed_rules = json.loads(rules_data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed_rules = None

        config_protocol_name, config_protocol_version = extract_protocol_metadata_from_config(
            config_data,
            config_name,
        )

        rules_protocol_fallback = normalize_protocol_name(
            parsed_rules,
            strip_extension(rules_name),
        )
        protocol_name = config_protocol_name or rules_protocol_fallback
        if config_protocol_name:
            LOGGER.info(
                "Static analysis protocol resolved from config %s: %s",
                config_name,
                config_protocol_name,
            )
        else:
            LOGGER.info(
                "Static analysis protocol falling back to %s (config %s missing protocol_name)",
                rules_protocol_fallback,
                config_name,
            )

        rules_version_fallback = extract_protocol_version(parsed_rules, None)
        protocol_version = config_protocol_version or rules_version_fallback
        if config_protocol_version:
            LOGGER.info(
                "Static analysis protocol version resolved from config %s: %s",
                config_name,
                config_protocol_version,
            )
        elif rules_version_fallback:
            LOGGER.info(
                "Static analysis protocol version falling back to %s (config %s missing protocol_version)",
                rules_version_fallback,
                config_name,
            )
        rules_summary = try_extract_rules_summary(parsed_rules)
        notes = request.form.get("notes")

        snapshot = submit_static_analysis_job(
            code_payload=(code_name, code_data),
            config_payload=(config_name, config_data),
            rules_payload=(rules_name, rules_data),
            notes=notes,
            protocol_name=protocol_name,
            protocol_version=protocol_version,
            rules_summary=rules_summary,
        )
        return make_response(success_response(snapshot), 202)

    @bp.route("/static-analysis/history", methods=["GET"])
    def static_analysis_history():
        _, error = ensure_authenticated()
        if error:
            return error

        limit = to_int(request.args.get("limit"), 50)
        limit = max(1, min(limit, 200))
        history = list_static_analysis_history(limit=limit)
        payload = success_response({"items": history, "limit": limit, "count": len(history)})
        return make_response(payload, 200)

    @bp.route("/static-analysis/history/<job_id>", methods=["DELETE"])
    def delete_static_analysis_history(job_id: str):
        """Delete a static analysis job from the history."""
        _, error = ensure_authenticated()
        if error:
            return error

        if not job_id or not isinstance(job_id, str):
            return make_response(error_response("无效的任务 ID"), 400)

        try:
            deleted = delete_static_analysis_job(job_id)
            if not deleted:
                return make_response(error_response("任务不存在"), 404)
            return make_response(success_response({"jobId": job_id, "deleted": True}), 200)
        except Exception as exc:
            LOGGER.exception("Failed to delete static analysis job %s", job_id)
            return make_response(error_response(f"删除失败：{str(exc)}"), 500)

    return {
        "static_analysis": static_analysis,
        "static_analysis_history": static_analysis_history,
        "delete_static_analysis_history": delete_static_analysis_history,
    }
