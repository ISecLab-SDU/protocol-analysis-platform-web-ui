from __future__ import annotations

import os
import sys
import zipfile
import logging
import time
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import routes  # noqa: E402
from protocol_compliance import aflnet, fuzz_config_routes, fuzz_job_routes  # noqa: E402


def _create_completed_fuzz_config_job(
    tmp_path: Path,
    *,
    source_zip: Path,
    protocol: str = "MQTT",
) -> str:
    snapshot = fuzz_config_routes.FUZZ_CONFIG_JOBS.create(
        assert_generation_job_id="assert-job-1",
        instrumented_code_zip_path=source_zip,
        notes=None,
        protocol=protocol,
        protocol_implementations=["SOL"],
    )
    artifacts = snapshot["artifacts"]
    bundle = Path(artifacts["bundlePath"])
    (bundle / "target").mkdir(parents=True)
    (bundle / "seeds").mkdir(parents=True)
    program = bundle / "target" / "program"
    program.write_text("#!/usr/bin/env sh\n", encoding="utf-8")
    program.chmod(0o755)
    (bundle / "seeds" / "seed.raw").write_bytes(b"seed")
    Path(artifacts["manifestPath"]).write_text(
        "{}\n",
        encoding="utf-8",
    )
    Path(artifacts["envPath"]).write_text(
        (
            "{\n"
            '  "PG_FUZZ_PROTOCOL": "MQTT",\n'
            '  "PG_FUZZ_TARGET_BINARY": "/workspace/target/program",\n'
            '  "PG_FUZZ_TARGET_ARGS": "1883",\n'
            '  "PG_FUZZ_SEED_DIR": "/workspace/seeds",\n'
            '  "PG_FUZZ_NETSPEC": "tcp://127.0.0.1/1883"\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    fuzz_config_routes.FUZZ_CONFIG_JOBS.update(
        snapshot["jobId"],
        status="completed",
        stage="completed",
        artifacts={
            **artifacts,
            "instrumentedCodeZipPath": str(source_zip),
            "instrumentedCodePath": str(tmp_path / "instrumented_code"),
        },
    )
    return str(snapshot["jobId"])


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
    monkeypatch.setattr(
        routes, "verify_access_token", lambda _header: {"username": "admin"}
    )

    runtime_root = tmp_path / "protocolguard"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)
    fuzz_job_routes.FUZZ_JOBS._jobs.clear()
    fuzz_config_routes.FUZZ_CONFIG_JOBS._jobs.clear()

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
    fuzz_config_job_id = _create_completed_fuzz_config_job(tmp_path, source_zip=source_zip)

    response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={
            "assertGenerationJobId": "assert-job-1",
            "fuzzConfigJobId": fuzz_config_job_id,
            "protocol": "MQTT",
            "protocolImplementations": ["SOL"],
        },
    )

    assert response.status_code == 202
    payload = response.get_json()["data"]
    staged_zip = Path(payload["artifacts"]["instrumentedCodeZipPath"])
    instrumented_dir = Path(payload["artifacts"]["instrumentedCodePath"])
    output_root = Path(payload["artifacts"]["outputRoot"])

    assert payload["assertGenerationJobId"] == "assert-job-1"
    assert staged_zip.exists()
    assert (instrumented_dir / "instrumented_code" / "main.c").exists()
    assert output_root == Path(payload["artifacts"]["outputPath"]) / "aflnet-output"
    assert output_root.exists()
    assert commands
    assert f"-e PG_HOST_UID={os.getuid()}" in commands[0]
    assert f"-e PG_HOST_GID={os.getgid()}" in commands[0]
    assert "PG_FUZZ_TARGET_BINARY=/workspace/target/program" in commands[0]
    assert "PG_FUZZ_TARGET_ARGS=1883" in commands[0]
    assert "PG_FUZZ_SEED_DIR=/workspace/seeds" in commands[0]
    assert "PG_FUZZ_NETSPEC=tcp://127.0.0.1/1883" in commands[0]
    assert "PG_FUZZ_PROTOCOL=MQTT" in commands[0]
    assert f"{Path(payload['artifacts']['fuzzBundlePath'])}:/workspace:ro" in commands[0]
    assert f"{output_root}:/out/fuzz-output" in commands[0]


