from __future__ import annotations

import sys
import tarfile
from pathlib import Path
from typing import Any, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance.compiler import CompilerController  # noqa: E402
from protocol_compliance.compiler import AgentExecutor, AgentExecutorSettings  # noqa: E402


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        *,
        config: str,
        rule: dict[str, Any],
        structure: str,
        error_log: str | None = None,
        last_dockerfile: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "config": config,
                "rule": rule,
                "structure": structure,
                "error_log": error_log,
                "last_dockerfile": last_dockerfile,
            }
        )
        return "FROM scratch\n"


class FakeDocker:
    def __init__(self) -> None:
        self.build_calls: list[tuple[str, str]] = []
        self.check_calls: list[str] = []
        self.copy_calls: list[tuple[str, str]] = []

    def build(
        self,
        _path: str,
        *,
        tag: str,
        dockerfile_content: str,
        build_context: str,
    ) -> tuple[bool, str]:
        self.build_calls.append((tag, build_context))
        return True, "build ok"

    def check_output(self, image_tag: str) -> tuple[bool, str]:
        self.check_calls.append(image_tag)
        return True, "workspace ok"

    def copy_output(self, image_tag: str, dest_path: str) -> tuple[bool, str]:
        self.copy_calls.append((image_tag, dest_path))
        return True, "copy ok"


def _controller() -> CompilerController:
    controller = cast(Any, CompilerController.__new__(CompilerController))
    controller.llm = FakeLLM()
    controller.docker = FakeDocker()
    controller.max_runtime = 60
    return cast(CompilerController, controller)


def _tar_file(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    tar_path = tmp_path / "sol.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(source / "main.c", arcname="main.c")
    return tar_path


def test_compiler_controller_reports_ai_compilation_progress(tmp_path: Path) -> None:
    controller = _controller()
    tar_path = _tar_file(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    events: list[tuple[str, str, str]] = []

    dockerfile = controller.run(
        sol_tar=str(tar_path),
        config_content='protocol = "demo"\n',
        rule_content='{"rules": []}',
        output_dir=str(output_dir),
        job_id="job-compiler",
        progress_callback=lambda job_id, stage, message: events.append((job_id, stage, message)),
    )

    assert dockerfile == "FROM scratch\n"
    assert events == [
        ("job-compiler", "compile", "Prepared AI compiler build context"),
        ("job-compiler", "compile", "Round 1: generating Dockerfile with AI"),
        ("job-compiler", "compile", "Round 1: generated Dockerfile"),
        ("job-compiler", "compile", "Round 1: building generated Dockerfile"),
        ("job-compiler", "compile", "Round 1: Docker image build succeeded"),
        ("job-compiler", "compile", "Round 1: validating builder output"),
        ("job-compiler", "compile", "Round 1: builder output validated"),
        ("job-compiler", "compile", "Round 1: copying builder output"),
        ("job-compiler", "compile", "Round 1: builder output copied"),
    ]


def test_agent_settings_enable_claude_builder_from_anthropic_env(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("PG_CLAUDE_BUILDER_IMAGE", "protocolguard-claude-builder:test")

    settings = AgentExecutorSettings.from_env()

    assert settings.enabled is True
    assert settings.api_key == "test-anthropic-key"
    assert settings.base_url == "https://example.invalid"
    assert settings.builder_image == "protocolguard-claude-builder:test"
    assert "ANTHROPIC_API_KEY" in settings.env_passthrough
    assert "ANTHROPIC_BASE_URL" in settings.env_passthrough


def test_agent_executor_forwards_anthropic_env_without_openai_fallback(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://anthropic.example/v1")
    settings = AgentExecutorSettings(
        enabled=True,
        api_key="anthropic-key",
        base_url="https://anthropic.example/v1",
        model="unused",
        workspace_root=tmp_path,
        max_runtime=60,
        env_passthrough=("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"),
        builder_image="protocolguard-claude-builder:test",
    )
    executor = AgentExecutor(settings)

    env = executor._build_passthrough_environment()

    assert "OPENAI_API_KEY" not in env
    assert env["ANTHROPIC_API_KEY"] == "anthropic-key"
    assert env["ANTHROPIC_BASE_URL"] == "https://anthropic.example/v1"
    assert env["PG_HOST_UID"]
    assert env["PG_HOST_GID"]

    env_args = executor._docker_env_args()
    assert ["-e", "ANTHROPIC_API_KEY"] == env_args[0:2]
    assert "OPENAI_API_KEY" not in env_args
    assert "-e" in env_args
    assert "IS_SANDBOX=1" in env_args


def test_agent_executor_redacts_secret_command_values() -> None:
    command = [
        "docker",
        "run",
        "-e",
        "ANTHROPIC_API_KEY=secret",
        "-e",
        "PG_HOST_UID=1000",
    ]

    assert AgentExecutor._redact_command(command) == [
        "docker",
        "run",
        "-e",
        "ANTHROPIC_API_KEY=<redacted>",
        "-e",
        "PG_HOST_UID=1000",
    ]


def test_agent_executor_classifies_claude_builder_log_markers() -> None:
    assert (
        AgentExecutor._claude_builder_progress_stage(
            "[claude-command] cmake -S . -B build",
            "builder-log",
        )
        == "claude-command"
    )
    assert (
        AgentExecutor._claude_builder_progress_stage(
            "[pg-builder][config.toml] protocol_name = \"MQTT\"",
            "builder-log",
        )
        == "claude-config"
    )
    assert (
        AgentExecutor._claude_builder_progress_stage(
            "[pg-builder][artifact-file] /workspace/program.bc: LLVM IR bitcode",
            "builder-log",
        )
        == "claude-artifact"
    )
    assert (
        AgentExecutor._claude_builder_progress_stage(
            "plain Claude output line",
            "builder-log",
        )
        == "builder-log"
    )
