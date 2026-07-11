from __future__ import annotations

from io import BytesIO
import sys
import tarfile
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance.compiler import AgentExecutor, AgentExecutorSettings  # noqa: E402


def _executor(tmp_path: Path) -> AgentExecutor:
    executor = AgentExecutor.__new__(AgentExecutor)
    executor.settings = AgentExecutorSettings(
        enabled=True,
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
        workspace_root=tmp_path,
        max_runtime=60,
        env_passthrough=(),
    )
    return executor


class _FakeCompiler:
    def run(self, **_kwargs: Any) -> str:
        return "FROM scratch\n"


class _FakeDocker:
    def build(self, *_args: Any, **_kwargs: Any) -> tuple[bool, str]:
        return True, "build ok"

    def copy_output(self, *_args: Any, **_kwargs: Any) -> tuple[bool, str]:
        return True, "copy ok"


def test_generated_analysis_config_prefers_discovered_workspace_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / "job-1"
    build_dir = workspace / "project" / "demo" / "build"
    build_dir.mkdir(parents=True)
    (workspace / "project" / "demo" / "CMakeLists.txt").write_text("project(demo)\n", encoding="utf-8")
    (build_dir / "demo.bc").write_bytes(b"bc")
    (build_dir / "demo.ll").write_text("; ll\n", encoding="utf-8")
    (build_dir / "build_log.txt").write_text("build ok\n", encoding="utf-8")
    (build_dir / "demo").write_text("#!/bin/sh\n", encoding="utf-8")

    config = _executor(tmp_path)._build_analysis_config(
        workspace_dir=workspace,
        protocol_name="MQTT",
        protocol_version="3.1.1",
        project_name="Demo",
    )

    project = config["project"]
    assert project["project_path"] == "/workspace/project/demo"
    assert project["bitcode_path"] == "/workspace/project/demo/build/demo.bc"
    assert project["original_llvm_ir_path"] == "/workspace/project/demo/build/demo.ll"
    assert project["build_log_path"] == "/workspace/project/demo/build/build_log.txt"
    assert project["binary_path"] == "/workspace/project/demo/build/demo"
    assert project["protocol_name"] == "MQTT"
    assert project["protocol_version"] == "3.1.1"
    assert project["project_name"] == "Demo"


def test_generated_analysis_config_falls_back_to_workspace_conventions(tmp_path: Path) -> None:
    workspace = tmp_path / "job-2"
    workspace.mkdir()

    config = _executor(tmp_path)._build_analysis_config(
        workspace_dir=workspace,
        protocol_name=None,
        protocol_version=None,
        project_name=None,
    )

    project = config["project"]
    assert project["project_path"] == "/workspace"
    assert project["bitcode_path"] == "/workspace/program.bc"
    assert project["original_llvm_ir_path"] == "/workspace/program.bc"
    assert project["build_log_path"] == "/workspace/build_log.txt"
    assert project["binary_path"] == "/workspace/program"


def test_run_compilation_reports_generated_config_content(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    executor.compiler = _FakeCompiler()
    executor._docker_available = True
    executor.compiler.docker = _FakeDocker()
    executor._run_analysis_container = lambda *args, **kwargs: None
    source_file = tmp_path / "main.c"
    source_file.write_text("int main(void) { return 0; }\n", encoding="utf-8")
    archive = BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        tar.add(source_file, arcname="main.c")
    archive.seek(0)

    events: list[tuple[str, str, str]] = []
    generated_dockerfile = BACKEND_ROOT / "protocol_compliance" / "Dockerfile.txt"

    try:
        executor.run_compilation(
            code_stream=archive,
            code_filename="sol.tar",
            config_stream=None,
            config_filename="generated-config.toml",
            rules_stream=BytesIO(b'{"rules": []}'),
            rules_filename="rules.json",
            protocol_name="MQTT",
            protocol_version="3.1.1",
            project_name="Sol",
            job_id="job-generated-config-log",
            progress_callback=lambda job_id, stage, message: events.append((job_id, stage, message)),
        )
    finally:
        generated_dockerfile.unlink(missing_ok=True)

    config_events = [event for event in events if event[1] == "config"]

    assert config_events
    assert config_events[0][0] == "job-generated-config-log"
    assert "generated-config.toml" in config_events[0][2]
    assert "protocol_name = \"MQTT\"" in config_events[0][2]
    assert "project_name = \"Sol\"" in config_events[0][2]
