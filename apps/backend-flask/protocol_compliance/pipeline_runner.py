"""Utilities for invoking the stand-alone protocol extraction pipeline."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Optional, Sequence
from urllib.parse import urlparse

if TYPE_CHECKING:  # 仅在类型检查时导入
    from werkzeug.datastructures import FileStorage  # type: ignore[import]
else:  # pragma: no cover - 运行时用宽松类型，避免依赖缺失
    FileStorage = Any  # type: ignore[assignment]

from .job_logging import JobStageLogger, ProgressCallback

LOGGER = logging.getLogger(__name__)


class PipelineExecutionError(RuntimeError):
    """Raised when the protocol pipeline exits with a non-zero status."""

    def __init__(
        self,
        message: str,
        *,
        log_path: str | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
    ):
        super().__init__(message)
        self.log_path = log_path
        self.stdout = stdout
        self.stderr = stderr


class PipelineResultNotFoundError(RuntimeError):
    """Raised when the pipeline finishes but the expected result file is missing."""


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_ROOT = (Path(__file__).resolve().parents[1] / "protocol_extract").resolve()
STORAGE_ROOT = PIPELINE_ROOT / "project_store"
UPLOAD_ROOT = PIPELINE_ROOT / "uploads"
LOG_ROOT = PIPELINE_ROOT / "logs"


UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
LOG_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class PipelineRuleItem:
    rule: str
    req_type: list[str]
    req_fields: list[str]
    res_type: list[str]
    res_fields: list[str]
    group: str | None = None


@dataclass(slots=True)
class PipelineResult:
    protocol: str
    version: str
    store_dir: Path
    result_path: Path
    rules: list[PipelineRuleItem]


_TOKEN_SPLIT_RE = re.compile(r"\s*(?:,|;|/|\bor\b|\band\b)\s*", re.IGNORECASE)


def _ensure_pipeline_root() -> None:
    if not PIPELINE_ROOT.exists():
        raise FileNotFoundError(f"pipeline root does not exist: {PIPELINE_ROOT}")


def _resolve_llm_base_url() -> str:
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise ValueError("环境变量 OPENAI_BASE_URL 不能为空")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("模型接口地址必须是有效的 http(s) URL")
    return base_url


def _redact_pipeline_output(value: str | None, secrets: Sequence[str]) -> str:
    if not value:
        return ""
    redacted = value
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "<API_KEY>")
    return re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "<API_KEY>", redacted)


def _write_pipeline_log(
    *,
    command: Sequence[str],
    protocol: str,
    stderr: str,
    stdout: str,
    version: str,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    protocol_part = _sanitize_segment(protocol.lower(), "protocol")
    version_part = _sanitize_segment(version.replace(".", "_"), "version")
    log_path = (
        LOG_ROOT / f"{timestamp}-{protocol_part}-{version_part}-{uuid.uuid4().hex[:8]}.log"
    )
    content = [
        f"timestamp: {timestamp}",
        f"protocol: {protocol}",
        f"version: {version}",
        f"command: {' '.join(str(part) for part in command)}",
        "",
        "===== STDOUT =====",
        stdout or "<empty>",
        "",
        "===== STDERR =====",
        stderr or "<empty>",
        "",
    ]
    log_path.write_text("\n".join(content), encoding="utf-8")
    return log_path


def _sanitize_segment(value: str, fallback: str) -> str:
    stripped = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    stripped = stripped.strip("-")
    return stripped or fallback


def _save_upload(upload: FileStorage) -> Path:
    filename = upload.filename or "protocol-document.html"
    suffix = Path(filename).suffix or ".html"
    token = uuid.uuid4().hex
    safe_name = _sanitize_segment(Path(filename).stem, "protocol")
    target = UPLOAD_ROOT / f"{safe_name}-{token}{suffix}"
    upload.save(target)
    return target


def _normalize_list(values: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        stripped = value.strip()
        if not stripped:
            continue
        normalized.append(stripped)
    return normalized


def _ensure_list(payload: object) -> list[str]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return _normalize_list(str(item) for item in payload if item is not None)
    if isinstance(payload, str):
        if not payload.strip():
            return []
        tokens = [segment for segment in _TOKEN_SPLIT_RE.split(payload) if segment]
        return _normalize_list(tokens) or [payload.strip()]
    return []


def _load_rules(result_path: Path) -> list[PipelineRuleItem]:
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineResultNotFoundError(
            f"无法解析规则文件 {result_path}: {exc}"
        ) from exc

    records: Sequence[dict] | dict
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        # Some pipelines produce a mapping of group -> list
        items: list[dict] = []
        for group_name, group_rules in payload.items():
            if not isinstance(group_rules, list):
                continue
            for rule in group_rules:
                if isinstance(rule, dict):
                    rule = {**rule, "group": group_name}
                    items.append(rule)
        records = items
    else:
        raise PipelineResultNotFoundError(f"规则文件格式不受支持: {type(payload)!r}")

    rule_items: list[PipelineRuleItem] = []
    for entry in records:
        if not isinstance(entry, dict):
            continue
        rule_text = str(entry.get("rule") or "").strip()
        if not rule_text:
            continue
        item = PipelineRuleItem(
            rule=rule_text,
            req_type=_ensure_list(entry.get("req_type")),
            req_fields=_ensure_list(entry.get("req_fields")),
            res_type=_ensure_list(entry.get("res_type")),
            res_fields=_ensure_list(entry.get("res_fields")),
            group=str(entry.get("group")).strip() if entry.get("group") else None,
        )
        rule_items.append(item)
    return rule_items


def _resolve_result_path(protocol: str, version: str) -> tuple[Path, Path]:
    normalized_protocol = protocol.lower().strip()
    normalized_version = version.replace(".", "_").replace(" ", "_").strip()
    store_dir = STORAGE_ROOT / f"{normalized_protocol}_{normalized_version}"
    if not store_dir.exists():
        raise PipelineResultNotFoundError(f"未找到存储目录: {store_dir}")

    candidates = [
        store_dir / "ruleDir" / "processed_results.json",
        store_dir / "processed_results.json",
    ]

    # Include pattern-based fallbacks (processed_results*.json)
    candidates.extend(sorted(store_dir.glob("ruleDir/processed_results*.json"), reverse=True))
    candidates.extend(sorted(store_dir.glob("processed_results*.json"), reverse=True))

    for candidate in candidates:
        if candidate.is_file():
            return store_dir, candidate

    raise PipelineResultNotFoundError(f"未在 {store_dir} 中找到 processed_results.json 文件")


def _build_command(
    api_key: str,
    protocol: str,
    version: str,
    html_path: Path,
    *,
    filter_headings: bool,
) -> list[str]:
    command = [
        sys.executable,
        "main.py",
        "--protocol",
        protocol,
        "--version",
        version,
        "--html-file",
        str(html_path),
    ]
    if filter_headings:
        command.append("--filter_headings")
    return command


def run_protocol_pipeline(
    *,
    protocol: str,
    version: str,
    html_upload: FileStorage,
    filter_headings: bool = False,
    job_id: str = "standalone",
    progress_callback: Optional[ProgressCallback] = None,
) -> PipelineResult:
    """Execute the protocol extraction pipeline and load its results."""

    _ensure_pipeline_root()

    protocol = protocol.strip()
    version = version.strip()
    if not protocol:
        raise ValueError("protocol 不能为空")
    if not version:
        raise ValueError("version 不能为空")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("环境变量 OPENAI_API_KEY 不能为空")
    resolved_llm_base_url = _resolve_llm_base_url()

    saved_path = _save_upload(html_upload)

    command = _build_command(
        api_key,
        protocol,
        version,
        saved_path,
        filter_headings=filter_headings,
    )
    child_env = os.environ.copy()
    child_env["OPENAI_API_KEY"] = api_key
    child_env["OPENAI_BASE_URL"] = resolved_llm_base_url
    child_env.pop("PROTOCOL_EXTRACT_LLM_BASE_URL", None)
    child_env["PYTHONUNBUFFERED"] = "1"

    job_logger = JobStageLogger(
        job_id=job_id,
        logger=LOGGER,
        progress_callback=progress_callback,
    )
    output_lines: list[str] = []
    current_stage = "pipeline"
    job_logger.info(
        "Preparing protocol extraction pipeline",
        stage="inputs",
        protocol=protocol,
        version=version,
        filter_headings=filter_headings,
    )
    job_logger.info(
        "Launching protocol extraction subprocess",
        stage="pipeline",
        command=command,
        pipeline_root=str(PIPELINE_ROOT),
    )

    try:
        process = subprocess.Popen(
            command,
            cwd=str(PIPELINE_ROOT),
            env=child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = _redact_pipeline_output(raw_line.rstrip(), [api_key])
            if not line:
                continue
            current_stage = _pipeline_stage_for_line(line, current_stage)
            output_lines.append(line)
            job_logger.log(
                _pipeline_level_for_line(line),
                line,
                stage=current_stage,
                stream="stdout-stderr",
                emit_progress=False,
            )
        return_code = process.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, command)
    except subprocess.CalledProcessError as exc:
        stdout = "\n".join(output_lines)
        stderr = ""
        log_path = _write_pipeline_log(
            command=command,
            protocol=protocol,
            stderr=stderr,
            stdout=stdout,
            version=version,
        )
        job_logger.error(
            "Protocol extraction subprocess failed with exit code %s",
            exc.returncode,
            stage=current_stage,
            return_code=exc.returncode,
            log_path=str(log_path),
        )
        raise PipelineExecutionError(
            "协议分析流程执行失败",
            log_path=str(log_path),
            stdout=stdout,
            stderr=stderr,
        ) from exc
    finally:
        # 删除临时文件，忽略失败
        with contextlib.suppress(Exception):
            saved_path.unlink()

    job_logger.info("Loading extracted rule artifacts", stage="artifacts")
    try:
        store_dir, result_path = _resolve_result_path(protocol, version)
        rules = _load_rules(result_path)
    except Exception as exc:
        job_logger.error(
            "Failed to load protocol extraction artifacts: %s",
            exc,
            stage="artifacts",
            exc_info=True,
        )
        raise
    job_logger.info(
        "Loaded %s extracted rules",
        len(rules),
        stage="artifacts",
        result_path=str(result_path),
        rule_count=len(rules),
    )
    job_logger.info(
        "Protocol extraction pipeline completed successfully",
        stage="completed",
        rule_count=len(rules),
    )

    return PipelineResult(
        protocol=protocol,
        version=version,
        store_dir=store_dir,
        result_path=result_path,
        rules=rules,
    )


def _pipeline_stage_for_line(line: str, current_stage: str) -> str:
    lowered = line.lower()
    markers = (
        (("文档处理阶段", "processing html", "processing text", "filtering protocol headings"), "document"),
        (("关键词处理阶段", "正在执行 keywords", "关键词"), "keywords"),
        (("规则处理阶段", "stage 1", "基础规则过滤"), "rule-filter"),
        (("enhance", "增强阶段", "句子增强"), "rule-enhance"),
        (("stage 2", "ai 规则验证"), "rule-validation"),
        (("stage 3", "协议字段解析"), "rule-fields"),
    )
    for candidates, stage in markers:
        if any(candidate in lowered for candidate in candidates):
            return stage
    return current_stage


def _pipeline_level_for_line(line: str) -> int:
    lowered = line.lower()
    if any(marker in lowered for marker in ("traceback", "error", "failed", "失败", "错误")):
        return logging.ERROR
    if any(marker in lowered for marker in ("[warn", "warning", "警告", "⚠")):
        return logging.WARNING
    if any(marker in lowered for marker in ("[debug]", "debug")):
        return logging.DEBUG
    return logging.INFO


def _ensure_pipeline_dependencies() -> None:
    """Placeholder to keep backwards compatibility; dependencies需手动安装。"""
    return
