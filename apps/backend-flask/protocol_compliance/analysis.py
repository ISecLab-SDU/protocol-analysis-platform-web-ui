"""Static analysis helpers and ProtocolGuard Docker integration."""

from __future__ import annotations

import random
import uuid
import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import BinaryIO, Dict, Optional

from .docker_runner import (
    ProtocolGuardDockerError,
    ProtocolGuardDockerRunner,
    ProtocolGuardDockerSettings,
    ProtocolGuardExecutionError,
    ProtocolGuardNotAvailableError,
)

LOGGER = logging.getLogger(__name__)

ComplianceStatus = str  # 'compliant' | 'needs_review' | 'non_compliant'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_mock_analysis(
    *,
    code_file_name: str,
    rules_file_name: str,
    protocol_name: str,
    notes: Optional[str],
    rules_summary: Optional[str],
) -> Dict[str, object]:
    findings = [_build_finding(code_file_name) for _ in range(random.randint(4, 6))]
    counts = {"compliant": 0, "needs_review": 0, "non_compliant": 0}
    for finding in findings:
        counts[finding["compliance"]] += 1

    if counts["non_compliant"]:
        overall_status: ComplianceStatus = "non_compliant"
    elif counts["needs_review"]:
        overall_status = "needs_review"
    else:
        overall_status = "compliant"

    now = _now_iso()

    return {
        "analysisId": str(uuid.uuid4()),
        "durationMs": random.randint(1800, 4200),
        "inputs": {
            "codeFileName": code_file_name,
            "notes": notes or None,
            "protocolName": protocol_name,
            "rulesFileName": rules_file_name,
            "rulesSummary": rules_summary or None,
        },
        "model": "protocol-guard-static-preview",
        "modelResponse": {
            "metadata": {
                "generatedAt": now,
                "modelVersion": "protocol-guard-llm-2024-10",
                "protocol": protocol_name,
                "ruleSet": rules_file_name,
            },
            "summary": {
                "compliantCount": counts["compliant"],
                "needsReviewCount": counts["needs_review"],
                "nonCompliantCount": counts["non_compliant"],
                "notes": notes
                or "本次静态检测通过 ProtocolGuard 原型进行（Mock 数据）。",
                "overallStatus": overall_status,
            },
            "verdicts": findings,
        },
        "submittedAt": now,
    }


def normalize_protocol_name(parsed_rules: Optional[dict], fallback: str) -> str:
    if not parsed_rules or not isinstance(parsed_rules, dict):
        return fallback
    for key in ("protocol", "protocolName", "title", "name"):
        value = parsed_rules.get(key)
        if isinstance(value, str):
            return value
    return fallback


def extract_protocol_version(parsed_rules: Optional[dict], fallback: Optional[str] = None) -> Optional[str]:
    if not parsed_rules or not isinstance(parsed_rules, dict):
        return fallback
    for key in ("protocolVersion", "version", "protocol_version"):
        value = parsed_rules.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return fallback


def try_extract_rules_summary(parsed_rules: Optional[dict]) -> Optional[str]:
    if not parsed_rules or not isinstance(parsed_rules, dict):
        return None
    candidate = parsed_rules.get("summary") or parsed_rules.get("description")
    if isinstance(candidate, str):
        return candidate
    rules = parsed_rules.get("rules")
    if isinstance(rules, list) and rules:
        first = rules[0]
        if isinstance(first, dict) and "requirement" in first:
            return f"包含 {len(rules)} 条规则，示例：{first.get('requirement')}"
    return None


def _build_finding(code_file_name: str) -> Dict[str, object]:
    compliance = random.choice(["compliant", "needs_review", "non_compliant"])
    line_start = random.randint(12, 320)
    line_end = line_start + random.randint(2, 14)
    recommendation = (
        _random_sentence(12, 18) if compliance == "non_compliant" else None
    )

    return {
        "category": random.choice(["状态机约束", "消息字段校验", "握手流程", "错误处理"]),
        "compliance": compliance,
        "confidence": random.choice(["low", "medium", "high"]),
        "explanation": _random_paragraph(),
        "findingId": str(uuid.uuid4()),
        "lineRange": [line_start, line_end],
        "location": {
            "file": code_file_name,
            "function": random.choice(
                ["handle_handshake", "process_record", "validate_request", "dispatch_message"]
            ),
        },
        "recommendation": recommendation,
        "relatedRule": {
            "id": f"RULE-{random.randint(101, 999)}",
            "requirement": _random_sentence(10, 18),
            "source": f"RFC {random.randint(1000, 8999)} Section {random.randint(1, 6)}.{random.randint(1, 9)}",
        },
    }


