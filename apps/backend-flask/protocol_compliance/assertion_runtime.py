"""Resolve request-local assertion settings into the core runtime environment."""

from __future__ import annotations

from .provider_config import APIS, provider_defaults, provider_credential, validate_endpoint


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
    env = provider_defaults()
    default_api = env["PG_PI_API"]
    agent = settings.get("agent", "pi")
    if agent != "pi":
        raise ValueError("agent must be pi; Claude models use anthropic-messages through Pi")
    env["PG_ASSERT_AGENT"] = agent
    api = settings.get("api", default_api)
    if api is None or api == "":
        api = default_api
    if not isinstance(api, str) or api not in APIS:
        raise ValueError("Unsupported provider API")
    if api != default_api:
        # A different protocol needs its own endpoint and model. Never send the
        # configured provider's credential to the newly selected provider.
        env.pop("PG_PI_BASE_URL", None)
        env.pop("PG_PI_MODEL", None)
    env["PG_PI_API_KEY"] = provider_credential(api, configured_provider=api == default_api)
    mapping = {
        "model": "PG_PI_MODEL",
        "baseUrl": "PG_PI_BASE_URL",
        "apiKey": "PG_PI_API_KEY",
    }
    for field, name in mapping.items():
        value = settings.get(field)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{field} must be a string")
            if value.strip():
                env[name] = value.strip()
    env["PG_PI_API"] = api
    url = env.get("PG_PI_BASE_URL", "")
    if url:
        env["PG_PI_BASE_URL"] = validate_endpoint(url)
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
        "api": env["PG_PI_API"],
        "model": env.get("PG_PI_MODEL", ""),
    }