def test_start_fuzz_job_requires_completed_fuzz_config(monkeypatch, tmp_path: Path) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(
        routes, "verify_access_token", lambda _header: {"username": "admin"}
    )
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

    response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={"assertGenerationJobId": "assert-job-1", "protocol": "MQTT"},
    )

    assert response.status_code == 400


def test_fuzz_config_job_streams_agent_logs_and_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(
        routes, "verify_access_token", lambda _header: {"username": "admin"}
    )

    runtime_root = tmp_path / "protocolguard"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    fuzz_config_routes.FUZZ_CONFIG_JOBS._jobs.clear()

    source_zip = tmp_path / "instrumented_code.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("instrumented_code/main.c", "int main(void) { return 0; }\n")

    monkeypatch.setattr(
        fuzz_config_routes,
        "get_assert_generation_job",
        lambda job_id: {"jobId": job_id, "status": "completed"},
    )
    monkeypatch.setattr(
        fuzz_config_routes,
        "get_assert_generation_result",
        lambda job_id: {
            "jobId": job_id,
            "artifacts": {"instrumentedCodeZipPath": str(source_zip)},
        },
    )

    class FakeProcess:
        def __init__(self, command, **_kwargs):
            self.command = command
            self.pid = 1234
            self.stdout = StringIO(
                'PG_PROGRESS_JSON {"stage":"claude-command","message":"Bash: make"}\n'
            )
            self.stderr = StringIO("")

        def wait(self):
            bundle_arg = next(
                item for item in self.command if item.endswith(":/out/fuzz-bundle:rw")
            )
            bundle = Path(bundle_arg.split(":", 1)[0])
            (bundle / "target").mkdir(parents=True, exist_ok=True)
            (bundle / "seeds").mkdir(parents=True, exist_ok=True)
            (bundle / "evidence").mkdir(parents=True, exist_ok=True)
            (bundle / "target" / "program").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
            (bundle / "seeds" / "seed.raw").write_bytes(b"seed")
            (bundle / "fuzz-runtime.json").write_text('{"schemaVersion":1}\n', encoding="utf-8")
            (bundle / "fuzz-env.json").write_text(
                '{"PG_FUZZ_TARGET_BINARY":"/workspace/target/program"}\n',
                encoding="utf-8",
            )
            return 0

    monkeypatch.setattr(fuzz_config_routes.subprocess, "Popen", FakeProcess)

    response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/config-jobs",
        headers={"Authorization": "Bearer test-token"},
        json={
            "assertGenerationJobId": "assert-job-1",
            "protocol": "MQTT",
            "protocolImplementations": ["SOL"],
        },
    )

    assert response.status_code == 202
    job = response.get_json()["data"]
    log_response = None
    for _ in range(20):
        log_response = app.test_client().get(
            f"/api/protocol-compliance/fuzzing/config-jobs/{job['jobId']}/logs",
            headers={"Authorization": "Bearer test-token"},
            query_string={"fromPosition": 0},
        )
        if log_response.get_json()["data"]["job"]["status"] == "completed":
            break
        time.sleep(0.01)

    assert log_response is not None
    assert log_response.status_code == 200
    payload = log_response.get_json()["data"]
    assert payload["job"]["status"] == "completed"
    assert "PG_PROGRESS_JSON" in payload["content"]
    assert "Bash: make" in payload["content"]


def test_start_fuzz_job_rejects_missing_instrumented_zip(monkeypatch) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(
        routes, "verify_access_token", lambda _header: {"username": "admin"}
    )

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
    monkeypatch.setattr(
        routes, "verify_access_token", lambda _header: {"username": "admin"}
    )

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
    output_root = Path(payload["artifacts"]["outputRoot"])

    assert payload["assertGenerationJobId"] == "debug:assert-job-2"
    assert payload["debugSource"] == "instrumentedCodeZipPath"
    assert staged_zip.exists()
    assert (instrumented_dir / "instrumented_code" / "main.c").exists()
    assert output_root == Path(payload["artifacts"]["outputPath"]) / "aflnet-output"
    assert commands
    assert f"{instrumented_dir}:/workspace/instrumented_code:ro" in commands[0]
    assert f"{output_root}:/out/fuzz-output" in commands[0]


def test_start_dev_fuzz_job_uses_latest_instrumented_zip(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(
        routes, "verify_access_token", lambda _header: {"username": "admin"}
    )

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
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout="abc123def4567890\n", stderr=""
        ),
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


