"""High-level runner that coordinates ProtocolGuard Docker workloads."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import socket
import subprocess
import sqlite3
import textwrap
import tarfile
import time
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import toml

from .config import DEFAULT_CONFIG_PACKET_TYPES, ProtocolGuardDockerSettings, _ensure_directory, _env_int
from .errors import ProtocolGuardDockerError, ProtocolGuardExecutionError, ProtocolGuardNotAvailableError
from .job import JobPaths
from ..job_logging import JobStageLogger

docker: Any
DockerException: type[Exception]
ImageNotFound: type[Exception]

try:  # pragma: no cover - optional dependency
    import docker as _docker
    from docker.errors import DockerException as _DockerException, ImageNotFound as _ImageNotFound

    docker = _docker
    DockerException = _DockerException
    ImageNotFound = _ImageNotFound
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    docker = None
    DockerException = RuntimeError
    ImageNotFound = RuntimeError

LOGGER = logging.getLogger(__name__)


class ProtocolGuardDockerRunner:
    """High-level runner that coordinates builder + analysis containers."""

    def __init__(self, settings: ProtocolGuardDockerSettings) -> None:
        self._settings = settings
        if not settings.enabled:
            raise ProtocolGuardNotAvailableError("ProtocolGuard Docker integration is disabled")
        if docker is None:
            raise ProtocolGuardNotAvailableError("python -m pip install docker is required for Docker integration")
        try:
            self._client = docker.from_env()
        except DockerException as exc:  # pragma: no cover - requires docker engine
            raise ProtocolGuardNotAvailableError(f"Unable to connect to Docker engine: {exc}") from exc
        self._progress_callback: Optional[Callable[[str, str, str], None]] = None
        self._current_workspace_snapshots: List[Dict[str, str]] = []

    def _logger(self, job_paths: JobPaths) -> JobStageLogger:
        return JobStageLogger(
            job_id=job_paths.job_id,
            logger=LOGGER,
            progress_callback=self._progress_callback,
        )

    def _log_step(
        self,
        job_paths: JobPaths,
        stage: str,
        message: str,
        *,
        level: int = logging.INFO,
        context: Optional[Mapping[str, object]] = None,
    ) -> None:
        LOGGER.log(
            level,
            "[job %s][%s] %s",
            job_paths.job_id,
            stage,
            message,
            extra={"protocolguard_context": dict(context or {})},
        )
        if self._progress_callback:
            try:
                self._progress_callback(job_paths.job_id, stage, message)
            except Exception:  # pragma: no cover - defensive
                LOGGER.debug("Progress callback failed for job %s", job_paths.job_id, exc_info=True)

    # Public API -----------------------------------------------------------------

    def run_static_analysis(
        self,
        *,
        code_stream: BinaryIO,
        code_filename: str,
        builder_stream: BinaryIO,
        builder_filename: str,
        config_stream: BinaryIO,
        config_filename: str,
        rules_stream: BinaryIO,
        rules_filename: str,
        notes: Optional[str],
        protocol_name: Optional[str],
        protocol_version: Optional[str],
        rules_summary: Optional[str],
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> Dict[str, object]:
        """Execute the ProtocolGuard static workflow and return a structured response."""
        start = time.time()
        job_id = job_id or str(uuid.uuid4())
        job_paths = self._prepare_job_paths(job_id)
        self._progress_callback = progress_callback
        logger = self._logger(job_paths)
        self._current_workspace_snapshots = []

        with logger.state(stage="init"):
            logger.info("Starting ProtocolGuard static analysis job")

        built_builder_image: Optional[str] = None

        try:
            with logger.state(stage="workspace", workspace=job_paths.workspace):
                logger.info("Staging workspace directories")
                self._stage_workspace(job_paths)
                self._ensure_workspace_structure(job_paths)
                logger.info("Workspace directories prepared")

            uploads_dir = job_paths.workspace / "uploads"
            code_filename_real = code_filename or "source-archive"
            code_path = self._write_stream(uploads_dir / code_filename_real, code_stream)
            rules_filename_real = rules_filename or self._settings.artifacts.rule_config.name
            builder_filename_real = builder_filename or "Dockerfile"
            config_filename_real = config_filename or "config.toml"

            project_dir = job_paths.workspace / "project"
            with logger.state(stage="workspace", project_dir=project_dir, code_archive=code_path):
                logger.info("Preparing project directory for source archive")
                self._reset_directory(project_dir)
                self._extract_archive(code_path, project_dir)

                if not any(project_dir.iterdir()):
                    raise ProtocolGuardDockerError(
                        "Source archive did not contain any files. Please verify the uploaded archive."
                    )
                logger.info("Source archive extracted")

            with logger.state(stage="inputs", project_dir=project_dir):
                code_archive_in_project = project_dir / code_filename_real
                shutil.copy2(code_path, code_archive_in_project)
                logger.info(
                    "Copied code archive to project context: %s",
                    code_archive_in_project,
                    source=code_path,
                    destination=code_archive_in_project,
                )

                dockerfile_path = project_dir / builder_filename_real
                logger.info("Writing builder Dockerfile to workspace", path=dockerfile_path)
                self._write_stream(dockerfile_path, builder_stream)

                rules_path = self._stage_rules_file(job_paths, rules_stream)
                rules_path_in_project = project_dir / "inputs" / "rules.json"
                rules_path_in_project.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rules_path, rules_path_in_project)
                logger.info(
                    "Copied rules file to project context: %s",
                    rules_path_in_project,
                    source=rules_path,
                    destination=rules_path_in_project,
                )

                rule_config_path_in_project = project_dir / "rule_config.json"
                shutil.copy2(rules_path, rule_config_path_in_project)
                logger.info(
                    "Copied rule_config.json to project root: %s",
                    rule_config_path_in_project,
                    source=rules_path,
                    destination=rule_config_path_in_project,
                )

            with logger.state(stage="config", config_file=job_paths.config_file):
                logger.info("Loading and preparing config file", source=config_filename_real)
                config_data = self._load_config(config_stream, config_filename)
                prepared_config = self._prepare_config(
                    config_data=config_data,
                    job_paths=job_paths,
                    protocol_name=protocol_name,
                    protocol_version=protocol_version,
                )
                self._write_config(job_paths.config_file, prepared_config)
                logger.info("Config file written to workspace")

            with logger.state(stage="inputs", project_dir=project_dir):
                config_path_in_project = project_dir / "config.toml"
                self._write_config(config_path_in_project, prepared_config)
                logger.info(
                    "Copied prepared config file to project context: %s",
                    config_path_in_project,
                    destination=config_path_in_project,
                )

            builder_image = None
            with logger.state(stage="builder", project_dir=project_dir):
                if builder_stream:
                    logger.info("Building builder image from uploaded Dockerfile", dockerfile=dockerfile_path)
                    builder_image = self._build_builder_image(
                        job_paths=job_paths,
                        context_dir=project_dir,
                        dockerfile_path=dockerfile_path,
                    )
                    built_builder_image = builder_image
                elif self._settings.builder_image:
                    logger.info("Using default builder image from environment", image=self._settings.builder_image)
                    builder_image = self._settings.builder_image
                else:
                    raise ProtocolGuardDockerError(
                        "Builder Dockerfile not provided and no default builder image configured."
                    )

            LOGGER.debug("Staged code archive at %s, project at %s, rules at %s", code_path, project_dir, rules_path)

            if builder_image:
                with logger.state(stage="builder", image=builder_image):
                    logger.info("Running builder container image %s", builder_image)
                    self._run_builder(
                        job_paths,
                        image=builder_image,
                        command=self._settings.builder_command,
                    )
                    logger.info("Builder container completed")

            with logger.state(stage="validation"):
                logger.info("Validating required artefacts exist before analysis")
                self._validate_required_inputs(job_paths)
                logger.info("All required artefacts present")

            with logger.state(stage="analysis", image=self._settings.analysis_image):
                logger.info("Launching analysis container image %s", self._settings.analysis_image)
                logs = self._run_analysis(job_paths, command=self._settings.analysis_command)
                logger.info("Analysis container completed successfully")

            with logger.state(stage="results", output=job_paths.output):
                logger.info("Collecting analysis results and metadata")
                result = self._collect_results(
                    job_paths=job_paths,
                    start_time=start,
                    code_filename=Path(code_filename_real).name,
                    builder_filename=Path(builder_filename_real).name,
                    config_filename=Path(config_filename_real).name,
                    notes=notes,
                    rules_summary=rules_summary,
                    rules_filename=Path(rules_filename_real).name,
                    protocol_name=protocol_name,
                    protocol_version=protocol_version,
                    docker_logs=logs,
                    workspace_snapshots=self._current_workspace_snapshots,
                )
                logger.info("ProtocolGuard job completed successfully")
            return result
        except Exception:
            with logger.state(stage="error"):
                logger.log(logging.ERROR, "ProtocolGuard job failed")
            LOGGER.exception("ProtocolGuard job %s failed", job_id)
            raise
        finally:
            self._progress_callback = None
            self._current_workspace_snapshots = []
            with logger.state(stage="cleanup", workspace=job_paths.workspace):
                if built_builder_image:
                    with logger.state(image=built_builder_image):
                        if self._settings.keep_builder_images:
                            logger.info("Retaining builder image %s for Docker cache reuse", built_builder_image)
                        else:
                            logger.info("Removing temporary builder image %s", built_builder_image)
                            self._remove_builder_image(built_builder_image)
                if not self._settings.keep_artifacts:
                    logger.info("Cleaning up workspace artefacts")
                    self._cleanup_job(job_paths)
            self._rotate_runtime_artifacts(active_job_id=job_paths.job_id)

    def run_assert_generation(
        self,
        *,
        code_stream: BinaryIO,
        code_filename: str,
        database_stream: BinaryIO,
        database_filename: str,
        build_instructions: Optional[str],
        notes: Optional[str],
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> Dict[str, object]:
        """Execute the ProtocolGuard assertion generation workflow."""

        start = time.time()
        job_id = job_id or str(uuid.uuid4())
        job_paths = self._prepare_job_paths(job_id)
        self._progress_callback = progress_callback
        logger = self._logger(job_paths)
        self._current_workspace_snapshots = []

        with logger.state(stage="init"):
            logger.info("Starting ProtocolGuard assertion generation job")

        if not build_instructions or not build_instructions.strip():
            raise ProtocolGuardDockerError("Build instructions are required for assertion generation")

        command = ["assert", "--compile-command", build_instructions.strip()]

        try:
            with logger.state(stage="workspace", workspace=job_paths.workspace):
                logger.info("Preparing workspace directories")
                self._reset_directory(job_paths.workspace)
                self._stage_workspace(job_paths)

                uploads_dir = job_paths.workspace / "uploads"
                project_dir = job_paths.workspace / "project"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                project_dir.mkdir(parents=True, exist_ok=True)

                code_filename_real = code_filename or "source-archive"
                with logger.state(uploads_dir=uploads_dir):
                    logger.info("Persisting uploaded source archive", filename=code_filename_real)
                    code_path = self._write_stream(uploads_dir / code_filename_real, code_stream)

                with logger.state(project_dir=project_dir):
                    logger.info("Extracting source archive into /workspace/project")
                    self._reset_directory(project_dir)
                    self._extract_archive(code_path, project_dir)
                    if not any(project_dir.iterdir()):
                        raise ProtocolGuardDockerError(
                            "Source archive did not contain any files. Please verify the uploaded archive."
                        )
                    logger.info("Source archive extracted into project directory")

                database_filename_real = database_filename or "violations.db"
                database_destination = job_paths.workspace / "violations.db"
                logger.info(
                    "Staging analysis result data for assertion generation",
                    destination=database_destination,
                )
                self._write_stream(database_destination, database_stream)
                if not database_destination.exists() or database_destination.stat().st_size == 0:
                    raise ProtocolGuardDockerError("Uploaded database file is empty. Please verify the input.")

                build_instructions_text = build_instructions.strip() if build_instructions else ""
                if build_instructions_text:
                    instructions_path = job_paths.workspace / "build_instructions.txt"
                    instructions_path.write_text(build_instructions_text, encoding="utf-8")
                    logger.info("Build instructions written to build_instructions.txt", path=instructions_path)
                else:
                    logger.info("No build instructions provided; skipping file write")

                notes_text = notes.strip() if notes else ""
                if notes_text:
                    notes_path = job_paths.workspace / "notes.txt"
                    notes_path.write_text(notes_text, encoding="utf-8")
                    logger.info("Notes written to notes.txt", path=notes_path)

            self._snapshot_workspace(job_paths, stage="prepared")

            with logger.state(stage="analysis", image=self._settings.analysis_image):
                logger.info("Launching assertion generation container image %s", self._settings.analysis_image)
                logs = self._run_analysis(job_paths, command=command)
                logger.info("Assertion generation container completed successfully")

            assert_tasks_dir = job_paths.output / "assert_tasks"
            if not assert_tasks_dir.exists() or not assert_tasks_dir.is_dir():
                raise ProtocolGuardExecutionError(
                    "Assertion generation completed but assert_tasks directory was not found in /out.",
                    logs=logs,
                    image=self._settings.analysis_image,
                    status=0,
                )

            with logger.state(stage="results", output=job_paths.output):
                zip_destination = job_paths.output / "assert_tasks.zip"
                logger.info(
                    "Packaging assert_tasks artefacts into ZIP archive",
                    source=assert_tasks_dir,
                    destination=zip_destination,
                )
                self._zip_directory(assert_tasks_dir, zip_destination)

                self._snapshot_workspace(job_paths, stage="post-run")

                workspace_snapshots = [dict(snapshot) for snapshot in self._current_workspace_snapshots]
                duration_ms = int((time.time() - start) * 1000)
                now_iso = datetime.now(timezone.utc).isoformat()
                assertion_count = self._count_files(assert_tasks_dir)
                protocol_name = self._settings.default_protocol_name

                result: Dict[str, object] = {
                    "jobId": job_paths.job_id,
                    "generatedAt": now_iso,
                    "assertionCount": assertion_count,
                    "protocolName": protocol_name,
                    "inputs": {
                        "codeFileName": Path(code_filename_real).name,
                        "databaseFileName": Path(database_filename_real).name,
                        "buildInstructions": build_instructions_text or None,
                        "notes": notes_text or None,
                    },
                    "artifacts": {
                        "workspace": str(job_paths.workspace),
                        "output": str(job_paths.output),
                        "logs": str(job_paths.log_file),
                        "zipPath": str(zip_destination),
                        "database": str(database_destination),
                        "workspaceSnapshots": workspace_snapshots,
                    },
                    "docker": {
                        "image": self._settings.analysis_image,
                        "command": list(command),
                        "logs": logs,
                        "durationMs": duration_ms,
                    },
                }

                logger.info("Assertion generation completed successfully", assertion_count=assertion_count)
            return result
        except Exception:
            with logger.state(stage="error"):
                logger.log(logging.ERROR, "Assertion generation job failed")
            LOGGER.exception("ProtocolGuard assertion generation job %s failed", job_id)
            raise
        finally:
            self._progress_callback = None
            self._current_workspace_snapshots = []
            self._rotate_runtime_artifacts(active_job_id=job_paths.job_id)

    # Workspace preparation ------------------------------------------------------

    def _prepare_job_paths(self, job_id: str) -> JobPaths:
        workspace = _ensure_directory((self._settings.workspace_root / job_id).resolve())
        output = _ensure_directory((self._settings.output_root / job_id).resolve())
        config_dir = _ensure_directory((self._settings.config_root / job_id).resolve())
        config_file = config_dir / "config.toml"
        log_file = output / "analysis.log"
        return JobPaths(
            job_id=job_id,
            workspace=workspace,
            output=output,
            config_dir=config_dir,
            config_file=config_file,
            log_file=log_file,
        )

    def _stage_workspace(self, job_paths: JobPaths) -> None:
        if self._settings.template_workspace:
            LOGGER.debug(
                "Seeding workspace %s from template %s",
                job_paths.workspace,
                self._settings.template_workspace,
            )
            self._copy_tree(self._settings.template_workspace, job_paths.workspace)

    def _copy_tree(self, source: Path, destination: Path) -> None:
        if not source.exists():
            LOGGER.warning("Template workspace %s does not exist; skipping copy", source)
            return
        for item in source.iterdir():
            dest_path = destination / item.name
            if item.is_dir():
                shutil.copytree(item, dest_path, dirs_exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)

    def _write_stream(self, destination: Path, stream: BinaryIO) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(Exception):
            stream.seek(0)
        with destination.open("wb") as handle:
            shutil.copyfileobj(stream, handle)
        return destination

    def _reset_directory(self, target: Path) -> None:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

    def _ensure_workspace_structure(self, job_paths: JobPaths) -> None:
        workspace = job_paths.workspace
        artifacts = self._settings.artifacts
        for relative in (
            artifacts.bitcode,
            artifacts.build_log,
            artifacts.wpa_report,
            artifacts.packet_callgraph,
            artifacts.function_summary,
            artifacts.rule_config,
        ):
            (workspace / relative).parent.mkdir(parents=True, exist_ok=True)
        database_dir = workspace / artifacts.database
        database_dir.mkdir(parents=True, exist_ok=True)

    def _extract_archive(self, archive: Path, destination: Path) -> None:
        if tarfile.is_tarfile(archive):
            with tarfile.open(archive, "r:*") as tar:
                self._safe_extract_tar(tar, destination)
            return
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive, "r") as zip_file:
                self._safe_extract_zip(zip_file, destination)
            return
        shutil.copy2(archive, destination / archive.name)

    def _safe_extract_tar(self, tar_obj: tarfile.TarFile, destination: Path) -> None:
        for member in tar_obj.getmembers():
            member_path = destination / member.name
            if not self._is_within_directory(destination, member_path):
                raise ProtocolGuardDockerError(
                    f"Tar archive contains unsafe path traversal entry: {member.name}"
                )
        tar_obj.extractall(destination)

    def _safe_extract_zip(self, zip_obj: zipfile.ZipFile, destination: Path) -> None:
        for member in zip_obj.namelist():
            member_path = destination / member
            if not self._is_within_directory(destination, member_path):
                raise ProtocolGuardDockerError(
                    f"Zip archive contains unsafe path traversal entry: {member}"
                )
        zip_obj.extractall(destination)

    def _is_within_directory(self, base: Path, target: Path) -> bool:
        try:
            target.resolve(strict=False).relative_to(base.resolve(strict=False))
            return True
        except ValueError:
            return False

    def _stage_rules_file(self, job_paths: JobPaths, stream: BinaryIO) -> Path:
        rules_path = job_paths.workspace / self._settings.artifacts.rule_config
        return self._write_stream(rules_path, stream)

    def _load_config(self, stream: BinaryIO, filename: str) -> Dict[str, object]:
        with contextlib.suppress(Exception):
            stream.seek(0)
        raw = stream.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolGuardDockerError(
                f"Configuration file {filename!r} must be UTF-8 encoded."
            ) from exc
        try:
            data = toml.loads(text)
        except toml.TomlDecodeError as exc:
            raise ProtocolGuardDockerError(
                f"Failed to parse configuration file {filename!r}: {exc}"
            ) from exc
        return data

    def _prepare_config(
        self,
        *,
        config_data: Dict[str, object],
        job_paths: JobPaths,
        protocol_name: Optional[str],
        protocol_version: Optional[str],
    ) -> Dict[str, object]:
        data: Dict[str, object] = deepcopy(config_data)
        artifacts = self._settings.artifacts
        protocol = protocol_name or self._settings.default_protocol_name
        version = protocol_version or self._settings.default_protocol_version
        workspace_prefix = "/workspace"

        def container_path(relative: Path) -> str:
            rel = relative.as_posix()
            if rel in ("", "."):
                return workspace_prefix
            return f"{workspace_prefix}/{rel}"

        def object_dict(value: object) -> Dict[str, object]:
            return {str(key): item for key, item in value.items()} if isinstance(value, Mapping) else {}

        project_section = object_dict(data.get("project"))
        project_section["project_name"] = project_section.get("project_name") or self._settings.project_name
        project_section["project_path"] = f"{workspace_prefix}/project"
        project_section["protocol_name"] = protocol
        project_section["protocol_version"] = version
        project_section["bitcode_path"] = container_path(artifacts.bitcode)
        project_section["binary_path"] = container_path(artifacts.binary_path)
        project_section["build_log_path"] = container_path(artifacts.build_log)
        project_section["original_llvm_ir_path"] = container_path(artifacts.original_ir)
        project_section["packet_related_callgraph_path"] = container_path(artifacts.packet_callgraph)
        project_section["function_arg_path"] = container_path(artifacts.function_summary)
        project_section["rule_path"] = container_path(artifacts.rule_config)
        data["project"] = project_section

        database_section = object_dict(data.get("database"))
        database_section["path"] = container_path(artifacts.database)
        data["database"] = database_section

        wpa_section = object_dict(data.get("wpa"))
        wpa_section["path"] = container_path(artifacts.wpa_report)
        data["wpa"] = wpa_section

        debug_section = object_dict(data.get("debug"))
        debug_section["code_slice_replace_mode"] = self._settings.debug_code_slice_mode
        debug_section["log_print"] = _env_int("PG_DEBUG_LOG_PRINT", 0) or 0
        data["debug"] = debug_section

        config_section = object_dict(data.get("config"))
        for key, values in DEFAULT_CONFIG_PACKET_TYPES.items():
            config_section.setdefault(key, list(values))
        data["config"] = config_section

        return data

    def _build_builder_image(
        self,
        *,
        job_paths: JobPaths,
        context_dir: Path,
        dockerfile_path: Path,
    ) -> str:
        try:
            dockerfile_rel = dockerfile_path.relative_to(context_dir)
        except ValueError as exc:
            raise ProtocolGuardDockerError(
                f"Builder Dockerfile {dockerfile_path} must reside within the uploaded project directory."
            ) from exc

        tag = f"protocolguard-builder:{job_paths.job_id}"
        self._log_step(
            job_paths,
            "builder",
            f"Using docker CLI (BuildKit) for builder image (tag={tag}, context={context_dir}, dockerfile={dockerfile_rel})",
        )

        proxy_url = self._detect_builder_proxy()
        if proxy_url:
            self._log_step(
                job_paths,
                "proxy",
                f"✓ Proxy detected and will be configured: {proxy_url}",
            )
        else:
            self._log_step(
                job_paths,
                "proxy",
                "✗ No proxy detected on port 63333 - building without proxy",
            )
        try:
            return self._build_builder_image_with_cli(
                job_paths=job_paths,
                context_dir=context_dir,
                dockerfile_rel=dockerfile_rel,
                tag=tag,
                proxy_url=proxy_url,
            )
        except ProtocolGuardDockerError:
            raise

    def _build_builder_image_with_cli(
        self,
        *,
        job_paths: JobPaths,
        context_dir: Path,
        dockerfile_rel: Path,
        tag: str,
        proxy_url: Optional[str] = None,
    ) -> str:
        env = {str(k): str(v) for k, v in os.environ.items()}
        env.setdefault("DOCKER_BUILDKIT", "1")
        env.setdefault("BUILDKIT_PROGRESS", "plain")
        
        # Type 4: Proxy provided by the SHELL when Docker process runs
        # Set proxy environment variables if port 63333 is responsive
        if proxy_url:
            self._log_step(
                job_paths,
                "proxy",
                f"[Type 4] Setting shell proxy environment (HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy) = {proxy_url}",
            )
            for proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                env.setdefault(proxy_var, proxy_url)
        command = [
            "docker",
            "build",
            "--progress=plain",
            "--network=host",
            "--file",
            str(dockerfile_rel),
            "--tag",
            tag,
        ]
        if proxy_url:
            self._log_step(
                job_paths,
                "proxy",
                f"[Type 1] Setting Docker CLI build-args (HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy) = {proxy_url}",
            )
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                command.extend(["--build-arg", f"{key}={proxy_url}"])
        
        # Log comprehensive proxy status summary
        proxy_summary = self._build_proxy_summary(proxy_url)
        self._log_step(job_paths, "proxy", f"Proxy Configuration Summary:\n{proxy_summary}")
        
        command.append(".")
        self._log_step(job_paths, "builder", f"Retrying builder image {tag} using docker CLI with BuildKit enabled")
        try:
            process = subprocess.Popen(
                command,
                cwd=str(context_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
            )
        except OSError as exc:
            raise ProtocolGuardDockerError(f"Failed to invoke docker CLI for builder image build: {exc}") from exc

        assert process.stdout is not None
        build_log_lines: List[str] = []
        with job_paths.log_file.open("a", encoding="utf-8") as log_file:
            try:
                for line in process.stdout:
                    text = line.rstrip()
                    if text:
                        build_log_lines.append(text)
                        log_file.write(text + "\n")
                        self._log_step(job_paths, "builder-log", text)
            finally:
                process.stdout.close()
        exit_code = process.wait()
        if exit_code != 0:
            last_lines = "\n".join(build_log_lines[-30:]) if build_log_lines else "(no log output)"
            raise ProtocolGuardDockerError(
                f"Docker CLI build failed for builder image {tag} with exit code {exit_code}.\n"
                f"Last 30 lines of build output:\n{last_lines}"
            )
        self._log_step(job_paths, "builder", f"docker CLI build completed for {tag}")
        return tag

    @staticmethod
    def _detect_builder_proxy(host: str = "127.0.0.1", port: int = 63333, timeout: float = 0.5) -> Optional[str]:
        """
        Detect if a proxy is available on the specified port.
        This checks port 63333 by default for proxy availability.
        """
        LOGGER.info("🔍 Checking for proxy availability on %s:%s (timeout=%.1fs)", host, port, timeout)
        try:
            with contextlib.closing(socket.create_connection((host, port), timeout=timeout)):
                proxy_url = f"http://{host}:{port}"
                LOGGER.info("✓ Proxy is RESPONSIVE on %s:%s → Will use: %s", host, port, proxy_url)
                return proxy_url
        except OSError as exc:
            LOGGER.info("✗ Proxy is NOT responsive on %s:%s → Building WITHOUT proxy (reason: %s)", host, port, exc)
            return None

    @staticmethod
    def _build_proxy_summary(proxy_url: Optional[str]) -> str:
        """
        Build a human-readable summary of Docker proxy configuration status.
        Explains which of the 4 proxy types are configured.
        """
        if proxy_url:
            return textwrap.dedent(f"""\
                ┌─────────────────────────────────────────────────────────────┐
                │ Docker Proxy Configuration Status (Port 63333 RESPONSIVE)  │
                ├─────────────────────────────────────────────────────────────┤
                │ [Type 1] Docker CLI Build Args      : ✓ ENABLED ({proxy_url})
                │ [Type 2] Docker Daemon Config       : ⊗ NOT CONFIGURABLE
                │ [Type 3] Inside Container Proxy     : ⊗ NOT SET (Dockerfile only)
                │ [Type 4] Shell Environment Proxy    : ✓ ENABLED ({proxy_url})
                └─────────────────────────────────────────────────────────────┘
                """).strip()
        else:
            return textwrap.dedent("""\
                ┌─────────────────────────────────────────────────────────────┐
                │ Docker Proxy Configuration Status (Port 63333 NOT DETECTED)│
                ├─────────────────────────────────────────────────────────────┤
                │ [Type 1] Docker CLI Build Args      : ✗ DISABLED
                │ [Type 2] Docker Daemon Config       : ⊗ NOT CONFIGURABLE
                │ [Type 3] Inside Container Proxy     : ⊗ NOT SET (Dockerfile only)
                │ [Type 4] Shell Environment Proxy    : ✗ DISABLED
                └─────────────────────────────────────────────────────────────┘
                """).strip()

    def _remove_builder_image(self, tag: str) -> None:
        if not tag or docker is None:
            return
        try:
            self._client.images.remove(tag, force=True)
            LOGGER.debug("Removed temporary builder image %s", tag)
        except DockerException as exc:
            LOGGER.warning("Failed to remove builder image %s: %s", tag, exc)

    # Container orchestration ----------------------------------------------------

    def _build_volumes(self, job_paths: JobPaths, *, include_config: bool) -> Mapping[str, Mapping[str, str]]:
        volumes: Dict[str, Dict[str, str]] = {
            str(job_paths.workspace): {"bind": "/workspace", "mode": "rw"},
            str(job_paths.output): {"bind": "/out", "mode": "rw"},
        }
        if include_config:
            volumes[str(job_paths.config_dir)] = {"bind": "/config", "mode": "ro"}
        return volumes

    def _build_environment(self) -> Dict[str, str]:
        env: Dict[str, str] = {}
        for name in self._settings.env_passthrough:
            value = os.environ.get(name)
            if value is not None:
                env[name] = value
        env["PG_HOST_UID"] = str(os.getuid())
        env["PG_HOST_GID"] = str(os.getgid())
        return env

    def _snapshot_workspace(self, job_paths: JobPaths, *, stage: str) -> Optional[Path]:
        if not self._settings.workspace_snapshots_enabled:
            self._log_step(
                job_paths,
                "workspace-snapshot",
                f"Workspace snapshot for stage {stage} skipped; snapshots are disabled",
            )
            return None

        slug = f"{stage}-{uuid.uuid4().hex[:8]}"
        snapshot_root = _ensure_directory(
            (self._settings.output_root / "_workspace_snapshots" / job_paths.job_id).resolve()
        )
        destination = snapshot_root / slug
        try:
            shutil.copytree(job_paths.workspace, destination)
        except Exception as exc:  # pragma: no cover - defensive
            self._log_step(
                job_paths,
                "workspace-snapshot",
                f"Failed to capture workspace snapshot for stage {stage}: {exc}",
                level=logging.WARNING,
            )
            return None

        self._log_step(
            job_paths,
            "workspace-snapshot",
            f"Workspace snapshot for stage {stage} stored at {destination}",
        )
        self._current_workspace_snapshots.append({"stage": stage, "path": str(destination)})
        return destination

    def _run_builder(
        self,
        job_paths: JobPaths,
        *,
        image: str,
        command: Optional[Sequence[str]] = None,
    ) -> None:
        if not image:
            raise ProtocolGuardDockerError("Builder image is required to execute the ProtocolGuard pipeline.")
        self._log_step(
            job_paths,
            "builder",
            f"Starting builder container (image={image}, command={' '.join(command) if command else '<default>'})",
        )
        self._run_container(
            job_paths=job_paths,
            image=image,
            command=command,
            volumes=self._build_volumes(job_paths, include_config=False),
            environment=self._build_environment(),
            log_destination=job_paths.log_file,
        )
        self._snapshot_workspace(job_paths, stage="builder")

    def _run_analysis(self, job_paths: JobPaths, *, command: Sequence[str]) -> List[str]:
        command_display = " ".join(command) if command else "<default>"
        self._log_step(
            job_paths,
            "analysis",
            f"Starting analysis container (image={self._settings.analysis_image}, command={command_display})",
        )
        volumes = self._build_volumes(job_paths, include_config=True)
        environment = self._build_environment()

        self._inspect_analysis_workspace(job_paths, volumes=volumes, environment=environment)
        logs = self._run_container(
            image=self._settings.analysis_image,
            command=command,
            job_paths=job_paths,
            volumes=volumes,
            environment=environment,
            log_destination=job_paths.log_file,
            timeout=self._settings.analysis_timeout,
        )
        self._snapshot_workspace(job_paths, stage="main")
        return logs

    def _inspect_analysis_workspace(
        self,
        job_paths: JobPaths,
        *,
        volumes: Mapping[str, Mapping[str, str]],
        environment: Mapping[str, str],
    ) -> None:
        preview_command = textwrap.dedent(
            """\
            set -eu
            echo '[pg-debug] ===== workspace mount inspection ====='
            echo '[pg-debug] container pwd: ' "$(pwd)"
            if [ -d /workspace ]; then
              echo '[pg-debug] ls -al /workspace'
              ls -al /workspace
              echo '[pg-debug] tree -a -L 2 /workspace'
              tree -a -L 2 /workspace || (echo '[pg-debug] tree failed - falling back to find'; find /workspace -maxdepth 2 -mindepth 1 -print || true)
            else
              echo '[pg-debug] /workspace directory missing'
            fi
            """
        ).strip()

        try:
            image_details = self._client.images.get(self._settings.analysis_image)
        except ImageNotFound:
            self._log_step(
                job_paths,
                "analysis-debug",
                f"Skipping workspace inspection: analysis image {self._settings.analysis_image} not found locally",
                level=logging.WARNING,
            )
            return
        except DockerException as exc:  # pragma: no cover - requires docker engine
            self._log_step(
                job_paths,
                "analysis-debug",
                f"Failed to resolve analysis image {self._settings.analysis_image}: {exc}",
                level=logging.WARNING,
            )
            return

        # Prefer the tagged reference for readability; fall back to image ID.
        image_reference = self._settings.analysis_image or image_details.id
        # Some Docker SDK versions are finicky about entrypoint types; try robust fallbacks.
        run_attempts = [
            {"entrypoint": ["/bin/sh", "-lc"], "command": [preview_command]},
            {"entrypoint": ["bash", "-lc"], "command": [preview_command]},
            {"entrypoint": "/bin/sh", "command": ["-c", preview_command]},
        ]

        last_error: Optional[Exception] = None
        for attempt in run_attempts:
            try:
                output = self._client.containers.run(
                    image=image_reference,
                    entrypoint=attempt["entrypoint"],
                    command=attempt["command"],
                    volumes=volumes,
                    environment=environment,
                    stdout=True,
                    stderr=True,
                    remove=True,
                    network=self._settings.network,
                )
                break
            except DockerException as exc:  # pragma: no cover - requires docker engine
                last_error = exc
                continue
        else:
            # All attempts failed; log the last error and continue without inspection.
            self._log_step(
                job_paths,
                "analysis-debug",
                f"Failed to inspect /workspace mount before analysis: {last_error}",
                level=logging.WARNING,
            )
            return

        if not output:
            self._log_step(job_paths, "analysis-debug", "Workspace inspection produced no output")
            return

        if isinstance(output, bytes):
            lines = output.decode("utf-8", errors="replace").splitlines()
        else:
            lines = str(output).splitlines()

        with job_paths.log_file.open("a", encoding="utf-8") as log_file:
            for raw_line in lines:
                line = raw_line.rstrip()
                if not line:
                    continue
                log_file.write(line + "\n")
                display_line = line if len(line) <= 2000 else f"{line[:2000]}..."
                self._log_step(job_paths, "analysis-debug", display_line)

    def _run_container(
        self,
        *,
        job_paths: JobPaths,
        image: str,
        command: Optional[Sequence[str]],
        volumes: Mapping[str, Mapping[str, str]],
        environment: Mapping[str, str],
        log_destination: Path,
        timeout: Optional[int] = None,
    ) -> List[str]:
        if not volumes:
            raise ProtocolGuardDockerError("No volumes specified for container execution")
        try:
            container = self._client.containers.run(
                image=image,
                command=list(command) if command else None,
                volumes=volumes,
                environment=environment,
                detach=True,
                remove=False,
                stdout=True,
                stderr=True,
                network=self._settings.network,
            )
        except DockerException as exc:  # pragma: no cover - requires docker engine
            raise ProtocolGuardDockerError(f"Failed to start container {image}: {exc}") from exc
        self._log_step(job_paths, "container", f"Container {container.id[:12]} started for image {image}")

        logs: List[str] = []
        with log_destination.open("a", encoding="utf-8") as log_file:
            for chunk in container.logs(stream=True, follow=True):
                line = chunk.decode("utf-8", errors="replace").rstrip()
                log_file.write(line + "\n")
                logs.append(line)
                if line:
                    display_line = line if len(line) <= 2000 else f"{line[:2000]}..."
                    self._log_step(
                        job_paths,
                        "container-log",
                        f"{image}: {display_line}",
                    )

        try:
            result = container.wait(timeout=timeout)
        except DockerException as exc:  # pragma: no cover - requires docker engine
            raise ProtocolGuardDockerError(f"Failed waiting for container exit: {exc}") from exc
        finally:
            with contextlib.suppress(Exception):
                container.remove(force=True)

        status = result.get("StatusCode", 1)
        if status != 0:
            excerpt = "\n".join(logs[-40:]) if logs else None
            self._log_step(
                job_paths,
                "container",
                f"Container for image {image} exited with status {status}",
                level=logging.ERROR,
            )
            raise ProtocolGuardExecutionError(
                f"Container {image} exited with status {status}",
                logs=logs,
                log_excerpt=excerpt,
                image=image,
                status=status,
            )
        self._log_step(job_paths, "container", f"Container for image {image} exited cleanly")
        return logs

    # Validation ----------------------------------------------------------------

    def _validate_required_inputs(self, job_paths: JobPaths) -> None:
        workspace = job_paths.workspace
        artefacts = {
            "bitcode": workspace / self._settings.artifacts.bitcode,
            "build log": workspace / self._settings.artifacts.build_log,
        }
        missing = [label for label, path in artefacts.items() if not path.exists()]
        self._log_step(job_paths, "container", f"Validating required artefacts: {str(artefacts)}")
        if missing:
            raise ProtocolGuardDockerError(
                f"Missing required artefacts before analysis: {', '.join(missing)}"
            )

    # Config generation ----------------------------------------------------------

    def _build_config(
        self,
        *,
        job_paths: JobPaths,
        rules_path: Path,
        protocol_name: Optional[str],
        protocol_version: Optional[str],
    ) -> Dict[str, object]:
        workspace = job_paths.workspace
        artifacts = self._settings.artifacts
        protocol = protocol_name or self._settings.default_protocol_name
        version = protocol_version or self._settings.default_protocol_version
        project_name = self._settings.project_name

        database_path = workspace / artifacts.database

        config: Dict[str, object] = {
            "wpa": {
                "path": str((workspace / artifacts.wpa_report).resolve()),
            },
            "database": {
                "path": str(database_path.resolve()),
            },
            "llm": {
                "llm_api_platform": os.environ.get("PG_LLM_API_BASE", "https://example.com/v1/chat/completions"),
                "llm_model_deepseek_v3": self._settings.llm_model_v3,
                "llm_model_deepseek_r1": self._settings.llm_model_r1,
                "llm_query_repeat_times": self._settings.llm_query_repeat,
                "llm_query_max_attempts": self._settings.llm_query_max_attempts,
                "llm_violation_repeat_times": self._settings.llm_violation_repeat_times,
                "llm_multithread": _env_int("PG_LLM_MAX_THREADS", 32) or 32,
            },
            "project": {
                "project_path": str(workspace.resolve()),
                "packet_related_callgraph_path": str((workspace / artifacts.packet_callgraph).resolve()),
                "function_arg_path": str((workspace / artifacts.function_summary).resolve()),
                "rule_path": str(rules_path.resolve()),
                "protocol_name": protocol,
                "protocol_version": version,
                "project_name": project_name,
                "original_llvm_ir_path": str((workspace / artifacts.original_ir).resolve()),
                "binary_path": str((workspace / artifacts.binary_path).resolve()),
                "bitcode_path": str((workspace / artifacts.bitcode).resolve()),
                "build_log_path": str((workspace / artifacts.build_log).resolve()),
            },
            "debug": {
                "code_slice_replace_mode": self._settings.debug_code_slice_mode,
                "log_print": _env_int("PG_DEBUG_LOG_PRINT", 0) or 0,
            },
            "config": {key: list(values) for key, values in DEFAULT_CONFIG_PACKET_TYPES.items()},
        }
        return config

    def _write_config(self, destination: Path, config_data: Mapping[str, object]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as handle:
            toml.dump(config_data, handle)

    # Result collation -----------------------------------------------------------

    def _collect_results(
        self,
        *,
        job_paths: JobPaths,
        start_time: float,
        code_filename: str,
        builder_filename: str,
        config_filename: str,
        notes: Optional[str],
        rules_summary: Optional[str],
        rules_filename: str,
        protocol_name: Optional[str],
        protocol_version: Optional[str],
        docker_logs: List[str],
        workspace_snapshots: Sequence[Mapping[str, str]],
    ) -> Dict[str, object]:
        end = time.time()
        protocol = protocol_name or self._settings.default_protocol_name
        version = protocol_version or self._settings.default_protocol_version

        db_path = self._find_database(job_paths)
        if db_path is None:
            raise ProtocolGuardExecutionError(
                "ProtocolGuard analysis completed but database file was not found",
                logs=docker_logs,
            )
        db_path = self._persist_database_artifact(job_paths, db_path)
        findings, summary_counts = self._extract_findings(db_path, protocol, version)

        if not findings:
            raise ProtocolGuardExecutionError(
                "ProtocolGuard analysis completed but no findings were produced",
                logs=docker_logs,
            )

        overall_status = self._determine_overall_status(summary_counts)
        now_iso = datetime.now(timezone.utc).isoformat()

        summary_notes = notes or rules_summary or "ProtocolGuard static analysis completed via Docker integration."

        result: Dict[str, object] = {
            "analysisId": job_paths.job_id,
            "durationMs": int((end - start_time) * 1000),
            "inputs": {
                "codeFileName": code_filename,
                "builderDockerfileName": builder_filename,
                "configFileName": config_filename,
                "notes": notes or None,
                "protocolName": protocol,
                "rulesFileName": rules_filename,
                "rulesSummary": rules_summary or None,
            },
            "model": self._settings.analysis_image,
            "modelResponse": {
                "metadata": {
                    "generatedAt": now_iso,
                    "modelVersion": self._settings.analysis_image,
                    "protocol": protocol,
                    "ruleSet": rules_filename,
                    "protocolVersion": version,
                },
                "summary": {
                    "compliantCount": summary_counts["compliant"],
                    "needsReviewCount": summary_counts["needs_review"],
                    "nonCompliantCount": summary_counts["non_compliant"],
                    "notes": summary_notes,
                    "overallStatus": overall_status,
                },
                "verdicts": findings,
            },
            "submittedAt": now_iso,
            "artifacts": {
                "workspace": str(job_paths.workspace),
                "output": str(job_paths.output),
                "config": str(job_paths.config_file),
                "logs": str(job_paths.log_file),
                "database": str(db_path) if db_path else None,
                "workspaceSnapshots": [dict(snapshot) for snapshot in workspace_snapshots],
            },
        }
        return result

    def _find_database(self, job_paths: JobPaths) -> Optional[Path]:
        # 优先搜索已知的database子目录
        database_dir = job_paths.output / "database"
        LOGGER.debug("[查找数据库] 优先搜索 database 子目录: %s", database_dir)
        if database_dir.exists():
            candidates = list(database_dir.glob("*.db"))
            LOGGER.debug("[查找数据库] 在 %s 找到 %d 个 .db 文件: %s", database_dir, len(candidates), candidates)
            if candidates:
                LOGGER.debug("[查找数据库] 选择数据库: %s", candidates[0])
                return candidates[0]

        # 回退到递归搜索output目录
        LOGGER.debug("[查找数据库] 递归搜索 output 目录: %s", job_paths.output)
        candidates = list(job_paths.output.rglob("*.db"))
        LOGGER.debug("[查找数据库] 在 output 找到 %d 个 .db 文件: %s", len(candidates), candidates)

        if not candidates:
            LOGGER.debug("[查找数据库] 递归搜索 workspace 目录: %s", job_paths.workspace)
            candidates = list(job_paths.workspace.rglob("*.db"))
            LOGGER.debug("[查找数据库] 在 workspace 找到 %d 个 .db 文件: %s", len(candidates), candidates)

        if not candidates:
            LOGGER.error(
                "[查找数据库] 未找到数据库文件！Output: %s, Workspace: %s",
                job_paths.output,
                job_paths.workspace,
            )
            return None

        LOGGER.info("[查找数据库] 最终选择数据库: %s", candidates[0])
        return candidates[0]

    def _persist_database_artifact(self, job_paths: JobPaths, db_path: Path) -> Path:
        database_dir = job_paths.output / "database"
        database_dir.mkdir(parents=True, exist_ok=True)
        destination = database_dir / db_path.name
        if db_path.resolve(strict=False) == destination.resolve(strict=False):
            return db_path
        try:
            shutil.copy2(db_path, destination)
        except OSError as exc:
            LOGGER.warning("Failed to persist SQLite database artifact %s -> %s: %s", db_path, destination, exc)
            return db_path
        return destination

    def _zip_directory(self, source: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        root_parent = source.parent
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for folder_path, dirnames, filenames in os.walk(source):
                folder = Path(folder_path)
                rel_dir = folder.relative_to(root_parent).as_posix()
                zip_file.writestr(f"{rel_dir}/", "")
                for filename in filenames:
                    abs_path = folder / filename
                    arcname = abs_path.relative_to(root_parent).as_posix()
                    zip_file.write(abs_path, arcname)
        return destination

    def _count_files(self, directory: Path) -> int:
        return sum(1 for path in directory.rglob("*") if path.is_file())

    def _extract_findings(
        self,
        db_path: Optional[Path],
        protocol_name: str,
        protocol_version: str,
    ) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
        findings: List[Dict[str, object]] = []
        counts = {"compliant": 0, "needs_review": 0, "non_compliant": 0}

        if db_path is None or not db_path.exists():
            LOGGER.warning("No SQLite database found in analysis outputs")
            return findings, counts

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("PRAGMA table_info(rule_code_snippet)")
                columns = [str(row[1]) for row in cursor.fetchall()]
                LOGGER.debug(
                    "*** ProtocolGuard rule_code_snippet static collect: db=%s columns=%s ***",
                    db_path,
                    columns,
                )
                cursor.execute("SELECT rowid, rule_desc, code_snippet, llm_response FROM rule_code_snippet")
            except sqlite3.DatabaseError as exc:
                LOGGER.warning("Unable to query rule_code_snippet table: %s", exc)
                return findings, counts

            rows = cursor.fetchall()

        LOGGER.debug(
            "*** ProtocolGuard rule_code_snippet static collect: db=%s row_count=%d ***",
            db_path,
            len(rows),
        )

        for index, (row_id, rule_desc, code_snippet, llm_response) in enumerate(rows, start=1):
            code_snippet_text = code_snippet if isinstance(code_snippet, str) else ""
            llm_response_text = llm_response if isinstance(llm_response, str) else ""
            LOGGER.debug(
                (
                    "*** ProtocolGuard rule_code_snippet static collect row=%s "
                    "rule_len=%d code_snippet_len=%d llm_response_len=%d "
                    "code_snippet_preview=%r ***"
                ),
                row_id,
                len(str(rule_desc or "")),
                len(code_snippet_text),
                len(llm_response_text),
                code_snippet_text[:240].replace("\n", "\\n"),
            )
            compliance, rule_findings = self._parse_llm_response(
                llm_response,
                rule_desc,
                protocol_name,
                protocol_version,
                index,
            )
            counts[compliance] += 1
            findings.extend(rule_findings)

        return findings, counts

    def _parse_llm_response(
        self,
        llm_response: Optional[str],
        rule_desc: str,
        protocol_name: str,
        protocol_version: str,
        index: int,
    ) -> Tuple[str, List[Dict[str, object]]]:
        compliance = "needs_review"
        verdicts: List[Dict[str, object]] = []

        if not llm_response:
            LOGGER.debug("Empty LLM response for rule %s", rule_desc)
            return compliance, verdicts

        try:
            payload = json.loads(llm_response)
        except json.JSONDecodeError:
            LOGGER.warning("Failed to decode LLM response for rule %s", rule_desc)
            return compliance, verdicts

        result = str(payload.get("result", "")).strip().lower()
        reason = str(payload.get("reason", "")).strip()
        violations = payload.get("violations")

        if result == "violation found!" or result == "violation_found":
            compliance = "non_compliant"
        elif result == "no violation found!" or result == "no_violation_found":
            compliance = "compliant"
        else:
            compliance = "needs_review"

        if isinstance(violations, list) and violations:
            for violation in violations:
                verdicts.append(
                    self._build_verdict_entry(
                        compliance=compliance,
                        reason=reason,
                        violation=violation,
                        rule_desc=rule_desc,
                        protocol_name=protocol_name,
                        protocol_version=protocol_version,
                        index=index,
                    )
                )
        else:
            verdicts.append(
                self._build_verdict_entry(
                    compliance=compliance,
                    reason=reason,
                    violation=None,
                    rule_desc=rule_desc,
                    protocol_name=protocol_name,
                    protocol_version=protocol_version,
                    index=index,
                )
            )

        return compliance, verdicts

    def _build_verdict_entry(
        self,
        *,
        compliance: str,
        reason: str,
        violation: Optional[Mapping[str, object]],
        rule_desc: str,
        protocol_name: str,
        protocol_version: str,
        index: int,
    ) -> Dict[str, object]:
        line_range: Optional[List[int]] = None
        location_file: Optional[str] = None
        location_function: Optional[str] = None

        if violation and isinstance(violation, Mapping):
            lines = violation.get("code_lines")
            if isinstance(lines, list) and lines:
                numeric = [int(line) for line in lines if isinstance(line, (int, float))]
                if numeric:
                    line_range = [min(numeric), max(numeric)]
            file_name = violation.get("filename")
            if isinstance(file_name, str):
                location_file = file_name
            function_name = violation.get("function_name")
            if isinstance(function_name, str):
                location_function = function_name

        verdict: Dict[str, object] = {
            "category": "LLM Rule Compliance",
            "compliance": compliance,
            "confidence": "medium",
            "explanation": reason or "ProtocolGuard did not provide additional context.",
            "findingId": str(uuid.uuid4()),
            "location": {
                "file": location_file or "",
                "function": location_function or None,
            },
            "recommendation": None,
            "relatedRule": {
                "id": f"RULE-{index:03d}",
                "requirement": rule_desc,
                "source": f"{protocol_name} {protocol_version}".strip(),
            },
        }
        if line_range:
            verdict["lineRange"] = line_range
        return verdict

    def _determine_overall_status(self, counts: Mapping[str, int]) -> str:
        if counts.get("non_compliant", 0):
            return "non_compliant"
        if counts.get("needs_review", 0):
            return "needs_review"
        return "compliant"

    # Cleanup -------------------------------------------------------------------

    def _cleanup_job(self, job_paths: JobPaths) -> None:
        for path in (job_paths.workspace, job_paths.output, job_paths.config_dir):
            with contextlib.suppress(Exception):
                shutil.rmtree(path)

    def cleanup_assertion_intermediates(
        self,
        *,
        job_id: Optional[str] = None,
    ) -> None:
        """Rotate old runtime artefacts.  Intermediate files are no longer deleted."""
        self._rotate_runtime_artifacts(active_job_id=job_id)

    def _rotate_runtime_artifacts(self, *, active_job_id: Optional[str] = None) -> None:
        if not self._settings.runtime_cleanup_enabled:
            return
        try:
            self._rotate_runtime_artifacts_once(active_job_id=active_job_id)
        except Exception as exc:  # pragma: no cover - defensive cleanup guard
            LOGGER.warning("ProtocolGuard runtime cleanup failed: %s", exc, exc_info=True)

    def _rotate_runtime_artifacts_once(self, *, active_job_id: Optional[str] = None) -> None:
        job_paths = self._collect_runtime_job_paths()
        if active_job_id:
            job_paths.pop(active_job_id, None)
        if not job_paths:
            return

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self._settings.runtime_retention_days)
        ordered_job_ids = sorted(
            job_paths,
            key=lambda job_id: self._latest_mtime(job_paths[job_id]),
            reverse=True,
        )
        retained_by_count = set(ordered_job_ids[: self._settings.runtime_retention_max_jobs])

        for job_id, paths in job_paths.items():
            older_than_retention = all(self._path_mtime(path) < cutoff for path in paths)
            beyond_count = job_id not in retained_by_count
            if not older_than_retention and not beyond_count:
                continue
            self._delete_runtime_paths(job_id, paths)

        self._remove_empty_snapshot_root()

    def _collect_runtime_job_paths(self) -> Dict[str, List[Path]]:
        roots = (
            self._settings.workspace_root,
            self._settings.output_root,
            self._settings.config_root,
            self._settings.output_root / "_workspace_snapshots",
        )
        jobs: Dict[str, List[Path]] = {}
        for root in roots:
            root_resolved = root.expanduser().resolve(strict=False)
            if not root_resolved.exists() or not root_resolved.is_dir() or root_resolved.is_symlink():
                continue
            for child in root_resolved.iterdir():
                if child.name == "_workspace_snapshots":
                    continue
                if not child.is_dir() or child.is_symlink():
                    continue
                if not self._is_managed_runtime_path(child):
                    continue
                jobs.setdefault(child.name, []).append(child)
        return jobs

    def _is_managed_runtime_path(self, path: Path) -> bool:
        managed_roots = (
            self._settings.workspace_root,
            self._settings.output_root,
            self._settings.config_root,
            self._settings.output_root / "_workspace_snapshots",
        )
        resolved = path.resolve(strict=False)
        for root in managed_roots:
            root_resolved = root.expanduser().resolve(strict=False)
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                continue
            return True
        return False

    def _delete_runtime_paths(self, job_id: str, paths: Sequence[Path]) -> None:
        for path in paths:
            if not self._is_managed_runtime_path(path):
                LOGGER.warning("Skipping unmanaged ProtocolGuard cleanup path for job %s: %s", job_id, path)
                continue
            if path.is_symlink() or not path.exists() or not path.is_dir():
                continue
            try:
                shutil.rmtree(path, ignore_errors=True)
                LOGGER.info("Deleted ProtocolGuard runtime artefacts for job %s: %s", job_id, path)
            except Exception as exc:  # pragma: no cover - defensive cleanup guard
                LOGGER.warning("Failed to delete ProtocolGuard runtime path %s for job %s: %s", path, job_id, exc)

    def _remove_empty_snapshot_root(self) -> None:
        snapshot_root = (self._settings.output_root / "_workspace_snapshots").expanduser().resolve(strict=False)
        if not snapshot_root.exists() or not snapshot_root.is_dir() or snapshot_root.is_symlink():
            return
        with contextlib.suppress(Exception):
            snapshot_root.rmdir()

    def _latest_mtime(self, paths: Sequence[Path]) -> datetime:
        return max(self._path_mtime(path) for path in paths)

    def _path_mtime(self, path: Path) -> datetime:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