def _random_sentence(min_words: int = 8, max_words: int = 18) -> str:
    word_count = random.randint(min_words, max_words)
    words = random.choices(_WORD_BANK, k=word_count)
    return " ".join(words)


def _random_paragraph(sentences: int = 1) -> str:
    return " ".join(_random_sentence(8, 15) for _ in range(sentences))


_WORD_BANK = [
    "协议",
    "握手",
    "报文",
    "验证",
    "状态",
    "同步",
    "密钥",
    "交换",
    "流程",
    "校验",
    "加密",
    "套件",
    "确认",
    "策略",
    "超时",
    "重传",
    "检测",
    "结果",
    "安全",
    "约束",
    "分析",
    "规则",
    "字段",
    "覆盖",
    "路径",
    "机制",
]


# Docker integration ------------------------------------------------------------


class AnalysisError(RuntimeError):
    """Base error for ProtocolGuard analysis orchestration."""


class AnalysisNotReadyError(AnalysisError):
    """Raised when Docker integration is enabled but not available."""


class AnalysisExecutionError(AnalysisError):
    """Raised when the Docker pipeline fails."""

    def __init__(
        self,
        message: str,
        *,
        logs: Optional[list[str]] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.logs = logs or []
        self.details = details or {}


@lru_cache(maxsize=1)
def _docker_settings() -> ProtocolGuardDockerSettings:
    return ProtocolGuardDockerSettings.from_env()


def run_static_analysis(
    *,
    code_stream: BinaryIO,
    code_file_name: str,
    builder_stream: BinaryIO,
    builder_file_name: str,
    config_stream: BinaryIO,
    config_file_name: str,
    rules_stream: BinaryIO,
    rules_file_name: str,
    notes: Optional[str],
    protocol_name: str,
    protocol_version: Optional[str],
    rules_summary: Optional[str],
) -> Dict[str, object]:
    """Dispatch static analysis either via Docker or the mock generator."""
    settings = _docker_settings()
    if not settings.enabled:
        LOGGER.debug("ProtocolGuard Docker disabled; returning mock analysis.")
        return build_mock_analysis(
            code_file_name=code_file_name,
            rules_file_name=rules_file_name,
            protocol_name=protocol_name,
            notes=notes,
            rules_summary=rules_summary,
        )

    try:
        runner = ProtocolGuardDockerRunner(settings)
    except ProtocolGuardNotAvailableError as exc:
        raise AnalysisNotReadyError(str(exc)) from exc

    try:
        return runner.run_static_analysis(
            code_stream=code_stream,
            code_filename=code_file_name,
            builder_stream=builder_stream,
            builder_filename=builder_file_name,
            config_stream=config_stream,
            config_filename=config_file_name,
            rules_stream=rules_stream,
            rules_filename=rules_file_name,
            notes=notes,
            protocol_name=protocol_name,
            protocol_version=protocol_version,
            rules_summary=rules_summary,
        )
    except ProtocolGuardExecutionError as exc:
        LOGGER.error(
            "ProtocolGuard analysis execution failed (image=%s, status=%s): %s",
            getattr(exc, "image", None),
            getattr(exc, "status", None),
            exc,
        )
        raise AnalysisExecutionError(
            str(exc),
            logs=getattr(exc, "logs", []),
            details={
                "status": getattr(exc, "status", None),
                "image": getattr(exc, "image", None),
                "logExcerpt": getattr(exc, "log_excerpt", None),
            },
        ) from exc
    except ProtocolGuardDockerError as exc:
        LOGGER.error("ProtocolGuard Docker error: %s", exc)
        raise AnalysisError(str(exc)) from exc
