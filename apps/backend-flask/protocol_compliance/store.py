"""In-memory Protocol Compliance task store with lifecycle simulation."""

from __future__ import annotations

import random
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Literal, Optional


TaskStatus = Literal["completed", "failed", "processing", "queued"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProtocolComplianceTask:
    id: str
    name: str
    document_name: str
    document_size: Optional[int]
    description: Optional[str]
    tags: Optional[List[str]]
    status: TaskStatus
    progress: int
    submitted_at: str
    updated_at: str
    completed_at: Optional[str] = None
    result_payload: Optional[Dict[str, object]] = None


class TaskStore:
    """Maintain protocol compliance tasks and simulate async progression."""

    def __init__(self) -> None:
        self._tasks: List[ProtocolComplianceTask] = []
        self._lock = threading.Lock()
        self._timers: Dict[str, List[threading.Timer]] = {}

    def create_task(
        self,
        *,
        name: str,
        document_name: str,
        document_size: Optional[int],
        description: Optional[str],
        tags: Optional[List[str]],
    ) -> ProtocolComplianceTask:
        now = _now_iso()
        task = ProtocolComplianceTask(
            id=str(uuid.uuid4()),
            name=name,
            document_name=document_name,
            document_size=document_size,
            description=description,
            tags=tags if tags else None,
            status="queued",
            progress=18,
            submitted_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks.insert(0, task)
            if len(self._tasks) > 50:
                excess = self._tasks[50:]
                self._tasks = self._tasks[:50]
                for removed in excess:
                    self._clear_task_timers(removed.id)

        self._plan_lifecycle(task)
        return task

    def list_tasks(self, *, status: Optional[Iterable[TaskStatus]] = None) -> List[ProtocolComplianceTask]:
        with self._lock:
            tasks = list(self._tasks)

        if status:
            status_set = set(status)
            tasks = [task for task in tasks if task.status in status_set]

        tasks.sort(key=lambda item: item.submitted_at, reverse=True)
        return tasks

    def get_task(self, task_id: str) -> Optional[ProtocolComplianceTask]:
        with self._lock:
            for task in self._tasks:
                if task.id == task_id:
                    return task
        return None

    def serialize_task(self, task: ProtocolComplianceTask, base_url: str) -> Dict[str, object]:
        result_download_url: Optional[str]
        if task.status == "completed":
            result_download_url = f"{base_url.rstrip('/')}/api/protocol-compliance/tasks/{task.id}/result"
        else:
            result_download_url = None

        return {
            "id": task.id,
            "name": task.name,
            "documentName": task.document_name,
            "documentSize": task.document_size,
            "description": task.description,
            "tags": task.tags,
            "status": task.status,
            "progress": task.progress,
            "submittedAt": task.submitted_at,
            "updatedAt": task.updated_at,
            "completedAt": task.completed_at,
            "resultDownloadUrl": result_download_url,
        }

    # Internal helpers -------------------------------------------------

    def _plan_lifecycle(self, task: ProtocolComplianceTask) -> None:
        plan = [
            (0.6, {"progress": 35, "status": "processing"}),
            (1.6, {"progress": 68}),
            (2.8, {"progress": 85}),
            (4.2, {"progress": 100, "status": "completed", "completed": True}),
        ]

        for delay, patch in plan:
            timer = threading.Timer(delay, self._apply_patch, args=(task.id, patch))
            timer.daemon = True
            timer.start()
            self._register_timer(task.id, timer)

    def _register_timer(self, task_id: str, timer: threading.Timer) -> None:
        with self._lock:
            self._timers.setdefault(task_id, []).append(timer)

    def _clear_task_timers(self, task_id: str) -> None:
        timers = self._timers.pop(task_id, [])
        for timer in timers:
            timer.cancel()

    def _apply_patch(self, task_id: str, patch: Dict[str, object]) -> None:
        with self._lock:
            target = next((task for task in self._tasks if task.id == task_id), None)
            if not target:
                return

            now = _now_iso()
            target.progress = int(patch.get("progress", target.progress))
            target.status = patch.get("status", target.status)  # type: ignore[assignment]
            target.updated_at = now

            if patch.get("completed"):
                target.completed_at = now
                target.status = "completed"  # type: ignore[assignment]
                target.result_payload = self._build_result_payload(target)
                self._clear_task_timers(task_id)

    def _build_result_payload(self, task: ProtocolComplianceTask) -> Dict[str, object]:
        def random_rule() -> Dict[str, str]:
            action = random.choice(
                [
                    "验证握手报文结构",
                    "检查密钥交换流程",
                    "验证状态同步",
                    "校验加密套件协商",
                    "确认超时重传策略",
                ]
            )
            reference = f"RFC {random.randint(1000, 9000)}.{random.randint(1, 9)}"
            requirement = _random_sentence()
            return {"action": action, "reference": reference, "requirement": requirement}

        def random_finding() -> Dict[str, object]:
            description = _random_sentence(10, 22)
            section = f"{random.randint(1, 7)}.{random.randint(1, 9)}"
            severity = random.choice(["low", "medium", "high"])
            return {"description": description, "section": section, "severity": severity}

        rules = [random_rule() for _ in range(random.randint(4, 8))]
        findings = [random_finding() for _ in range(random.randint(1, 3))]

        return {
            "complianceSummary": {
                "criticalFindings": findings,
                "docTitle": task.name or task.document_name,
                "extractedAt": _now_iso(),
                "overview": _random_paragraph(),
            },
            "metadata": {
                "documentName": task.document_name,
                "documentSize": task.document_size,
                "taskId": task.id,
                "uploadedAt": task.submitted_at,
            },
            "protocolRules": rules,
            "tags": task.tags or [],
        }


def _random_sentence(min_words: int = 8, max_words: int = 18) -> str:
    word_count = random.randint(min_words, max_words)
    words = random.choices(_WORD_BANK, k=word_count)
    sentence = " ".join(words).capitalize() + "。"
    return sentence


def _random_paragraph(sentences: int = 3) -> str:
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


STORE = TaskStore()
