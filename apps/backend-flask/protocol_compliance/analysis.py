"""Static analysis helpers and ProtocolGuard Docker integration."""

from __future__ import annotations

import logging
import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from typing import BinaryIO, Callable, Dict, List, Literal, Optional

from .docker_runner import (
    ProtocolGuardDockerError,
    ProtocolGuardDockerRunner,
    ProtocolGuardDockerSettings,
    ProtocolGuardExecutionError,
    ProtocolGuardNotAvailableError,
)
from .state_repository import analysis_state_repository

LOGGER = logging.getLogger(__name__)

ComplianceStatus = str  # 'compliant' | 'needs_review' | 'non_compliant'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


AnalysisJobStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class AnalysisProgressEvent:
    timestamp: str
    stage: str
    message: str
    event_id: Optional[int] = None  # Event ID from database, None for in-memory events


@dataclass
class AnalysisProgressState:
    job_id: str
    status: AnalysisJobStatus
    stage: str
    message: str
    created_at: str
    updated_at: str
    events: List[AnalysisProgressEvent] = field(default_factory=list)
    result: Optional[Dict[str, object]] = None
    error: Optional[str] = None
    details: Optional[Dict[str, object]] = None


class AnalysisProgressRegistry:
    """Track live progress for static analysis jobs."""

    def __init__(self) -> None:
        self._states: Dict[str, AnalysisProgressState] = {}
        self._lock = threading.Lock()
        self._repository = analysis_state_repository

    def create_job(self) -> AnalysisProgressState:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        state = AnalysisProgressState(
            job_id=job_id,
            status="queued",
            stage="queued",
            message="Job queued",
            created_at=now,
            updated_at=now,
        )
        state.events.append(AnalysisProgressEvent(timestamp=now, stage="queued", message="Job queued"))
        with self._lock:
            self._states[job_id] = state
        self._repository.record_progress(
            job_id=job_id,
            status=state.status,
            stage=state.stage,
            message=state.message,
            created_at=now,
            updated_at=now,
        )
        self._repository.add_event(job_id=job_id, timestamp=now, stage="queued", message="Job queued")
        return state

    def mark_running(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "running"
            self._append_event(state, stage, message)

    def append_event(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            self._append_event(state, stage, message)

    def complete(self, job_id: str, result: Dict[str, object]) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "completed"
            state.result = result
            self._append_event(state, "completed", "Static analysis completed successfully")
            self._repository.record_completion(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                updated_at=state.updated_at,
                result=result,
            )

    def fail(
        self,
        job_id: str,
        stage: str,
        message: str,
        *,
        error: Optional[str] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "failed"
            state.error = error or message
            state.details = details
            self._append_event(state, stage, message)
            self._repository.record_failure(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                updated_at=state.updated_at,
                error=state.error,
                details=state.details,
            )

    def snapshot(
        self,
        job_id: str,
        from_event_id: Optional[int] = None,
    ) -> Optional[Dict[str, object]]:
        """
        Return snapshot of job state with incremental events.
        
        Always fetches events from database (which have IDs).
        If from_event_id is provided, only return events after that ID.
        If from_event_id is None, return all events from database.
        """
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return None
            state_copy = AnalysisProgressState(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                created_at=state.created_at,
                updated_at=state.updated_at,
                events=list(state.events),
                result=state.result,
                error=state.error,
                details=state.details.copy() if state.details else None,
            )

        # Always fetch events from database (they have IDs)
        db_events = self._repository.fetch_events(
            job_id=job_id,
            from_event_id=from_event_id,
        )
        events_list = [
            {
                "id": event["id"],
                "timestamp": event["timestamp"],
                "stage": event["stage"],
                "message": event["message"],
            }
            for event in db_events
        ]

        return {
            "jobId": state_copy.job_id,
            "status": state_copy.status,
            "stage": state_copy.stage,
            "message": state_copy.message,
            "createdAt": state_copy.created_at,
            "updatedAt": state_copy.updated_at,
            "events": events_list,
            "result": state_copy.result,
            "error": state_copy.error,
            "details": state_copy.details,
        }

    def _append_event(self, state: AnalysisProgressState, stage: str, message: str) -> None:
        timestamp = _now_iso()
        state.stage = stage
        state.message = message
        state.updated_at = timestamp
        state.events.append(AnalysisProgressEvent(timestamp=timestamp, stage=stage, message=message))
        self._repository.record_progress(
            job_id=state.job_id,
            status=state.status,
            stage=state.stage,
            message=state.message,
            updated_at=timestamp,
        )
        self._repository.add_event(job_id=state.job_id, timestamp=timestamp, stage=stage, message=message)

    def make_callback(self, job_id: str) -> Callable[[str, str, str], None]:
        def callback(_job_id: str, stage: str, message: str) -> None:
            # Ignore mismatched job ids to keep callback tolerant.
            target_id = job_id or _job_id
            self.append_event(target_id, stage, message)

        return callback


PROGRESS_REGISTRY = AnalysisProgressRegistry()


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
    job_id: Optional[str] = None,
    progress_callback: Optional[Callable[[str, str, str], None]] = None,
) -> Dict[str, object]:
    """Dispatch static analysis either via Docker or the mock generator."""
    job_identifier = job_id or str(uuid.uuid4())
    settings = _docker_settings()
    if not settings.enabled:
        LOGGER.debug("ProtocolGuard Docker disabled; returning mock analysis.")
        if progress_callback:
            progress_callback(job_identifier, "mock", "Generating mock analysis response")
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
            job_id=job_identifier,
            progress_callback=progress_callback,
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


def submit_static_analysis_job(
    *,
    code_payload: tuple[str, bytes],
    builder_payload: tuple[str, bytes],
    config_payload: tuple[str, bytes],
    rules_payload: tuple[str, bytes],
    notes: Optional[str],
    protocol_name: str,
    protocol_version: Optional[str],
    rules_summary: Optional[str],
) -> Dict[str, object]:
    """Launch static analysis asynchronously and return the initial job snapshot."""
    state = PROGRESS_REGISTRY.create_job()
    job_id = state.job_id

    def _run_job() -> None:
        PROGRESS_REGISTRY.mark_running(job_id, "init", "Preparing analysis inputs")
        progress_callback = PROGRESS_REGISTRY.make_callback(job_id)
        progress_callback(job_id, "inputs", "Persisting uploaded artefacts")
        try:
            code_name, code_bytes = code_payload
            builder_name, builder_bytes = builder_payload
            config_name, config_bytes = config_payload
            rules_name, rules_bytes = rules_payload

            result = run_static_analysis(
                code_stream=BytesIO(code_bytes),
                code_file_name=code_name,
                builder_stream=BytesIO(builder_bytes),
                builder_file_name=builder_name,
                config_stream=BytesIO(config_bytes),
                config_file_name=config_name,
                rules_stream=BytesIO(rules_bytes),
                rules_file_name=rules_name,
                notes=notes,
                protocol_name=protocol_name,
                protocol_version=protocol_version,
                rules_summary=rules_summary,
                job_id=job_id,
                progress_callback=progress_callback,
            )
            PROGRESS_REGISTRY.complete(job_id, result)
        except AnalysisExecutionError as exc:
            details = exc.details if isinstance(exc.details, dict) else {}
            if exc.logs:
                details = {**details, "logs": list(exc.logs)}
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Static analysis execution failed",
                error=str(exc),
                details=details,
            )
        except AnalysisNotReadyError as exc:
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Static analysis backend is not ready",
                error=str(exc),
            )
        except AnalysisError as exc:
            PROGRESS_REGISTRY.fail(job_id, "error", "Static analysis service error", error=str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("Static analysis job %s encountered an unexpected error", job_id)
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Unexpected static analysis failure",
                error=str(exc),
            )

    worker = threading.Thread(target=_run_job, name=f"static-analysis-{job_id[:8]}", daemon=True)
    worker.start()
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    assert snapshot is not None
    return snapshot


