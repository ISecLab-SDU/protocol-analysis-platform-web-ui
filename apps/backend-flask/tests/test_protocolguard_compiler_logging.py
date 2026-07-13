from __future__ import annotations

import logging
import sys
import types
from pathlib import Path
from typing import Any, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import compiler as compiler_module  # noqa: E402

if "claude_agent_sdk" not in sys.modules:
    fake_claude_agent_sdk = types.ModuleType("claude_agent_sdk")
    for name in (
        "AssistantMessage",
        "ClaudeAgentOptions",
        "ResultMessage",
        "StreamEvent",
        "SystemMessage",
        "TextBlock",
        "ToolResultBlock",
        "ToolUseBlock",
    ):
        setattr(fake_claude_agent_sdk, name, type(name, (), {}))
    cast(Any, fake_claude_agent_sdk).query = None
    sys.modules["claude_agent_sdk"] = fake_claude_agent_sdk

from protocol_compliance.compiler import ClaudeBuilderRunner, ClaudeBuilderRunnerSettings  # noqa: E402
from protocol_compliance.claude_agent_events import (  # noqa: E402
    is_hidden_system_message as _is_hidden_system_message,
    progress_events_from_message,
    sanitize_event_value as _sanitize_event_value,
)
from protocol_compliance.claude_builder.pg_claude_builder_sdk import (  # noqa: E402
    CLAUDE_CLI_PATH,
    _build_claude_environment,
)


