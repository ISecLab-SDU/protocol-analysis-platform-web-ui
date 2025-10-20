"""Docker orchestration helpers for ProtocolGuard static analysis."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import sqlite3
import tarfile
import tempfile
import time
import uuid
import zipfile
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    import docker
    from docker.errors import BuildError, DockerException
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    docker = None  # type: ignore
    DockerException = RuntimeError  # type: ignore
    BuildError = RuntimeError  # type: ignore

import toml

LOGGER = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _split_env_list(name: str, default: Sequence[str] = ()) -> Tuple[str, ...]:
    raw = os.environ.get(name)
    if not raw:
        return tuple(default)
    items = [item.strip() for item in raw.split(",")]
    return tuple(item for item in items if item)


def _default_runtime_root() -> Path:
    base = os.environ.get("PG_RUNTIME_ROOT")
    if base:
        return Path(base).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "protocolguard"


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class ArtifactLayout:
    """Relative paths inside the workspace for expected ProtocolGuard artefacts."""

    bitcode: Path = Path("program.bc")
    build_log: Path = Path("build_log.txt")
    wpa_report: Path = Path("ffp.txt")
    packet_callgraph: Path = Path("callgraph_report.txt")
    function_summary: Path = Path("function_arg_summary.txt")
    database: Path = Path("database")
    rule_config: Path = Path("inputs/rules.json")
    original_ir: Path = Path("program.ll")
    binary_path: Path = Path("program")

    @classmethod
    def from_env(cls) -> "ArtifactLayout":
        def pick(name: str, default: Path) -> Path:
            value = os.environ.get(name)
            if not value:
                return default
            return Path(value)

        return cls(
            bitcode=pick("PG_ARTIFACT_BITCODE", cls.bitcode),
            build_log=pick("PG_ARTIFACT_BUILD_LOG", cls.build_log),
            wpa_report=pick("PG_ARTIFACT_WPA_REPORT", cls.wpa_report),
            packet_callgraph=pick("PG_ARTIFACT_PACKET_REPORT", cls.packet_callgraph),
            function_summary=pick("PG_ARTIFACT_FUNCTION_SUMMARY", cls.function_summary),
            database=pick("PG_ARTIFACT_DATABASE_DIR", cls.database),
            rule_config=pick("PG_ARTIFACT_RULE_CONFIG", cls.rule_config),
            original_ir=pick("PG_ARTIFACT_ORIGINAL_IR", cls.original_ir),
            binary_path=pick("PG_ARTIFACT_BINARY_PATH", cls.binary_path),
        )


DEFAULT_CONFIG_PACKET_TYPES: Dict[str, List[str]] = {
    "mqtt_packet_type": [
        "CONNECT",
        "CONNACK",
        "PUBLISH",
        "PUBACK",
        "PUBREC",
        "PUBREL",
        "PUBCOMP",
        "SUBSCRIBE",
        "SUBACK",
        "UNSUBSCRIBE",
        "UNSUBACK",
        "PINGREQ",
        "PINGRESP",
        "DISCONNECT",
        "AUTH",
    ],
    "dhcpv6_packet_type": [
        "DHCP6_SOLICIT",
        "DHCP6_ADVERTISE",
        "DHCP6_REQUEST",
        "DHCP6_REPLY",
        "DHCP6_CONFIRM",
        "DHCP6_RELEASE",
        "DHCP6_DECLINE",
        "DHCP6_RENEW",
        "DHCP6_REBIND",
        "DHCP6_IREQ",
        "DHCP6_RECONFIGURE",
        "DHCP6_RELAYFORW",
        "DHCP6_RELAYREPL",
    ],
    "coap_packet_type": [
        "CONFIRMABLE",
        "NON_CONFIRMABLE",
        "ACKNOWLEDGEMENT",
        "RESET",
    ],
    "ftp_packet_type": [
        "USER",
        "PASS",
        "ACCT",
        "REIN",
        "QUIT",
        "PORT",
        "PASV",
        "TYPE",
        "STRU",
        "MODE",
        "RETR",
        "STOR",
        "APPE",
        "DELE",
        "RNFR",
        "RNTO",
        "ABOR",
        "CWD",
        "CDUP",
        "PWD",
        "MKD",
        "RMD",
        "LIST",
        "NLST",
        "SYST",
        "STAT",
        "FEAT",
        "HELP",
        "NOOP",
        "ALLO",
        "REST",
        "MLST",
        "MLSD",
        "OPTS",
        "EPSV",
        "EPRT",
        "AUTH",
        "ADAT",
        "CCC",
        "CONF",
        "ENC",
        "MIC",
        "PBSZ",
        "PROT",
    ],
    "tls13_message_type": [
        "CLIENT_HELLO",
        "SERVER_HELLO",
        "NEW_SESSION_TICKET",
        "END_OF_EARLY_DATA",
        "ENCRYPTED_EXTENSIONS",
        "CERTIFICATE",
        "CERTIFICATE_REQUEST",
        "CERTIFICATE_VERIFY",
        "FINISHED",
        "KEY_UPDATE",
        "HELLO_RETRY_REQUEST",
    ],
}


@dataclass(frozen=True)
class ProtocolGuardDockerSettings:
    """Runtime configuration for the Docker integration."""

    enabled: bool
    analysis_image: str
    analysis_command: Tuple[str, ...]
    workspace_root: Path
    output_root: Path
    config_root: Path
    template_workspace: Optional[Path]
    env_passthrough: Tuple[str, ...]
    artifacts: ArtifactLayout
    builder_image: Optional[str]
    builder_command: Optional[Tuple[str, ...]]
    keep_artifacts: bool
    analysis_timeout: Optional[int]
    network: Optional[str]
    project_name: str
    default_protocol_name: str
    default_protocol_version: str
    llm_model_r1: str
    llm_model_v3: str
    llm_query_repeat: int
    llm_query_max_attempts: int
    llm_violation_repeat_times: int
    debug_code_slice_mode: int

    @classmethod
    def from_env(cls) -> "ProtocolGuardDockerSettings":
        enabled = _env_bool("PG_DOCKER_ENABLED", default=False)
        analysis_image = os.environ.get("PG_ANALYSIS_IMAGE", "protocolguard:main")
        builder_image = os.environ.get("PG_BUILDER_IMAGE") or None

        import shlex

        def parse_command(env_name: str, default: str) -> Tuple[str, ...]:
            raw = os.environ.get(env_name)
            if raw:
                return tuple(shlex.split(raw))
            return tuple(shlex.split(default))

        analysis_command = parse_command("PG_ANALYSIS_COMMAND", "static")
        builder_command_env = os.environ.get("PG_BUILDER_COMMAND")
        builder_command = tuple(shlex.split(builder_command_env)) if builder_command_env else None

        runtime_root = _default_runtime_root()
        workspace_root = Path(os.environ.get("PG_WORKSPACE_ROOT", runtime_root / "workspaces")).expanduser()
        output_root = Path(os.environ.get("PG_OUTPUT_ROOT", runtime_root / "outputs")).expanduser()
        config_root = Path(os.environ.get("PG_CONFIG_ROOT", runtime_root / "configs")).expanduser()

        template_workspace_raw = os.environ.get("PG_TEMPLATE_WORKSPACE")
        template_workspace = Path(template_workspace_raw).expanduser() if template_workspace_raw else None

        env_passthrough = _split_env_list("PG_ENV_VARS", ("OPENAI_API_KEY",))
        artifacts = ArtifactLayout.from_env()
        keep_artifacts = _env_bool("PG_KEEP_ARTIFACTS", default=True)
        analysis_timeout = _env_int("PG_ANALYSIS_TIMEOUT_SECONDS", None)
        network = os.environ.get("PG_DOCKER_NETWORK") or None

        project_name = os.environ.get("PG_PROJECT_NAME", "protocolguard-project")
        default_protocol_name = os.environ.get("PG_PROTOCOL_NAME", "MQTT")
        default_protocol_version = os.environ.get("PG_PROTOCOL_VERSION", "5")

        llm_model_r1 = os.environ.get("PG_LLM_MODEL_R1", "deepseek-ai/DeepSeek-R1-0528")
        llm_model_v3 = os.environ.get("PG_LLM_MODEL_V3", "deepseek-ai/DeepSeek-V3-0324")
        llm_query_repeat = _env_int("PG_LLM_QUERY_REPEAT", 1) or 1
        llm_query_max_attempts = _env_int("PG_LLM_QUERY_MAX_ATTEMPTS", 10) or 10
        llm_violation_repeat_times = _env_int("PG_LLM_VIOLATION_REPEAT", 3) or 3
        debug_code_slice_mode = _env_int("PG_DEBUG_CODE_SLICE_MODE", 0) or 0

        return cls(
            enabled=enabled,
            analysis_image=analysis_image,
            analysis_command=analysis_command,
            workspace_root=workspace_root,
            output_root=output_root,
            config_root=config_root,
            template_workspace=template_workspace,
            env_passthrough=env_passthrough,
            artifacts=artifacts,
            builder_image=builder_image,
            builder_command=builder_command,
            keep_artifacts=keep_artifacts,
            analysis_timeout=analysis_timeout,
            network=network,
            project_name=project_name,
            default_protocol_name=default_protocol_name,
            default_protocol_version=default_protocol_version,
            llm_model_r1=llm_model_r1,
            llm_model_v3=llm_model_v3,
            llm_query_repeat=llm_query_repeat,
            llm_query_max_attempts=llm_query_max_attempts,
            llm_violation_repeat_times=llm_violation_repeat_times,
            debug_code_slice_mode=debug_code_slice_mode,
        )


@dataclass
class JobPaths:
    job_id: str
    workspace: Path
    output: Path
    config_dir: Path
    config_file: Path
    log_file: Path


class ProtocolGuardDockerError(RuntimeError):
    """Base exception for Docker integration errors."""


class ProtocolGuardNotAvailableError(ProtocolGuardDockerError):
    """Raised when Docker SDK or engine is unavailable."""


class ProtocolGuardExecutionError(ProtocolGuardDockerError):
    """Raised when the container exits with a non-zero status."""

    def __init__(
        self,
        message: str,
        *,
        logs: Optional[List[str]] = None,
        log_excerpt: Optional[str] = None,
        image: Optional[str] = None,
        status: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.logs = logs or []
        self.log_excerpt = log_excerpt
        self.image = image
        self.status = status


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
    ) -> Dict[str, object]:
        """Execute the ProtocolGuard static workflow and return a structured response."""
        start = time.time()
        job_id = str(uuid.uuid4())
        job_paths = self._prepare_job_paths(job_id)

        LOGGER.info("Starting ProtocolGuard static analysis job %s", job_id)

        built_builder_image: Optional[str] = None

        try:
            self._stage_workspace(job_paths)
            self._ensure_workspace_structure(job_paths)

            uploads_dir = job_paths.workspace / "uploads"
            code_filename_real = code_filename or "source-archive"
            code_path = self._write_stream(uploads_dir / code_filename_real, code_stream)
            rules_filename_real = rules_filename or self._settings.artifacts.rule_config.name
            builder_filename_real = builder_filename or "Dockerfile"
            config_filename_real = config_filename or "config.toml"

            project_dir = job_paths.workspace / "project"
            self._reset_directory(project_dir)
            self._extract_archive(code_path, project_dir)
            if not any(project_dir.iterdir()):
                raise ProtocolGuardDockerError(
                    "Source archive did not contain any files. Please verify the uploaded archive."
                )

            dockerfile_path = project_dir / builder_filename_real
            self._write_stream(dockerfile_path, builder_stream)

            builder_image = None
            if builder_stream:
                builder_image = self._build_builder_image(
                    job_paths=job_paths,
                    context_dir=project_dir,
                    dockerfile_path=dockerfile_path,
                )
                built_builder_image = builder_image
            elif self._settings.builder_image:
                builder_image = self._settings.builder_image
            else:
                raise ProtocolGuardDockerError(
                    "Builder Dockerfile not provided and no default builder image configured."
                )

            rules_path = self._stage_rules_file(job_paths, rules_stream)
            LOGGER.debug("Staged code archive at %s, project at %s, rules at %s", code_path, project_dir, rules_path)

            config_data = self._load_config(config_stream, config_filename)
            prepared_config = self._prepare_config(
                config_data=config_data,
                job_paths=job_paths,
                protocol_name=protocol_name,
                protocol_version=protocol_version,
            )
            self._write_config(job_paths.config_file, prepared_config)

            if builder_image:
                self._run_builder(
                    job_paths,
                    image=builder_image,
                    command=self._settings.builder_command,
                )

            self._validate_required_inputs(job_paths)

            logs = self._run_analysis(job_paths)

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
            )
            LOGGER.info("ProtocolGuard job %s completed successfully", job_id)
            return result
        except Exception:
            LOGGER.exception("ProtocolGuard job %s failed", job_id)
            raise
        finally:
            if built_builder_image:
                self._remove_builder_image(built_builder_image)
            if not self._settings.keep_artifacts:
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
        # Fallback: treat as single file
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
        if docker is None:
            raise ProtocolGuardNotAvailableError("Docker SDK is not available; cannot build builder image.")

        try:
            dockerfile_rel = dockerfile_path.relative_to(context_dir)
        except ValueError as exc:
            raise ProtocolGuardDockerError(
                f"Builder Dockerfile {dockerfile_path} must reside within the uploaded project directory."
            ) from exc

        tag = f"protocolguard-builder:{job_paths.job_id}"
        LOGGER.info("Building builder image %s using context %s", tag, context_dir)
        try:
            _image, build_logs = self._client.images.build(
                path=str(context_dir),
                dockerfile=str(dockerfile_rel),
                tag=tag,
                rm=True,
            )
        except BuildError as exc:
            logs = getattr(exc, "build_log", None) or []
            rendered = [chunk.get("stream", "") for chunk in logs if isinstance(chunk, dict)]
            LOGGER.error("Builder image build failed: %s", exc)
            if rendered:
                for line in rendered:
                    LOGGER.error("[builder build %s] %s", job_paths.job_id, line.rstrip())
            raise ProtocolGuardDockerError(f"Builder image build failed: {exc}") from exc
        except DockerException as exc:
            raise ProtocolGuardDockerError(f"Failed to build builder image: {exc}") from exc

        for chunk in build_logs or []:
            stream = chunk.get("stream")
            if stream:
                LOGGER.debug("[builder build %s] %s", job_paths.job_id, stream.rstrip())
        LOGGER.debug("Builder image %s build completed", tag)
        return tag

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

    def _run_builder(
        self,
        job_paths: JobPaths,
        *,
        image: str,
        command: Optional[Sequence[str]] = None,
    ) -> None:
        if not image:
            raise ProtocolGuardDockerError("Builder image is required to execute the ProtocolGuard pipeline.")
        LOGGER.info(
            "Running ProtocolGuard builder image %s for job %s",
            image,
            job_paths.job_id,
        )
        self._run_container(
            image=image,
            command=command,
            volumes=self._build_volumes(job_paths, include_config=False),
            environment=self._build_environment(),
            log_destination=job_paths.log_file,
        )

    def _run_analysis(self, job_paths: JobPaths) -> List[str]:
        LOGGER.info(
            "Running ProtocolGuard analysis image %s for job %s",
            self._settings.analysis_image,
            job_paths.job_id,
        )
        return self._run_container(
            image=self._settings.analysis_image,
            command=self._settings.analysis_command,
            volumes=self._build_volumes(job_paths, include_config=True),
            environment=self._build_environment(),
            log_destination=job_paths.log_file,
            timeout=self._settings.analysis_timeout,
        )

    def _run_container(
        self,
        *,
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

        logs: List[str] = []
        with log_destination.open("a", encoding="utf-8") as log_file:
            for chunk in container.logs(stream=True, follow=True):
                line = chunk.decode("utf-8", errors="replace").rstrip()
                log_file.write(line + "\n")
                logs.append(line)

        try:
            result = container.wait(timeout=timeout)
        except DockerException as exc:  # pragma: no cover - requires docker engine
            container.remove(force=True)
            raise ProtocolGuardDockerError(f"Failed waiting for container exit: {exc}") from exc

        status = result.get("StatusCode", 1)
        if status != 0:
            excerpt = "\n".join(logs[-40:]) if logs else None
            raise ProtocolGuardExecutionError(
                f"Container {image} exited with status {status}",
                logs=logs,
                log_excerpt=excerpt,
                image=image,
                status=status,
            )
        return logs

    # Validation ----------------------------------------------------------------

    def _validate_required_inputs(self, job_paths: JobPaths) -> None:
        workspace = job_paths.workspace
        artefacts = {
            "bitcode": workspace / self._settings.artifacts.bitcode,
            "build log": workspace / self._settings.artifacts.build_log,
        }
        missing = [label for label, path in artefacts.items() if not path.exists()]
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
