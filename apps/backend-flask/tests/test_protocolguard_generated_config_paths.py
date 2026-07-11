from __future__ import annotations

import sys
from pathlib import Path

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
