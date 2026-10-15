"""Exercise the portable handoff at its real file, API and CLI boundaries."""

from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import zipfile

import pytest
from flask import Flask

from pg_analysis_exchange import (
    eligible_results,
    export_database,
    extract_archive,
    read_database_document,
    validate_document,
)
from protocol_compliance.analysis_exchange import (
    persist_exchange,
    prepare_assertion_document,
)
from protocol_compliance import static_analysis_job_routes

CORE = Path(__file__).resolve().parents[4] / "ProtocolGuard"


def archive_bytes(files, wrapper="release"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in files.items():
            archive.writestr(f"{wrapper}/{name}", data)
    return stream.getvalue()


@pytest.fixture
def exchange(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    (original / "main.c").write_text("int main(void) {\n  return 0;\n}\n")
    database = tmp_path / "analysis.db"
    with sqlite3.connect(database) as conn:
        conn.execute(
            "CREATE TABLE rule_code_snippet (rule_desc TEXT, code_snippet TEXT, call_graph TEXT, llm_response TEXT)"
        )
        conn.executemany(
            "INSERT INTO rule_code_snippet VALUES (?, ?, ?, ?)",
            [
                (
                    "Reject invalid input",
                    "original slice",
                    "main -> parse",
                    json.dumps(
                        {
                            "result": "violation found!",
                            "reason": "Missing validation",
                            "violations": [
                                {
                                    "filename": "/workspace/project/main.c",
                                    "function_name": "main",
                                    "code_lines": [2],
                                }
                            ],
                        }
                    ),
                ),
                (
                    "Correct behavior",
                    "slice",
                    "",
                    '{"result":"no violation found!","reason":"Validated"}',
                ),
                ("Uncertain behavior", "slice", "", "{broken"),
            ],
        )
    document = export_database(
        database,
        original,
        analysis_id="analysis-1",
        archive_name="source.zip",
        protocol="MQTT",
        protocol_version="3.1.1",
        analyzed_root=original,
        rules=[{"rule": "Reject invalid input", "req_type": "PUBLISH"}],
    )
    return original, database, document


def test_export_preserves_all_results_and_has_no_ast_dependency(exchange):
    original, _, document = exchange
    assert {r["verdict"] for r in document["results"]} == {
        "compliant",
        "non_compliant",
        "needs_review",
    }
    (result,) = eligible_results(document)
    assert result["rule"]["requestTypes"] == ["PUBLISH"]
    assert result["locations"][0]["path"] == "main.c"
    assert result["locations"][0]["code"] == "  return 0;\n"
    assert validate_document(document, original) is document


def test_repackaging_and_fresh_workspace_import(exchange):
    original, database, document = exchange
    source = archive_bytes(
        {"main.c": (original / "main.c").read_bytes()}, "different-wrapper"
    )
    database.unlink()
    imported = prepare_assertion_document(
        "repacked.zip", source, document_data=json.dumps(document).encode()
    )
    assert imported == document


@pytest.mark.parametrize(
    "files",
    [
        {"main.c": "changed"},
        {"main.c": "int main(void) {\n  return 0;\n}\n", "added.txt": "extra"},
        {"other.c": "int main(void) {\n  return 0;\n}\n"},
    ],
)
def test_source_mismatch_blocks_before_job(exchange, files):
    with pytest.raises(ValueError, match="does not match"):
        prepare_assertion_document(
            "source.zip",
            archive_bytes(files),
            document_data=json.dumps(exchange[2]).encode(),
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(schemaVersion="2.0"),
        lambda d: d.update(generatedAt="not-a-date"),
        lambda d: d["results"].append(copy.deepcopy(d["results"][0])),
        lambda d: eligible_results(d)[0]["locations"][0].update(path="../main.c"),
        lambda d: eligible_results(d)[0]["locations"][0].update(endLine=999),
        lambda d: eligible_results(d)[0]["locations"][0].update(code="fabricated code"),
        lambda d: d["diagnostics"].append(
            {
                "code": "test",
                "severity": "blocking",
                "message": "test",
                "resultId": "missing",
            }
        ),
    ],
)
def test_invalid_contracts_rejected(exchange, change):
    original, _, document = exchange
    change(document)
    with pytest.raises(ValueError):
        validate_document(document, original)


def test_additive_fields_and_manifest_property_order(exchange):
    original, _, document = exchange
    document["schemaVersion"] = "1.1"
    document["futureMetadata"] = {"test": True}
    document["source"]["files"] = [
        {"sha256": e["sha256"], "path": e["path"]} for e in document["source"]["files"]
    ]
    validate_document(document, original)


def test_unresolved_or_changed_analysis_source_is_blocked(exchange):
    original, database, _ = exchange
    built = original.parent / "built"
    built.mkdir()
    (built / "main.c").write_text("changed during build")
    document = export_database(
        database,
        original,
        analysis_id="test",
        archive_name="src.zip",
        protocol="MQTT",
        analyzed_root=built,
    )
    assert not eligible_results(document)
    assert any(
        d["code"] == "location_unresolved"
        for r in document["results"]
        for d in r["diagnostics"]
    )


def test_legacy_requires_provenance_and_matches_database(exchange):
    original, database, document = exchange
    with pytest.raises(ValueError, match="Legacy database"):
        read_database_document(database, original)
    persist_exchange(document, database.parent, database)
    assert read_database_document(database, original) == document
    with database.open("ab") as stream:
        stream.write(b"modified")
    with pytest.raises(ValueError, match="Legacy database"):
        read_database_document(database, original)


def test_real_consumer_cli_without_producer_workspace(exchange, tmp_path):
    original, database, document = exchange
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    (fresh / "main.c").write_bytes((original / "main.c").read_bytes())
    document_path = tmp_path / "exchange.json"
    document_path.write_text(json.dumps(document))
    database.unlink()
    (original / "main.c").unlink()
    output = tmp_path / "tasks"
    output.mkdir()
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [
                str(CORE / "dynamic_verification/analysis_exchange/src"),
                str(CORE / "dynamic_verification/assert_generate/src"),
            ]
        ),
    }
    result = subprocess.run(
        [
            os.sys.executable,
            "-m",
            "assert_generate",
            "--analysis-document",
            str(document_path),
            "--source-root",
            str(fresh),
            "--output_dir",
            str(output),
        ],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    prompt = (output / "cursorkleosr/task/rule1.txt").read_text()
    assert (
        "Reject invalid input" in prompt and "main.c" in prompt and "return 0" in prompt
    )
    index = json.loads((output / "cursorkleosr/analysis-task-index.json").read_text())
    assert index["analysisId"] == document["analysisId"]
    assert len(index["tasks"]) == 1


def test_schema_and_implementation_mirrors_match():
    backend = Path(__file__).resolve().parents[1] / "pg_analysis_exchange"
    core = CORE / "dynamic_verification/analysis_exchange/src/pg_analysis_exchange"
    for name in ["__init__.py", "schema.json"]:
        assert (backend / name).read_bytes() == (core / name).read_bytes()


def test_download_auth_completion_and_persisted_artifact(exchange, monkeypatch):
    _, database, document = exchange
    path = persist_exchange(document, database.parent, database)
    app = Flask(__name__)
    handlers = static_analysis_job_routes.create_static_analysis_job_handlers(
        lambda: ("user", None)
    )
    app.add_url_rule(
        "/exchange/<job_id>", view_func=handlers["download_static_analysis_exchange"]
    )
    snapshot = {"status": "completed"}
    monkeypatch.setattr(
        static_analysis_job_routes, "get_static_analysis_job", lambda _: snapshot
    )
    monkeypatch.setattr(
        static_analysis_job_routes,
        "get_static_analysis_result",
        lambda _: {"artifacts": {"exchange": str(path)}},
    )
    response = app.test_client().get("/exchange/analysis-1")
    assert response.status_code == 200
    assert response.json == document
    assert "analysis-analysis-1.json" in response.headers["Content-Disposition"]
    snapshot["status"] = "running"
    assert app.test_client().get("/exchange/analysis-1").status_code == 409
    snapshot["status"] = "failed"
    assert app.test_client().get("/exchange/analysis-1").status_code == 409
    monkeypatch.setattr(
        static_analysis_job_routes, "get_static_analysis_job", lambda _: None
    )
    assert app.test_client().get("/exchange/analysis-1").status_code == 404
    denied = static_analysis_job_routes.create_static_analysis_job_handlers(
        lambda: (None, ("unauthorized", 401))
    )
    with app.test_request_context():
        assert denied["download_static_analysis_exchange"]("analysis-1") == (
            "unauthorized",
            401,
        )


@pytest.mark.parametrize("name", ["../escape.c", "/escape.c", "bad\\escape.c"])
def test_archive_member_escapes_rejected(tmp_path, name):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr(name, "unsafe")
    with pytest.raises(ValueError):
        extract_archive(archive, tmp_path / "source")


def test_assertion_http_rejects_invalid_or_ambiguous_inputs_before_job(
    monkeypatch, portable_analysis_uploads
):
    from protocol_compliance import assertion_routes

    monkeypatch.setattr(assertion_routes, "resolve_assertion_runtime", lambda _: {})
    submitted = []
    monkeypatch.setattr(
        assertion_routes,
        "submit_assert_generation_job",
        lambda **kwargs: submitted.append(kwargs) or {"jobId": "test-job"},
    )
    handlers = assertion_routes.create_assertion_handlers(
        lambda: ("user", None),
        lambda _: None,
        lambda f: (f.filename, f.read()),
        lambda _: (None, []),
    )
    app = Flask(__name__)
    app.add_url_rule(
        "/assert", view_func=handlers["assertion_generation"], methods=["POST"]
    )
    code, document = portable_analysis_uploads
    client = app.test_client()

    def payload(doc=document):
        return {
            "codeArchive": (io.BytesIO(code), "source.zip"),
            "analysisDocument": (io.BytesIO(doc), "analysis.json"),
        }

    request = payload()
    request["database"] = (io.BytesIO(b"db"), "legacy.db")
    assert client.post("/assert", data=request).status_code == 400
    assert client.post("/assert", data=payload(b"{broken")).status_code == 400
    changed = payload()
    changed["codeArchive"] = (
        io.BytesIO(archive_bytes({"main.c": "changed"})),
        "changed.zip",
    )
    assert client.post("/assert", data=changed).status_code == 400
    assert submitted == []
    assert client.post("/assert", data=payload()).status_code == 202
    assert len(submitted) == 1
    name, data = submitted[0]["database_payload"]
    assert name == "analysis.json"
    assert json.loads(data) == json.loads(document)


def test_export_retry_uses_retained_inputs_and_then_serves_same_artifact(exchange):
    import shutil
    from protocol_compliance.analysis_exchange import resolve_exchange_artifact

    original, database, _ = exchange
    workspace = original.parent / "workspace"
    shutil.copytree(original, workspace / "exchange-source")
    shutil.copytree(original, workspace / "project")
    (workspace / "inputs").mkdir()
    (workspace / "inputs/rules.json").write_text("{}")
    result = {
        "analysisId": "retry-analysis",
        "artifacts": {
            "workspace": str(workspace),
            "database": str(database),
            "output": str(original.parent / "output"),
        },
        "inputs": {"codeFileName": "source.zip", "protocolName": "MQTT"},
    }
    path = resolve_exchange_artifact(result)
    contents = path.read_bytes()
    database.unlink()
    assert resolve_exchange_artifact(result).read_bytes() == contents
    assert json.loads(contents)["analysisId"] == "retry-analysis"


def test_multiple_locations_keep_one_assertion_task_per_result(exchange):
    original, _, document = exchange
    result = eligible_results(document)[0]
    extra = copy.deepcopy(result["locations"][0])
    extra.update(
        id="location-2",
        startLine=1,
        endLine=1,
        relevantLines=[1],
        code="int main(void) {\n",
    )
    result["locations"].append(extra)
    validate_document(document, original)
    assert len(eligible_results(document)) == 1
    assert len(eligible_results(document)[0]["locations"]) == 2
