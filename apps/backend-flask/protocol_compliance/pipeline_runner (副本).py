"""Utilities for invoking the stand-alone protocol extraction pipeline."""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
import venv
from typing import Iterable, Sequence

from werkzeug.datastructures import FileStorage


class PipelineExecutionError(RuntimeError):
    """Raised when the protocol pipeline exits with a non-zero status."""

    def __init__(self, message: str, *, stdout: str | None = None, stderr: str | None = None):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class PipelineResultNotFoundError(RuntimeError):
    """Raised when the pipeline finishes but the expected result file is missing."""


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_ROOT = (REPO_ROOT / "protocolProject-1").resolve()
STORAGE_ROOT = PIPELINE_ROOT / "project_store"
UPLOAD_ROOT = PIPELINE_ROOT / "uploads"


UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
_DEPS_MARKER = PIPELINE_ROOT / ".deps_installed"


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
        "--apikey",
        api_key,
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
) -> PipelineResult:
    """Execute the protocol extraction pipeline and load its results."""

    _ensure_pipeline_root()
    _ensure_pipeline_dependencies()

    protocol = protocol.strip()
    version = version.strip()
    if not protocol:
        raise ValueError("protocol 不能为空")
    if not version:
        raise ValueError("version 不能为空")
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("API 密钥不能为空")

    saved_path = _save_upload(html_upload)

    command = _build_command(
        api_key,
        protocol,
        version,
        saved_path,
        filter_headings=filter_headings,
    )

    try:
        subprocess.run(
            command,
            cwd=str(PIPELINE_ROOT),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - interactive error handling
        raise PipelineExecutionError(
            "协议分析流程执行失败",
            stdout=exc.stdout,
            stderr=exc.stderr,
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
    if _DEPS_MARKER.exists():
        return
    requirements = PIPELINE_ROOT / "requirements.txt"
    if not requirements.is_file():
        _DEPS_MARKER.touch(exist_ok=True)
        return
    pip_exec = _resolve_pip_executable()
    try:
        subprocess.run(
            [pip_exec, "install", "-r", str(requirements)],
            cwd=str(PIPELINE_ROOT),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _DEPS_MARKER.touch(exist_ok=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        if "externally-managed-environment" in stderr:
            pip_exec = _ensure_virtualenv_with_pip()
            subprocess.run(
                [pip_exec, "install", "-r", str(requirements)],
                cwd=str(PIPELINE_ROOT),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _DEPS_MARKER.touch(exist_ok=True)
            return
        raise PipelineExecutionError(
            "协议分析依赖安装失败",
            stdout=exc.stdout,
            stderr=stderr,
        ) from exc

def _resolve_pip_executable() -> str:
    from shutil import which

    candidates = [
        str(Path(sys.executable).with_name("pip")),
        str(Path(sys.executable).with_name("pip3")),
    ]
    resolved = None
    for candidate in candidates:
        if which(candidate):
            resolved = candidate
            break
    if resolved is None:
        resolved = which("pip3") or which("pip")
    return resolved or "pip"


def _ensure_virtualenv_with_pip() -> str:
    venv_dir = PIPELINE_ROOT / ".venv"
    if not venv_dir.exists():
        builder = venv.EnvBuilder(with_pip=True, upgrade=True)
        builder.create(str(venv_dir))

    pip_candidates = [
        venv_dir / "bin" / "pip",
        venv_dir / "bin" / "pip3",
        venv_dir / "Scripts" / "pip.exe",
        venv_dir / "Scripts" / "pip3.exe",
    ]
    for candidate in pip_candidates:
        if candidate.is_file():
            return str(candidate)

    raise PipelineExecutionError(
        "未能在虚拟环境中找到 pip 可执行文件",
        stdout=None,
        stderr=None,
    )



