from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance.assertion import _container_host_identity_env  # noqa: E402


def test_instrumentation_environment_includes_host_identity() -> None:
    env = _container_host_identity_env()

    assert env == {
        "PG_HOST_UID": str(os.getuid()),
        "PG_HOST_GID": str(os.getgid()),
    }
