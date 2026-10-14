from __future__ import annotations

import json
import sys
import time
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from protocol_compliance import assertion, assertion_routes  # noqa: E402
from protocol_compliance.assertion_runtime import resolve_assertion_runtime  # noqa: E402


@pytest.fixture
def provider(monkeypatch):
    for name in list(assertion.os.environ):
        if (
            name.startswith(("PG_PI_", "ANTHROPIC_", "OPENAI_"))
            or name == "PG_ASSERT_AGENT"
        ):
            monkeypatch.delenv(name)
    monkeypatch.setenv("OPENAI_API_KEY", "server-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://cache.test/v1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://anthropic.test")


def test_runtime_is_request_local_and_uses_provider_defaults(provider):
    before = dict(assertion.os.environ)
    pi = resolve_assertion_runtime({"agent": "pi", "model": "test-model"})
    claude = resolve_assertion_runtime({"agent": "claude", "model": "claude-test"})
    assert pi["PG_PI_API_KEY"] == "server-key"
    assert pi["PG_PI_BASE_URL"] == "http://cache.test/v1"
    assert claude["PG_ASSERT_AGENT"] == "claude"
    assert claude["PG_CLAUDE_MODEL"] == "claude-test"
    assert dict(assertion.os.environ) == before
    anthropic = resolve_assertion_runtime(
        {"agent": "pi", "api": "anthropic-messages", "model": "claude-test"}
    )
    assert anthropic["PG_PI_API_KEY"] == "claude-key"


def test_blank_pi_server_settings_use_normal_provider_defaults(provider, monkeypatch):
    monkeypatch.setenv("PG_PI_API_KEY", "")
    monkeypatch.setenv("PG_PI_BASE_URL", "")
    monkeypatch.setenv("PG_PI_MODEL", "")
    monkeypatch.setenv("PG_LLM_MODEL_V3", "server-model")
    env = resolve_assertion_runtime({"agent": "pi"})
    assert env["PG_PI_API_KEY"] == "server-key"
    assert env["PG_PI_BASE_URL"] == "http://cache.test/v1"
    assert env["PG_PI_MODEL"] == "server-model"


@pytest.mark.parametrize(
    "settings",
    [
        [],
        {"agent": "bad"},
        {"agent": "pi"},
        {"api": "bad"},
        {"baseUrl": "file:///tmp/x"},
        {"baseUrl": "https://key@host"},
        {"maxTurns": -1},
        {"timeoutSeconds": True},
        {"unknown": "value"},
    ],
)
def test_runtime_rejects_invalid_settings(provider, settings):
    with pytest.raises((ValueError, TypeError)):
        resolve_assertion_runtime(settings)


def test_container_receives_pi_and_preserves_failure_details(
    provider, monkeypatch, tmp_path
):
    seen = {}

    class Container:
        def logs(self, **kwargs):
            return [
                b'PG_PROGRESS_JSON {"stage":"instrumentation","message":"read main.c","metadata":{"activity":"inspect","primary":"main.c"}}'
            ]

        def wait(self):
            return {"StatusCode": 7}

    def run(**kwargs):
        seen.update(kwargs)
        return Container()

    monkeypatch.setitem(
        sys.modules,
        "docker",
        SimpleNamespace(
            from_env=lambda: SimpleNamespace(containers=SimpleNamespace(run=run))
        ),
    )
    env = resolve_assertion_runtime({"agent": "pi", "model": "pi-model"})
    events = []
    with pytest.raises(assertion.AssertGenerationExecutionError) as exc:
        assertion._run_instrumentation_container(
            image="test",
            network="host",
            workspace=tmp_path,
            output=tmp_path,
            runtime_env=env,
            progress_callback=lambda *args: events.append(args),
        )
    assert seen["environment"]["PG_ASSERT_AGENT"] == "pi"
    assert seen["environment"]["PG_PI_MODEL"] == "pi-model"
    assert seen["environment"]["PG_PI_API_KEY"] == "server-key"
    assert exc.value.details["status"] == 7
    assert events[-1][-1] == {"activity": "inspect", "primary": "main.c"}


@pytest.mark.parametrize(
    "agent,failed", [("pi", False), ("claude", False), ("pi", True)]
)
def test_http_job_lifecycle_and_artifact_download(
    provider, monkeypatch, tmp_path, agent, failed
):
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(
        assertion, "PROGRESS_REGISTRY", assertion.AssertGenerationProgressRegistry()
    )
    archive = tmp_path / "instrumented.zip"
    archive.write_bytes(b"zip-artifact")
    observed = []

    def run(**kwargs):
        observed.append(kwargs["runtime_env"])
        kwargs["progress_callback"](
            kwargs["job_id"],
            "instrumentation",
            "Read: main.c",
            {"activity": "inspect", "primary": "main.c"},
        )
        if failed:
            raise assertion.AssertGenerationExecutionError(
                "provider failed", details={"status": 9}
            )
        return {
            "jobId": kwargs["job_id"],
            "artifacts": {
                "zipPath": str(archive),
                "instrumentedCodeZipPath": str(archive),
            },
            "instrumentation": {
                "artifacts": {"diffOutput": {"available": True, "content": "diff"}}
            },
        }

    monkeypatch.setattr(assertion, "run_assert_generation", run)
    handlers = assertion_routes.create_assertion_handlers(
        lambda: (None, None),
        lambda p: None,
        lambda f: (f.filename, f.read()),
        lambda p: (None, []),
    )
    app = Flask(__name__)
    app.add_url_rule(
        "/jobs", view_func=handlers["assertion_generation"], methods=["POST"]
    )
    app.add_url_rule(
        "/jobs/<job_id>", view_func=handlers["assertion_generation_progress"]
    )
    app.add_url_rule(
        "/jobs/<job_id>/download", view_func=handlers["assertion_generation_download"]
    )
    client = app.test_client()
    response = client.post(
        "/jobs",
        data={
            "codeArchive": (BytesIO(b"source"), "source.tar"),
            "database": (BytesIO(b"db"), "input.db"),
            "runtime": json.dumps({"agent": agent, "model": "test-model"}),
        },
    )
    assert response.status_code == 202
    job_id = response.json["data"]["jobId"]
    for _ in range(100):
        state = client.get(f"/jobs/{job_id}").json["data"]
        if state["status"] in {"completed", "failed"}:
            break
        time.sleep(0.01)
    assert observed[0]["PG_ASSERT_AGENT"] == agent
    assert state["status"] == ("failed" if failed else "completed")
    assert any(
        e.get("metadata", {}).get("activity") == "inspect"
        for e in state["events"]
        if isinstance(e.get("metadata"), dict)
    )
    assert "server-key" not in json.dumps(state)
    download = client.get(f"/jobs/{job_id}/download?artifact=instrumented-code")
    if failed:
        assert state["details"]["status"] == 9
        assert download.status_code == 409
    else:
        assert state["result"]["runtime"]["agent"] == agent
        assert download.data == b"zip-artifact"
        assert download.status_code == 200
