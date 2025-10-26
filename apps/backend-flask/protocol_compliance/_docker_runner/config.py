"""Configuration helpers for ProtocolGuard Docker integration."""

from __future__ import annotations

import os
import shlex
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "ArtifactLayout",
    "DEFAULT_CONFIG_PACKET_TYPES",
    "ProtocolGuardDockerSettings",
    "_default_runtime_root",
    "_ensure_directory",
    "_env_bool",
    "_env_int",
    "_split_env_list",
]


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
    keep_builder_images: bool
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
        enabled = _env_bool("PG_DOCKER_ENABLED", default=True)
        analysis_image = os.environ.get("PG_ANALYSIS_IMAGE", "protocolguard:latest")
        builder_image = os.environ.get("PG_BUILDER_IMAGE") or None

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
        keep_artifacts = _env_bool("PG_KEEP_ARTIFACTS", default=False)
        keep_builder_images = _env_bool("PG_KEEP_BUILDER_IMAGES", default=False)
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
            keep_builder_images=keep_builder_images,
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
