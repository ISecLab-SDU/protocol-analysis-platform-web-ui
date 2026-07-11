"""Protocol extraction and task route registration."""

from __future__ import annotations

import json
import logging
import re
from typing import Callable, Optional

from flask import Blueprint, make_response, request
from werkzeug.datastructures import FileStorage

from utils.responses import (
    error_response,
    make_error_payload,
    paginate,
    success_response,
)

from .pipeline_runner import (
    PipelineExecutionError,
    PipelineResultNotFoundError,
    run_protocol_pipeline,
)
from .store import STORE

LOGGER = logging.getLogger(__name__)


def register_task_routes(
    bp: Blueprint,
    ensure_authenticated: Callable[[], tuple[object, object]],
    *,
    normalize_status: Callable[[object], object],
    parse_tags: Callable[[Optional[str]], Optional[list[str]]],
    strip_extension: Callable[[str], str],
    to_int: Callable[[object, int], int],
) -> dict[str, Callable[..., object]]:
    @bp.route("/extract/run", methods=["POST"])
    def run_protocol_extract():
        _, error = ensure_authenticated()
        if error:
            return error

        html_upload = request.files.get("htmlFile")
        if not isinstance(html_upload, FileStorage):
            return make_response(error_response("请上传协议 HTML 文件"), 400)

        api_key = (request.form.get("apiKey") or "").strip()
        llm_base_url = (request.form.get("llmBaseUrl") or "").strip()
        protocol = (request.form.get("protocol") or "").strip()
        version = (request.form.get("version") or "").strip()
        filter_flag = (request.form.get("filterHeadings") or "").strip().lower()
        filter_headings = filter_flag in {"1", "true", "yes", "on"}

        try:
            result = run_protocol_pipeline(
                api_key=api_key,
                protocol=protocol,
                version=version,
                html_upload=html_upload,
                filter_headings=filter_headings,
                llm_base_url=llm_base_url,
            )
        except ValueError as exc:
            payload = make_error_payload("参数错误", details=str(exc))
            return make_response(payload, 400)
        except FileNotFoundError as exc:
            LOGGER.exception("Protocol extraction pipeline is not ready")
            payload = make_error_payload("流程未准备就绪", details=str(exc))
            return make_response(payload, 500)
        except PipelineResultNotFoundError as exc:
            LOGGER.exception("Protocol extraction pipeline result file was not found")
            detail = {"message": str(exc)}
            payload = make_error_payload("未找到分析结果文件", details=detail)
            return make_response(payload, 500)
        except PipelineExecutionError as exc:
            LOGGER.exception(
                "Protocol extraction pipeline execution failed. log_path=%s",
                exc.log_path,
            )
            detail = {
                "logPath": exc.log_path,
                "stdout": (exc.stdout or "").splitlines()[-40:] or None,
                "stderr": (exc.stderr or "").splitlines()[-40:] or None,
            }
            payload = make_error_payload("协议分析执行失败", details=detail)
            return make_response(payload, 500)

        payload = success_response(
            {
                "protocol": result.protocol,
                "version": result.version,
                "ruleCount": len(result.rules),
                "rules": [
                    {
                        "rule": item.rule,
                        "req_type": item.req_type,
                        "req_fields": item.req_fields,
                        "res_type": item.res_type,
                        "res_fields": item.res_fields,
                        "group": item.group,
                    }
                    for item in result.rules
                ],
                "storeDir": str(result.store_dir),
                "resultPath": str(result.result_path),
            }
        )
        return make_response(payload, 200)

    @bp.route("/tasks", methods=["GET"])
    def list_tasks():
        _, error = ensure_authenticated()
        if error:
            return error

        page = to_int(request.args.get("page"), 1)
        page_size = min(to_int(request.args.get("pageSize"), 20), 50)
        status = normalize_status(request.args.getlist("status"))

        tasks = STORE.list_tasks(status=status)
        paged, total = paginate(tasks, page, page_size)

        base_url = request.url_root.rstrip("/")
        items = [STORE.serialize_task(task, base_url) for task in paged]

        if page > 1 and not items and total > 0:
            payload = error_response("Requested page exceeds available data")
            return make_response(payload, 400)

        payload = success_response(
            {
                "items": items,
                "page": page,
                "pageSize": page_size,
                "total": total,
            }
        )
        return payload

    @bp.route("/tasks", methods=["POST"])
    def create_task():
        _, error = ensure_authenticated()
        if error:
            return error

        if "file" not in request.files and not request.files:
            payload = error_response("请上传协议文档")
            return make_response(payload, 400)

        document_name: Optional[str] = None
        document_size: Optional[int] = None

        for upload in request.files.values():
            if not isinstance(upload, FileStorage):
                continue
            document_name = upload.filename
            data = upload.read()
            document_size = len(data) if data else None
            upload.stream.seek(0)
            break

        if not document_name:
            payload = error_response("缺少协议文档，请重新上传")
            return make_response(payload, 400)

        description = request.form.get("description", "").strip() or None
        name = (
            request.form.get("name", "").strip()
            or strip_extension(document_name)
            or "协议任务"
        )
        tags = parse_tags(request.form.get("tags"))

        task = STORE.create_task(
            name=name,
            document_name=document_name,
            document_size=document_size,
            description=description,
            tags=tags,
        )

        base_url = request.url_root.rstrip("/")
        payload = success_response(STORE.serialize_task(task, base_url))
        return payload

    @bp.route("/tasks/<task_id>/result", methods=["GET"])
    def download_result(task_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        task = STORE.get_task(task_id)
        if not task:
            return make_response(error_response("未找到指定任务"), 404)

        if task.status != "completed" or not task.result_payload:
            return make_response(
                error_response("任务尚未完成，暂不可下载结果"), 409
            )

        content = json.dumps(task.result_payload, ensure_ascii=False, indent=2)
        base_name = re.sub(r"\s+", "-", task.name or task.document_name)
        file_name = f"{base_name}-rules.json"

        response = make_response(content)
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response

    return {
        "run_protocol_extract": run_protocol_extract,
        "list_tasks": list_tasks,
        "create_task": create_task,
        "download_result": download_result,
    }
