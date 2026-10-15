"""Provider configuration shared by builder, instrumentation and fuzz jobs.

Non-secret defaults live in config.toml; environment variables hold credentials.
PG_PI_* values returned here are the container transport, not server settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

import toml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.toml"
PROVIDER_FIELDS = {
    "api", "model", "base_url", "context_window", "max_tokens", "max_turns", "timeout_seconds",
}
LIMITS = {
    "context_window": "PG_PI_CONTEXT_WINDOW",
    "max_tokens": "PG_PI_MAX_TOKENS",
    "max_turns": "PG_PI_MAX_TURNS",
    "timeout_seconds": "PG_PI_TIMEOUT_SECONDS",
}
APIS = {"openai-completions", "openai-responses", "anthropic-messages"}


def validate_endpoint(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("baseUrl must be an HTTP(S) endpoint without credentials, query or fragment")
    return value.rstrip("/")


def load_provider_sections() -> dict:
    path = Path(os.environ.get("PG_CONFIG_FILE") or CONFIG_PATH)
    with path.open(encoding="utf-8") as handle:
        sections = toml.load(handle).get("protocolguard", {})
    if not isinstance(sections, dict) or set(sections) - {"provider", "analysis"}:
        raise ValueError("Invalid protocolguard configuration section")
    return sections


def provider_defaults() -> dict[str, str]:
    config = load_provider_sections().get("provider", {})
    if not isinstance(config, dict) or set(config) - PROVIDER_FIELDS:
        raise ValueError("Unknown protocolguard.provider setting")
    env = {}
    for field, fallback in {
        "api": "openai-completions", "model": "deepseek-flash",
        "base_url": "https://api.deepseek.com/v1",
    }.items():
        value = config.get(field, fallback)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"protocolguard.provider.{field} must be a non-empty string")
        env[f"PG_PI_{field.upper()}"] = value.strip()
    if env["PG_PI_API"] not in APIS:
        raise ValueError("Unsupported provider API")
    env["PG_PI_BASE_URL"] = validate_endpoint(env["PG_PI_BASE_URL"])
    for field, name in LIMITS.items():
        if field in config:
            value = config[field]
            if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= 9007199254740991:
                raise ValueError(f"protocolguard.provider.{field} must be a positive integer")
            env[name] = str(value)
    return env


def provider_credential(api: str, *, configured_provider: bool = True) -> str:
    prefix = "ANTHROPIC" if api == "anthropic-messages" else "OPENAI"
    return (
        (os.environ.get("PG_PI_API_KEY", "") if configured_provider else "")
        or os.environ.get(f"{prefix}_API_KEY", "")
        or (os.environ.get("ANTHROPIC_AUTH_TOKEN", "") if prefix == "ANTHROPIC" else "")
    )


def agent_environment() -> dict[str, str]:
    env = provider_defaults()
    env["PG_PI_API_KEY"] = provider_credential(env["PG_PI_API"])
    return env


def analysis_llm_config() -> dict:
    """Native analysis uses Chat Completions and retains its TOML key contract."""
    config = load_provider_sections().get("analysis", {})
    allowed = {"base_url", "model", "reasoning_model", "query_repeat", "max_attempts", "violation_repeat", "max_threads"}
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError("Unknown protocolguard.analysis setting")
    base_url = config.get("base_url", "https://api.deepseek.com/v1")
    if not isinstance(base_url, str):
        raise ValueError("protocolguard.analysis.base_url must be a string")
    result: dict = {"llm_api_platform": validate_endpoint(base_url) + "/chat/completions"}
    for field, key in {"model": "llm_model_deepseek_v3", "reasoning_model": "llm_model_deepseek_r1"}.items():
        value = config.get(field, "deepseek-flash")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"protocolguard.analysis.{field} must be a non-empty string")
        result[key] = value.strip()
    for field, key, fallback in (
        ("query_repeat", "llm_query_repeat_times", 1),
        ("max_attempts", "llm_query_max_attempts", 10),
        ("violation_repeat", "llm_violation_repeat_times", 3),
        ("max_threads", "llm_multithread", 32),
    ):
        value = config.get(field, fallback)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"protocolguard.analysis.{field} must be a positive integer")
        result[key] = value
    return result
