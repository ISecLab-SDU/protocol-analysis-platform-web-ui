"""High-level runner that coordinates ProtocolGuard Docker workloads."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shlex
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
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import toml

from .config import DEFAULT_CONFIG_PACKET_TYPES, ProtocolGuardDockerSettings, _ensure_directory, _env_int
from .errors import ProtocolGuardDockerError, ProtocolGuardExecutionError, ProtocolGuardNotAvailableError
from .job import JobPaths

try:  # pragma: no cover - optional dependency
    import docker
    from docker.errors import DockerException, ImageNotFound
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    docker = None  # type: ignore
    DockerException = RuntimeError  # type: ignore
    ImageNotFound = RuntimeError  # type: ignore

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

    def _log_step(
        self,
        job_paths: JobPaths,
        stage: str,
        message: str,
        *,
        level: int = logging.INFO,
    ) -> None:
        LOGGER.log(level, "[job %s][%s] %s", job_paths.job_id, stage, message)
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
        self._current_workspace_snapshots = []

        self._log_step(job_paths, "init", "Starting ProtocolGuard static analysis job")

        built_builder_image: Optional[str] = None

        try:
            self._log_step(job_paths, "workspace", "Staging workspace directories")
            self._stage_workspace(job_paths)
            self._ensure_workspace_structure(job_paths)
            self._log_step(job_paths, "workspace", "Workspace directories prepared")

            uploads_dir = job_paths.workspace / "uploads"
            code_filename_real = code_filename or "source-archive"
            code_path = self._write_stream(uploads_dir / code_filename_real, code_stream)
            rules_filename_real = rules_filename or self._settings.artifacts.rule_config.name
            builder_filename_real = builder_filename or "Dockerfile"
            config_filename_real = config_filename or "config.toml"

            project_dir = job_paths.workspace / "project"
            self._log_step(job_paths, "workspace", "Preparing project directory for source archive")
            self._reset_directory(project_dir)
            self._extract_archive(code_path, project_dir)
            if not any(project_dir.iterdir()):
                raise ProtocolGuardDockerError(
                    "Source archive did not contain any files. Please verify the uploaded archive."
                )
            self._log_step(job_paths, "workspace", "Source archive extracted")

            dockerfile_path = project_dir / builder_filename_real
            self._log_step(job_paths, "inputs", "Writing builder Dockerfile to workspace")
            self._write_stream(dockerfile_path, builder_stream)

            builder_image = None
            if builder_stream:
                self._log_step(job_paths, "builder", "Building builder image from uploaded Dockerfile")
                builder_image = self._build_builder_image(
                    job_paths=job_paths,
                    context_dir=project_dir,
                    dockerfile_path=dockerfile_path,
                )
                built_builder_image = builder_image
            elif self._settings.builder_image:
                self._log_step(job_paths, "builder", "Using default builder image from environment")
                builder_image = self._settings.builder_image
            else:
                raise ProtocolGuardDockerError(
                    "Builder Dockerfile not provided and no default builder image configured."
                )

            rules_path = self._stage_rules_file(job_paths, rules_stream)
            LOGGER.debug("Staged code archive at %s, project at %s, rules at %s", code_path, project_dir, rules_path)

            self._log_step(job_paths, "config", "Loading and preparing config file")
            config_data = self._load_config(config_stream, config_filename)
            prepared_config = self._prepare_config(
                config_data=config_data,
                job_paths=job_paths,
                protocol_name=protocol_name,
                protocol_version=protocol_version,
            )
            self._write_config(job_paths.config_file, prepared_config)
            self._log_step(job_paths, "config", "Config file written to workspace")

            if builder_image:
                self._log_step(job_paths, "builder", f"Running builder container image {builder_image}")
                self._run_builder(
                    job_paths,
                    image=builder_image,
                    command=self._settings.builder_command,
                )
                self._log_step(job_paths, "builder", "Builder container completed")

            self._log_step(job_paths, "validation", "Validating required artefacts exist before analysis")
            self._validate_required_inputs(job_paths)
            self._log_step(job_paths, "validation", "All required artefacts present")

            self._log_step(
                job_paths,
                "analysis",
                f"Launching analysis container image {self._settings.analysis_image}",
            )
            logs = self._run_analysis(job_paths, command=self._settings.analysis_command)
            self._log_step(job_paths, "analysis", "Analysis container completed successfully")

            self._log_step(job_paths, "results", "Collecting analysis results and metadata")
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
            self._log_step(job_paths, "results", "ProtocolGuard job completed successfully")
            return result
        except Exception:
            self._log_step(job_paths, "error", "ProtocolGuard job failed", level=logging.ERROR)
            LOGGER.exception("ProtocolGuard job %s failed", job_id)
            raise
        finally:
            self._progress_callback = None
            self._current_workspace_snapshots = []
            if built_builder_image:
                if self._settings.keep_builder_images:
                    self._log_step(
                        job_paths,
                        "cleanup",
                        f"Retaining builder image {built_builder_image} for Docker cache reuse",
                    )
                else:
                    self._log_step(job_paths, "cleanup", f"Removing temporary builder image {built_builder_image}")
                    self._remove_builder_image(built_builder_image)
            if not self._settings.keep_artifacts:
                self._log_step(job_paths, "cleanup", "Cleaning up workspace artefacts")
                self._cleanup_job(job_paths)

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
        self._current_workspace_snapshots = []

        self._log_step(job_paths, "init", "Starting ProtocolGuard assertion generation job")

        command_env = os.environ.get("PG_ASSERT_COMMAND")
        parsed_command = shlex.split(command_env) if command_env else ["assert"]
        command = tuple(parsed_command or ["assert"])

        try:
            self._log_step(job_paths, "workspace", "Preparing workspace directories")
            self._reset_directory(job_paths.workspace)
            self._stage_workspace(job_paths)

            uploads_dir = job_paths.workspace / "uploads"
            project_dir = job_paths.workspace / "project"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)

            code_filename_real = code_filename or "source-archive"
            self._log_step(job_paths, "workspace", "Persisting uploaded source archive")
            code_path = self._write_stream(uploads_dir / code_filename_real, code_stream)

            self._log_step(job_paths, "workspace", "Extracting source archive into /workspace/project")
            self._reset_directory(project_dir)
            self._extract_archive(code_path, project_dir)
            if not any(project_dir.iterdir()):
                raise ProtocolGuardDockerError(
                    "Source archive did not contain any files. Please verify the uploaded archive."
                )
            self._log_step(job_paths, "workspace", "Source archive extracted into project directory")

            database_filename_real = database_filename or "violations.db"
            database_destination = job_paths.workspace / "violations.db"
            self._log_step(job_paths, "workspace", "Staging SQLite database as /workspace/violations.db")
            self._write_stream(database_destination, database_stream)
            if not database_destination.exists() or database_destination.stat().st_size == 0:
                raise ProtocolGuardDockerError("Uploaded database file is empty. Please verify the input.")

            build_instructions_text = build_instructions.strip() if build_instructions else ""
            if build_instructions_text:
                instructions_path = job_paths.workspace / "build_instructions.txt"
                instructions_path.write_text(build_instructions_text, encoding="utf-8")
                self._log_step(job_paths, "workspace", "Build instructions written to build_instructions.txt")
            else:
                self._log_step(job_paths, "workspace", "No build instructions provided; skipping file write")

            notes_text = notes.strip() if notes else ""
            if notes_text:
                notes_path = job_paths.workspace / "notes.txt"
                notes_path.write_text(notes_text, encoding="utf-8")
                self._log_step(job_paths, "workspace", "Notes written to notes.txt")

            self._snapshot_workspace(job_paths, stage="prepared")

            self._log_step(
                job_paths,
                "analysis",
                f"Launching assertion generation container image {self._settings.analysis_image}",
            )
            logs = self._run_analysis(job_paths, command=command)
            self._log_step(job_paths, "analysis", "Assertion generation container completed successfully")

            cursorkleosr_dir = self._find_cursorkleosr_directory(job_paths.workspace)
            if cursorkleosr_dir is None:
                raise ProtocolGuardExecutionError(
                    "Assertion generation completed but cursorkleosr directory was not found in the workspace.",
                    logs=logs,
                    image=self._settings.analysis_image,
                    status=0,
                )

            zip_destination = job_paths.output / "cursorkleosr.zip"
            self._log_step(job_paths, "results", "Packaging cursorkleosr artefacts into ZIP archive")
            self._zip_directory(cursorkleosr_dir, zip_destination)

            self._snapshot_workspace(job_paths, stage="post-run")

            workspace_snapshots = [dict(snapshot) for snapshot in self._current_workspace_snapshots]
            duration_ms = int((time.time() - start) * 1000)
            now_iso = datetime.now(timezone.utc).isoformat()
            assertion_count = self._count_files(cursorkleosr_dir)
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

            self._log_step(job_paths, "results", "Assertion generation completed successfully")
            return result
        except Exception:
            self._log_step(job_paths, "error", "Assertion generation job failed", level=logging.ERROR)
            LOGGER.exception("ProtocolGuard assertion generation job %s failed", job_id)
            raise
        finally:
            self._progress_callback = None
            self._current_workspace_snapshots = []
            if not self._settings.keep_artifacts:
                self._log_step(job_paths, "cleanup", "Cleaning up workspace artefacts")
                self._cleanup_job(job_paths)

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

        project_section = dict(data.get("project") or {})
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

        database_section = dict(data.get("database") or {})
        database_section["path"] = container_path(artifacts.database)
        data["database"] = database_section

        wpa_section = dict(data.get("wpa") or {})
        wpa_section["path"] = container_path(artifacts.wpa_report)
        data["wpa"] = wpa_section

        debug_section = dict(data.get("debug") or {})
        debug_section["code_slice_replace_mode"] = self._settings.debug_code_slice_mode
        debug_section["log_print"] = _env_int("PG_DEBUG_LOG_PRINT", 0) or 0
        data["debug"] = debug_section

        config_section = dict(data.get("config") or {})
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
        command = [
            "docker",
            "build",
            "--progress=plain",
            "--file",
            str(dockerfile_rel),
            "--tag",
            tag,
        ]
        if proxy_url:
            command.append("--network=host")
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                command.extend(["--build-arg", f"{key}={proxy_url}"])
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
        with job_paths.log_file.open("a", encoding="utf-8") as log_file:
            try:
                for line in process.stdout:
                    text = line.rstrip()
                    if text:
                        log_file.write(text + "\n")
                        self._log_step(job_paths, "builder-log", text)
            finally:
                process.stdout.close()
        exit_code = process.wait()
        if exit_code != 0:
            raise ProtocolGuardDockerError(
                f"Docker CLI build failed for builder image {tag} with exit code {exit_code}."
            )
        self._log_step(job_paths, "builder", f"docker CLI build completed for {tag}")
        return tag

    @staticmethod
    def _detect_builder_proxy(host: str = "127.0.0.1", port: int = 63333, timeout: float = 0.5) -> Optional[str]:
        try:
            with contextlib.closing(socket.create_connection((host, port), timeout=timeout)):
                return f"http://{host}:{port}"
        except OSError:
            LOGGER.debug("No proxy detected on %s:%s for builder builds.", host, port)
            return None

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
        return env

    def _snapshot_workspace(self, job_paths: JobPaths, *, stage: str) -> Optional[Path]:
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

        image_reference = image_details.id or self._settings.analysis_image
        try:
            output = self._client.containers.run(
                image=image_reference,
                command=["/bin/sh", "-c", preview_command],
                volumes=volumes,
                environment=environment,
                stdout=True,
                stderr=True,
                remove=True,
                network=self._settings.network,
            )
        except DockerException as exc:  # pragma: no cover - requires docker engine
            self._log_step(
                job_paths,
                "analysis-debug",
                f"Failed to inspect /workspace mount before analysis: {exc}",
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
                remove=True,
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
            container.remove(force=True)
            raise ProtocolGuardDockerError(f"Failed waiting for container exit: {exc}") from exc

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
        candidates = list(job_paths.output.rglob("*.db"))
        if not candidates:
            candidates = list(job_paths.workspace.rglob("*.db"))
        if not candidates:
            return None
        return candidates[0]

    def _find_cursorkleosr_directory(self, workspace: Path) -> Optional[Path]:
        for candidate in workspace.rglob("cursorkleosr"):
            if candidate.is_dir():
                return candidate
        return None

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
                cursor.execute("SELECT rowid, rule_desc, llm_response FROM rule_code_snippet")
            except sqlite3.DatabaseError as exc:
                LOGGER.warning("Unable to query rule_code_snippet table: %s", exc)
                return findings, counts

            rows = cursor.fetchall()

        for index, (row_id, rule_desc, llm_response) in enumerate(rows, start=1):
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

        result = str(payload.get("result", "")).lower()
        reason = str(payload.get("reason", "")).strip()
        violations = payload.get("violations")

        if "violation" in result:
            compliance = "non_compliant"
        elif "no violation" in result:
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

        verdict = {
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
