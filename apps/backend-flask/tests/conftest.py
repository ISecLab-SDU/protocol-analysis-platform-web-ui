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


@pytest.fixture
def portable_analysis_uploads(tmp_path):
    """Valid independent source/analysis upload pair for HTTP lifecycle tests."""
    import io
    import json
    import zipfile
    from pg_analysis_exchange import manifest

    root = tmp_path / "input-source"
    root.mkdir()
    code = "int main(void) { return 0; }\n"
    (root / "main.c").write_text(code)
    source = io.BytesIO()
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("main.c", code)
    document = {
        "format": "protocolguard.analysis", "schemaVersion": "1.0", "analysisId": "analysis-1",
        "generatedAt": "2026-10-15T09:00:00Z", "producer": {"name": "test", "version": "1"},
        "protocol": {"name": "MQTT", "version": "3.1.1"},
        "source": {"archiveName": "source.zip", **manifest(root)},
        "results": [{"id": "result-1", "rule": {"id": "rule-1", "description": "Validate input", "reference": None,
                     "requestTypes": ["PUBLISH"], "requestFields": [], "responseTypes": [], "responseFields": []},
                     "verdict": "non_compliant", "reason": "Missing validation",
                     "locations": [{"id": "location-1", "path": "main.c", "function": "main", "startLine": 1, "endLine": 1, "relevantLines": [1], "code": code}],
                     "context": {"codeSlice": code, "callGraph": None}, "diagnostics": []}],
        "diagnostics": [],
    }
    return source.getvalue(), json.dumps(document).encode()
