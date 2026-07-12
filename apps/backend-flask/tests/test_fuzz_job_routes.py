from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import routes  # noqa: E402
from protocol_compliance import aflnet, fuzz_job_routes  # noqa: E402


def test_aflnet_artifact_routes_keep_result_endpoint_names() -> None:
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


def test_fuzz_job_routes_replace_legacy_public_routes() -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)

    fuzz_rules = {
        rule.rule: rule.endpoint
        for rule in app.url_map.iter_rules()
        if "/fuzzing/jobs" in rule.rule or "/fuzzing/dev/jobs" in rule.rule
    }
    legacy_route_names = {
        "/api/protocol-compliance/check-status",
        "/api/protocol-compliance/execute-command",
        "/api/protocol-compliance/pre-start-cleanup",
        "/api/protocol-compliance/read-log",
        "/api/protocol-compliance/stop-and-cleanup",
        "/api/protocol-compliance/stop-process",
        "/api/protocol-compliance/write-script",
    }
    legacy_rules = {
        rule.rule: rule.endpoint
        for rule in app.url_map.iter_rules()
        if rule.rule in legacy_route_names
    }

    assert fuzz_rules == {
        "/api/protocol-compliance/fuzzing/jobs": "protocol_compliance.start_fuzz_job",
        "/api/protocol-compliance/fuzzing/dev/jobs": "protocol_compliance.start_dev_fuzz_job",
        "/api/protocol-compliance/fuzzing/jobs/<job_id>": "protocol_compliance.get_fuzz_job",
        "/api/protocol-compliance/fuzzing/jobs/<job_id>/logs": "protocol_compliance.read_fuzz_job_logs",
        "/api/protocol-compliance/fuzzing/jobs/<job_id>/stop": "protocol_compliance.stop_fuzz_job",
    }
    assert legacy_rules == {}


def test_start_fuzz_job_stages_instrumented_code_zip(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(routes, "verify_access_token", lambda _header: {"username": "admin"})

    runtime_root = tmp_path / "protocolguard"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)
    fuzz_job_routes.FUZZ_JOBS._jobs.clear()

    source_zip = tmp_path / "instrumented_code.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("instrumented_code/main.c", "int main(void) { return 0; }\n")

    monkeypatch.setattr(
        fuzz_job_routes,
        "get_assert_generation_job",
        lambda job_id: {"jobId": job_id, "status": "completed"},
    )
    monkeypatch.setattr(
        fuzz_job_routes,
        "get_assert_generation_result",
        lambda job_id: {
            "jobId": job_id,
            "artifacts": {"instrumentedCodeZipPath": str(source_zip)},
        },
    )

    commands: list[str] = []

    def fake_run(command, *args, **kwargs):
        commands.append(command if isinstance(command, str) else " ".join(command))
        return SimpleNamespace(returncode=0, stdout="abc123def4567890\n", stderr="")

    monkeypatch.setattr(fuzz_job_routes.subprocess, "run", fake_run)

    response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={
            "assertGenerationJobId": "assert-job-1",
            "protocol": "MQTT",
            "protocolImplementations": ["SOL"],
        },
    )

    assert response.status_code == 202
    payload = response.get_json()["data"]
    staged_zip = Path(payload["artifacts"]["instrumentedCodeZipPath"])
    instrumented_dir = Path(payload["artifacts"]["instrumentedCodePath"])

    assert payload["assertGenerationJobId"] == "assert-job-1"
    assert staged_zip.exists()
    assert (instrumented_dir / "instrumented_code" / "main.c").exists()
    assert commands
    assert f"-e PG_HOST_UID={os.getuid()}" in commands[0]
    assert f"-e PG_HOST_GID={os.getgid()}" in commands[0]
    assert "PG_FUZZ_INSTRUMENTED_CODE_DIR=/workspace/instrumented_code" in commands[0]
    assert f"{instrumented_dir}:/workspace/instrumented_code:ro" in commands[0]


def test_start_fuzz_job_rejects_missing_instrumented_zip(monkeypatch) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(routes, "verify_access_token", lambda _header: {"username": "admin"})

    monkeypatch.setattr(
        fuzz_job_routes,
        "get_assert_generation_job",
        lambda job_id: {"jobId": job_id, "status": "completed"},
    )
    monkeypatch.setattr(
        fuzz_job_routes,
        "get_assert_generation_result",
        lambda job_id: {"jobId": job_id, "artifacts": {}},
    )

    response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={
            "assertGenerationJobId": "assert-job-1",
            "protocol": "MQTT",
        },
    )

    assert response.status_code == 400


