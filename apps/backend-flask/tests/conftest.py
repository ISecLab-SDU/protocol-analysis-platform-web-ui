"""Shared temporary provider configuration for integration tests."""

import pytest
import toml


@pytest.fixture
def provider_config_file(monkeypatch, tmp_path):
    def write(provider=None, analysis=None):
        config = {"protocolguard": {"provider": provider or {}, "analysis": analysis or {}}}
        path = tmp_path / "provider.toml"
        path.write_text(toml.dumps(config), encoding="utf-8")
        monkeypatch.setenv("PG_CONFIG_FILE", str(path))
        return path
    return write
