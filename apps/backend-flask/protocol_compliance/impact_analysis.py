"""Authenticated, durable Docker jobs for ProtoXploit Phase 1."""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import request, send_file

from pg_analysis_exchange import eligible_results, extract_archive, validate_document
from utils.responses import error_response, success_response

from .assertion_runtime import resolve_assertion_runtime, runtime_summary

ROOT = Path(
    os.environ.get(
        "PROTOXPLOIT_STATE_DIR",
        Path.home() / ".local/share/protocolguard/impact-analysis",
    )
)
LOCK = threading.RLock()
PROCESSES: dict[str, subprocess.Popen] = {}


def job_path(job_id):
    if str(uuid.UUID(job_id)) != job_id:
        raise ValueError("Invalid job ID")
    return ROOT / job_id


def read_job(job_id):
    return json.loads((job_path(job_id) / "job.json").read_text())


def save_job(path, **fields):
    with LOCK:
        metadata = path / "job.json"
        data = json.loads(metadata.read_text()) if metadata.exists() else {}
        data.update(fields, updatedAt=datetime.now(timezone.utc).isoformat())
        temporary = path / "job.tmp"
        temporary.write_text(json.dumps(data, indent=2))
        temporary.replace(metadata)
        return data


def prepare_cases(document, source):
    validate_document(document, source)
    selected = eligible_results(document)
    if not selected:
        raise ValueError("No eligible non-compliant findings with source evidence")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", item["id"]) for item in selected):
        raise ValueError("Invalid finding ID")
    return [
        {
            "id": item["id"],
            "report": {
                "target_source_path": "/source",
                "source_tool": document["producer"]["name"],
                "protocol_target": document["protocol"]["name"],
                "rule_description": item["rule"]["description"],
                "deviation_description": item["reason"],
                "context_hints": json.dumps(
                    {
                        "locations": item["locations"],
                        "evidence": item.get("context", {}),
                    },
                    ensure_ascii=False,
                ),
            },
        }
        for item in selected
    ]


def run_job(path, source, env):
    job_id = path.name
    command = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        "pg-impact-" + job_id,
        "--network=host",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "-v",
        f"{source}:/source:ro",
        "-v",
        f"{path / 'input.json'}:/input.json:ro",
        "-v",
        f"{path / 'artifacts'}:/output:rw",
    ]
    for key in env:
        if key.startswith("PG_PI_"):
            command.extend(["-e", key])
    command.extend(
        [
            os.environ.get("PROTOXPLOIT_DOCKER_IMAGE", "protoxploit-phase1:main"),
            "--input",
            "/input.json",
            "--output-dir",
            "/output",
        ]
    )
    try:
        save_job(
            path,
            status="running",
            stage="phase1",
            message="Planning, collecting evidence and judging impact",
        )
        with (path / "execution.log").open("w") as log:
            process = subprocess.Popen(
                command, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, **env}
            )
            with LOCK:
                PROCESSES[job_id] = process
            code = process.wait(
                timeout=26
                * int(env.get("PG_PI_TIMEOUT_SECONDS", 2700))
                * len(json.loads((path / "input.json").read_text())["cases"])
                + 120
            )
        if code:
            raise RuntimeError(
                f"Phase 1 container exited with status {code}; inspect execution logs"
            )
        result = json.loads((path / "artifacts/result.json").read_text())
        if not result.get("results"):
            raise RuntimeError("Phase 1 did not produce assessments")
        save_job(
            path,
            status="completed",
            stage="completed",
            message="Impact analysis completed",
        )
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        subprocess.run(
            ["docker", "rm", "-f", "pg-impact-" + job_id],
            capture_output=True,
            check=False,
        )
        save_job(path, status="failed", stage="failed", message=str(exc))
    finally:
        with LOCK:
            PROCESSES.pop(job_id, None)


