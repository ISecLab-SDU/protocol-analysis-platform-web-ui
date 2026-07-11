"""Static-analysis job route registration."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable, Optional

from flask import Blueprint, make_response, request, send_file

from utils.responses import error_response, success_response

from .analysis import get_static_analysis_job, get_static_analysis_result

LOGGER = logging.getLogger(__name__)


def register_static_analysis_job_routes(
    bp: Blueprint,
    ensure_authenticated: Callable[[], tuple[object, object]],
) -> dict[str, Callable[..., object]]:
    @bp.route("/static-analysis/<job_id>/progress", methods=["GET"])
    def static_analysis_progress(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        from_event_id_raw = request.args.get("fromEventId")
        from_event_id: Optional[int] = None
        if from_event_id_raw is not None:
            try:
                from_event_id = int(from_event_id_raw)
            except (TypeError, ValueError):
                LOGGER.warning(
                    "Invalid fromEventId parameter: %s (job_id=%s)",
                    from_event_id_raw,
                    job_id,
                )

        snapshot = get_static_analysis_job(job_id, from_event_id=from_event_id)
        if not snapshot:
            return make_response(error_response("未找到静态分析任务"), 404)
        return make_response(success_response(snapshot), 200)

    @bp.route("/static-analysis/<job_id>/result", methods=["GET"])
    def static_analysis_result(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        result = get_static_analysis_result(job_id)
        if result is None:
            snapshot = get_static_analysis_job(job_id)
            if not snapshot:
                return make_response(error_response("未找到静态分析任务"), 404)
            status = snapshot.get("status")
            return make_response(
                error_response("静态分析任务尚未完成", {"status": status}),
                409,
            )
        return make_response(success_response(result), 200)

    @bp.route("/static-analysis/<job_id>/artifact/database", methods=["GET"])
    def download_static_analysis_database(job_id: str):
        LOGGER.info("[下载数据库] 请求下载任务 %s 的数据库文件", job_id)
        _, error = ensure_authenticated()
        if error:
            LOGGER.warning("[下载数据库] 任务 %s 认证失败", job_id)
            return error

        snapshot = get_static_analysis_job(job_id)
        if not snapshot:
            LOGGER.error("[下载数据库] 任务 %s 未找到", job_id)
            return make_response(error_response("未找到静态分析任务"), 404)

        LOGGER.info("[下载数据库] 任务 %s 找到，状态: %s", job_id, snapshot.get("status"))

        database_path = snapshot.get("database_path")
        LOGGER.info("[下载数据库] 任务 %s 的 database_path: %s", job_id, database_path)

        if isinstance(database_path, str) and database_path:
            db_file = Path(database_path)
            if db_file.exists():
                LOGGER.info("[下载数据库] 使用存储的路径: %s", db_file)
                return send_file(
                    db_file,
                    as_attachment=True,
                    download_name=f"analysis-{job_id}.db",
                    mimetype="application/octet-stream",
                )

        LOGGER.warning("[下载数据库] database_path 无效，尝试从 output_path 查找")
        output_path = snapshot.get("output_path")
        if isinstance(output_path, str) and output_path:
            output_dir = Path(output_path)
            database_dir = output_dir / "database"
            LOGGER.info("[下载数据库] 在 %s 目录查找数据库文件", database_dir)

            if database_dir.exists():
                candidates = list(database_dir.glob("*.db"))
                LOGGER.info("[下载数据库] 找到 %d 个 .db 文件: %s", len(candidates), candidates)
                if candidates:
                    db_file = candidates[0]
                    LOGGER.info("[下载数据库] 使用 output_path 找到的文件: %s", db_file)
                    return send_file(
                        db_file,
                        as_attachment=True,
                        download_name=f"analysis-{job_id}.db",
                        mimetype="application/octet-stream",
                    )

        LOGGER.warning("[下载数据库] output_path 也无效，尝试从环境变量构造路径")
        output_root = os.environ.get("PG_OUTPUT_ROOT", "/tmp/protocolguard/outputs")
        constructed_path = Path(output_root) / job_id / "database"
        LOGGER.info("[下载数据库] 尝试构造的路径: %s", constructed_path)

        if constructed_path.exists():
            candidates = list(constructed_path.glob("*.db"))
            LOGGER.info("[下载数据库] 在构造路径找到 %d 个 .db 文件: %s", len(candidates), candidates)
            if candidates:
                db_file = candidates[0]
                LOGGER.info("[下载数据库] 使用构造路径找到的文件: %s", db_file)
                return send_file(
                    db_file,
                    as_attachment=True,
                    download_name=f"analysis-{job_id}.db",
                    mimetype="application/octet-stream",
                )

        LOGGER.error("[下载数据库] 所有方法都失败，无法找到数据库文件")
        return make_response(error_response("数据库文件不存在"), 404)

    return {
        "static_analysis_progress": static_analysis_progress,
        "static_analysis_result": static_analysis_result,
        "download_static_analysis_database": download_static_analysis_database,
    }
