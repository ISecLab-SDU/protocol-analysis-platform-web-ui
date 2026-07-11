"""Assertion history request handlers."""

from __future__ import annotations

from typing import Callable

from flask import make_response, request, send_file

from utils.responses import error_response, success_response

from .assertion import (
    get_assertion_history_diff_path,
    get_assertion_history_entry,
    list_assertion_history,
)


def create_assertion_history_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
    *,
    to_int: Callable[[object, int], int],
) -> dict[str, Callable[..., object]]:
    def assertion_history():
        _, error = ensure_authenticated()
        if error:
            return error

        limit = to_int(request.args.get("limit"), 50)
        limit = max(1, min(limit, 200))
        items = list_assertion_history(limit=limit)
        payload = {"items": items, "limit": limit, "count": len(items)}
        return make_response(success_response(payload), 200)

    def assertion_history_entry(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        entry = get_assertion_history_entry(job_id)
        if not entry:
            return make_response(error_response("历史记录不存在"), 404)
        return make_response(success_response(entry), 200)

    def download_assertion_diff(job_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        diff_path = get_assertion_history_diff_path(job_id)
        if not diff_path:
            return make_response(error_response("Diff 文件不存在"), 404)
        return send_file(diff_path, as_attachment=True, download_name=diff_path.name)

    return {
        "assertion_history": assertion_history,
        "assertion_history_entry": assertion_history_entry,
        "download_assertion_diff": download_assertion_diff,
    }
