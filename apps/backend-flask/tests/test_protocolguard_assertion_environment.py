from __future__ import annotations

from io import BytesIO
import os
import sys
from pathlib import Path
from typing import Any, cast

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import protocol_compliance.assertion as assertion_module  # noqa: E402
from protocol_compliance.assertion import _container_host_identity_env  # noqa: E402
from protocol_compliance.docker_runner import ProtocolGuardDockerSettings  # noqa: E402


def test_instrumentation_environment_includes_host_identity() -> None:
    env = _container_host_identity_env()

    assert env == {
        "PG_HOST_UID": str(os.getuid()),
        "PG_HOST_GID": str(os.getgid()),
    }


def test_protocolguard_containers_use_host_network_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PG_DOCKER_NETWORK", raising=False)

    settings = ProtocolGuardDockerSettings.from_env()

    assert settings.network == "host"


def test_protocolguard_container_network_can_be_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PG_DOCKER_NETWORK", "protocolguard-network")

    settings = ProtocolGuardDockerSettings.from_env()

    assert settings.network == "protocolguard-network"


def test_assertion_generation_skips_instrumentation_when_no_tasks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeRunner:
        cleanup_job_id: str | None = None

        def __init__(self, _settings: ProtocolGuardDockerSettings) -> None:
            pass

        def run_assert_generation(self, **_kwargs: Any) -> dict[str, object]:
            return {
                "jobId": "job-empty",
                "assertionCount": 0,
                "artifacts": {
                    "workspace": str(tmp_path / "workspace"),
                    "output": str(tmp_path / "output"),
                    "zipPath": str(tmp_path / "output" / "assert_tasks.zip"),
                },
            }

        def cleanup_assertion_intermediates(self, *, job_id: str | None = None) -> None:
            self.cleanup_job_id = job_id

    events: list[tuple[str, str, str]] = []
    settings = ProtocolGuardDockerSettings.from_env()
    monkeypatch.setattr(assertion_module, "_docker_settings", lambda: settings)
    monkeypatch.setattr(assertion_module, "ProtocolGuardDockerRunner", FakeRunner)

    def fail_instrumentation(**_kwargs: Any) -> dict[str, object]:
        raise AssertionError("instrumentation should be skipped for empty assertion results")

    monkeypatch.setattr(assertion_module, "_run_instrumentation_container", fail_instrumentation)

    result = assertion_module.run_assert_generation(
        code_stream=BytesIO(b"source"),
        code_file_name="source.tar",
        database_stream=BytesIO(b"sqlite"),
        database_file_name="violations.db",
        notes=None,
        job_id="job-empty",
        progress_callback=lambda job_id, stage, message: events.append((job_id, stage, message)),
    )
    instrumentation = cast(dict[str, Any], result["instrumentation"])

    assert result["assertionCount"] == 0
    assert result["instrumentation"] == {
        "skipped": True,
        "reason": "assertion generation produced no tasks",
        "artifacts": {
            "instrumentedCodePath": None,
            "instrumentedCodeZipPath": None,
            "diffFiles": [],
            "diffOutput": {
                "available": False,
                "path": None,
                "size": 0,
                "content": None,
                "truncated": False,
            },
        },
        "logs": [],
        "completedAt": instrumentation["completedAt"],
    }
    assert events == [
        (
            "job-empty",
            "instrumentation",
            "Skipping instrumentation because assertion generation produced no tasks",
        )
    ]


def test_filter_unified_diff_keeps_only_c_cpp_sections() -> None:
    mixed_diff = """diff --git a/assert_instrumentation_events.jsonl b/assert_instrumentation_events.jsonl
new file mode 100644
--- /dev/null
+++ b/assert_instrumentation_events.jsonl
@@ -0,0 +1,2 @@
+{\"source\":\"claude-agent-sdk\"}
diff --git a/project/sol/src/server.c b/project/sol/src/server.c
index 1111111..2222222 100755
--- a/project/sol/src/server.c
+++ b/project/sol/src/server.c
@@ -1,2 +1,2 @@
-old
+new
"""

    filtered = assertion_module._filter_unified_diff_to_c_cpp_sources(mixed_diff)

    assert "assert_instrumentation_events.jsonl" not in filtered
    assert "project/sol/src/server.c" in filtered
    assert filtered.startswith("diff --git a/project/sol/src/server.c b/project/sol/src/server.c")