def test_fuzz_job_logs_include_docker_and_aflnet_runtime_output(
    caplog,
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(
        routes, "verify_access_token", lambda _header: {"username": "admin"}
    )

    runtime_root = tmp_path / "protocolguard"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.delenv("PG_OUTPUT_ROOT", raising=False)
    monkeypatch.delenv("AFLNET_OUTPUT_ROOT", raising=False)
    fuzz_job_routes.FUZZ_JOBS._jobs.clear()

    source_dir = runtime_root / "outputs" / "assert-job-logs"
    source_dir.mkdir(parents=True)
    source_zip = source_dir / "instrumented_code.zip"
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("instrumented_code/main.c", "int main(void) { return 0; }\n")

    def fake_run(command, *args, **kwargs):
        if isinstance(command, str) and command.startswith("docker run"):
            return SimpleNamespace(returncode=0, stdout="abc123def4567890\n", stderr="")
        if command[:2] == ["docker", "logs"]:
            assert "--timestamps" in command
            assert "--since" in command
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "2026-07-12T14:10:22.000000000Z afl-fuzz started\n"
                    "2026-07-12T14:10:23.000000000Z execs_done : 128\n"
                ),
                stderr=(
                    "2026-07-12T14:10:24.000000000Z "
                    "PROGRAM ABORT : No seed corpus found\n"
                ),
            )
        if isinstance(command, str) and command.startswith("docker ps -q"):
            return SimpleNamespace(returncode=0, stdout="abc123def4567890\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(fuzz_job_routes.subprocess, "run", fake_run)

    start_response = app.test_client().post(
        "/api/protocol-compliance/fuzzing/dev/jobs",
        headers={"Authorization": "Bearer test-token"},
        json={"instrumentedCodeZipPath": str(source_zip), "protocol": "MQTT"},
    )

    assert start_response.status_code == 202
    job = start_response.get_json()["data"]
    output_root = Path(job["artifacts"]["outputRoot"])
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "plot_data").write_text(
        "# unix_time, cycles_done, cur_path, paths_total, execs_per_sec\n"
        "1, 2, 3, 4, 5.5\n",
        encoding="utf-8",
    )
    (output_root / "queue").mkdir()
    (output_root / "queue" / "id:000000").write_text("seed", encoding="utf-8")

    caplog.clear()
    caplog.set_level(logging.INFO, logger="protocol_compliance.fuzz_job_routes")
    log_response = app.test_client().get(
        f"/api/protocol-compliance/fuzzing/jobs/{job['jobId']}/logs",
        headers={"Authorization": "Bearer test-token"},
        query_string={"fromPosition": 0},
    )

    assert log_response.status_code == 200
    content = log_response.get_json()["data"]["content"]
    updated_job = log_response.get_json()["data"]["job"]
    assert "Fuzz job" in content
    assert "Extracted source preview" in content
    assert "Synced Docker container logs: 2 stdout line(s), 1 stderr line(s)" in content
    assert "[container:stdout] afl-fuzz started" in content
    assert "[container:stdout] execs_done : 128" in content
    assert "[container:stderr] PROGRAM ABORT : No seed corpus found" in content
    assert "ERROR: AFLNet startup failed: PROGRAM ABORT : No seed corpus found" in content
    assert updated_job["status"] == "failed"
    assert updated_job["stage"] == "error"
    assert updated_job["error"] == "PROGRAM ABORT : No seed corpus found"
    assert "AFLNet plot_data emitted 2 new line(s)" in content
    assert "[plot_data] 1, 2, 3, 4, 5.5" in content
    assert "AFLNet output snapshot: plot_data" in content
    assert "queue/ (1 item)" in content
    assert any(
        record.name == "protocol_compliance.fuzz_job_routes"
        and "[container:stderr] PROGRAM ABORT : No seed corpus found"
        in record.getMessage()
        and record.protocolguard_context["job_id"] == job["jobId"]
        for record in caplog.records
    )


def test_start_dev_fuzz_job_rejects_zip_outside_runtime_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    monkeypatch.setattr(
        routes, "verify_access_token", lambda _header: {"username": "admin"}
    )

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


def test_aflnet_output_defaults_to_protocolguard_runtime_tree(
    monkeypatch, tmp_path: Path
) -> None:
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
