"""Assertion generation helpers and Docker orchestration glue."""

from __future__ import annotations

import difflib
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Callable, Dict, List, Optional, Tuple

from .docker_runner import (
    ProtocolGuardDockerError,
    ProtocolGuardDockerRunner,
    ProtocolGuardDockerSettings,
    ProtocolGuardExecutionError,
    ProtocolGuardNotAvailableError,
)

LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


AssertGenerationJobStatus = str  # Literal['queued', 'running', 'completed', 'failed']


@dataclass
class AssertGenerationProgressEvent:
    timestamp: str
    stage: str
    message: str


@dataclass
class AssertGenerationProgressState:
    job_id: str
    status: AssertGenerationJobStatus
    stage: str
    message: str
    created_at: str
    updated_at: str
    events: List[AssertGenerationProgressEvent] = field(default_factory=list)
    result: Optional[Dict[str, object]] = None
    error: Optional[str] = None
    details: Optional[Dict[str, object]] = None


class AssertGenerationError(RuntimeError):
    """Base error for assertion generation orchestration."""


class AssertGenerationNotReadyError(AssertGenerationError):
    """Raised when Docker integration is disabled or unavailable."""


class AssertGenerationExecutionError(AssertGenerationError):
    """Raised when the assertion generation container fails."""

    def __init__(
        self,
        message: str,
        *,
        logs: Optional[List[str]] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        super().__init__(message)
        self.logs = logs or []
        self.details = details or {}


class AssertGenerationProgressRegistry:
    """Track live progress for assertion generation jobs."""

    def __init__(self) -> None:
        self._states: Dict[str, AssertGenerationProgressState] = {}
        self._lock = threading.Lock()

    def create_job(self) -> AssertGenerationProgressState:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        state = AssertGenerationProgressState(
            job_id=job_id,
            status="queued",
            stage="queued",
            message="Job queued",
            created_at=now,
            updated_at=now,
        )
        state.events.append(
            AssertGenerationProgressEvent(timestamp=now, stage="queued", message="Job queued")
        )
        with self._lock:
            self._states[job_id] = state
        return state

    def mark_running(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "running"
            self._append_event(state, stage, message)

    def append_event(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            self._append_event(state, stage, message)

    def complete(self, job_id: str, result: Dict[str, object]) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "completed"
            state.result = result
            self._append_event(state, "completed", "Assertion generation completed successfully")

    def fail(
        self,
        job_id: str,
        stage: str,
        message: str,
        *,
        error: Optional[str] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "failed"
            state.error = error or message
            state.details = details
            self._append_event(state, stage, message)

    def snapshot(self, job_id: str) -> Optional[Dict[str, object]]:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return None
            state_copy = AssertGenerationProgressState(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                created_at=state.created_at,
                updated_at=state.updated_at,
                events=list(state.events),
                result=state.result,
                error=state.error,
                details=state.details.copy() if state.details else None,
            )

        return {
            "jobId": state_copy.job_id,
            "status": state_copy.status,
            "stage": state_copy.stage,
            "message": state_copy.message,
            "createdAt": state_copy.created_at,
            "updatedAt": state_copy.updated_at,
            "events": [
                {"timestamp": event.timestamp, "stage": event.stage, "message": event.message}
                for event in state_copy.events
            ],
            "result": state_copy.result,
            "error": state_copy.error,
            "details": state_copy.details,
        }

    def make_callback(self, job_id: str) -> Callable[[str, str, str], None]:
        def callback(_job_id: str, stage: str, message: str) -> None:
            target_id = job_id or _job_id
            safe_stage = stage or "progress"
            safe_message = message or ""
            self.append_event(target_id, safe_stage, safe_message)

        return callback

    def _append_event(
        self,
        state: AssertGenerationProgressState,
        stage: str,
        message: str,
    ) -> None:
        timestamp = _now_iso()
        state.stage = stage or state.stage
        state.message = message or state.message
        state.updated_at = timestamp
        state.events.append(
            AssertGenerationProgressEvent(timestamp=timestamp, stage=stage or state.stage, message=message)
        )


PROGRESS_REGISTRY = AssertGenerationProgressRegistry()


@lru_cache(maxsize=1)
def _docker_settings() -> ProtocolGuardDockerSettings:
    return ProtocolGuardDockerSettings.from_env()


def run_assert_generation(
    *,
    code_stream: BinaryIO,
    code_file_name: str,
    database_stream: BinaryIO,
    database_file_name: str,
    build_instructions: Optional[str],
    notes: Optional[str],
    job_id: Optional[str] = None,
    progress_callback: Optional[Callable[[str, str, str], None]] = None,
) -> Dict[str, object]:
    """Dispatch assertion generation via Docker."""

    job_identifier = job_id or str(uuid.uuid4())
    settings = _docker_settings()
    if not settings.enabled:
        raise AssertGenerationNotReadyError("ProtocolGuard Docker integration is disabled")

    try:
        runner = ProtocolGuardDockerRunner(settings)
    except ProtocolGuardNotAvailableError as exc:
        raise AssertGenerationNotReadyError(str(exc)) from exc

    try:
        return runner.run_assert_generation(
            code_stream=code_stream,
            code_filename=code_file_name,
            database_stream=database_stream,
            database_filename=database_file_name,
            build_instructions=build_instructions,
            notes=notes,
            job_id=job_identifier,
            progress_callback=progress_callback,
        )
    except ProtocolGuardExecutionError as exc:
        details: Dict[str, object] = {
            "image": getattr(exc, "image", None),
            "status": getattr(exc, "status", None),
        }
        if exc.log_excerpt:
            details["logExcerpt"] = exc.log_excerpt
        raise AssertGenerationExecutionError(
            str(exc),
            logs=list(getattr(exc, "logs", []) or []),
            details=details,
        ) from exc
    except ProtocolGuardDockerError as exc:
        raise AssertGenerationError(str(exc)) from exc


def submit_assert_generation_job(
    *,
    code_payload: Tuple[str, bytes],
    database_payload: Tuple[str, bytes],
    build_instructions: Optional[str],
    notes: Optional[str],
) -> Dict[str, object]:
    """Launch assertion generation asynchronously and return initial snapshot."""

    state = PROGRESS_REGISTRY.create_job()
    job_id = state.job_id

    def _run_job() -> None:
        PROGRESS_REGISTRY.mark_running(job_id, "init", "Preparing assertion generation inputs")
        progress_callback = PROGRESS_REGISTRY.make_callback(job_id)
        progress_callback(job_id, "inputs", "Persisting uploaded artefacts")

        try:
            code_name, code_bytes = code_payload
            database_name, database_bytes = database_payload

            result = run_assert_generation(
                code_stream=BytesIO(code_bytes),
                code_file_name=code_name,
                database_stream=BytesIO(database_bytes),
                database_file_name=database_name,
                build_instructions=build_instructions,
                notes=notes,
                job_id=job_id,
                progress_callback=progress_callback,
            )
            PROGRESS_REGISTRY.complete(job_id, result)
        except AssertGenerationExecutionError as exc:
            details = exc.details.copy()
            if exc.logs:
                details["logs"] = list(exc.logs)
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation execution failed",
                error=str(exc),
                details=details or None,
            )
        except AssertGenerationNotReadyError as exc:
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation backend is not ready",
                error=str(exc),
            )
        except AssertGenerationError as exc:
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation service error",
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("Assertion generation job %s encountered an unexpected error", job_id)
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Unexpected assertion generation failure",
                error=str(exc),
            )

    worker = threading.Thread(target=_run_job, name=f"assert-generation-{job_id[:8]}", daemon=True)
    worker.start()
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    assert snapshot is not None
    return snapshot


def get_assert_generation_job(job_id: str) -> Optional[Dict[str, object]]:
    return PROGRESS_REGISTRY.snapshot(job_id)


def get_assert_generation_result(job_id: str) -> Optional[Dict[str, object]]:
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    if not snapshot:
        return None
    if snapshot.get("status") != "completed":
        return None
    result = snapshot.get("result")
    if isinstance(result, dict):
        return result
    return None


def get_assert_generation_zip_path(job_id: str) -> Optional[Path]:
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    if not snapshot:
        return None
    result = snapshot.get("result")
    if not isinstance(result, dict):
        return None
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    raw_zip = artifacts.get("zipPath")
    if not raw_zip:
        return None
    zip_path = Path(raw_zip)
    if not zip_path.exists():
        return None
    return zip_path


# ============================================================================
# Diff Parsing Workflow
# ============================================================================

DiffParsingJobStatus = str  # Literal['queued', 'running', 'completed', 'failed']


@dataclass
class DiffParsingProgressEvent:
    timestamp: str
    stage: str
    message: str
    percentage: int


@dataclass
class DiffParsingProgressState:
    job_id: str
    parent_job_id: str
    status: DiffParsingJobStatus
    stage: str
    message: str
    percentage: int
    created_at: str
    updated_at: str
    events: List[DiffParsingProgressEvent] = field(default_factory=list)
    result: Optional[Dict[str, object]] = None
    error: Optional[str] = None


class DiffParsingProgressRegistry:
    """Track live progress for diff parsing jobs."""

    def __init__(self) -> None:
        self._states: Dict[str, DiffParsingProgressState] = {}
        self._lock = threading.Lock()

    def create_job(self, parent_job_id: str) -> DiffParsingProgressState:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        state = DiffParsingProgressState(
            job_id=job_id,
            parent_job_id=parent_job_id,
            status="queued",
            stage="queued",
            message="Diff parsing queued",
            percentage=0,
            created_at=now,
            updated_at=now,
        )
        state.events.append(
            DiffParsingProgressEvent(
                timestamp=now,
                stage="queued",
                message="Diff parsing queued",
                percentage=0,
            )
        )
        with self._lock:
            self._states[job_id] = state
        return state

    def mark_running(self, job_id: str, stage: str, message: str, percentage: int) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "running"
            self._append_event(state, stage, message, percentage)

    def append_event(self, job_id: str, stage: str, message: str, percentage: int) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            self._append_event(state, stage, message, percentage)

    def complete(self, job_id: str, result: Dict[str, object]) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "completed"
            state.result = result
            self._append_event(state, "completed", "Diff parsing completed successfully", 100)

    def fail(
        self,
        job_id: str,
        stage: str,
        message: str,
        *,
        error: Optional[str] = None,
    ) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "failed"
            state.error = error or message
            self._append_event(state, stage, message, state.percentage)

    def snapshot(self, job_id: str) -> Optional[Dict[str, object]]:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return None
            state_copy = DiffParsingProgressState(
                job_id=state.job_id,
                parent_job_id=state.parent_job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                percentage=state.percentage,
                created_at=state.created_at,
                updated_at=state.updated_at,
                events=list(state.events),
                result=state.result,
                error=state.error,
            )

        return {
            "jobId": state_copy.job_id,
            "parentJobId": state_copy.parent_job_id,
            "status": state_copy.status,
            "stage": state_copy.stage,
            "message": state_copy.message,
            "percentage": state_copy.percentage,
            "createdAt": state_copy.created_at,
            "updatedAt": state_copy.updated_at,
            "events": [
                {
                    "timestamp": event.timestamp,
                    "stage": event.stage,
                    "message": event.message,
                    "percentage": event.percentage,
                }
                for event in state_copy.events
            ],
            "result": state_copy.result,
            "error": state_copy.error,
        }

    def _append_event(
        self,
        state: DiffParsingProgressState,
        stage: str,
        message: str,
        percentage: int,
    ) -> None:
        timestamp = _now_iso()
        state.stage = stage or state.stage
        state.message = message or state.message
        state.percentage = max(0, min(100, percentage))
        state.updated_at = timestamp
        state.events.append(
            DiffParsingProgressEvent(
                timestamp=timestamp,
                stage=stage or state.stage,
                message=message,
                percentage=state.percentage,
            )
        )


DIFF_PARSING_REGISTRY = DiffParsingProgressRegistry()


def _generate_mock_diff() -> Dict[str, object]:
    """Generate a realistic mock diff for demonstration purposes."""

    # Mock diff content as a string
    diff_content = """diff --git a/src/protocol/tls_handler.c b/src/protocol/tls_handler.c
index 1a2b3c4..5d6e7f8 100644
--- a/src/protocol/tls_handler.c
+++ b/src/protocol/tls_handler.c
@@ -45,7 +45,7 @@ int verify_certificate(SSL *ssl, const char *hostname) {
     X509 *cert = SSL_get_peer_certificate(ssl);

     if (!cert) {
-        fprintf(stderr, "No certificate presented\\n");
+        log_error("No certificate presented by peer");
         return -1;
     }

@@ -67,12 +67,18 @@ int tls_handshake(connection_t *conn) {
         return -1;
     }

-    // Set verification mode
-    SSL_set_verify(conn->ssl, SSL_VERIFY_PEER, NULL);
+    // Set strict verification mode with callback
+    SSL_set_verify(conn->ssl, SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT, verify_callback);
+
+    // Set minimum TLS version to 1.2
+    SSL_set_min_proto_version(conn->ssl, TLS1_2_VERSION);

     // Perform handshake
     int ret = SSL_do_handshake(conn->ssl);
     if (ret != 1) {
+        int ssl_error = SSL_get_error(conn->ssl, ret);
+        log_error("TLS handshake failed with error code: %d", ssl_error);
+        ERR_print_errors_fp(stderr);
         return -1;
     }

diff --git a/src/protocol/assertions.c b/src/protocol/assertions.c
new file mode 100644
index 0000000..9a8b7c1
--- /dev/null
+++ b/src/protocol/assertions.c
@@ -0,0 +1,52 @@
+#include "assertions.h"
+#include <assert.h>
+#include <string.h>
+
+/**
+ * Assert that TLS version is at least 1.2
+ */
+void assert_min_tls_version(SSL *ssl) {
+    int version = SSL_version(ssl);
+    assert(version >= TLS1_2_VERSION && "TLS version must be at least 1.2");
+}
+
+/**
+ * Assert that certificate verification succeeded
+ */
+void assert_certificate_verified(SSL *ssl) {
+    long verify_result = SSL_get_verify_result(ssl);
+    assert(verify_result == X509_V_OK && "Certificate verification must succeed");
+}
+
+/**
+ * Assert that cipher suite is secure
+ */
+void assert_secure_cipher(SSL *ssl) {
+    const SSL_CIPHER *cipher = SSL_get_current_cipher(ssl);
+    assert(cipher != NULL && "Cipher suite must be negotiated");
+
+    const char *cipher_name = SSL_CIPHER_get_name(cipher);
+    // Ensure no weak ciphers (NULL, EXPORT, DES, MD5, etc.)
+    assert(strstr(cipher_name, "NULL") == NULL && "NULL cipher not allowed");
+    assert(strstr(cipher_name, "EXPORT") == NULL && "EXPORT cipher not allowed");
+    assert(strstr(cipher_name, "DES") == NULL && "DES cipher not allowed");
+    assert(strstr(cipher_name, "MD5") == NULL && "MD5 cipher not allowed");
+}
+
+/**
+ * Assert that peer certificate is present
+ */
+void assert_peer_certificate_present(SSL *ssl) {
+    X509 *cert = SSL_get_peer_certificate(ssl);
+    assert(cert != NULL && "Peer certificate must be present");
+    X509_free(cert);
+}
+
+/**
+ * Run all TLS protocol assertions
+ */
+void run_tls_assertions(SSL *ssl) {
+    assert_min_tls_version(ssl);
+    assert_certificate_verified(ssl);
+    assert_secure_cipher(ssl);
+    assert_peer_certificate_present(ssl);
+}
diff --git a/tests/test_tls_protocol.c b/tests/test_tls_protocol.c
index a1b2c3d..e4f5g6h 100644
--- a/tests/test_tls_protocol.c
+++ b/tests/test_tls_protocol.c
@@ -15,6 +15,7 @@
 #include "../src/protocol/tls_handler.h"
+#include "../src/protocol/assertions.h"
 #include "test_helpers.h"

 void test_basic_handshake() {
@@ -28,7 +29,12 @@ void test_basic_handshake() {

     int result = tls_handshake(&conn);
     assert(result == 0);
+
+    // Run protocol compliance assertions
+    run_tls_assertions(conn.ssl);
+
     cleanup_connection(&conn);
+    printf("✓ Basic handshake test passed\\n");
 }

 void test_certificate_verification() {
"""

    # Parse diff into structured format
    files = [
        {
            "from": "src/protocol/tls_handler.c",
            "to": "src/protocol/tls_handler.c",
            "additions": 7,
            "deletions": 2,
            "hunks": [
                {
                    "oldStart": 45,
                    "oldLines": 7,
                    "newStart": 45,
                    "newLines": 7,
                    "lines": [
                        {"type": "normal", "content": "    X509 *cert = SSL_get_peer_certificate(ssl);"},
                        {"type": "normal", "content": "    "},
                        {"type": "normal", "content": "    if (!cert) {"},
                        {"type": "delete", "content": '        fprintf(stderr, "No certificate presented\\n");'},
                        {"type": "add", "content": '        log_error("No certificate presented by peer");'},
                        {"type": "normal", "content": "        return -1;"},
                        {"type": "normal", "content": "    }"},
                    ],
                },
                {
                    "oldStart": 67,
                    "oldLines": 12,
                    "newStart": 67,
                    "newLines": 18,
                    "lines": [
                        {"type": "normal", "content": "        return -1;"},
                        {"type": "normal", "content": "    }"},
                        {"type": "normal", "content": "    "},
                        {"type": "delete", "content": "    // Set verification mode"},
                        {"type": "delete", "content": "    SSL_set_verify(conn->ssl, SSL_VERIFY_PEER, NULL);"},
                        {"type": "add", "content": "    // Set strict verification mode with callback"},
                        {"type": "add", "content": "    SSL_set_verify(conn->ssl, SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT, verify_callback);"},
                        {"type": "add", "content": "    "},
                        {"type": "add", "content": "    // Set minimum TLS version to 1.2"},
                        {"type": "add", "content": "    SSL_set_min_proto_version(conn->ssl, TLS1_2_VERSION);"},
                        {"type": "normal", "content": "    "},
                        {"type": "normal", "content": "    // Perform handshake"},
                        {"type": "normal", "content": "    int ret = SSL_do_handshake(conn->ssl);"},
                        {"type": "normal", "content": "    if (ret != 1) {"},
                        {"type": "add", "content": "        int ssl_error = SSL_get_error(conn->ssl, ret);"},
                        {"type": "add", "content": '        log_error("TLS handshake failed with error code: %d", ssl_error);'},
                        {"type": "add", "content": "        ERR_print_errors_fp(stderr);"},
                        {"type": "normal", "content": "        return -1;"},
                        {"type": "normal", "content": "    }"},
                    ],
                },
            ],
        },
        {
            "from": "src/protocol/assertions.c",
            "to": "src/protocol/assertions.c",
            "additions": 52,
            "deletions": 0,
            "hunks": [
                {
                    "oldStart": 0,
                    "oldLines": 0,
                    "newStart": 1,
                    "newLines": 52,
                    "lines": [
                        {"type": "add", "content": '#include "assertions.h"'},
                        {"type": "add", "content": "#include <assert.h>"},
                        {"type": "add", "content": "#include <string.h>"},
                        {"type": "add", "content": ""},
                        {"type": "add", "content": "/**"},
                        {"type": "add", "content": " * Assert that TLS version is at least 1.2"},
                        {"type": "add", "content": " */"},
                        {"type": "add", "content": "void assert_min_tls_version(SSL *ssl) {"},
                        {"type": "add", "content": "    int version = SSL_version(ssl);"},
                        {"type": "add", "content": '    assert(version >= TLS1_2_VERSION && "TLS version must be at least 1.2");'},
                        {"type": "add", "content": "}"},
                        {"type": "add", "content": ""},
                        {"type": "add", "content": "/**"},
                        {"type": "add", "content": " * Assert that certificate verification succeeded"},
                        {"type": "add", "content": " */"},
                        {"type": "add", "content": "void assert_certificate_verified(SSL *ssl) {"},
                        {"type": "add", "content": "    long verify_result = SSL_get_verify_result(ssl);"},
                        {"type": "add", "content": '    assert(verify_result == X509_V_OK && "Certificate verification must succeed");'},
                        {"type": "add", "content": "}"},
                    ],
                },
            ],
        },
        {
            "from": "tests/test_tls_protocol.c",
            "to": "tests/test_tls_protocol.c",
            "additions": 6,
            "deletions": 0,
            "hunks": [
                {
                    "oldStart": 15,
                    "oldLines": 6,
                    "newStart": 15,
                    "newLines": 7,
                    "lines": [
                        {"type": "normal", "content": " "},
                        {"type": "normal", "content": '#include "../src/protocol/tls_handler.h"'},
                        {"type": "add", "content": '#include "../src/protocol/assertions.h"'},
                        {"type": "normal", "content": '#include "test_helpers.h"'},
                        {"type": "normal", "content": ""},
                        {"type": "normal", "content": "void test_basic_handshake() {"},
                    ],
                },
                {
                    "oldStart": 28,
                    "oldLines": 7,
                    "newStart": 29,
                    "newLines": 12,
                    "lines": [
                        {"type": "normal", "content": "    "},
                        {"type": "normal", "content": "    int result = tls_handshake(&conn);"},
                        {"type": "normal", "content": "    assert(result == 0);"},
                        {"type": "add", "content": "    "},
                        {"type": "add", "content": "    // Run protocol compliance assertions"},
                        {"type": "add", "content": "    run_tls_assertions(conn.ssl);"},
                        {"type": "add", "content": "    "},
                        {"type": "normal", "content": "    cleanup_connection(&conn);"},
                        {"type": "add", "content": '    printf("✓ Basic handshake test passed\\n");'},
                        {"type": "normal", "content": "}"},
                        {"type": "normal", "content": ""},
                        {"type": "normal", "content": "void test_certificate_verification() {"},
                    ],
                },
            ],
        },
    ]

    total_insertions = sum(f["additions"] for f in files)
    total_deletions = sum(f["deletions"] for f in files)

    return {
        "jobId": str(uuid.uuid4()),
        "diffContent": diff_content,
        "files": files,
        "summary": {
            "filesChanged": len(files),
            "insertions": total_insertions,
            "deletions": total_deletions,
        },
        "generatedAt": _now_iso(),
    }


# ============================================================================
# Patch File Reading & Matching
# ============================================================================

# Define the path to the assert-mock directory
# From: /home/xinrui/GitHub/vue-vben-admin/apps/backend-flask/protocol_compliance/assertion.py
# To:   /home/xinrui/GitHub/assert-mock
ASSERT_MOCK_DIR = Path(__file__).parent.parent.parent.parent.parent / "assert-mock"

# Available patch files
AVAILABLE_PATCH_FILES = [
    "wolfssl_assertion.patch",
    "uftp_assertion.patch",
    "tlse_assertion.patch",
    "tinymqtt_assertion.patch",
    "sol_assertion_changes.patch",
    "pure_ftpd_assertion.patch",
    "ndhs_assertion.patch",
    "mosquitto_assertion.patch",
    "libcoap_assertion.patch",
    "freecoap_assertion.patch",
]


def extract_protocol_name_from_database(database_filename: str) -> str:
    """
    Extract protocol name from database filename.
    Examples:
        sqlite_wolfssl.db -> wolfssl
        sqlite_mosquitto.db -> mosquitto
        violations.db -> violations
    """
    # Remove .db extension
    name = database_filename.replace(".db", "")
    
    # Remove sqlite_ prefix if present
    if name.startswith("sqlite_"):
        name = name[7:]  # len("sqlite_") = 7
    
    return name.lower()


def find_best_matching_patch_file(protocol_name: str, available_files: List[str]) -> Optional[str]:
    """
    Find the best matching patch file using string similarity.
    Returns the filename with the highest similarity score, or None if no good match.
    """
    if not protocol_name or not available_files:
        return None
    
    protocol_name_lower = protocol_name.lower()
    best_match = None
    best_score = 0.0
    
    for filename in available_files:
        # Extract the base name from the patch file (e.g., "wolfssl" from "wolfssl_assertion.patch")
        base_name = filename.replace("_assertion.patch", "").replace("_assertion_changes.patch", "")
        
        # Calculate similarity using SequenceMatcher
        similarity = difflib.SequenceMatcher(None, protocol_name_lower, base_name.lower()).ratio()
        
        if similarity > best_score:
            best_score = similarity
            best_match = filename
    
    # Only return a match if similarity is above 0.5 (50%)
    if best_score >= 0.5:
        LOGGER.info(
            "Matched protocol '%s' to patch file '%s' with similarity %.2f",
            protocol_name,
            best_match,
            best_score,
        )
        return best_match
    
    LOGGER.warning(
        "No good match found for protocol '%s'. Best match was '%s' with similarity %.2f",
        protocol_name,
        best_match,
        best_score,
    )
    return None


def parse_unified_diff(patch_content: str) -> Dict[str, object]:
    """
    Parse a unified diff patch file into structured format.
    Returns a dictionary with 'diffContent', 'files', and 'summary'.
    """
    files = []
    current_file = None
    current_hunk = None
    
    lines = patch_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Match file header: diff --git a/... b/...
        if line.startswith('diff --git'):
            # Save previous file if exists
            if current_file and current_hunk:
                current_file["hunks"].append(current_hunk)
                files.append(current_file)
            
            # Extract filenames
            match = re.search(r'a/(.*?)\s+b/(.*?)$', line)
            if match:
                current_file = {
                    "from": match.group(1),
                    "to": match.group(2),
                    "additions": 0,
                    "deletions": 0,
                    "hunks": []
                }
            current_hunk = None
        
        # Match old file: --- a/...
        elif line.startswith('---'):
            if current_file is None:
                match = re.search(r'---\s+a/(.*?)$', line)
                if match:
                    current_file = {
                        "from": match.group(1),
                        "to": "",
                        "additions": 0,
                        "deletions": 0,
                        "hunks": []
                    }
        
        # Match new file: +++ b/...
        elif line.startswith('+++'):
            if current_file:
                match = re.search(r'\+\+\+\s+b/(.*?)$', line)
                if match:
                    current_file["to"] = match.group(1)
        
        # Match hunk header: @@ -old_start,old_lines +new_start,new_lines @@
        elif line.startswith('@@'):
            # Save previous hunk if exists
            if current_hunk:
                current_file["hunks"].append(current_hunk)
            
            match = re.search(r'@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@', line)
            if match:
                old_start = int(match.group(1))
                old_lines = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_lines = int(match.group(4)) if match.group(4) else 1
                
                current_hunk = {
                    "oldStart": old_start,
                    "oldLines": old_lines,
                    "newStart": new_start,
                    "newLines": new_lines,
                    "lines": []
                }
        
        # Match diff content lines
        elif current_hunk is not None:
            if line.startswith('+') and not line.startswith('+++'):
                current_hunk["lines"].append({"type": "add", "content": line[1:]})
                current_file["additions"] += 1
            elif line.startswith('-') and not line.startswith('---'):
                current_hunk["lines"].append({"type": "delete", "content": line[1:]})
                current_file["deletions"] += 1
            elif line.startswith(' '):
                current_hunk["lines"].append({"type": "normal", "content": line[1:]})
            elif line.startswith('\\'):
                # Handle "\ No newline at end of file"
                pass
            else:
                # Context line without leading space (treat as normal)
                current_hunk["lines"].append({"type": "normal", "content": line})
        
        i += 1
    
    # Save last file and hunk
    if current_file:
        if current_hunk:
            current_file["hunks"].append(current_hunk)
        files.append(current_file)
    
    # Calculate summary
    total_files = len(files)
    total_insertions = sum(f["additions"] for f in files)
    total_deletions = sum(f["deletions"] for f in files)
    
    return {
        "diffContent": patch_content,
        "files": files,
        "summary": {
            "filesChanged": total_files,
            "insertions": total_insertions,
            "deletions": total_deletions,
        },
    }


def load_patch_from_database_name(database_filename: str) -> Optional[Dict[str, object]]:
    """
    Load and parse a patch file based on the database filename.
    Returns parsed diff structure or None if no matching patch found.
    """
    # Extract protocol name from database filename
    protocol_name = extract_protocol_name_from_database(database_filename)
    LOGGER.info("Extracted protocol name '%s' from database '%s'", protocol_name, database_filename)
    
    # Find best matching patch file
    patch_filename = find_best_matching_patch_file(protocol_name, AVAILABLE_PATCH_FILES)
    if not patch_filename:
        LOGGER.warning("No matching patch file found for protocol '%s'", protocol_name)
        return None
    
    # Construct full path to patch file
    patch_path = ASSERT_MOCK_DIR / patch_filename
    
    # Check if file exists
    if not patch_path.exists():
        LOGGER.error("Patch file not found at path: %s", patch_path)
        return None
    
    # Read patch file
    try:
        with open(patch_path, 'r', encoding='utf-8') as f:
            patch_content = f.read()
        
        LOGGER.info("Successfully read patch file: %s (%d bytes)", patch_filename, len(patch_content))
        
        # Parse the patch file
        parsed_diff = parse_unified_diff(patch_content)
        LOGGER.info(
            "Parsed patch: %d files, %d insertions, %d deletions",
            parsed_diff["summary"]["filesChanged"],
            parsed_diff["summary"]["insertions"],
            parsed_diff["summary"]["deletions"],
        )
        
        return parsed_diff
    except Exception as e:
        LOGGER.exception("Error reading or parsing patch file %s: %s", patch_path, e)
        return None


def submit_diff_parsing_job(parent_job_id: str) -> Dict[str, object]:
    """Launch diff parsing asynchronously and return initial snapshot."""

    state = DIFF_PARSING_REGISTRY.create_job(parent_job_id)
    job_id = state.job_id

    def _run_job() -> None:
        try:
            # Retrieve the parent assertion generation job to get database filename
            DIFF_PARSING_REGISTRY.mark_running(job_id, "init", "Starting diff parsing", 0)
            time.sleep(1)
            
            DIFF_PARSING_REGISTRY.append_event(job_id, "load", "Loading assertion generation metadata", 10)
            parent_snapshot = get_assert_generation_job(parent_job_id)
            
            database_filename = None
            if parent_snapshot:
                result = parent_snapshot.get("result")
                if isinstance(result, dict):
                    inputs = result.get("inputs")
                    if isinstance(inputs, dict):
                        database_filename = inputs.get("databaseFileName")
            
            if not database_filename:
                LOGGER.warning(
                    "Could not extract database filename from parent job %s, using fallback mock data",
                    parent_job_id
                )
                database_filename = "violations.db"  # Fallback
            
            LOGGER.info("Diff parsing job %s: database filename = %s", job_id, database_filename)
            
            # Try to load patch file from assert-mock directory
            DIFF_PARSING_REGISTRY.append_event(job_id, "match", "Matching database to patch file", 20)
            time.sleep(1)
            
            parsed_diff = load_patch_from_database_name(database_filename)
            
            if parsed_diff:
                LOGGER.info("Successfully loaded real patch file for database: %s", database_filename)
                DIFF_PARSING_REGISTRY.append_event(job_id, "parse", "Parsing unified diff format", 40)
                time.sleep(1)
                DIFF_PARSING_REGISTRY.append_event(job_id, "struct", "Building diff structure", 60)
                time.sleep(1)
                DIFF_PARSING_REGISTRY.append_event(job_id, "validate", "Validating diff hunks", 80)
                time.sleep(1)
                DIFF_PARSING_REGISTRY.append_event(job_id, "finalize", "Finalizing results", 95)
                time.sleep(0.5)
                
                # Add metadata to the result
                result = parsed_diff.copy()
                result["jobId"] = job_id
                result["generatedAt"] = _now_iso()
                result["metadata"] = {
                    "databaseFileName": database_filename,
                    "source": "patch_file"
                }
            else:
                # Fallback to mock data if no patch file found
                LOGGER.warning("No patch file found for database %s, using mock data", database_filename)
                DIFF_PARSING_REGISTRY.append_event(job_id, "fallback", "Using mock diff data", 50)
                time.sleep(2)
                DIFF_PARSING_REGISTRY.append_event(job_id, "finalize", "Finalizing mock results", 90)
                time.sleep(1)
                
                result = _generate_mock_diff()
                result["metadata"] = {
                    "databaseFileName": database_filename,
                    "source": "mock_data"
                }
            
            DIFF_PARSING_REGISTRY.complete(job_id, result)

        except Exception as exc:  # pragma: no cover
            LOGGER.exception("Diff parsing job %s encountered an error", job_id)
            DIFF_PARSING_REGISTRY.fail(
                job_id,
                "error",
                "Diff parsing failed",
                error=str(exc),
            )

    worker = threading.Thread(target=_run_job, name=f"diff-parsing-{job_id[:8]}", daemon=True)
    worker.start()
    snapshot = DIFF_PARSING_REGISTRY.snapshot(job_id)
    assert snapshot is not None
    return snapshot


def get_diff_parsing_job(job_id: str) -> Optional[Dict[str, object]]:
    return DIFF_PARSING_REGISTRY.snapshot(job_id)


def get_diff_parsing_result(job_id: str) -> Optional[Dict[str, object]]:
    snapshot = DIFF_PARSING_REGISTRY.snapshot(job_id)
    if not snapshot:
        return None
    if snapshot.get("status") != "completed":
        return None
    result = snapshot.get("result")
    if isinstance(result, dict):
        return result
    return None
