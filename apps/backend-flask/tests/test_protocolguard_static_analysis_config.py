from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import routes  # noqa: E402


def _app(monkeypatch) -> Flask:
    monkeypatch.setattr(routes, "_ensure_authenticated", lambda: (None, None))
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    return app


def test_static_analysis_accepts_generated_config_inputs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_submit_static_analysis_job(**kwargs):
        captured.update(kwargs)
        return {"jobId": "job-generated-config", "status": "queued"}

    monkeypatch.setattr(routes, "submit_static_analysis_job", fake_submit_static_analysis_job)

    rules = {
        "protocol": "MQTT-from-rules",
        "protocolVersion": "5.0",
        "rules": [{"requirement": "CONNECT must be validated"}],
    }
    response = _app(monkeypatch).test_client().post(
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

    assert response.status_code == 202
    assert captured["config_payload"] == ("generated-config.toml", None)
    assert captured["protocol_name"] == "MQTT"
    assert captured["protocol_version"] == "3.1.1"
    assert captured["project_name"] == "Sol"
    assert captured["code_payload"] == ("sol.tar.gz", b"archive-bytes")


def test_static_analysis_uses_rules_metadata_when_form_protocol_missing(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_submit_static_analysis_job(**kwargs):
        captured.update(kwargs)
        return {"jobId": "job-rules-metadata", "status": "queued"}

    monkeypatch.setattr(routes, "submit_static_analysis_job", fake_submit_static_analysis_job)

    rules = {
        "protocol": "MQTT",
        "protocolVersion": "3.1.1",
        "rules": [{"requirement": "PUBLISH QoS must be checked"}],
    }
    response = _app(monkeypatch).test_client().post(
        "/api/protocol-compliance/static-analysis",
        data={
            "codeArchive": (io.BytesIO(b"archive-bytes"), "sol.tar.gz"),
            "rules": (io.BytesIO(json.dumps(rules).encode("utf-8")), "rules.json"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    assert captured["config_payload"] == ("generated-config.toml", None)
    assert captured["protocol_name"] == "MQTT"
    assert captured["protocol_version"] == "3.1.1"
    assert captured["project_name"] is None
