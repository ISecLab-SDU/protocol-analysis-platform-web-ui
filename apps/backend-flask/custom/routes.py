"""Custom API endpoints for fuzz testing data."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint

try:
    from ..utils.responses import success_response
except ImportError:
    from utils.responses import success_response

bp = Blueprint("custom", __name__, url_prefix="/api/custom")


@bp.get("/text")
def get_fuzz_text():
    """Get fuzz testing text data."""
    # Try to find the fuzz_output.txt file from the mock backend
    candidates = [
        # From the mock backend location
        Path(__file__).parent.parent.parent / "backend-mock" / "api" / "custom" / "fuzz_output.txt",
        # From current directory
        Path("fuzz_output.txt"),
        # From custom directory
        Path(__file__).parent / "fuzz_output.txt",
    ]
    
    text_content = ""
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                with open(candidate, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content and content.strip():
                        text_content = content
                        break
            except Exception:
                continue
    
    # If no file found, return default fuzz data
    if not text_content:
        text_content = """[1] 版本=v1, 类型=get
选择OIDs=['1.3.6.1.2.1.1.1.0']
报文HEX: 302902010004067075626C6963A01C02040E8F83C502010002010030
[发送尝试] 长度=43 字节
[接收成功] 42 字节
[2] 版本=v2c, 类型=set
选择OIDs=['1.3.6.1.2.1.1.2.0']
报文HEX: 304502010104067075626C6963A03802040E8F83C502010002010030
[发送尝试] 长度=71 字节
[接收超时]
[3] 版本=v3, 类型=getnext
选择OIDs=['1.3.6.1.2.1.1.3.0']
报文HEX: 305502010304067075626C6963A04802040E8F83C502010002010030
[发送尝试] 长度=87 字节
[接收成功] 156 字节
[4] 生成失败: 无效的OID格式
[5] 版本=v1, 类型=getbulk
选择OIDs=['1.3.6.1.2.1.1.4.0']
报文HEX: 306502010004067075626C6963A05802040E8F83C502010002010030
[发送尝试] 长度=103 字节
[运行监控] 收到崩溃通知: 健康服务报告 VM 不可达
[崩溃信息] 疑似崩溃数据包: 306502010004067075626C6963A05802040E8F83C502010002010030
[崩溃信息] 崩溃队列信息导出: /home/hhh/下载/snmp_fuzz/snmp_github/snmp_fuzz/scan_result/crash_logs/20251014-110318
[运行监控] 检测到崩溃，停止 fuzz 循环
统计: {'v1': 3, 'v2c': 1, 'v3': 1}, {'get': 2, 'set': 1, 'getnext': 1, 'getbulk': 1}
开始时间: 2025-01-14 11:03:18
结束时间: 2025-01-14 11:03:25
总耗时: 7.2 秒
发送总数据包: 5
平均发送速率: 0.69 包/秒"""
    
    return success_response({"text": text_content})