def test_claude_builder_runner_settings_enable_from_anthropic_env(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("PG_CLAUDE_BUILDER_IMAGE", "protocolguard-claude-builder:test")

    settings = ClaudeBuilderRunnerSettings.from_env()

    assert settings.enabled is True
    assert settings.api_key == "test-anthropic-key"
    assert settings.base_url == "https://example.invalid"
    assert settings.builder_image == "protocolguard-claude-builder:test"
    assert "ANTHROPIC_API_KEY" in settings.env_passthrough
    assert "ANTHROPIC_BASE_URL" in settings.env_passthrough


def test_claude_builder_runner_forwards_anthropic_env_without_openai_fallback(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://anthropic.example/v1")
    settings = ClaudeBuilderRunnerSettings(
        enabled=True,
        api_key="anthropic-key",
        base_url="https://anthropic.example/v1",
        model="unused",
        workspace_root=tmp_path,
        max_runtime=60,
        env_passthrough=("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"),
        builder_image="protocolguard-claude-builder:test",
    )
    executor = ClaudeBuilderRunner(settings)

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


def test_claude_builder_runner_redacts_secret_command_values() -> None:
    command = [
        "docker",
        "run",
        "-e",
        "ANTHROPIC_API_KEY=secret",
        "-e",
        "PG_HOST_UID=1000",
    ]

    assert ClaudeBuilderRunner._redact_command(command) == [
        "docker",
        "run",
        "-e",
        "ANTHROPIC_API_KEY=<redacted>",
        "-e",
        "PG_HOST_UID=1000",
    ]


def test_claude_builder_runner_classifies_claude_builder_log_markers() -> None:
    assert (
        ClaudeBuilderRunner._claude_builder_progress_stage(
            "[claude-command] cmake -S . -B build",
            "builder-log",
        )
        == "claude-command"
    )
    assert (
        ClaudeBuilderRunner._claude_builder_progress_stage(
            "[pg-builder][config.toml] protocol_name = \"MQTT\"",
            "builder-log",
        )
        == "claude-config"
    )
    assert (
        ClaudeBuilderRunner._claude_builder_progress_stage(
            "[pg-builder][artifact-file] /workspace/program.bc: LLVM IR bitcode",
            "builder-log",
        )
        == "claude-artifact"
    )
    assert (
        ClaudeBuilderRunner._claude_builder_progress_stage(
            "plain Claude output line",
            "builder-log",
        )
        == "builder-log"
    )


def test_claude_builder_runner_streams_analysis_container_logs(
    caplog: Any,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspaces"
    workspace_dir = workspace_root / "job-analysis-stream"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "build_log.txt").write_text("build ok\n", encoding="utf-8")
    (workspace_dir / "rule_config.json").write_text('{"rules": []}\n', encoding="utf-8")
    (workspace_dir / "program.bc").write_text("bitcode\n", encoding="utf-8")
    (workspace_dir / "program.ll").write_text("llvm ir\n", encoding="utf-8")
    (workspace_dir / "program").write_text("binary\n", encoding="utf-8")
    src_dir = workspace_dir / "project" / "demo" / "src"
    src_dir.mkdir(parents=True)
    (src_dir / ".cf_main.json").write_text("{}\n", encoding="utf-8")

    settings = ClaudeBuilderRunnerSettings(
        enabled=True,
        api_key="test",
        base_url="",
        model="unused",
        workspace_root=workspace_root,
        max_runtime=60,
        env_passthrough=(),
        builder_image="unused",
    )
    executor = ClaudeBuilderRunner(settings)
    executor._docker_available = True
    executor._analysis_image = "protocolguard:latest"
    executor._analysis_command = ["static"]

    class FakeStdout:
        def __init__(self) -> None:
            self._lines = iter(
                [
                    "Running match-pass with configuration\n",
                    "\rProcessing records:   0%|          | 0/1 [00:00<?, ?it/s]\n",
                    "[LLM Query] Succeeded in 31 ms. Model: deepseek-v3.\n",
                    "",
                ]
            )

        def readline(self) -> str:
            return next(self._lines)

    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = FakeStdout()
            self.returncode = 0

        def wait(self, timeout: int | None = None) -> int:
            return self.returncode

    monkeypatch.setattr(compiler_module.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr(
        compiler_module.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )
    events: list[tuple[str, str, str]] = []

    with caplog.at_level(logging.INFO, logger="protocol_compliance.compiler"):
        executor._run_analysis_container(
            workspace_dir,
            "job-analysis-stream",
            lambda job_id, stage, message: events.append((job_id, stage, message)),
            project_name="Demo",
        )

    output_log = tmp_path / "outputs" / "job-analysis-stream" / "analysis.log"
    assert output_log.exists()
    assert "[LLM Query] Succeeded in 31 ms. Model: deepseek-v3." in output_log.read_text(encoding="utf-8")
    assert "[LLM Query] Succeeded in 31 ms. Model: deepseek-v3." in caplog.text
    assert (
        "job-analysis-stream",
        "analysis-log",
        "[LLM Query] Succeeded in 31 ms. Model: deepseek-v3.",
    ) in events


def test_claude_builder_runner_extracts_claude_sdk_progress_json() -> None:
    line = (
        'PG_PROGRESS_JSON {"stage":"claude-command",'
        '"message":"Bash: cmake -S . -B build",'
        '"tool":"Bash"}'
    )

    assert ClaudeBuilderRunner._extract_progress_line(line, "builder-log") == (
        "claude-command",
        "Bash: cmake -S . -B build",
    )


def test_claude_builder_runner_falls_back_for_invalid_claude_sdk_progress_json() -> None:
    line = "PG_PROGRESS_JSON {not-json"

    stage, message = ClaudeBuilderRunner._extract_progress_line(line, "builder-log")

    assert stage == "claude-status"
    assert message == line


def test_run_logged_command_emits_claude_sdk_progress_json(
    tmp_path: Path,
) -> None:
    settings = ClaudeBuilderRunnerSettings(
        enabled=True,
        api_key="anthropic-key",
        base_url="",
        model="unused",
        workspace_root=tmp_path,
        max_runtime=60,
        env_passthrough=(),
        builder_image="protocolguard-claude-builder:test",
    )
    executor = ClaudeBuilderRunner(settings)
    events: list[tuple[str, str, str]] = []
    command = [
        sys.executable,
        "-c",
        (
            "print("
            "'PG_PROGRESS_JSON "
            "{\"stage\":\"claude-write\",\"message\":\"Write: /workspace/program.bc\"}'"
            ")"
        ),
    ]

    logs = executor._run_logged_command(
        command,
        cwd=tmp_path,
        log_path=tmp_path / "command.log",
        progress_callback=lambda job_id, stage, message: events.append((job_id, stage, message)),
        job_identifier="job-sdk",
        stage="builder-log",
        timeout=10,
    )

    assert logs == [
        'PG_PROGRESS_JSON {"stage":"claude-write","message":"Write: /workspace/program.bc"}'
    ]
    assert events == [("job-sdk", "claude-write", "Write: /workspace/program.bc")]


def test_claude_sdk_environment_passes_all_anthropic_credentials(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "api-key")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "auth-token")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://gateway.example")

    env = _build_claude_environment()

    assert env["ANTHROPIC_API_KEY"] == "api-key"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "auth-token"
    assert env["ANTHROPIC_BASE_URL"] == "http://gateway.example"


def test_claude_sdk_uses_system_cli_instead_of_bundled_cli() -> None:
    assert CLAUDE_CLI_PATH
    assert "_bundled" not in CLAUDE_CLI_PATH


def test_claude_sdk_sanitizes_hidden_thinking_tokens() -> None:
    payload = {
        "usage": {
            "input_tokens": 42,
            "thinking_tokens": 1024,
            "nested": [{"thinking_tokens": 256, "output_tokens": 7}],
        },
        "model_usage": {
            "claude": {
                "cache_creation_input_tokens": 3,
                "thinking_tokens": 512,
            }
        },
    }

    sanitized = _sanitize_event_value(payload)
    serialized = str(sanitized)

    assert "thinking_tokens" not in serialized
    assert sanitized == {
        "usage": {
            "input_tokens": 42,
            "nested": [{"output_tokens": 7}],
        },
        "model_usage": {
            "claude": {
                "cache_creation_input_tokens": 3,
            }
        },
    }


def test_claude_sdk_identifies_hidden_thinking_token_system_events() -> None:
    hidden_by_subtype = types.SimpleNamespace(subtype="thinking_tokens", data={})
    hidden_by_data = types.SimpleNamespace(
        subtype="system",
        data={
            "subtype": "thinking_tokens",
            "estimated_tokens": 82,
            "estimated_tokens_delta": 2,
        },
    )
    visible = types.SimpleNamespace(subtype="hook_pre_tool", data={"subtype": "hook_pre_tool"})

    assert _is_hidden_system_message(hidden_by_subtype)
    assert _is_hidden_system_message(hidden_by_data)
    assert not _is_hidden_system_message(visible)


def test_claude_agent_event_conversion_is_reusable_without_builder_runner() -> None:
    fake_sdk = cast(Any, sys.modules["claude_agent_sdk"])
    tool_block = fake_sdk.ToolUseBlock.__new__(fake_sdk.ToolUseBlock)
    tool_block.name = "Bash"
    tool_block.input = {"command": "cmake -S . -B build"}
    tool_block.id = "tool-1"
    message = fake_sdk.AssistantMessage.__new__(fake_sdk.AssistantMessage)
    message.session_id = "session-1"
    message.model = "claude-test"
    message.content = [tool_block]

    events = progress_events_from_message(message, result_label="Assertion insertion")

    assert events == [
        {
            "type": "sdk-message",
            "stage": "claude-status",
            "message": "Assistant turn received from claude-test",
            "sdk_message_type": "AssistantMessage",
            "session_id": "session-1",
            "model": "claude-test",
        },
        {
            "type": "progress",
            "stage": "claude-command",
            "message": "Bash: cmake -S . -B build",
            "sdk_message_type": "ToolUseBlock",
            "tool": "Bash",
            "tool_use_id": "tool-1",
            "tool_input": {"command": "cmake -S . -B build"},
        },
    ]
