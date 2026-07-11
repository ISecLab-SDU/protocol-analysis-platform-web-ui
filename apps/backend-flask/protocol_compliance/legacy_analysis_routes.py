"""Legacy detection-result and analysis-history request handlers."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Callable

from flask import make_response, request

from utils.responses import error_response, success_response

from .legacy_analysis_history import (
    append_analysis_history,
    list_available_implementations as list_legacy_available_implementations,
    read_analysis_history,
    read_detection_results,
)


def create_legacy_analysis_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
) -> dict[str, Callable[..., Any]]:
    def get_detection_results(implementation_name: str):
        """获取指定协议实现的检测结果"""
        _, error = ensure_authenticated()
        if error:
            return error

        try:
            items = read_detection_results(implementation_name)
        except FileNotFoundError:
            return make_response(
                error_response(f"未找到协议实现 '{implementation_name}' 的数据库文件"),
                404,
            )
        except sqlite3.Error as e:
            return make_response(
                error_response(f"数据库读取错误: {str(e)}"),
                500,
            )

        return success_response({"items": items})

    def list_available_implementations():
        """获取所有可用的协议实现列表"""
        _, error = ensure_authenticated()
        if error:
            return error

        implementations = list_legacy_available_implementations()
        return success_response({"items": implementations})

    def get_analysis_history():
        """获取历史记录"""
        _, error = ensure_authenticated()
        if error:
            return error

        try:
            history = read_analysis_history()
            return success_response({"items": history})
        except (json.JSONDecodeError, IOError) as e:
            return make_response(
                error_response(f"读取历史记录失败: {str(e)}"),
                500,
            )

    def add_analysis_history():
        """添加历史记录"""
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json()
        implementation_name = data.get("implementationName")
        protocol_name = data.get("protocolName")

        if not implementation_name or not protocol_name:
            return make_response(
                error_response("缺少必要参数"),
                400,
            )

        try:
            append_analysis_history(implementation_name, protocol_name)
        except IOError as e:
            return make_response(
                error_response(f"保存历史记录失败: {str(e)}"),
                500,
            )

        return success_response({"message": "已添加到历史记录"})

    return {
        "get_detection_results": get_detection_results,
        "list_available_implementations": list_available_implementations,
        "get_analysis_history": get_analysis_history,
        "add_analysis_history": add_analysis_history,
    }