def test_start_dev_fuzz_job_accepts_instrumented_zip_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(routes, "verify_access_token", lambda _header: {"username": "admin"})

    runtime_root = tmp_path / "protocolguard"
    source_dir = runtime_root / "outputs" / "assert-job-2"
    source_dir.mkdir(parents=True)
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)
    fuzz_job_routes.FUZZ_JOBS._jobs.clear()

    source_zip = source_dir / "instrumented_code.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("instrumented_code/main.c", "int main(void) { return 0; }\n")

    commands: list[str] = []

    def fake_run(command, *args, **kwargs):
        commands.append(command if isinstance(command, str) else " ".join(command))
        return SimpleNamespace(returncode=0, stdout="abc123def4567890\n", stderr="")

    monkeypatch.setattr(fuzz_job_routes.subprocess, "run", fake_run)

    response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/dev/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={
            "instrumentedCodeZipPath": str(source_zip),
            "protocol": "MQTT",
            "protocolImplementations": ["SOL"],
        },
    )

    assert response.status_code == 202
    payload = response.get_json()["data"]
    staged_zip = Path(payload["artifacts"]["instrumentedCodeZipPath"])
    instrumented_dir = Path(payload["artifacts"]["instrumentedCodePath"])

    assert payload["assertGenerationJobId"] == "debug:assert-job-2"
    assert payload["debugSource"] == "instrumentedCodeZipPath"
    assert staged_zip.exists()
    assert (instrumented_dir / "instrumented_code" / "main.c").exists()
    assert commands
    assert f"{instrumented_dir}:/workspace/instrumented_code:ro" in commands[0]


def test_start_dev_fuzz_job_uses_latest_instrumented_zip(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(routes, "verify_access_token", lambda _header: {"username": "admin"})

    runtime_root = tmp_path / "protocolguard"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)
    fuzz_job_routes.FUZZ_JOBS._jobs.clear()

    older_zip = runtime_root / "outputs" / "older" / "instrumented_code.zip"
    newer_zip = runtime_root / "outputs" / "newer" / "instrumented_code.zip"
    older_zip.parent.mkdir(parents=True)
    newer_zip.parent.mkdir(parents=True)
    with zipfile.ZipFile(older_zip, "w") as archive:
        archive.writestr("instrumented_code/older.c", "int older(void) { return 0; }\n")
    with zipfile.ZipFile(newer_zip, "w") as archive:
        archive.writestr("instrumented_code/newer.c", "int newer(void) { return 0; }\n")
    os.utime(older_zip, (1_700_000_000, 1_700_000_000))
    os.utime(newer_zip, (1_800_000_000, 1_800_000_000))

    monkeypatch.setattr(
        fuzz_job_routes.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="abc123def4567890\n", stderr=""),
    )

    response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/dev/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={"protocol": "MQTT"},
    )

    assert response.status_code == 202
    payload = response.get_json()["data"]
    assert payload["inputs"]["instrumentedCodeZipPath"] == str(newer_zip)
    assert payload["assertGenerationJobId"] == "debug:newer"


def test_start_dev_fuzz_job_rejects_zip_outside_runtime_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(routes, "verify_access_token", lambda _header: {"username": "admin"})

    runtime_root = tmp_path / "protocolguard"
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)

    source_zip = outside_dir / "instrumented_code.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("instrumented_code/main.c", "int main(void) { return 0; }\n")

    response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/dev/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={"instrumentedCodeZipPath": str(source_zip)},
    )

    assert response.status_code == 400


def test_aflnet_output_defaults_to_protocolguard_runtime_tree(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "protocolguard"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)

    expected_output_root = runtime_root / "fuzz-output"

    assert aflnet._aflnet_output_root() == expected_output_root
    assert aflnet._aflnet_log_file_for_source() == expected_output_root / "plot_data"

    command = aflnet._aflnet_shell_command()

    assert expected_output_root.exists()
    assert f"-v {expected_output_root}:/out/fuzz-output" in command
