"""Exercise the config boundary and its handoff to all agent workflows."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from protocol_compliance.assertion_runtime import resolve_assertion_runtime
from protocol_compliance.compiler import ClaudeBuilderRunner, ClaudeBuilderRunnerSettings
from protocol_compliance.fuzz_config_routes import _docker_env_flags
from protocol_compliance.provider_config import analysis_llm_config, provider_defaults


def test_all_workflows_share_config_and_accept_arbitrary_models(monkeypatch, provider_config_file):
    provider_config_file(
        {"api": "openai-completions", "model": "vendor/future-model", "base_url": "http://cache.test/v1", "max_turns": 17},
        {"model": "vendor/static", "reasoning_model": "vendor/reasoning", "base_url": "http://static.test/v1"},
    )
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.delenv("PG_PI_API_KEY", raising=False)
    for name in ("PG_PI_MODEL", "PG_AGENT_MODEL", "PG_CLAUDE_MODEL", "ANTHROPIC_MODEL", "PG_LLM_MODEL_V3"):
        monkeypatch.setenv(name, "deepseek-v3")
    monkeypatch.setenv("PG_PI_MAX_TURNS", "999")
    monkeypatch.setenv("PG_CLAUDE_MAX_TURNS", "999")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://obsolete.test")
    settings = ClaudeBuilderRunnerSettings.from_env()
    runtime = resolve_assertion_runtime()
    flags = _docker_env_flags({})
    monkeypatch.setattr(ClaudeBuilderRunner, "_check_docker", lambda self: True)
    builder = ClaudeBuilderRunner(settings)
    for key in ("PG_PI_MODEL", "PG_PI_API", "PG_PI_BASE_URL", "PG_PI_MAX_TURNS"):
        assert runtime[key] == settings.runtime_env[key]
        assert f"{key}={runtime[key]}" in flags
        assert f"{key}={runtime[key]}" in builder._docker_env_args()
    assert runtime["PG_PI_MODEL"] == "vendor/future-model"
    assert settings.runtime_env["PG_PI_API_KEY"] == "secret"
    assert "secret" not in " ".join(flags + builder._docker_env_args())
    llm = analysis_llm_config()
    assert llm["llm_model_deepseek_v3"] == "vendor/static"
    assert llm["llm_model_deepseek_r1"] == "vendor/reasoning"
    assert llm["llm_api_platform"] == "http://static.test/v1/chat/completions"


def test_request_overrides_do_not_change_other_jobs(monkeypatch, provider_config_file):
    provider_config_file({"model": "configured", "base_url": "http://cache.test/v1"})
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    request = resolve_assertion_runtime({"model": "vendor/custom", "maxTurns": 3})
    assert request["PG_PI_MODEL"] == "vendor/custom"
    assert request["PG_PI_MAX_TURNS"] == "3"
    assert resolve_assertion_runtime()["PG_PI_MODEL"] == "configured"
    assert "PG_PI_MAX_TURNS" not in resolve_assertion_runtime()


def test_switching_provider_requires_endpoint_and_model(monkeypatch, provider_config_file):
    provider_config_file()
    monkeypatch.setenv("PG_PI_API_KEY", "original-provider-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    with pytest.raises(ValueError):
        resolve_assertion_runtime({"api": "anthropic-messages"})
    env = resolve_assertion_runtime({"api": "anthropic-messages", "model": "claude-custom", "baseUrl": "https://anthropic.test"})
    assert env["PG_PI_API_KEY"] == "anthropic-secret"
    assert "original-provider-secret" not in env.values()


@pytest.mark.parametrize("config", [
    {"model": ""}, {"model": 3}, {"api": "invalid"}, {"base_url": "file:///tmp/cache"},
    {"base_url": "https://secret@host"}, {"base_url": "https://host?key=secret"},
    {"max_turns": 0}, {"max_turns": True}, {"obsolete_switch": True},
])
def test_invalid_config_is_rejected(provider_config_file, config):
    provider_config_file(config)
    with pytest.raises(ValueError):
        provider_defaults()
