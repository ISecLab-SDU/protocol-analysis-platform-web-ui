import io
import json
from zipfile import ZipFile

import pytest
from flask import Blueprint, Flask
from protocol_compliance import impact_analysis as impact


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(impact, "ROOT", tmp_path / "jobs")
    monkeypatch.setattr(impact.threading.Thread, "start", lambda self: None)
    monkeypatch.setattr(
        impact,
        "resolve_assertion_runtime",
        lambda settings: {
            "PG_ASSERT_AGENT": "pi",
            "PG_PI_API": "openai-completions",
            "PG_PI_MODEL": "test",
        },
    )
    app = Flask(__name__)
    bp = Blueprint("impact_test", __name__)

    def authenticate():
        from flask import request

        return (
            ({"id": 1}, None)
            if request.headers.get("Authorization")
            else (None, ({"error": "unauthorized"}, 401))
        )

    impact.register_impact_routes(bp, authenticate)
    app.register_blueprint(bp)
    return app.test_client()


def submit(api, uploads):
    code, document = uploads
    return api.post(
        "/impact-analysis",
        headers={"Authorization": "test"},
        data={
            "code": (io.BytesIO(code), "source.zip"),
            "analysis": (io.BytesIO(document), "analysis.json"),
        },
    )


def test_authentication_applies_to_every_endpoint(api):
    for path in [
        "/impact-analysis/history",
        "/impact-analysis/bad/progress",
        "/impact-analysis/bad/result",
        "/impact-analysis/bad/download",
    ]:
        assert api.get(path).status_code == 401
    assert api.post("/impact-analysis").status_code == 401


def test_portable_upload_job_and_download(api, portable_analysis_uploads):
    response = submit(api, portable_analysis_uploads)
    assert response.status_code == 202, response.json
    job = response.json["data"]
    path = impact.job_path(job["jobId"])
    staged = json.loads((path / "input.json").read_text())
    assert staged["cases"][0]["report"]["target_source_path"] == "/source"
    assert staged["heavyStaticAnalysis"] is False
    assert "API_KEY" not in (path / "job.json").read_text()
    assert (
        api.get(
            f"/impact-analysis/{job['jobId']}/result", headers={"Authorization": "test"}
        ).status_code
        == 409
    )
    result = {"results": [{"assessment": {"outcome": "NON_SECURITY"}}]}
    (path / "artifacts/result.json").write_text(json.dumps(result))
    impact.save_job(path, status="completed")
    assert (
        api.get(
            f"/impact-analysis/{job['jobId']}/result", headers={"Authorization": "test"}
        ).json["data"]
        == result
    )
    archive = api.get(
        f"/impact-analysis/{job['jobId']}/download", headers={"Authorization": "test"}
    )
    with ZipFile(io.BytesIO(archive.data)) as bundle:
        assert json.loads(bundle.read("result.json")) == result
    assert (
        len(
            api.get("/impact-analysis/history", headers={"Authorization": "test"}).json[
                "data"
            ]
        )
        == 1
    )


def test_rejects_mismatching_source(api, portable_analysis_uploads):
    code, document = portable_analysis_uploads
    doc = json.loads(document)
    doc["source"]["files"][0]["sha256"] = "0" * 64
    response = submit(api, (code, json.dumps(doc).encode()))
    assert response.status_code == 400
    assert not list(impact.ROOT.glob("*/job.json"))


def test_rejects_ineligible_findings(api, portable_analysis_uploads):
    code, document = portable_analysis_uploads
    doc = json.loads(document)
    doc["results"][0]["verdict"] = "compliant"
    assert submit(api, (code, json.dumps(doc).encode())).status_code == 400