def get_static_analysis_job(
    job_id: str,
    from_event_id: Optional[int] = None,
) -> Optional[Dict[str, object]]:
    """
    Return the current snapshot for a running static analysis job.
    
    If from_event_id is provided, only return events after that ID (incremental update).
    Otherwise, return full snapshot with all events.
    """
    return PROGRESS_REGISTRY.snapshot(job_id, from_event_id=from_event_id)


def get_static_analysis_result(job_id: str) -> Optional[Dict[str, object]]:
    """Return the final static analysis result if the job completed."""
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    if not snapshot:
        return None
    if snapshot.get("status") != "completed":
        return None
    result = snapshot.get("result")
    if isinstance(result, dict):
        return result
    return None


def list_static_analysis_history(limit: int = 50) -> List[Dict[str, object]]:
    """Return persisted static analysis job history entries."""
    entries = analysis_state_repository.fetch_jobs(limit=limit)
    history: List[Dict[str, object]] = []
    for entry in entries:
        result = entry.get("result")
        result_dict = result if isinstance(result, dict) else None
        model_response = result_dict.get("modelResponse") if isinstance(result_dict, dict) else None
        metadata = model_response.get("metadata") if isinstance(model_response, dict) else None
        summary = model_response.get("summary") if isinstance(model_response, dict) else None
        inputs = result_dict.get("inputs") if isinstance(result_dict, dict) else None

        protocol = None
        protocol_version = None
        rule_set = None
        model_version = None
        summary_payload = summary if isinstance(summary, dict) else None
        overall_status = None

        if isinstance(metadata, dict):
            protocol = metadata.get("protocol")
            protocol_version = metadata.get("protocolVersion")
            rule_set = metadata.get("ruleSet")
            model_version = metadata.get("modelVersion")
        if summary_payload:
            overall_status = summary_payload.get("overallStatus")

        duration_ms = result_dict.get("durationMs") if result_dict else None
        submitted_at = result_dict.get("submittedAt") if result_dict else None
        analysis_id = result_dict.get("analysisId") if result_dict else None
        model_name = result_dict.get("model") if result_dict else None

        rules_file_name = None
        protocol_input_name = None
        if isinstance(inputs, dict):
            rules_file_name = inputs.get("rulesFileName")
            protocol_input_name = inputs.get("protocolName")
            if protocol is None:
                protocol = protocol_input_name

        snapshots = entry.get("workspace_snapshots")
        if isinstance(snapshots, list):
            workspace_snapshots = [item for item in snapshots if isinstance(item, dict)]
        else:
            workspace_snapshots = []

        history.append(
            {
                "jobId": entry.get("job_id"),
                "status": entry.get("status"),
                "stage": entry.get("stage"),
                "message": entry.get("message"),
                "workspacePath": entry.get("workspace_path"),
                "outputPath": entry.get("output_path"),
                "configPath": entry.get("config_path"),
                "logsPath": entry.get("logs_path"),
                "databasePath": entry.get("database_path"),
                "createdAt": entry.get("created_at"),
                "updatedAt": entry.get("updated_at"),
                "completedAt": entry.get("completed_at"),
                "error": entry.get("error"),
                "details": entry.get("details"),
                "analysisId": analysis_id,
                "model": model_name,
                "modelVersion": model_version,
                "durationMs": duration_ms,
                "submittedAt": submitted_at,
                "protocolName": protocol,
                "protocolVersion": protocol_version,
                "ruleSet": rule_set,
                "overallStatus": overall_status,
                "summary": summary_payload,
                "rulesFileName": rules_file_name,
                "workspaceSnapshots": workspace_snapshots,
            }
        )
    return history


def delete_static_analysis_job(job_id: str) -> bool:
    """Delete a static analysis job from the database.
    
    Returns True if the job was deleted, False if it didn't exist.
    Raises an exception if the deletion failed.
    """
    return analysis_state_repository.delete_job(job_id)
