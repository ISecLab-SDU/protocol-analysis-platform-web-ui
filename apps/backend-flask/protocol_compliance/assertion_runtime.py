"""Resolve request-local assertion settings into the core runtime environment."""

from __future__ import annotations

import os
from urllib.parse import urlsplit


def resolve_assertion_runtime(settings: object = None) -> dict[str, str]:
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError("runtime must be an object")
    allowed = {
        "agent",
        "api",
        "model",
        "baseUrl",
        "apiKey",
        "contextWindow",
        "maxTokens",
        "maxTurns",
        "timeoutSeconds",
    }
    if set(settings) - allowed:
        raise ValueError("Unknown assertion runtime setting")
    env = {
        name: value
        for name, value in os.environ.items()
        if name.startswith(("PG_PI_", "ANTHROPIC_", "OPENAI_"))
        or name == "PG_CLAUDE_MODEL"
    }
    agent = settings.get("agent", os.environ.get("PG_ASSERT_AGENT", "pi"))
    if agent != "pi":
        raise ValueError("agent must be pi; Claude models use anthropic-messages through Pi")
    env["PG_ASSERT_AGENT"] = agent
    api = settings.get(
        "api",
        env.get("PG_PI_API") or ("openai-completions" if env.get("OPENAI_BASE_URL") else "anthropic-messages" if env.get("ANTHROPIC_BASE_URL") else "openai-completions"),
    )
    if api not in {"openai-completions", "openai-responses", "anthropic-messages"}:
        raise ValueError("Unsupported provider API")
    prefix = "ANTHROPIC" if api == "anthropic-messages" else "OPENAI"
    mapping = {
        "model": "PG_PI_MODEL",
        "baseUrl": "PG_PI_BASE_URL",
        "apiKey": "PG_PI_API_KEY",
    }
    # Changing protocol must not pick credentials from a different Pi provider.
    if agent == "pi" and api != (env.get("PG_PI_API") or ("openai-completions" if env.get("OPENAI_BASE_URL") else "anthropic-messages" if env.get("ANTHROPIC_BASE_URL") else "openai-completions")):
        env.pop("PG_PI_BASE_URL", None)
        env.pop("PG_PI_API_KEY", None)
    for field, name in mapping.items():
        value = settings.get(field)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{field} must be a string")
            if value.strip():
                env[name] = value.strip()
    if agent == "pi":
        env["PG_PI_API"] = api
        if not env.get("PG_PI_MODEL"):
            env["PG_PI_MODEL"] = os.environ.get("PG_AGENT_MODEL") or env.get("PG_CLAUDE_MODEL") or env.get("ANTHROPIC_MODEL") or os.environ.get("PG_LLM_MODEL_V3", "")
        for suffix in ("BASE_URL", "API_KEY"):
            if not env.get(f"PG_PI_{suffix}"):
                env[f"PG_PI_{suffix}"] = env.get(f"{prefix}_{suffix}", "") or (env.get("ANTHROPIC_AUTH_TOKEN", "") if prefix == "ANTHROPIC" and suffix == "API_KEY" else "")
    url = env.get(mapping["baseUrl"], "")
    if url:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "baseUrl must be an HTTP(S) endpoint without credentials, query or fragment"
            )
    for field, name in {
        "contextWindow": "PG_PI_CONTEXT_WINDOW",
        "maxTokens": "PG_PI_MAX_TOKENS",
        "maxTurns": "PG_PI_MAX_TURNS",
        "timeoutSeconds": "PG_PI_TIMEOUT_SECONDS",
    }.items():
        value = settings.get(field, env.get(name))
        if value is not None:
            if (
                isinstance(value, bool)
                or not str(value).isdigit()
                or not 0 < int(value) <= 9007199254740991
            ):
                raise ValueError(f"{field} must be a positive integer")
            env[name] = str(value)
    if agent == "pi" and not all(env.get(mapping[field]) for field in mapping):
        raise ValueError(
            "Pi requires a model, provider base URL and API key (request settings or server defaults)"
        )
    return env


def runtime_summary(env: dict[str, str]) -> dict[str, str]:
    agent = env["PG_ASSERT_AGENT"]
    return {
        "agent": agent,
        "api": env.get("PG_PI_API") or ("openai-completions" if env.get("OPENAI_BASE_URL") else "anthropic-messages" if env.get("ANTHROPIC_BASE_URL") else "openai-completions"),
        "model": env.get("PG_PI_MODEL", ""),
    }
