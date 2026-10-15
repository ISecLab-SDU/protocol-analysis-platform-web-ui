"""Static-analysis submission and job history request handlers."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional, cast

from flask import make_response, request
from werkzeug.datastructures import FileStorage

from utils.responses import error_response, success_response

from .analysis import (
    delete_static_analysis_job,
    extract_protocol_version,
    normalize_protocol_name,
    try_extract_rules_summary,
)

from .rules_input import canonical_protocol, validate_rules

LOGGER = logging.getLogger(__name__)


def create_static_analysis_submission_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
    *,
    extract_protocol_metadata_from_config: Callable[
        [Optional[bytes], Optional[str]],
        tuple[Optional[str], Optional[str]],
    ],
    list_static_analysis_history: Callable[..., list[dict[str, object]]],
    read_upload: Callable[[FileStorage], tuple[str, Optional[bytes]]],
    strip_extension: Callable[[str], str],
    submit_static_analysis_job: Callable[..., dict[str, object]],
    to_int: Callable[[object, int], int],
) -> dict[str, Callable[..., Any]]:
    def static_analysis():
        _, error = ensure_authenticated()
        if error:
            return error

        if not request.files:
            return make_response(error_response("请上传源码、协议规则和配置文件"), 400)

        uploads_map = {
            "codeArchive": request.files.get("codeArchive"),
            "rules": request.files.get("rules"),
        }

        required_missing = [
            key
            for key, value in uploads_map.items()
            if not isinstance(value, FileStorage)
        ]
        if required_missing:
            labels = {
                "codeArchive": "源码压缩包",
                "rules": "协议规则 JSON",
            }
            readable = "、".join(labels.get(item, item) for item in required_missing)
            return make_response(error_response(f"请上传完整文件：{readable}"), 400)

        code_upload = cast(FileStorage, uploads_map["codeArchive"])
        rules_upload = cast(FileStorage, uploads_map["rules"])
        config_upload = request.files.get("config")

        code_name, code_data = read_upload(code_upload)
        rules_name, rules_data = read_upload(rules_upload)
        if isinstance(config_upload, FileStorage):
            config_name, config_data = read_upload(config_upload)
        else:
            config_name, config_data = "generated-config.toml", None

        if code_data is None or rules_data is None:
            return make_response(error_response("上传的文件内容为空，请重新上传"), 400)
        if isinstance(config_upload, FileStorage) and config_data is None:
            return make_response(
                error_response("上传的配置文件内容为空，请重新上传"), 400
            )

        try:
            parsed_rules = json.loads((rules_data or b"").decode("utf-8"))
            normalized_rules = validate_rules(parsed_rules)
            inferred_protocol = normalize_protocol_name(parsed_rules, "")
            inferred_version = extract_protocol_version(parsed_rules, None)
        except (ValueError, UnicodeDecodeError) as exc:
            return make_response(error_response(f"Invalid rules JSON: {exc}"), 400)

        if config_data is not None:
            config_protocol_name, config_protocol_version = (
                extract_protocol_metadata_from_config(
                    config_data,
                    config_name,
                )
            )
        else:
            config_protocol_name, config_protocol_version = None, None

        form_protocol_name = (request.form.get("protocolName") or "").strip() or None
        try:
            fallback = inferred_protocol
            if not fallback:
                try:
                    fallback = canonical_protocol(strip_extension(rules_name))
                except ValueError:
                    pass
            candidates = [
                name
                for name in (
                    form_protocol_name,
                    config_protocol_name,
                    inferred_protocol,
                )
                if name
            ]
            names = {canonical_protocol(name) for name in candidates}
            if len(names) > 1:
                raise ValueError("Protocol in request/config conflicts with rules JSON")
            protocol_name = canonical_protocol(
                form_protocol_name or config_protocol_name or fallback or ""
            )
        except ValueError as exc:
            return make_response(
                error_response(f"Cannot resolve analysis protocol: {exc}"), 400
            )
        rules_protocol_fallback = protocol_name
        if config_protocol_name:
            LOGGER.info(
                "Static analysis protocol resolved from config %s: %s",
                config_name,
                config_protocol_name,
            )
        elif form_protocol_name:
            LOGGER.info(
                "Static analysis protocol resolved from request form: %s",
                form_protocol_name,
            )
        else:
            LOGGER.info(
                "Static analysis protocol falling back to %s (config %s missing protocol_name)",
                rules_protocol_fallback,
                config_name,
            )

        rules_version_fallback = inferred_version
        form_protocol_version = (
            request.form.get("protocolVersion") or ""
        ).strip() or None
        protocol_version = (
            form_protocol_version or config_protocol_version or rules_version_fallback
        )
        if config_protocol_version:
            LOGGER.info(
                "Static analysis protocol version resolved from config %s: %s",
                config_name,
                config_protocol_version,
            )
        elif form_protocol_version:
            LOGGER.info(
                "Static analysis protocol version resolved from request form: %s",
                form_protocol_version,
            )
        elif rules_version_fallback:
            LOGGER.info(
                "Static analysis protocol version falling back to %s (config %s missing protocol_version)",
                rules_version_fallback,
                config_name,
            )
        if protocol_name == "DHCP" and protocol_version not in {"4", "6"}:
            return make_response(
                error_response("DHCP analysis requires protocolVersion 4 or 6"), 400
            )
        rules_summary = try_extract_rules_summary(parsed_rules)
        notes = request.form.get("notes")
        project_name = (
            request.form.get("projectName")
            or request.form.get("implementationName")
            or ""
        ).strip() or None

        snapshot = submit_static_analysis_job(
            code_payload=(code_name, code_data),
            config_payload=(config_name, config_data),
            rules_payload=(
                rules_name,
                json.dumps(normalized_rules, ensure_ascii=False).encode("utf-8"),
            ),
            notes=notes,
            protocol_name=protocol_name,
            protocol_version=protocol_version,
            project_name=project_name,
            rules_summary=rules_summary,
        )
        return make_response(success_response(snapshot), 202)

    def static_analysis_history():
        _, error = ensure_authenticated()
        if error:
            return error

        limit = to_int(request.args.get("limit"), 50)
        limit = max(1, min(limit, 200))
        history = list_static_analysis_history(limit=limit)
        payload = success_response(
            {"items": history, "limit": limit, "count": len(history)}
        )
        return make_response(payload, 200)

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
            return make_response(
                success_response({"jobId": job_id, "deleted": True}), 200
            )
        except Exception as exc:
            LOGGER.exception("Failed to delete static analysis job %s", job_id)
            return make_response(error_response(f"删除失败：{str(exc)}"), 500)

    return {
        "static_analysis": static_analysis,
        "static_analysis_history": static_analysis_history,
        "delete_static_analysis_history": delete_static_analysis_history,
    }
