from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import routes  # noqa: E402


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
