"""Utilities for invoking the stand-alone protocol extraction pipeline."""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Sequence
from urllib.parse import urlparse

if TYPE_CHECKING:  # 仅在类型检查时导入
    from werkzeug.datastructures import FileStorage  # type: ignore[import]
else:  # pragma: no cover - 运行时用宽松类型，避免依赖缺失
    FileStorage = Any  # type: ignore[assignment]


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
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"


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


def _resolve_llm_base_url(value: str | None) -> str:
    base_url = (
        (value or "").strip()
        or os.environ.get("PROTOCOL_EXTRACT_LLM_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or DEFAULT_LLM_BASE_URL
    ).rstrip("/")
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
    api_key: str,
    protocol: str,
    version: str,
    html_upload: FileStorage,
    filter_headings: bool = False,
    llm_base_url: str | None = None,
) -> PipelineResult:
    """Execute the protocol extraction pipeline and load its results."""

    _ensure_pipeline_root()

    protocol = protocol.strip()
    version = version.strip()
    if not protocol:
        raise ValueError("protocol 不能为空")
    if not version:
        raise ValueError("version 不能为空")
    api_key = api_key.strip()
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("API 密钥不能为空")
    resolved_llm_base_url = _resolve_llm_base_url(llm_base_url)

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
    child_env["PROTOCOL_EXTRACT_LLM_BASE_URL"] = resolved_llm_base_url

    try:
        subprocess.run(
            command,
            cwd=str(PIPELINE_ROOT),
            env=child_env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - interactive error handling
        stdout = _redact_pipeline_output(exc.stdout, [api_key])
        stderr = _redact_pipeline_output(exc.stderr, [api_key])
        log_path = _write_pipeline_log(
            command=command,
            protocol=protocol,
            stderr=stderr,
            stdout=stdout,
            version=version,
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

    # 解析结果
    store_dir, result_path = _resolve_result_path(protocol, version)
    rules = _load_rules(result_path)

    return PipelineResult(
        protocol=protocol,
        version=version,
        store_dir=store_dir,
        result_path=result_path,
        rules=rules,
    )


def _ensure_pipeline_dependencies() -> None:
    """Placeholder to keep backwards compatibility; dependencies需手动安装。"""
    return
