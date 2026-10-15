from __future__ import annotations

import io
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from flask import Flask
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import routes  # noqa: E402
from protocol_compliance import analysis  # noqa: E402
from protocol_compliance.analysis import (  # noqa: E402
    AnalysisExecutionError,
    normalize_protocol_name,
)


def _rule(request_type="PUBLISH"):
    return {
        "rule": "Validate the message.",
        "req_type": request_type,
        "req_fields": [],
        "res_type": "",
        "res_fields": [],
    }


def _app(monkeypatch) -> Flask:
    monkeypatch.setattr(routes, "_ensure_authenticated", lambda: (None, None))
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    return app


def test_grouped_rules_preserve_protocol_version_and_strip_metadata(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        routes,
        "submit_static_analysis_job",
        lambda **kwargs: captured.update(kwargs) or {"jobId": "test"},
    )
    rules = {"MQTT-3.1.1-rules": [_rule()]}
    response = (
        _app(monkeypatch)
        .test_client()
        .post(
            "/api/protocol-compliance/static-analysis",
            data={
                "codeArchive": (io.BytesIO(b"archive"), "sol.tar"),
                "rules": (io.BytesIO(json.dumps(rules).encode()), "rules.json"),
            },
        )
    )
    assert response.status_code == 202
    assert captured["protocol_name"] == "MQTT"
    assert captured["protocol_version"] == "3.1.1"
    assert json.loads(captured["rules_payload"][1]) == rules


@pytest.mark.parametrize(
    "rules,form,fragment",
    [
        ({"MQTT-3.1.1-rules": [_rule("")]}, {}, "req_type"),
        ({"DEFAULT": [_rule("CUSTOM")]}, {}, "protocol"),
        ({"MQTT-3.1.1-rules": [_rule()]}, {"protocolName": "FTP"}, "conflicts"),
        ({"PUBLISH": [{**_rule(), "req_fields": None}]}, {}, "req_fields"),
        ({"PUBLISH": [{**_rule(), "res_fields": ["status"]}]}, {}, "res_type"),
        ({}, {}, "no analyzable rules"),
        ([], {}, "root"),
    ],
)
def test_invalid_rules_fail_before_a_job_is_created(monkeypatch, rules, form, fragment):
    def unexpected(**kwargs):
        pytest.fail("Invalid input must not create an analysis job")

    monkeypatch.setattr(routes, "submit_static_analysis_job", unexpected)
    response = (
        _app(monkeypatch)
        .test_client()
        .post(
            "/api/protocol-compliance/static-analysis",
            data={
                "codeArchive": (io.BytesIO(b"archive"), "sol.tar"),
                "rules": (io.BytesIO(json.dumps(rules).encode()), "rules.json"),
                **form,
            },
        )
    )
    assert response.status_code == 400
    assert fragment.lower() in response.get_data(as_text=True).lower()


def test_metadata_envelope_is_converted_to_compiler_rules(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        routes,
        "submit_static_analysis_job",
        lambda **kwargs: captured.update(kwargs) or {"jobId": "test"},
    )
    response = (
        _app(monkeypatch)
        .test_client()
        .post(
            "/api/protocol-compliance/static-analysis",
            data={
                "codeArchive": (io.BytesIO(b"archive"), "sol.tar"),
                "rules": (
                    io.BytesIO(
                        json.dumps(
                            {
                                "protocol": "mqtt",
                                "protocolVersion": "3.1.1",
                                "rules": [_rule()],
                            }
                        ).encode()
                    ),
                    "rules.json",
                ),
            },
        )
    )
    assert response.status_code == 202
    assert captured["protocol_name"] == "MQTT"
    assert json.loads(captured["rules_payload"][1]) == {"rules": [_rule()]}


def test_malformed_json_is_rejected(monkeypatch):
    response = (
        _app(monkeypatch)
        .test_client()
        .post(
            "/api/protocol-compliance/static-analysis",
            data={
                "codeArchive": (io.BytesIO(b"archive"), "sol.tar"),
                "rules": (io.BytesIO(b"{broken"), "rules.json"),
            },
        )
    )
    assert response.status_code == 400


def test_protocol_name_is_inferred_from_ftp_rule_type_when_metadata_is_unknown() -> (
    None
):
    assert normalize_protocol_name({"protocol": "UNKNOWN", "CCC": []}, "rules") == "FTP"


