from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import routes  # noqa: E402


def test_aflnet_artifact_routes_keep_legacy_endpoint_names() -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)

    aflnet_rules = {
        rule.rule: rule.endpoint
        for rule in app.url_map.iter_rules()
        if "aflnet-result" in rule.rule
    }

    assert aflnet_rules == {
        "/api/protocol-compliance/fuzzing/aflnet-result/download": (
            "protocol_compliance.download_aflnet_result"
        ),
        "/api/protocol-compliance/fuzzing/aflnet-result/snapshot": (
            "protocol_compliance.snapshot_aflnet_result"
        ),
        "/api/protocol-compliance/fuzzing/aflnet-result/artifacts/<artifact_id>/download": (
            "protocol_compliance.download_aflnet_result_artifact"
        ),
    }


def test_legacy_fuzz_routes_keep_legacy_endpoint_names() -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)

    legacy_fuzz_rules = {
        rule.rule: rule.endpoint
        for rule in app.url_map.iter_rules()
        if rule.rule
        in {
            "/api/protocol-compliance/check-status",
            "/api/protocol-compliance/execute-command",
            "/api/protocol-compliance/pre-start-cleanup",
            "/api/protocol-compliance/read-log",
            "/api/protocol-compliance/stop-and-cleanup",
            "/api/protocol-compliance/stop-process",
            "/api/protocol-compliance/write-script",
        }
    }

    assert legacy_fuzz_rules == {
        "/api/protocol-compliance/check-status": "protocol_compliance.check_status",
        "/api/protocol-compliance/execute-command": "protocol_compliance.execute_command",
        "/api/protocol-compliance/pre-start-cleanup": (
            "protocol_compliance.pre_start_cleanup"
        ),
        "/api/protocol-compliance/read-log": "protocol_compliance.read_log",
        "/api/protocol-compliance/stop-and-cleanup": (
            "protocol_compliance.stop_and_cleanup"
        ),
        "/api/protocol-compliance/stop-process": "protocol_compliance.stop_process",
        "/api/protocol-compliance/write-script": "protocol_compliance.write_script",
    }


def test_execute_command_passes_host_identity_to_protocolguard_container(monkeypatch, tmp_path: Path) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(routes, "verify_access_token", lambda _header: {"username": "admin"})
    runtime_root = tmp_path / "protocolguard"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)

    commands: list[str] = []

    def fake_run(command, *args, **kwargs):
        commands.append(command)
        if "docker ps -q --filter id=" in command:
            return SimpleNamespace(returncode=0, stdout="abc123def456\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="abc123def4567890\n", stderr="")

    monkeypatch.setattr(routes.subprocess, "run", fake_run)

    response = app.test_client().post(
        "/api/protocol-compliance/execute-command",
        headers={"Authorization": "Bearer test-token"},
        json={
            "protocol": "MQTT",
            "protocolImplementations": ["SOL"],
        },
    )

    assert response.status_code == 200
    docker_run_command = commands[0]
    assert f"-e PG_HOST_UID={os.getuid()}" in docker_run_command
    assert f"-e PG_HOST_GID={os.getgid()}" in docker_run_command


def test_legacy_fuzz_status_logs_use_protocolguard_context(
    caplog,
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(routes, "verify_access_token", lambda _header: {"username": "admin"})
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(tmp_path / "protocolguard"))

    def fake_run(command, *args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(routes.subprocess, "run", fake_run)

    with caplog.at_level(logging.DEBUG, logger="protocol_compliance.routes"):
        response = app.test_client().post(
            "/api/protocol-compliance/check-status",
            headers={"Authorization": "Bearer test-token"},
            json={
                "protocol": "MQTT",
                "protocolImplementations": ["SOL"],
            },
        )

    assert response.status_code == 200
    status_log = next(
        record for record in caplog.records if "状态检查结果" in record.getMessage()
    )
    assert "[job fuzz][fuzz] 状态检查结果:" in status_log.getMessage()
    assert cast(Any, status_log).protocolguard_context == {}


def test_aflnet_output_defaults_to_protocolguard_runtime_tree(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "protocolguard"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)

    expected_output_root = runtime_root / "fuzz-output"

    assert routes._aflnet_output_root() == expected_output_root
    assert routes._aflnet_log_file_for_source() == expected_output_root / "plot_data"

    command = routes._aflnet_shell_command()

    assert expected_output_root.exists()
    assert f"-v {expected_output_root}:/out/fuzz-output" in command