def register_impact_routes(bp, authenticate):
    @bp.post("/impact-analysis")
    def start_impact_analysis():
        _, error = authenticate()
        if error:
            return error
        code = request.files.get("code")
        analysis = request.files.get("analysis")
        if code is None or analysis is None:
            return error_response("Upload code and analysis files"), 400
        path = None
        try:
            mode = request.form.get("heavyStaticAnalysis", "false")
            if mode not in {"true", "false"}:
                raise ValueError("heavyStaticAnalysis must be true or false")
            heavy_static_analysis = mode == "true"
            runtime = json.loads(request.form.get("runtime", "{}"))
            env = resolve_assertion_runtime(runtime)
            document = json.load(analysis.stream)
            path = ROOT / str(uuid.uuid4())
            path.mkdir(parents=True)
            archive = path / "source.archive"
            code.save(archive)
            source = extract_archive(archive, path / "source")
            cases = prepare_cases(document, source)
            # Uploaded source is the evidence authority; portable evidence paths
            # are hints and never used as host filesystem paths.
            (path / "input.json").write_text(
                json.dumps(
                    {
                        "analysisId": document["analysisId"],
                        "cases": cases,
                        "heavyStaticAnalysis": heavy_static_analysis,
                        "timeoutSeconds": int(env.get("PG_PI_TIMEOUT_SECONDS", 2700)),
                    }
                )
            )
            (path / "analysis.json").write_text(json.dumps(document))
            (path / "artifacts").mkdir()
            job = save_job(
                path,
                jobId=path.name,
                workflow="Impact Analysis",
                status="queued",
                stage="queued",
                message="Impact analysis queued",
                createdAt=datetime.now(timezone.utc).isoformat(),
                analysisId=document["analysisId"],
                findingCount=len(cases),
                runtime=runtime_summary(env),
                heavyStaticAnalysis=heavy_static_analysis,
            )
            threading.Thread(
                target=run_job, args=(path, source, env), daemon=True
            ).start()
            return success_response(job), 202
        except (ValueError, OSError, KeyError, TypeError) as exc:
            if path:
                import shutil

                shutil.rmtree(path)
            return error_response(str(exc)), 400

    def get_authenticated(job_id):
        _, error = authenticate()
        if error:
            return None, error
        try:
            return read_job(job_id), None
        except (ValueError, OSError):
            return None, (error_response("Impact analysis job not found"), 404)

    @bp.get("/impact-analysis/history")
    def impact_history():
        _, error = authenticate()
        if error:
            return error
        entries = []
        for path in ROOT.glob("*/job.json"):
            try:
                entries.append(json.loads(path.read_text()))
            except (OSError, ValueError):
                continue
        return success_response(
            sorted(entries, key=lambda e: e["createdAt"], reverse=True)[:100]
        )

    @bp.get("/impact-analysis/<job_id>/progress")
    def impact_progress(job_id):
        job, error = get_authenticated(job_id)
        if error:
            return error
        log = job_path(job_id) / "execution.log"
        try:
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            return error_response("Invalid log offset"), 400
        content = b""
        if log.exists():
            with log.open("rb") as stream:
                stream.seek(offset)
                content = stream.read(128 * 1024)
        return success_response(
            {
                **job,
                "logs": content.decode(errors="replace"),
                "nextOffset": offset + len(content),
            }
        )

    @bp.get("/impact-analysis/<job_id>/result")
    def impact_result(job_id):
        job, error = get_authenticated(job_id)
        if error:
            return error
        if job["status"] != "completed":
            return error_response("Impact analysis has not completed", job), 409
        return success_response(
            json.loads((job_path(job_id) / "artifacts/result.json").read_text())
        )

    @bp.get("/impact-analysis/<job_id>/download")
    def impact_download(job_id):
        job, error = get_authenticated(job_id)
        if error:
            return error
        if job["status"] != "completed":
            return error_response("Impact analysis has not completed"), 409
        import io
        import zipfile

        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in (job_path(job_id) / "artifacts").rglob("*.json"):
                archive.write(path, path.relative_to(job_path(job_id) / "artifacts"))
        output.seek(0)
        return send_file(
            output,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"impact-{job_id}.zip",
        )