def test_protocol_name_is_inferred_from_nested_ftp_request_type() -> None:
    rules = {
        "FTP-5-rules": [
            {
                "rule": "REINITIALIZE terminates the current user session.",
                "req_type": "REIN",
                "res_type": "220",
            }
        ]
    }

    assert normalize_protocol_name(rules, "rules") == "FTP"


def test_static_analysis_rejects_empty_rule_results(
    monkeypatch, tmp_path: Path
) -> None:
    database_path = tmp_path / "analysis.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            """
            CREATE TABLE rule_code_snippet (
                rule_desc TEXT PRIMARY KEY,
                code_snippet TEXT NOT NULL,
                call_graph TEXT NOT NULL,
                llm_response TEXT NOT NULL DEFAULT ''
            )
            """
        )

    class FakeRunner:
        def __init__(self, _settings: object) -> None:
            pass

        def run_compilation(self, **_kwargs: object) -> dict[str, Any]:
            return {"artifacts": {"database": str(database_path)}}

    monkeypatch.setattr(
        analysis, "_agent_settings", lambda: SimpleNamespace(enabled=True)
    )
    monkeypatch.setattr(analysis, "ClaudeBuilderRunner", FakeRunner)
    events: list[tuple[str, str, str]] = []

    with pytest.raises(
        AnalysisExecutionError,
        match="ProtocolGuard analysis produced no rule results",
    ):
        analysis.run_static_analysis(
            code_stream=io.BytesIO(b"archive"),
            code_file_name="project.zip",
            config_stream=None,
            config_file_name="generated-config.toml",
            rules_stream=io.BytesIO(b"{}"),
            rules_file_name="rules.json",
            notes=None,
            protocol_name="FTP",
            protocol_version=None,
            project_name=None,
            rules_summary=None,
            job_id="empty-result-job",
            progress_callback=lambda job_id, stage, message: events.append(
                (job_id, stage, message)
            ),
        )

    assert all(stage != "completed" for _, stage, _ in events)


def test_static_analysis_accepts_generated_config_inputs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_submit_static_analysis_job(**kwargs):
        captured.update(kwargs)
        return {"jobId": "job-generated-config", "status": "queued"}

    monkeypatch.setattr(
        routes, "submit_static_analysis_job", fake_submit_static_analysis_job
    )

    rules = {
        "protocol": "MQTT",
        "protocolVersion": "5.0",
        "rules": [_rule("CONNECT")],
    }
    response = (
        _app(monkeypatch)
        .test_client()
        .post(
            "/api/protocol-compliance/static-analysis",
            data={
                "codeArchive": (io.BytesIO(b"archive-bytes"), "sol.tar.gz"),
                "rules": (io.BytesIO(json.dumps(rules).encode("utf-8")), "rules.json"),
                "protocolName": "MQTT",
                "protocolVersion": "3.1.1",
                "projectName": "Sol",
            },
            content_type="multipart/form-data",
        )
    )

    assert response.status_code == 202
    assert captured["config_payload"] == ("generated-config.toml", None)
    assert captured["protocol_name"] == "MQTT"
    assert captured["protocol_version"] == "3.1.1"
    assert captured["project_name"] == "Sol"
    assert captured["code_payload"] == ("sol.tar.gz", b"archive-bytes")


def test_static_analysis_uses_rules_metadata_when_form_protocol_missing(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_submit_static_analysis_job(**kwargs):
        captured.update(kwargs)
        return {"jobId": "job-rules-metadata", "status": "queued"}

    monkeypatch.setattr(
        routes, "submit_static_analysis_job", fake_submit_static_analysis_job
    )

    rules = {
        "protocol": "MQTT",
        "protocolVersion": "3.1.1",
        "rules": [_rule("PUBLISH")],
    }
    response = (
        _app(monkeypatch)
        .test_client()
        .post(
            "/api/protocol-compliance/static-analysis",
            data={
                "codeArchive": (io.BytesIO(b"archive-bytes"), "sol.tar.gz"),
                "rules": (io.BytesIO(json.dumps(rules).encode("utf-8")), "rules.json"),
            },
            content_type="multipart/form-data",
        )
    )

    assert response.status_code == 202
    assert captured["config_payload"] == ("generated-config.toml", None)
    assert captured["protocol_name"] == "MQTT"
    assert captured["protocol_version"] == "3.1.1"
    assert captured["project_name"] is None
