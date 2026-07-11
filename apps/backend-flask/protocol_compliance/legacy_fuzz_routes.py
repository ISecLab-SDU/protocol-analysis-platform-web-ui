"""Legacy fuzzing route registration."""

from __future__ import annotations

from typing import Callable, Dict

from flask import Blueprint, make_response, request

from utils.responses import error_response, success_response


def register_legacy_fuzz_routes(
    bp: Blueprint,
    ensure_authenticated: Callable[[], tuple[object, object]],
) -> Dict[str, Callable[..., object]]:
    @bp.route("/write-script", methods=["POST"])
    def write_script():
        """写入脚本文件到指定路径"""
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json()
        if not data:
            return make_response(error_response("请求数据不能为空"), 400)

        content = data.get("content")
        protocol = data.get("protocol", "UNKNOWN")

        if not content:
            return make_response(error_response("脚本内容不能为空"), 400)

        # 根据协议获取配置
        if protocol == "RTSP":
            # SOL使用ProtocolGuard，不需要脚本文件，直接返回成功
            return success_response({
                "message": "SOL不需要脚本文件，直接启动docker即可生成日志",
                "filePath": "N/A",
                "size": 0,
            })
        elif protocol == "MQTT":
            # MQTT协议暂时不需要脚本文件，直接返回成功
            return success_response({
                "message": f"{protocol}协议不需要脚本文件",
                "filePath": "N/A",
                "size": 0,
            })
        else:
            return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

    return {
        "write_script": write_script,
    }
