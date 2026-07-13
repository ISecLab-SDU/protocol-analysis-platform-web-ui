import os
import json
import logging
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Sequence, Tuple

from protocol_compliance.claude_agent_events import decode_progress_line
from protocol_compliance.job_logging import JobStageLogger

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ClaudeBuilderRunnerError(Exception):
    pass


class ClaudeBuilderRunnerExecutionError(ClaudeBuilderRunnerError):
    def __init__(self, message: str, *, logs: Optional[list] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.logs = logs or []
        self.details = details or {}


class ClaudeBuilderRunnerNotAvailableError(ClaudeBuilderRunnerError):
    pass


@dataclass(frozen=True)
class ClaudeBuilderRunnerSettings:
    enabled: bool
    api_key: str
    base_url: str
    model: str
    workspace_root: Path
    max_runtime: int
    env_passthrough: tuple
    builder_image: str

    @classmethod
    def from_env(cls) -> "ClaudeBuilderRunnerSettings":
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN") or ""
        enabled = bool(api_key) or bool(os.environ.get("PG_CLAUDE_BUILDER_IMAGE"))
        base_url = os.environ.get("ANTHROPIC_BASE_URL") or ""
        model = os.environ.get("PG_AGENT_MODEL", "deepseek-v3")

        runtime_root = Path(os.environ.get("PG_RUNTIME_ROOT", tempfile.gettempdir() + "/protocolguard"))
        workspace_root = Path(os.environ.get("PG_WORKSPACE_ROOT", runtime_root / "workspaces"))

        max_runtime = int(os.environ.get("PG_AGENT_MAX_RUNTIME", "3600"))

        env_passthrough_str = os.environ.get(
            "PG_ENV_VARS",
            "OPENAI_API_KEY,OPENAI_BASE_URL,ANTHROPIC_API_KEY,ANTHROPIC_AUTH_TOKEN,ANTHROPIC_BASE_URL",
        )
        env_passthrough = tuple(item.strip() for item in env_passthrough_str.split(",") if item.strip())
        builder_image = os.environ.get("PG_CLAUDE_BUILDER_IMAGE") or os.environ.get(
            "PG_BUILDER_IMAGE",
            "protocolguard-claude-builder:latest",
        )

        return cls(
            enabled=enabled,
            api_key=api_key,
            base_url=base_url,
            model=model,
            workspace_root=workspace_root,
            max_runtime=max_runtime,
            env_passthrough=env_passthrough,
            builder_image=builder_image,
        )


class ClaudeBuilderRunner:

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
            return compliance, verdicts

        try:
            payload = json.loads(llm_response)
        except json.JSONDecodeError:
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
        violation: Optional[Dict],
        rule_desc: str,
        protocol_name: str,
        protocol_version: str,
        index: int,
    ) -> Dict[str, object]:
        line_range: Optional[List[int]] = None
        location_file: Optional[str] = None
        location_function: Optional[str] = None

        if violation and isinstance(violation, dict):
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

    def _extract_findings(
        self,
        db_path: Optional[str],
        protocol_name: str,
        protocol_version: str,
    ) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
        findings: List[Dict[str, object]] = []
        counts = {"compliant": 0, "needs_review": 0, "non_compliant": 0}

        if not db_path or not Path(db_path).exists():
            return findings, counts

        db_path_obj = Path(db_path)
        try:
            db_path_obj.chmod(0o644)
        except Exception:
            pass

        try:
            db_path_obj.parent.chmod(0o755)
        except Exception:
            pass

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT rowid, rule_desc, code_snippet, llm_response FROM rule_code_snippet")
            except sqlite3.DatabaseError:
                return findings, counts

            rows = cursor.fetchall()

        for index, (row_id, rule_desc, code_snippet, llm_response) in enumerate(rows, start=1):
            llm_response_text = llm_response if isinstance(llm_response, str) else ""
            compliance, rule_findings = self._parse_llm_response(
                llm_response_text,
                rule_desc,
                protocol_name,
                protocol_version,
                index,
            )
            counts[compliance] += 1
            findings.extend(rule_findings)

        return findings, counts

    def _determine_overall_status(self, counts: Dict[str, int]) -> str:
        if counts.get("non_compliant", 0):
            return "non_compliant"
        if counts.get("needs_review", 0):
            return "needs_review"
        return "compliant"

    def __init__(self, settings: ClaudeBuilderRunnerSettings):
        self.settings = settings
        if not settings.enabled:
            raise ClaudeBuilderRunnerNotAvailableError("Claude builder runner is not enabled")

        self._docker_available = self._check_docker()
        self._analysis_image = os.environ.get("PG_ANALYSIS_IMAGE", "protocolguard:latest")
        self._analysis_command = os.environ.get("PG_ANALYSIS_COMMAND", "static").split()
        self._builder_image = settings.builder_image


    def _check_docker(self) -> bool:
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError):
            return False

    def _build_passthrough_environment(self) -> Dict[str, str]:
        env: Dict[str, str] = {}
        for name in self.settings.env_passthrough:
            value = os.environ.get(name)
            if value is not None:
                env[name] = value
        env["PG_HOST_UID"] = str(os.getuid())
        env["PG_HOST_GID"] = str(os.getgid())
        return env

    def _docker_env_args(self) -> List[str]:
        args: List[str] = []
        for name in self.settings.env_passthrough:
            if os.environ.get(name) is not None:
                args.extend(["-e", name])
        args.extend(["-e", f"PG_HOST_UID={os.getuid()}"])
        args.extend(["-e", f"PG_HOST_GID={os.getgid()}"])
        args.extend(["-e", "IS_SANDBOX=1"])
        return args

    @staticmethod
    def _redact_command(command: Sequence[str]) -> List[str]:
        redacted: List[str] = []
        previous_was_env_flag = False
        for item in command:
            if previous_was_env_flag:
                name = item.split("=", 1)[0]
                if name in {
                    "ANTHROPIC_API_KEY",
                    "ANTHROPIC_AUTH_TOKEN",
                    "ANTHROPIC_BASE_URL",
                    "OPENAI_API_KEY",
                    "OPENAI_BASE_URL",
                }:
                    redacted.append(f"{name}=<redacted>" if "=" in item else name)
                else:
                    redacted.append(item)
                previous_was_env_flag = False
                continue
            redacted.append(item)
            previous_was_env_flag = item in {"-e", "--env"}
        return redacted

    def _run_logged_command(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        log_path: Path,
        progress_callback: Optional[Callable[[str, str, str], None]],
        job_identifier: str,
        stage: str,
        stage_selector: Optional[Callable[[str, str], str]] = None,
        timeout: Optional[int] = None,
    ) -> List[str]:
        logger.debug("[*] Command: %s", " ".join(self._redact_command(command)))
        try:
            process = subprocess.Popen(
                list(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(cwd),
            )
        except OSError as exc:
            raise ClaudeBuilderRunnerExecutionError(f"Failed to start command: {exc}") from exc

        if process.stdout is None:
            raise ClaudeBuilderRunnerExecutionError("Command did not expose stdout")

        lines: List[str] = []
        with log_path.open("a", encoding="utf-8") as log_file:
            for raw_line in iter(process.stdout.readline, ""):
                line = raw_line.rstrip()
                lines.append(line)
                log_file.write(line + "\n")
                if line:
                    progress_stage, progress_message = self._extract_progress_line(
                        line,
                        stage,
                        stage_selector=stage_selector,
                    )
                    logger.debug("[%s] %s", progress_stage.upper(), progress_message)
                    if progress_callback:
                        progress_callback(job_identifier, progress_stage, progress_message[:500])

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            raise ClaudeBuilderRunnerExecutionError(
                f"{stage} command timed out after {timeout} seconds",
                logs=lines,
                details={"command": list(command), "workspace": str(cwd)},
            ) from exc

        if process.returncode != 0:
            raise ClaudeBuilderRunnerExecutionError(
                f"{stage} command exited with status {process.returncode}",
                logs=lines,
                details={
                    "command": list(command),
                    "workspace": str(cwd),
                    "logExcerpt": "\n".join(lines[-40:]),
                },
            )
        return lines

    @staticmethod
    def _extract_progress_line(
        line: str,
        default_stage: str,
        *,
        stage_selector: Optional[Callable[[str, str], str]] = None,
    ) -> tuple[str, str]:
        progress = decode_progress_line(line, default_stage)
        if progress:
            return progress

        progress_stage = stage_selector(line, default_stage) if stage_selector else default_stage
        return progress_stage, line

    @staticmethod
    def _claude_builder_progress_stage(line: str, default_stage: str) -> str:
        marker_stage = {
            "[claude-step]": "claude-step",
            "[claude-command]": "claude-command",
            "[claude-observation]": "claude-observation",
            "[claude-config]": "claude-config",
            "[claude-artifact]": "claude-artifact",
            "[prompt-preview]": "claude-prompt",
            "[config.toml]": "claude-config",
            "[rule_config.json]": "claude-config",
            "[artifact-file]": "claude-artifact",
            "[archive]": "claude-inputs",
            "[workspace]": "claude-inputs",
            "[claude-action-journal]": "claude-journal",
        }
        for marker, stage in marker_stage.items():
            if marker in line:
                return stage
        if "Claude builder agent exited with status" in line:
            return "claude-status"
        if "workspace inputs before Claude Code" in line:
            return "claude-inputs"
        if "post-Claude artifact validation" in line:
            return "claude-artifact"
        return default_stage

    def _run_claude_builder_container(
        self,
        workspace_dir: Path,
        job_identifier: str,
        progress_callback: Optional[Callable[[str, str, str], None]],
    ) -> List[str]:
        if not self._docker_available:
            raise ClaudeBuilderRunnerNotAvailableError("Docker is required for the Claude builder compiler")

        output_dir = self.settings.workspace_root.parent / "outputs" / job_identifier
        output_dir.mkdir(parents=True, exist_ok=True)
        log_path = workspace_dir / "build_log.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        config_path = workspace_dir / "config.toml"
        rules_path = workspace_dir / "rule_config.json"
        prompt_path = workspace_dir / "claude_builder_prompt.md"
        logger.info(
            "Starting Claude builder container for job %s with workspace=%s image=%s config=%s rules=%s",
            job_identifier,
            workspace_dir,
            self._builder_image,
            config_path if config_path.exists() else None,
            rules_path if rules_path.exists() else None,
            extra={
                "protocolguard_context": {
                    "job_id": job_identifier,
                    "stage": "claude-inputs",
                    "workspace": str(workspace_dir),
                    "builder_image": self._builder_image,
                    "config_path": str(config_path) if config_path.exists() else None,
                    "rules_path": str(rules_path) if rules_path.exists() else None,
                },
            },
        )
        if config_path.exists():
            logger.info(
                "Claude builder input config.toml for job %s:\n%s",
                job_identifier,
                config_path.read_text(encoding="utf-8", errors="replace"),
                extra={
                    "protocolguard_context": {
                        "job_id": job_identifier,
                        "stage": "claude-config",
                        "config_path": str(config_path),
                    },
                },
            )
        if rules_path.exists():
            logger.info(
                "Claude builder input rule_config.json for job %s:\n%s",
                job_identifier,
                rules_path.read_text(encoding="utf-8", errors="replace")[:8000],
                extra={
                    "protocolguard_context": {
                        "job_id": job_identifier,
                        "stage": "claude-config",
                        "rules_path": str(rules_path),
                    },
                },
            )
        workspace_preview = sorted(
            str(path.relative_to(workspace_dir))
            for path in workspace_dir.rglob("*")
            if path.is_file()
        )[:120]
        logger.info(
            "Claude builder workspace file preview for job %s: %s",
            job_identifier,
            workspace_preview,
            extra={
                "protocolguard_context": {
                    "job_id": job_identifier,
                    "stage": "claude-inputs",
                    "workspace": str(workspace_dir),
                    "file_count_preview": len(workspace_preview),
                },
            },
        )
        if progress_callback:
            progress_callback(job_identifier, "builder", f"Starting Claude builder image {self._builder_image}")

        command = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workspace_dir}:/workspace",
            "-v",
            f"{output_dir}:/out",
            "--network=host",
            *self._docker_env_args(),
            self._builder_image,
        ]

        logs = self._run_logged_command(
            command,
            cwd=workspace_dir,
            log_path=log_path,
            progress_callback=progress_callback,
            job_identifier=job_identifier,
            stage="builder-log",
            stage_selector=self._claude_builder_progress_stage,
            timeout=self.settings.max_runtime,
        )
        if prompt_path.exists():
            logger.info(
                "Claude builder prompt persisted for job %s at %s",
                job_identifier,
                prompt_path,
                extra={
                    "protocolguard_context": {
                        "job_id": job_identifier,
                        "stage": "claude-prompt",
                        "prompt_path": str(prompt_path),
                    },
                },
            )
        return logs

    def _validate_builder_outputs(self, workspace_dir: Path) -> None:
        required = {
            "bitcode": workspace_dir / "program.bc",
            "LLVM IR": workspace_dir / "program.ll",
            "build log": workspace_dir / "build_log.txt",
            "rules": workspace_dir / "inputs" / "rules.json",
        }
        missing = [label for label, path in required.items() if not path.exists()]
        if missing:
            raise ClaudeBuilderRunnerExecutionError(
                f"Claude builder completed but required artefacts are missing: {', '.join(missing)}",
                details={
                    "workspace": str(workspace_dir),
                    "missing": missing,
                    "contents": [str(path.relative_to(workspace_dir)) for path in workspace_dir.rglob("*")][:200],
                },
            )

        for path in workspace_dir.rglob("*"):
            try:
                if path.is_dir():
                    path.chmod(0o755)
                else:
                    path.chmod(0o644)
            except Exception:
                pass

    def _build_generated_config_content(
        self,
        *,
        protocol_name: Optional[str],
        protocol_version: Optional[str],
        project_name: Optional[str],
    ) -> str:
        import toml

        resolved_protocol = protocol_name or os.environ.get("PG_PROTOCOL_NAME", "MQTT")
        resolved_version = protocol_version or os.environ.get("PG_PROTOCOL_VERSION", "3.1.1")
        resolved_project = project_name or os.environ.get("PG_PROJECT_NAME", "ProtocolGuard project")
        config = {
            "wpa": {"path": "/workspace/ffp.txt"},
            "database": {"path": "/workspace/database"},
            "llm": {
                "llm_api_platform": os.environ.get(
                    "PG_LLM_API_BASE",
                    "http://10.102.32.6:47860/v1/chat/completions",
                ),
                "llm_model_deepseek_v3": os.environ.get("PG_LLM_MODEL_V3", "deepseek-v3"),
                "llm_model_deepseek_r1": os.environ.get("PG_LLM_MODEL_R1", "deepseek-r1"),
                "llm_query_repeat_times": 1,
                "llm_query_max_attempts": 10,
                "llm_violation_repeat_times": 3,
                "llm_multithread": 32,
            },
            "project": {
                "project_path": "/workspace/project",
                "packet_related_callgraph_path": "/workspace/callgraph_report.txt",
                "function_arg_path": "/workspace/function_arg_summary.txt",
                "rule_path": "/workspace/inputs/rules.json",
                "protocol_name": resolved_protocol,
                "protocol_version": resolved_version,
                "project_name": resolved_project,
                "original_llvm_ir_path": "/workspace/program.ll",
                "build_log_path": "/workspace/build_log.txt",
                "binary_path": "/workspace/program",
                "bitcode_path": "/workspace/program.bc",
            },
            "debug": {
                "code_slice_replace_mode": int(os.environ.get("PG_DEBUG_CODE_SLICE_MODE", "0") or 0),
                "log_print": int(os.environ.get("PG_DEBUG_LOG_PRINT", "0") or 0),
            },
            "config": {
                "mqtt_packet_type": [
                    "CONNECT", "CONNACK", "PUBLISH", "PUBACK", "PUBREC", "PUBREL", "PUBCOMP",
                    "SUBSCRIBE", "SUBACK", "UNSUBSCRIBE", "UNSUBACK", "PINGREQ", "PINGRESP",
                    "DISCONNECT", "AUTH",
                ],
                "dhcpv6_packet_type": [
                    "DHCP6_SOLICIT", "DHCP6_ADVERTISE", "DHCP6_REQUEST", "DHCP6_REPLY",
                    "DHCP6_CONFIRM", "DHCP6_RELEASE", "DHCP6_DECLINE", "DHCP6_RENEW",
                    "DHCP6_REBIND", "DHCP6_IREQ", "DHCP6_RECONFIGURE", "DHCP6_RELAYFORW",
                    "DHCP6_RELAYREPL",
                ],
                "coap_packet_type": ["CONFIRMABLE", "NON_CONFIRMABLE", "ACKNOWLEDGEMENT", "RESET"],
                "ftp_packet_type": [
                    "USER", "PASS", "ACCT", "REIN", "QUIT", "PORT", "PASV", "TYPE", "STRU",
                    "MODE", "RETR", "STOR", "APPE", "DELE", "RNFR", "RNTO", "ABOR", "CWD",
                    "CDUP", "PWD", "MKD", "RMD", "LIST", "NLST", "SYST", "STAT", "FEAT",
                    "HELP", "NOOP", "ALLO", "REST", "MLST", "MLSD", "OPTS", "EPSV", "EPRT",
                    "AUTH", "ADAT", "CCC", "CONF", "ENC", "MIC", "PBSZ", "PROT",
                ],
                "tls13_message_type": [
                    "CLIENT_HELLO", "SERVER_HELLO", "NEW_SESSION_TICKET", "END_OF_EARLY_DATA",
                    "ENCRYPTED_EXTENSIONS", "CERTIFICATE", "CERTIFICATE_REQUEST",
                    "CERTIFICATE_VERIFY", "FINISHED", "KEY_UPDATE", "HELLO_RETRY_REQUEST",
                ],
            },
        }
        return toml.dumps(config)

    def _container_path(self, workspace_dir: Path, path: Path) -> str:
        try:
            relative = path.resolve(strict=False).relative_to(workspace_dir.resolve(strict=False))
        except ValueError:
            return str(path)
        if relative.as_posix() == ".":
            return "/workspace"
        return f"/workspace/{relative.as_posix()}"

    def _first_existing(self, workspace_dir: Path, relative_paths: List[str]) -> Optional[Path]:
        for relative_path in relative_paths:
            candidate = workspace_dir / relative_path
            if candidate.exists():
                return candidate
        return None

    def _find_workspace_file(
        self,
        workspace_dir: Path,
        *,
        suffixes: Tuple[str, ...],
        exclude_suffixes: Tuple[str, ...] = (),
    ) -> Optional[Path]:
        matches: List[Path] = []
        for path in workspace_dir.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.lower()
            if exclude_suffixes and any(name.endswith(suffix) for suffix in exclude_suffixes):
                continue
            if any(name.endswith(suffix) for suffix in suffixes):
                matches.append(path)
        if not matches:
            return None
        matches.sort(key=lambda path: (len(path.relative_to(workspace_dir).parts), str(path)))
        return matches[0]

    def _infer_project_root(self, workspace_dir: Path) -> Path:
        project_dir = workspace_dir / "project"
        if not project_dir.exists():
            return workspace_dir

        build_markers = {
            "CMakeLists.txt",
            "Makefile",
            "configure",
            "meson.build",
            "compile_commands.json",
        }
        marker_dirs: List[Path] = []
        for path in project_dir.rglob("*"):
            if path.is_file() and path.name in build_markers:
                marker_dirs.append(path.parent)
        if marker_dirs:
            marker_dirs.sort(key=lambda path: (len(path.relative_to(project_dir).parts), str(path)))
            return marker_dirs[0]

        children = [path for path in project_dir.iterdir() if path.is_dir()]
        if len(children) == 1:
            return children[0]
        return project_dir

    def _build_analysis_config(
        self,
        *,
        workspace_dir: Path,
        protocol_name: Optional[str],
        protocol_version: Optional[str],
        project_name: Optional[str],
    ) -> Dict[str, Any]:
        project_root = self._infer_project_root(workspace_dir)
        project_build_dir = project_root / "build"

        bitcode_path = (
            self._first_existing(workspace_dir, ["program.bc"])
            or self._first_existing(project_build_dir, ["program.bc"])
            or self._first_existing(project_root, ["program.bc"])
            or self._find_workspace_file(
                workspace_dir,
                suffixes=(".bc",),
                exclude_suffixes=("_ssa.bc",),
            )
            or (workspace_dir / "program.bc")
        )
        original_ir_path = (
            self._first_existing(workspace_dir, ["program.ll"])
            or self._first_existing(project_build_dir, ["program.ll"])
            or self._first_existing(project_root, ["program.ll"])
            or self._find_workspace_file(workspace_dir, suffixes=(".ll",))
            or bitcode_path
        )
        build_log_path = (
            self._first_existing(workspace_dir, ["build_log.txt"])
            or self._first_existing(project_build_dir, ["build_log.txt"])
            or self._first_existing(project_root, ["build_log.txt"])
            or self._find_workspace_file(workspace_dir, suffixes=("build_log.txt",))
            or (workspace_dir / "build_log.txt")
        )
        bitcode_binary = bitcode_path.with_suffix("")
        binary_path = (
            self._first_existing(workspace_dir, ["program"])
            or self._first_existing(project_build_dir, [bitcode_binary.name])
            or self._first_existing(project_root, ["program"])
            or (bitcode_binary if bitcode_binary.exists() else workspace_dir / "program")
        )

        resolved_protocol = protocol_name or os.environ.get("PG_PROTOCOL_NAME", "MQTT")
        resolved_version = protocol_version or os.environ.get("PG_PROTOCOL_VERSION", "3.1.1")
        resolved_project = project_name or os.environ.get("PG_PROJECT_NAME", "ProtocolGuard project")

        return {
            "wpa": {
                "path": "/workspace/ffp.txt",
            },
            "database": {
                "path": "/workspace/database",
            },
            "llm": {
                "llm_api_platform": os.environ.get("PG_LLM_API_BASE", "http://10.102.32.6:47860/v1/chat/completions"),
                "llm_model_deepseek_v3": os.environ.get("PG_LLM_MODEL_V3", "deepseek-v3"),
                "llm_model_deepseek_r1": os.environ.get("PG_LLM_MODEL_R1", "deepseek-r1"),
                "llm_query_repeat_times": 1,
                "llm_query_max_attempts": 10,
                "llm_violation_repeat_times": 3,
                "llm_multithread": 32,
            },
            "project": {
                "project_path": self._container_path(workspace_dir, project_root),
                "packet_related_callgraph_path": "/workspace/callgraph_report.txt",
                "function_arg_path": "/workspace/function_arg_summary.txt",
                "rule_path": "/workspace/inputs/rules.json",
                "protocol_name": resolved_protocol,
                "protocol_version": resolved_version,
                "project_name": resolved_project,
                "original_llvm_ir_path": self._container_path(workspace_dir, original_ir_path),
                "build_log_path": self._container_path(workspace_dir, build_log_path),
                "binary_path": self._container_path(workspace_dir, binary_path),
                "bitcode_path": self._container_path(workspace_dir, bitcode_path),
            },
            "debug": {
                "code_slice_replace_mode": 0,
                "log_print": 0,
            },
            "config": {
                "mqtt_packet_type": [
                    "CONNECT", "CONNACK", "PUBLISH", "PUBACK", "PUBREC", "PUBREL", "PUBCOMP",
                    "SUBSCRIBE", "SUBACK", "UNSUBSCRIBE", "UNSUBACK", "PINGREQ", "PINGRESP", "DISCONNECT", "AUTH"
                ],
                "dhcpv6_packet_type": [
                    "DHCP6_SOLICIT", "DHCP6_ADVERTISE", "DHCP6_REQUEST", "DHCP6_REPLY",
                    "DHCP6_CONFIRM", "DHCP6_RELEASE", "DHCP6_DECLINE", "DHCP6_RENEW",
                    "DHCP6_REBIND", "DHCP6_IREQ", "DHCP6_RECONFIGURE", "DHCP6_RELAYFORW", "DHCP6_RELAYREPL"
                ],
                "coap_packet_type": ["CONFIRMABLE", "NON_CONFIRMABLE", "ACKNOWLEDGEMENT", "RESET"],
                "ftp_packet_type": [
                    "USER", "PASS", "ACCT", "REIN", "QUIT", "PORT", "PASV", "TYPE", "STRU", "MODE",
                    "RETR", "STOR", "APPE", "DELE", "RNFR", "RNTO", "ABOR", "CWD", "CDUP", "PWD",
                    "MKD", "RMD", "LIST", "NLST", "SYST", "STAT", "FEAT", "HELP", "NOOP", "ALLO",
                    "REST", "MLST", "MLSD", "OPTS", "EPSV", "EPRT", "AUTH", "ADAT", "CCC", "CONF",
                    "ENC", "MIC", "PBSZ", "PROT"
                ],
                "tls13_message_type": [
                    "CLIENT_HELLO", "SERVER_HELLO", "NEW_SESSION_TICKET", "END_OF_EARLY_DATA",
                    "ENCRYPTED_EXTENSIONS", "CERTIFICATE", "CERTIFICATE_REQUEST", "CERTIFICATE_VERIFY",
                    "FINISHED", "KEY_UPDATE", "HELLO_RETRY_REQUEST"
                ],
            },
        }

    def _run_analysis_container(
        self,
        workspace_dir: Path,
        job_identifier: str,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
        *,
        protocol_name: Optional[str] = None,
        protocol_version: Optional[str] = None,
        project_name: Optional[str] = None,
    ):
        job_logger = JobStageLogger(
            job_id=job_identifier,
            logger=logger,
            progress_callback=progress_callback,
        )
        if not self._docker_available:
            job_logger.debug(
                "Docker not available, skipping analysis container",
                stage="analysis",
                emit_progress=False,
            )
            return

        output_dir = self.settings.workspace_root.parent / "outputs" / job_identifier
        output_dir.mkdir(parents=True, exist_ok=True)

        config_dir = self.settings.workspace_root.parent / "configs" / job_identifier
        config_dir.mkdir(parents=True, exist_ok=True)

        logger.debug("[*] Generating config.toml with correct paths for ProtocolGuard analysis")

        prepared_config = self._build_analysis_config(
            workspace_dir=workspace_dir,
            protocol_name=protocol_name,
            protocol_version=protocol_version,
            project_name=project_name,
        )

        import toml
        final_config_content = toml.dumps(prepared_config)
        config_path = config_dir / "config.toml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(final_config_content)
        logger.info(
            "Generated final ProtocolGuard analysis config.toml for job %s at %s:\n%s",
            job_identifier,
            config_path,
            final_config_content,
            extra={
                "protocolguard_context": {
                    "job_id": job_identifier,
                    "stage": "config",
                    "config_source": "generated-final-analysis",
                    "config_path": str(config_path),
                },
            },
        )
        if progress_callback:
            progress_callback(
                job_identifier,
                "config",
                f"Generated final ProtocolGuard analysis config.toml at {config_path}:\n{final_config_content}",
            )

        inputs_dir = workspace_dir / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)

        rules_path = inputs_dir / "rules.json"
        if not rules_path.exists():
            rule_config_path = workspace_dir / "rule_config.json"
            if rule_config_path.exists():
                shutil.copy2(rule_config_path, rules_path)
                logger.debug("[*] Copied rule_config.json to %s", rules_path)
            else:
                logger.debug("⚠️ rules.json not found, skipping analysis container")
                return

        project_root = self._infer_project_root(workspace_dir)
        project_build_dir = project_root / "build"
        project_build_dir.mkdir(parents=True, exist_ok=True)

        workspace_build_log = workspace_dir / "build_log.txt"
        project_build_log = project_build_dir / "build_log.txt"

        if workspace_build_log.exists():
            shutil.copy2(workspace_build_log, project_build_log)
            logger.debug("[*] Copied build_log.txt to %s", project_build_log)
        else:
            logger.debug("⚠️ build_log.txt not found in workspace, searching in project/build")
            if project_build_log.exists():
                logger.debug("[*] Found build_log.txt in project/build")
            else:
                logger.debug("⚠️ build_log.txt not found anywhere, creating empty file in workspace")
                with open(workspace_build_log, "w") as f:
                    f.write("Empty build log - build may have failed")
                shutil.copy2(workspace_build_log, project_build_log)

        project_dir = workspace_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)

        cf_files = list(project_dir.rglob(".cf_*.json"))

        if cf_files:
            logger.debug("[*] Found %d .cf_*.json files under project directory", len(cf_files))
            for cf_file in cf_files[:5]:
                logger.debug("    - %s", cf_file.relative_to(project_dir))
            if len(cf_files) > 5:
                logger.debug("    - ... and %d more", len(cf_files) - 5)
        else:
            logger.debug("[*] No .cf_*.json files found under %s", project_dir)

        logger.debug("\n%s", "=" * 60)
        logger.debug("RUNNING PROTOCOL GUARD ANALYSIS")
        logger.debug("%s", "=" * 60)
        logger.debug("[*] Analysis image: %s", self._analysis_image)
        logger.debug("[*] Analysis command: %s", self._analysis_command)
        logger.debug("[*] Workspace: %s", workspace_dir)
        logger.debug("[*] Output: %s", output_dir)
        logger.debug("[*] Config: %s", config_dir)

        if progress_callback:
            progress_callback(job_identifier, "builder", "Starting builder container")

        command = [
            "docker", "run", "--rm",
            "-u", f"{os.getuid()}:{os.getgid()}",
            "-v", f"{workspace_dir}:/workspace",
            "-v", f"{output_dir}:/out",
            "-v", f"{config_dir}:/config",
            "--network=host",
        ]

        for env_arg in self._docker_env_args():
            command.append(env_arg)
        logger.debug("[*] Passing configured ProtocolGuard environment variables to container")
        logger.debug("[*] Passing PG_HOST_UID=%d to container", os.getuid())
        logger.debug("[*] Passing PG_HOST_GID=%d to container", os.getgid())

        command.extend([self._analysis_image, *self._analysis_command])

        logger.debug("[*] Command: %s", " ".join(command))

        workspace_log_path = workspace_dir / "analysis_log.txt"
        output_log_path = output_dir / "analysis.log"
        log_lines: List[str] = []
        process: Optional[subprocess.Popen[str]] = None

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(workspace_dir)
            )
            if process.stdout is None:
                raise ClaudeBuilderRunnerExecutionError("Analysis container did not expose stdout")

            step_keywords = [
                ("函数入口", "function-entry"),
                ("程序切片", "program-slicing"),
                ("代码定位", "code-location"),
                ("不一致检测", "inconsistency-detection"),
                ("LLM分析", "llm-analysis"),
                ("规则匹配", "rule-matching"),
                ("合规性检查", "compliance-check"),
                ("生成报告", "generating-report"),
                ("构建完成", "build-complete"),
            ]

            last_step = None

            with (
                workspace_log_path.open("w", encoding="utf-8") as workspace_log,
                output_log_path.open("w", encoding="utf-8") as output_log,
            ):
                for line in iter(process.stdout.readline, ''):
                    line = line.rstrip()
                    log_lines.append(line)
                    workspace_log.write(line + "\n")
                    workspace_log.flush()
                    output_log.write(line + "\n")
                    output_log.flush()

                    if line:
                        job_logger.info(
                            "%s",
                            line,
                            stage="analysis-log",
                            stream="docker-stdout-stderr",
                            frontend_message=line[:2000],
                        )

                    for keyword, step_name in step_keywords:
                        if keyword in line and step_name != last_step:
                            last_step = step_name
                            if progress_callback:
                                progress_callback(job_identifier, step_name, f"Step: {keyword}")
                            break

                    if "error" in line.lower() or "failed" in line.lower():
                        if progress_callback:
                            progress_callback(job_identifier, "error", line)

            process.wait(timeout=300)

            if process.returncode == 0:
                logger.debug("🎉 ANALYSIS SUCCESS")

                if progress_callback:
                    progress_callback(job_identifier, "analysis", "ProtocolGuard analysis completed")

                logger.debug("[*] Fixing permissions on source files in %s", output_dir)
                try:
                    subprocess.run(
                        ["chmod", "-R", "755", str(output_dir)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    logger.debug("[*] chmod -R 755 applied to %s", output_dir)
                except Exception as e:
                    logger.debug("[*] Failed to chmod: %s", e)

                try:
                    subprocess.run(
                        ["find", str(output_dir), "-type", "f", "-exec", "chmod", "644", "{}", "+"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    logger.debug("[*] find -type f -exec chmod 644 applied to %s", output_dir)
                except Exception as e:
                    logger.debug("[*] Failed to chmod files: %s", e)

                logger.debug("[*] Source file permissions fixed")

                logger.debug("[*] Copying analysis outputs from %s to %s", output_dir, workspace_dir)
                for item in output_dir.iterdir():
                    dest_path = workspace_dir / item.name
                    if item.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(item, dest_path)
                        for root, dirs, files in os.walk(dest_path):
                            for dir_name in dirs:
                                try:
                                    os.chmod(os.path.join(root, dir_name), 0o755)
                                except Exception:
                                    pass
                            for file_name in files:
                                try:
                                    os.chmod(os.path.join(root, file_name), 0o644)
                                except Exception:
                                    pass
                    else:
                        if dest_path.exists():
                            dest_path.unlink()
                        shutil.copy2(item, dest_path)
                        try:
                            dest_path.chmod(0o644)
                        except Exception:
                            pass
                logger.debug("[*] Analysis outputs copied to workspace")

                db_in_workspace = workspace_dir / "database"
                if db_in_workspace.exists():
                    try:
                        db_in_workspace.chmod(0o755)
                    except Exception:
                        pass
                    for db_file in db_in_workspace.glob("*.db"):
                        try:
                            db_file.chmod(0o644)
                        except Exception:
                            pass
                    logger.debug("[*] Set permissions on database files")
                else:
                    build_dir = project_build_dir
                    if build_dir.exists():
                        shutil.copytree(build_dir, db_in_workspace, dirs_exist_ok=True)
                        logger.debug("[*] Created database directory from build dir")

                for db_file in workspace_dir.rglob("*.db"):
                    try:
                        db_file.chmod(0o644)
                    except Exception:
                        pass
                    try:
                        db_file.parent.chmod(0o755)
                    except Exception:
                        pass
                logger.debug("[*] Set permissions on all .db files in workspace")

                logger.debug("[*] Final workspace contents:")
                for root, dirs, files in os.walk(workspace_dir):
                    level = root.replace(str(workspace_dir), '').count(os.sep)
                    indent = ' ' * 2 * level
                    logger.debug("%s%s/", indent, os.path.basename(root))
                    subindent = ' ' * 2 * (level + 1)
                    for file in files[:10]:
                        file_path = Path(root) / file
                        if file_path.suffix == '.db':
                            logger.debug("%s%s (DATABASE)", subindent, file)
                        else:
                            logger.debug("%s%s", subindent, file)
            else:
                logger.debug("❌ ANALYSIS FAILED")
                logger.debug("[*] Analysis error log:")
                logger.debug("-" * 40)
                logger.debug("\n".join(log_lines[-40:]) if log_lines else "")
                logger.debug("-" * 40)

                logger.debug("[*] Fixing permissions on source files in %s (failure path)", output_dir)
                try:
                    subprocess.run(
                        ["chmod", "-R", "755", str(output_dir)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    logger.debug("[*] chmod -R 755 applied to %s", output_dir)
                except Exception as e:
                    logger.debug("[*] Failed to chmod: %s", e)

                try:
                    subprocess.run(
                        ["find", str(output_dir), "-type", "f", "-exec", "chmod", "644", "{}", "+"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    logger.debug("[*] find -type f -exec chmod 644 applied to %s", output_dir)
                except Exception as e:
                    logger.debug("[*] Failed to chmod files: %s", e)

                logger.debug("[*] Source file permissions fixed (failure path)")

                logger.debug("[*] Copying analysis outputs from %s to %s (even on failure)", output_dir, workspace_dir)
                for item in output_dir.iterdir():
                    dest_path = workspace_dir / item.name
                    if item.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(item, dest_path)
                        for root, dirs, files in os.walk(dest_path):
                            for dir_name in dirs:
                                try:
                                    os.chmod(os.path.join(root, dir_name), 0o755)
                                except Exception:
                                    pass
                            for file_name in files:
                                try:
                                    os.chmod(os.path.join(root, file_name), 0o644)
                                except Exception:
                                    pass
                    else:
                        if dest_path.exists():
                            dest_path.unlink()
                        shutil.copy2(item, dest_path)
                        try:
                            dest_path.chmod(0o644)
                        except Exception:
                            pass
                logger.debug("[*] Analysis outputs copied to workspace")

                for db_file in workspace_dir.rglob("*.db"):
                    try:
                        db_file.chmod(0o644)
                    except Exception:
                        pass
                    try:
                        db_file.parent.chmod(0o755)
                    except Exception:
                        pass
                logger.debug("[*] Set permissions on all .db files in workspace (failure path)")

                ast_stderr_path = workspace_dir / "logs" / "ast_extraction.stderr"
                if ast_stderr_path.exists():
                    logger.debug("[*] AST extraction stderr content:")
                    logger.debug("-" * 40)
                    with open(ast_stderr_path, "r", encoding="utf-8", errors="ignore") as f:
                        logger.debug(f.read())
                    logger.debug("-" * 40)
                else:
                    logger.debug("[*] AST extraction stderr not found at %s", ast_stderr_path)

                if progress_callback:
                    progress_callback(job_identifier, "error", f"Analysis failed with exit code {process.returncode}")

                raise ClaudeBuilderRunnerExecutionError(
                    f"Analysis container exited with status {process.returncode}",
                    logs=log_lines,
                    details={
                        "command": self._redact_command(command),
                        "workspace": str(workspace_dir),
                        "output": str(output_dir),
                        "logExcerpt": "\n".join(log_lines[-40:]),
                    },
                )

        except subprocess.TimeoutExpired as exc:
            if process is not None:
                process.kill()
            logger.debug("❌ ANALYSIS TIMEOUT")
            if progress_callback:
                progress_callback(job_identifier, "error", "Analysis timeout after 300 seconds")
            raise ClaudeBuilderRunnerExecutionError(
                "Analysis container timed out after 300 seconds",
                logs=log_lines,
                details={
                    "command": self._redact_command(command),
                    "workspace": str(workspace_dir),
                    "output": str(output_dir),
                    "logExcerpt": "\n".join(log_lines[-40:]),
                },
            ) from exc
        except ClaudeBuilderRunnerExecutionError:
            raise
        except Exception as exc:
            logger.exception("Analysis execution raised an exception")
            if progress_callback:
                progress_callback(job_identifier, "error", str(exc))
            raise ClaudeBuilderRunnerExecutionError(
                f"Analysis container execution failed: {exc}",
                logs=log_lines,
                details={
                    "command": self._redact_command(command),
                    "workspace": str(workspace_dir),
                    "output": str(output_dir),
                    "logExcerpt": "\n".join(log_lines[-40:]),
                },
            ) from exc

    def run_compilation(
        self,
        *,
        code_stream: BinaryIO,
        code_filename: str,
        config_stream: Optional[BinaryIO],
        config_filename: Optional[str],
        rules_stream: BinaryIO,
        rules_filename: str,
        notes: Optional[str] = None,
        protocol_name: Optional[str] = None,
        protocol_version: Optional[str] = None,
        project_name: Optional[str] = None,
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> Dict[str, Any]:
        job_identifier = job_id or str(uuid.uuid4())
        job_logger = JobStageLogger(
            job_id=job_identifier,
            logger=logger,
            progress_callback=progress_callback,
        )

        if progress_callback:
            progress_callback(job_identifier, "init", "Preparing compiler inputs")

        workspace_dir = self.settings.workspace_root / job_identifier
        workspace_dir.mkdir(parents=True, exist_ok=True)

        code_bytes = code_stream.read()
        config_bytes = config_stream.read() if config_stream is not None else None
        rules_bytes = rules_stream.read()

        archive_path = workspace_dir / code_filename
        with open(archive_path, "wb") as f:
            f.write(code_bytes)

        if config_bytes is None:
            config_filename = config_filename or "generated-config.toml"
            config_content = self._build_generated_config_content(
                protocol_name=protocol_name,
                protocol_version=protocol_version,
                project_name=project_name,
            )
            job_logger.info(
                "No uploaded ProtocolGuard config was provided; generated %s for compiler bootstrap:\n%s",
                config_filename,
                config_content,
                stage="config",
                config_source="generated",
                config_filename=config_filename,
                protocol_name=protocol_name,
                protocol_version=protocol_version,
                project_name=project_name,
            )
        else:
            config_content = config_bytes.decode("utf-8")
            job_logger.info(
                "Using uploaded ProtocolGuard config %s for compiler bootstrap:\n%s",
                config_filename or "config.toml",
                config_content,
                stage="config",
                config_source="uploaded",
                config_filename=config_filename or "config.toml",
            )
        inputs_dir = workspace_dir / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        rules_path = inputs_dir / "rules.json"
        with open(rules_path, "wb") as f:
            f.write(rules_bytes)

        rule_config_path = workspace_dir / "rule_config.json"
        with open(rule_config_path, "wb") as f:
            f.write(rules_bytes)

        config_path = workspace_dir / "config.toml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        if progress_callback:
            progress_callback(job_identifier, "compile", "Starting Claude builder compilation")

        builder_logs = self._run_claude_builder_container(workspace_dir, job_identifier, progress_callback)
        logger.debug("[*] Claude builder emitted %d log lines", len(builder_logs))
        self._validate_builder_outputs(workspace_dir)
        if progress_callback:
            progress_callback(job_identifier, "compile", "Claude builder output validated")

        logger.debug("[*] Workspace contents after builder:")
        for root, dirs, files in os.walk(workspace_dir):
            level = root.replace(str(workspace_dir), '').count(os.sep)
            indent = ' ' * 2 * level
            logger.debug("%s%s/", indent, os.path.basename(root))
            subindent = ' ' * 2 * (level + 1)
            for file in files[:10]:
                logger.debug("%s%s", subindent, file)
            if len(files) > 10:
                logger.debug("%s... and %d more", subindent, len(files) - 10)

        self._run_analysis_container(
            workspace_dir,
            job_identifier,
            progress_callback,
            protocol_name=protocol_name,
            protocol_version=protocol_version,
            project_name=project_name,
        )

        database_path = None

        def _validate_db(db_path_candidate: Path) -> bool:
            try:
                try:
                    db_path_candidate.chmod(0o644)
                except Exception:
                    pass
                try:
                    db_path_candidate.parent.chmod(0o755)
                except Exception:
                    pass
                import sqlite3
                with sqlite3.connect(str(db_path_candidate)) as conn:
                    cursor = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='rule_code_snippet'"
                    )
                    row = cursor.fetchone()
                    return row is not None
            except Exception:
                return False

        standard_names = ["rule_code_snippet.db", "analysis.db", "protocolguard.db", "violations.db"]

        project_root = self._infer_project_root(workspace_dir)
        for db_candidate in [
            workspace_dir / "database" / "rule_code_snippet.db",
            workspace_dir / "database" / "analysis.db",
            workspace_dir / "database" / "protocolguard.db",
            project_root / "build" / "rule_code_snippet.db",
            project_root / "build" / "analysis.db",
            project_root / "build" / "protocolguard.db",
        ]:
            if db_candidate.exists() and _validate_db(db_candidate):
                database_path = str(db_candidate)
                logger.debug("[*] Found valid database file: %s", database_path)
                break

        if database_path is None:
            for ext in [".db", ".sqlite"]:
                for path in workspace_dir.rglob(f"*{ext}"):
                    if _validate_db(path):
                        database_path = str(path)
                        logger.debug("[*] Found valid database file (search): %s", database_path)
                        break
                if database_path:
                    break

        if database_path is None:
            for ext in [".db", ".sqlite"]:
                for path in workspace_dir.rglob(f"*{ext}"):
                    filename = path.name.lower()
                    if any(name in filename for name in standard_names):
                        database_path = str(path)
                        logger.debug("[*] Found database file by name (no validation): %s", database_path)
                        break
                    elif "sqlite" in filename or filename.endswith(".db"):
                        database_path = str(path)
                        logger.debug("[*] Found database file (fallback): %s", database_path)
                        break
                if database_path:
                    break

        if database_path is None:
            database_dir = workspace_dir / "database"
            if database_dir.exists():
                for db_file in database_dir.glob("*.db"):
                    if _validate_db(db_file):
                        database_path = str(db_file)
                        logger.debug("[*] Found valid database in database dir: %s", database_path)
                        break

            if database_path is None and database_dir.exists():
                for db_file in database_dir.glob("*.db"):
                    database_path = str(db_file)
                    logger.debug("[*] Using database file in database dir: %s", database_path)
                    break

                if database_path is None:
                    logger.debug("[*] No database file found in database dir: %s", database_dir)
            else:
                build_dir = project_root / "build"
                if build_dir.exists():
                    for db_file in build_dir.glob("*.db"):
                        if _validate_db(db_file):
                            database_path = str(db_file)
                            logger.debug("[*] Found valid database in build dir: %s", database_path)
                            break

                if database_path is None and build_dir.exists():
                    for db_file in build_dir.glob("*.db"):
                        database_path = str(db_file)
                        logger.debug("[*] Using database file in build dir: %s", database_path)
                        break

                if database_path is None:
                    database_path = str(workspace_dir / "database" / "rule_code_snippet.db")
                    logger.debug("[*] Using fallback database path: %s", database_path)

        db_path_for_findings = database_path if (database_path and Path(database_path).is_file()) else None

        findings, summary_counts = self._extract_findings(
            db_path_for_findings,
            protocol_name or "unknown",
            protocol_version or "unknown",
        )
        overall_status = self._determine_overall_status(summary_counts)

        logger.debug("[*] Extracted %d findings from database", len(findings))
        logger.debug("[*] Summary counts: %s", summary_counts)
        logger.debug("[*] Overall status: %s", overall_status)

        output_dir = self.settings.workspace_root.parent / "outputs" / job_identifier
        config_dir = self.settings.workspace_root.parent / "configs" / job_identifier
        log_file = workspace_dir / "build_log.txt"

        artifacts = {
            "workspace": str(workspace_dir),
            "output": str(output_dir) if output_dir.exists() else None,
            "config": str(config_dir / "config.toml") if (config_dir / "config.toml").exists() else None,
            "logs": str(log_file) if log_file.exists() else None,
            "database": db_path_for_findings if db_path_for_findings and Path(db_path_for_findings).exists() else None,
            "workspaceSnapshots": [],
        }

        if progress_callback:
            progress_callback(job_identifier, "completed", "Compilation and analysis completed successfully")

        now_iso = datetime.now(timezone.utc).isoformat()

        return {
            "analysisId": job_identifier,
            "durationMs": 0,
            "inputs": {
                "codeFileName": code_filename,
                "builderDockerfileName": None,
                "configFileName": config_filename or "generated-config.toml",
                "notes": notes or None,
                "protocolName": protocol_name,
                "rulesFileName": rules_filename,
                "rulesSummary": None,
            },
            "model": "protocolguard:latest",
            "modelResponse": {
                "metadata": {
                    "generatedAt": now_iso,
                    "modelVersion": "protocolguard:latest",
                    "protocol": protocol_name,
                    "ruleSet": rules_filename,
                    "protocolVersion": protocol_version,
                },
                "summary": {
                    "compliantCount": summary_counts.get("compliant", 0),
                    "needsReviewCount": summary_counts.get("needs_review", 0),
                    "nonCompliantCount": summary_counts.get("non_compliant", 0),
                    "notes": notes or "ProtocolGuard static analysis completed via AI Agent.",
                    "overallStatus": overall_status,
                },
                "verdicts": findings,
            },
            "submittedAt": now_iso,
            "artifacts": artifacts,
        }
