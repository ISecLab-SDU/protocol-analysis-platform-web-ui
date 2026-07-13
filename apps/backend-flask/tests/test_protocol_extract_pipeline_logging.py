from __future__ import annotations

import io
import logging
import sys
from pathlib import Path
from typing import Any

import pytest
from werkzeug.datastructures import FileStorage

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import pipeline_runner  # noqa: E402


class FakeProcess:
    def __init__(self, lines: list[str], return_code: int) -> None:
        self.stdout = io.StringIO("\n".join(lines) + "\n")
        self._return_code = return_code

    def wait(self) -> int:
        return self._return_code


def _upload() -> FileStorage:
    return FileStorage(stream=io.BytesIO(b"<html></html>"), filename="rfc.html")


def _set_openai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai.example/v1/")
    monkeypatch.setenv("PROTOCOL_EXTRACT_LLM_BASE_URL", "https://legacy.example/v1")


def test_pipeline_streams_child_output_with_job_stage_and_levels(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_openai_env(monkeypatch)
    store_root = tmp_path / "store"
    result_path = store_root / "ftp_5" / "ruleDir" / "processed_results.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        '[{"rule":"USER must precede PASS","req_type":["USER"],'
        '"req_fields":[],"res_type":[],"res_fields":[]}]',
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline_runner, "PIPELINE_ROOT", tmp_path)
    monkeypatch.setattr(pipeline_runner, "STORAGE_ROOT", store_root)
    monkeypatch.setattr(pipeline_runner, "UPLOAD_ROOT", tmp_path / "uploads")
    pipeline_runner.UPLOAD_ROOT.mkdir()
    popen_calls: list[dict[str, Any]] = []

    def fake_popen(*args: Any, **kwargs: Any) -> FakeProcess:
        popen_calls.append(kwargs)
        return FakeProcess(
            [
                "开始 文档处理阶段",
                "[DEBUG] selected章节数: 1",
                "[WARN] empty heading skipped",
                "开始 规则处理阶段",
            ],
            0,
        )

    monkeypatch.setattr(pipeline_runner.subprocess, "Popen", fake_popen)

    caplog.set_level(logging.DEBUG, logger="protocol_compliance.pipeline_runner")
    result = pipeline_runner.run_protocol_pipeline(
        protocol="FTP",
        version="5",
        html_upload=_upload(),
        job_id="extract-job",
    )

    assert len(result.rules) == 1
    assert popen_calls[0]["env"]["OPENAI_API_KEY"] == "secret-key"
    assert popen_calls[0]["env"]["OPENAI_BASE_URL"] == "https://openai.example/v1"
    assert "PROTOCOL_EXTRACT_LLM_BASE_URL" not in popen_calls[0]["env"]
    records = [record for record in caplog.records if "[job extract-job]" in record.message]
    assert any(record.levelno == logging.DEBUG and "selected章节数" in record.message for record in records)
    assert any(record.levelno == logging.WARNING and "empty heading" in record.message for record in records)
    assert any("[document]" in record.message for record in records)
    assert any("[rule-filter]" in record.message for record in records)
    assert any("[completed]" in record.message for record in records)


def test_pipeline_redacts_and_logs_subprocess_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_openai_env(monkeypatch)
    monkeypatch.setattr(pipeline_runner, "PIPELINE_ROOT", tmp_path)
    monkeypatch.setattr(pipeline_runner, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(pipeline_runner, "LOG_ROOT", tmp_path / "logs")
    pipeline_runner.UPLOAD_ROOT.mkdir()
    pipeline_runner.LOG_ROOT.mkdir()
    monkeypatch.setattr(
        pipeline_runner.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess(
            ["开始 规则处理阶段", "ERROR secret-key request failed"],
            7,
        ),
    )

    caplog.set_level(logging.DEBUG, logger="protocol_compliance.pipeline_runner")
    with pytest.raises(pipeline_runner.PipelineExecutionError) as error:
        pipeline_runner.run_protocol_pipeline(
            protocol="FTP",
            version="5",
            html_upload=_upload(),
            job_id="extract-job",
        )

    assert error.value.log_path
    assert "secret-key" not in (error.value.stdout or "")
    assert "<API_KEY>" in (error.value.stdout or "")
    failure_records = [
        record
        for record in caplog.records
        if record.levelno == logging.ERROR and "[job extract-job]" in record.message
    ]
    assert any("[rule-filter]" in record.message for record in failure_records)
    assert any(
        cast_context(record).get("return_code") == 7 for record in failure_records
    )


@pytest.mark.parametrize(
    ("missing_name", "expected_message"),
    [
        ("OPENAI_API_KEY", "环境变量 OPENAI_API_KEY 不能为空"),
        ("OPENAI_BASE_URL", "环境变量 OPENAI_BASE_URL 不能为空"),
    ],
)
def test_pipeline_requires_openai_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    missing_name: str,
    expected_message: str,
) -> None:
    _set_openai_env(monkeypatch)
    monkeypatch.delenv(missing_name)
    monkeypatch.setattr(pipeline_runner, "PIPELINE_ROOT", tmp_path)

    with pytest.raises(ValueError, match=expected_message):
        pipeline_runner.run_protocol_pipeline(
            protocol="FTP",
            version="5",
            html_upload=_upload(),
        )


def cast_context(record: logging.LogRecord) -> dict[str, Any]:
    return getattr(record, "protocolguard_context", {})
