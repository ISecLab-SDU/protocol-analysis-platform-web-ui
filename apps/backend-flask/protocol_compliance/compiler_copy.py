import os
import json
import logging
import re
import shutil
import sqlite3
import tarfile
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AgentExecutorError(Exception):
    pass


class AgentExecutionError(AgentExecutorError):
    def __init__(self, message: str, *, logs: Optional[list] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.logs = logs or []
        self.details = details or {}


class AgentNotAvailableError(AgentExecutorError):
    pass


@dataclass(frozen=True)
class AgentExecutorSettings:
    enabled: bool
    api_key: str
    base_url: str
    model: str
    workspace_root: Path
    max_runtime: int
    env_passthrough: tuple

    @classmethod
    def from_env(cls) -> "AgentExecutorSettings":
        api_key = os.environ.get("OPENAI_API_KEY")
        enabled = bool(api_key)
        base_url = os.environ.get("OPENAI_BASE_URL")
        model = os.environ.get("PG_AGENT_MODEL", "deepseek-v3")
        
        runtime_root = Path(os.environ.get("PG_RUNTIME_ROOT", tempfile.gettempdir() + "/protocolguard"))
        workspace_root = Path(os.environ.get("PG_WORKSPACE_ROOT", runtime_root / "workspaces"))
        
        max_runtime = int(os.environ.get("PG_AGENT_MAX_RUNTIME", "3600"))
        
        env_passthrough_str = os.environ.get("PG_ENV_VARS", "OPENAI_API_KEY")
        env_passthrough = tuple(item.strip() for item in env_passthrough_str.split(",") if item.strip())
        
        return cls(
            enabled=enabled,
            api_key=api_key,
            base_url=base_url,
            model=model,
            workspace_root=workspace_root,
            max_runtime=max_runtime,
            env_passthrough=env_passthrough
        )


class LLMClient:

    def __init__(self, api_key=None, base_url=None, model=None):
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        model = model or os.environ.get("PG_AGENT_MODEL", "deepseek-v3")
        
        if not api_key:
            raise ValueError("PG_AGENT_API_KEY or OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model

    def _clean(self, text: str) -> str:
        m = re.search(r"```(?:\w*)\n(.*?)```", text, re.DOTALL)
        return m.group(1).strip() if m else text.strip()

    def generate(self, config, rule, structure, error_log=None, last_dockerfile=None):

        error_block = ""
        if error_log:
            error_block = f"""
## ❌ EXECUTION ERROR
{error_log[-4000:]}

## LAST FAILED DOCKERFILE
{last_dockerfile}
"""

        prompt = f"""
You are an expert DevOps engineer.

Your task is to create a Dockerfile that rebuilds a pre-compiled project using gclang and extracts LLVM bitcode.

The sol.tar contains pre-compiled artifacts including .cf_*.json AST files. Do NOT modify or recreate these files.

========================
AVAILABLE FILES
========================
- sol.tar (pre-compiled source code archive with .cf_*.json AST files)
- rule_config.json (rule configuration)

========================
sol.tar CONTENTS
========================
{structure}

========================
REQUIREMENTS
========================
- Base image: ubuntu:22.04
- Install: ca-certificates, curl, wget, git, build-essential, cmake, ninja-build, pkg-config, python3.10, python3-pip, python3.10-venv, llvm-14, clang-14, libclang-14-dev, llvm-14-dev, llvm-12, clang-12, golang-1.18-go, libcurl4-openssl-dev, libsqlite3-dev, tshark, zlib1g-dev, libssl-dev, file, tree
- Install gllvm: go install github.com/SRI-CSL/gllvm/cmd/...@latest
- Set PATH to include /root/go/bin and /usr/lib/llvm-14/bin

========================
BUILD PROCESS
========================
Create an entrypoint script /usr/local/bin/pg-run that:
1. Note: /workspace/project/sol/ already exists with pre-compiled artifacts including .cf_*.json files
2. Removes and recreates /workspace/project/sol/build ONLY (keep src/ directory intact)
3. Runs cmake from /workspace/project/sol/build with:
   - DCMAKE_C_COMPILER=gclang
   - DCMAKE_CXX_COMPILER=gclang++
   - DCMAKE_BUILD_TYPE=Debug
   - DCMAKE_C_FLAGS_DEBUG="-g -O0 -Xclang -disable-O0-optnone -fno-discard-value-names"
   - DCMAKE_CXX_FLAGS_DEBUG="-g -O0 -Xclang -disable-O0-optnone -fno-discard-value-names"
4. Runs make with CC=gclang and CFLAGS="-g -Xclang -disable-O0-optnone -fno-discard-value-names", output to build_log.txt
5. Runs get-bc ./sol to extract bitcode
6. Copies sol.bc to program.bc
7. Runs llvm-dis-14 program.bc -o program.ll

CRITICAL POST-BUILD STEPS:
1. Copy all build artifacts to /workspace/:
   - cp /workspace/project/sol/build/* /workspace/
   - cp sol /workspace/
   - cp sol.bc /workspace/
   - cp sol.bc /workspace/program.bc
   - llvm-dis-14 /workspace/program.bc -o /workspace/program.ll
   - cp build_log.txt /workspace/

2. Copy rules config:
   - mkdir -p /workspace/inputs
   - cp /workspace/rule_config.json /workspace/inputs/rules.json

3. IMPORTANT: Do NOT modify or recreate any .cf_*.json files in /workspace/project/sol/src/
   - These files are pre-generated and required for AST extraction

OUTPUT VERIFICATION:
Before exiting, run:
- tree /workspace/project/sol/src/
- ls -la /workspace/project/sol/src/*.json
- ls -la /workspace/

Use COPY to bring sol.tar and rule_config.json from the build context into /workspace/.
Set ENTRYPOINT to ["/usr/local/bin/pg-run"]
Set WORKDIR to /workspace

========================
SELF-HEAL MODE
========================
{error_block}

If failed:
- Analyze the error carefully
- Fix the root cause
- Try a different approach if needed

========================
OUTPUT
========================
Return ONLY Dockerfile content
"""

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You generate robust Docker build environments."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=4096
        )

        return self._clean(resp.choices[0].message.content)


class DockerTester:

    def __init__(self, timeout=300):
        self.timeout = timeout

    def build(self, dockerfile_path, tag, dockerfile_content=None, build_context="."):
        try:
            if dockerfile_content is not None:
                r = subprocess.run(
                    ["docker", "build", "-f", dockerfile_path, "-t", tag, build_context],
                    input=dockerfile_content,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
            else:
                r = subprocess.run(
                    ["docker", "build", "-f", dockerfile_path, "-t", tag, build_context],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )

            log = (r.stdout or "") + "\n" + (r.stderr or "")
            return r.returncode == 0, log

        except Exception as e:
            return False, str(e)

    def check_output(self, tag):
        required_files = ["sol", "sol.bc", "program.bc", "program.ll", "build_log.txt"]

        try:
            r = subprocess.run(
                ["docker", "run", "--rm", tag, "ls", "-la", "/workspace"],
                capture_output=True,
                text=True,
                timeout=60
            )

            log = (r.stdout or "") + "\n" + (r.stderr or "")

            if r.returncode != 0:
                return False, f"Failed to check /workspace: {log}"

            missing_files = []
            for f in required_files:
                if f not in log:
                    missing_files.append(f)

            if missing_files:
                return False, f"Missing required files: {', '.join(missing_files)}\n/workspace contents:\n{log}"

            r2 = subprocess.run(
                ["docker", "run", "--rm", tag, "ls", "-la", "/workspace/project/sol/src/"],
                capture_output=True,
                text=True,
                timeout=60
            )

            src_log = (r2.stdout or "") + "\n" + (r2.stderr or "")

            if r2.returncode != 0:
                return False, f"Failed to check /workspace/project/sol/src/: {src_log}"

            cf_files_count = src_log.count(".cf_")
            if cf_files_count == 0:
                return False, f"No .cf_*.json files found in /workspace/project/sol/src/\nDirectory contents:\n{src_log}"

            return True, f"/workspace contains all required files\nFound {cf_files_count} .cf_*.json files in src/:\n{src_log}"

        except Exception as e:
            return False, f"Error checking output: {str(e)}"

    def copy_output(self, tag, dest_path):
        try:
            os.makedirs(dest_path, exist_ok=True)

            container_id = subprocess.run(
                ["docker", "create", tag],
                capture_output=True,
                text=True,
                timeout=30
            ).stdout.strip()

            if not container_id:
                return False, "Failed to create container"

            try:
                r_start = subprocess.run(
                    ["docker", "start", container_id],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if r_start.returncode != 0:
                    return False, f"Failed to start container: {r_start.stderr}"
                
                r_wait = subprocess.run(
                    ["docker", "wait", container_id],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if r_wait.returncode != 0:
                    return False, f"Container wait failed: {r_wait.stderr}"
                
                exit_code = int(r_wait.stdout.strip())
                if exit_code != 0:
                    logs = subprocess.run(
                        ["docker", "logs", container_id],
                        capture_output=True,
                        text=True,
                        timeout=60
                    ).stdout
                    return False, f"Container exited with code {exit_code}\nLogs:\n{logs}"

                r = subprocess.run(
                    ["docker", "cp", f"{container_id}:/workspace/.", dest_path],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if r.returncode != 0:
                    return False, f"Failed to copy output: {r.stderr}"

                for root, dirs, files in os.walk(dest_path):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            os.chmod(dir_path, 0o755)
                        except Exception:
                            pass
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        try:
                            os.chmod(file_path, 0o644)
                        except Exception:
                            pass

                return True, f"Output copied to {dest_path}"

            finally:
                subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, timeout=30)

        except Exception as e:
            return False, f"Error copying output: {str(e)}"


class CompilerController:

    def __init__(self, max_runtime=3600, api_key=None, base_url=None, model=None):
        self.llm = LLMClient(api_key=api_key, base_url=base_url, model=model)
        self.docker = DockerTester()
        self.max_runtime = max_runtime

    def load(self, config_content, rule_content):
        config = config_content
        rule = json.loads(rule_content)
        return config, rule

    def parse_tar(self, tar_path):
        with tarfile.open(tar_path) as tar:
            return "\n".join([m.name for m in tar.getmembers()])

    def run(self, sol_tar, config_content, rule_content, output_dir):
        config, rule = self.load(config_content, rule_content)
        structure = self.parse_tar(sol_tar)
        
        build_context = os.path.dirname(os.path.abspath(sol_tar))
        
        config_path = os.path.join(build_context, "config.toml")
        with open(config_path, "w") as f:
            f.write(config_content)
        
        rule_path = os.path.join(build_context, "rule_config.json")
        with open(rule_path, "w") as f:
            f.write(rule_content)

        last_dockerfile = None
        error_log = None

        start_time = time.time()
        i = 0

        logger.debug("🚀 START SELF-HEALING DOCKER LOOP")
        logger.debug(f"[*] Build context: {build_context}")

        while True:
            i += 1
            logger.debug(f"\n{'='*60}")
            logger.debug(f"ROUND {i}")
            logger.debug(f"{'='*60}")

            if time.time() - start_time > self.max_runtime:
                logger.debug("❌ TIME LIMIT REACHED")
                break

            logger.debug("[*] Generating Dockerfile with AI...")
            dockerfile = self.llm.generate(
                config=config,
                rule=rule,
                structure=structure,
                error_log=error_log,
                last_dockerfile=last_dockerfile
            )
            logger.debug("[*] Generated Dockerfile:")
            logger.debug("-" * 40)
            logger.debug(dockerfile[:1000] + "..." if len(dockerfile) > 1000 else dockerfile)
            logger.debug("-" * 40)

            logger.debug(f"[*] Building Docker image: build-{i}")
            logger.debug(f"[*] Build context: {build_context}")

            ok, log = self.docker.build("-", tag=f"build-{i}", dockerfile_content=dockerfile, build_context=build_context)

            if ok:
                logger.debug("🎉 BUILD SUCCESS")
                logger.debug("[*] Build log:")
                logger.debug("-" * 40)
                logger.debug(log[-3000:] if len(log) > 3000 else log)
                logger.debug("-" * 40)
                
                logger.debug("[+] Checking /workspace directory...")

                output_ok, output_log = self.docker.check_output(f"build-{i}")

                if output_ok:
                    logger.debug("✅ OUTPUT VALIDATED")
                    logger.debug(output_log)

                    logger.debug(f"[+] Copying output to {output_dir}...")
                    copy_ok, copy_log = self.docker.copy_output(f"build-{i}", output_dir)

                    if copy_ok:
                        logger.debug("✅ OUTPUT COPIED")
                        logger.debug(copy_log)
                    else:
                        logger.debug("❌ FAILED TO COPY OUTPUT")
                        logger.debug(copy_log)

                    logger.debug("Success")
                    return dockerfile
                else:
                    logger.debug("❌ OUTPUT INVALID")
                    logger.debug("-" * 40)
                    logger.debug(output_log)
                    logger.debug("-" * 40)
                    last_dockerfile = dockerfile
                    error_log = f"BUILD_SUCCESS_BUT_OUTPUT_INVALID\n{output_log}"
                    continue

            logger.debug("❌ BUILD FAILED")
            logger.debug("[*] Build error log:")
            logger.debug("-" * 40)
            logger.debug(log[-3000:] if len(log) > 3000 else log)
            logger.debug("-" * 40)

            last_dockerfile = dockerfile
            error_log = log

        logger.debug("💥 FAILED AFTER TIME LIMIT")

        bug_report = f"""==== FINAL ERROR LOG ====\n\n{error_log or ""}\n\n==== LAST DOCKERFILE ====\n{last_dockerfile or ""}\n\n==== STRUCTURE ====\n{structure}\n\n==== CONFIG ====\n{config}\n\n==== RULE ====\n{json.dumps(rule, indent=2)}"""
        
        bug_path = os.path.join(output_dir, "bug.txt")
        with open(bug_path, "w") as f:
            f.write(bug_report)
        
        return None


class AgentExecutor:

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

    def __init__(self, settings: AgentExecutorSettings):
        self.settings = settings
        if not settings.enabled:
            raise AgentNotAvailableError("Agent executor is not enabled")
        
        try:
            self.compiler = CompilerController(
                max_runtime=settings.max_runtime,
                api_key=settings.api_key,
                base_url=settings.base_url,
                model=settings.model
            )
        except ValueError as e:
            raise AgentNotAvailableError(str(e)) from e
        
        self._docker_available = self._check_docker()
        self._analysis_image = os.environ.get("PG_ANALYSIS_IMAGE", "protocolguard:latest")
        self._analysis_command = os.environ.get("PG_ANALYSIS_COMMAND", "static").split()

    def _check_docker(self) -> bool:
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError):
            return False

    def _run_analysis_container(self, workspace_dir: Path, job_identifier: str, progress_callback=None):
        if not self._docker_available:
            logger.debug("⚠️ Docker not available, skipping analysis container")
            return
        
        output_dir = self.settings.workspace_root.parent / "outputs" / job_identifier
        output_dir.mkdir(parents=True, exist_ok=True)
        
        config_dir = self.settings.workspace_root.parent / "configs" / job_identifier
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = workspace_dir / "config.toml"
        
        logger.debug("[*] Generating config.toml with correct paths for ProtocolGuard analysis")
        
        prepared_config = {
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
                "project_path": "/workspace/project/sol",
                "packet_related_callgraph_path": "/workspace/callgraph_report.txt",
                "function_arg_path": "/workspace/function_arg_summary.txt",
                "rule_path": "/workspace/inputs/rules.json",
                "protocol_name": os.environ.get("PG_PROTOCOL_NAME", "MQTT"),
                "protocol_version": os.environ.get("PG_PROTOCOL_VERSION", "5"),
                "project_name": os.environ.get("PG_PROJECT_NAME", "Sol"),
                "original_llvm_ir_path": "/workspace/program.ll",
                "build_command": "cmake -S . -B build -DCMAKE_C_COMPILER=gclang -DCMAKE_C_FLAGS='-g -Xclang -disable-O0-optnone -fno-discard-value-names' && cmake --build build -- VERBOSE=1",
                "build_log_path": "/workspace/build_log.txt",
                "binary_path": "/workspace/sol",
                "bitcode_path": "/workspace/program.bc",
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
        
        import toml
        with open(config_dir / "config.toml", "w", encoding="utf-8") as f:
            toml.dump(prepared_config, f)
        logger.debug(f"[*] Generated config.toml at {config_dir / 'config.toml'}")
        
        inputs_dir = workspace_dir / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        
        rules_path = inputs_dir / "rules.json"
        if not rules_path.exists():
            rule_config_path = workspace_dir / "rule_config.json"
            if rule_config_path.exists():
                shutil.copy2(rule_config_path, rules_path)
                logger.debug(f"[*] Copied rule_config.json to {rules_path}")
            else:
                logger.debug("⚠️ rules.json not found, skipping analysis container")
                return
        
        project_build_dir = workspace_dir / "project" / "sol" / "build"
        project_build_dir.mkdir(parents=True, exist_ok=True)
        
        workspace_build_log = workspace_dir / "build_log.txt"
        project_build_log = project_build_dir / "build_log.txt"
        
        if workspace_build_log.exists():
            shutil.copy2(workspace_build_log, project_build_log)
            logger.debug(f"[*] Copied build_log.txt to {project_build_log}")
        else:
            logger.debug("⚠️ build_log.txt not found in workspace, searching in project/build")
            if project_build_log.exists():
                logger.debug(f"[*] Found build_log.txt in project/build")
            else:
                logger.debug("⚠️ build_log.txt not found anywhere, creating empty file in workspace")
                with open(workspace_build_log, "w") as f:
                    f.write("Empty build log - build may have failed")
                shutil.copy2(workspace_build_log, project_build_log)
        
        project_dir = workspace_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        src_dir = project_dir / "sol" / "src"
        cf_files = list(src_dir.glob(".cf_*.json")) if src_dir.exists() else []
        
        if cf_files:
            logger.debug(f"[*] Found {len(cf_files)} .cf_*.json files from compiler.py output")
            for cf_file in cf_files[:5]:
                logger.debug(f"    - {cf_file.name}")
            if len(cf_files) > 5:
                logger.debug(f"    - ... and {len(cf_files) - 5} more")
        else:
            logger.debug(f"[*] No .cf_*.json files found from compiler.py, extracting sol.tar manually")
            tar_path = workspace_dir / "sol.tar"
            if tar_path.exists():
                with tarfile.open(tar_path, "r") as tar:
                    tar.extractall(project_dir)
                logger.debug(f"[*] sol.tar extracted successfully")
                
                cf_files = list(src_dir.glob(".cf_*.json")) if src_dir.exists() else []
                if cf_files:
                    logger.debug(f"[*] Found {len(cf_files)} .cf_*.json files after manual extraction")
                else:
                    logger.debug(f"⚠️ WARNING: No .cf_*.json files found in {src_dir}")
            else:
                logger.debug(f"⚠️ sol.tar not found at {tar_path}")
        
        logger.debug(f"\n{'='*60}")
        logger.debug("RUNNING PROTOCOL GUARD ANALYSIS")
        logger.debug(f"{'='*60}")
        logger.debug(f"[*] Analysis image: {self._analysis_image}")
        logger.debug(f"[*] Analysis command: {self._analysis_command}")
        logger.debug(f"[*] Workspace: {workspace_dir}")
        logger.debug(f"[*] Output: {output_dir}")
        logger.debug(f"[*] Config: {config_dir}")
        
        if progress_callback:
            progress_callback(job_identifier, "builder", "Starting builder container")
        
        command = [
            "docker", "run", "--rm",
            "-v", f"{workspace_dir}:/workspace",
            "-v", f"{output_dir}:/out",
            "-v", f"{config_dir}:/config",
            "--network=host",
        ]
        
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        
        command.extend(["-e", f"OPENAI_API_KEY={api_key}"])
        command.extend(["-e", f"OPENAI_BASE_URL={base_url}"])
        command.extend(["-e", f"ANTHROPIC_API_KEY={api_key}"])
        command.extend(["-e", f"ANTHROPIC_BASE_URL={base_url}"])
        logger.debug(f"[*] Passing OPENAI_API_KEY to container")
        logger.debug(f"[*] Passing OPENAI_BASE_URL to container")
        logger.debug(f"[*] Passing ANTHROPIC_API_KEY to container")
        logger.debug(f"[*] Passing ANTHROPIC_BASE_URL to container")
        
        command.extend([self._analysis_image, *self._analysis_command])
        
        logger.debug(f"[*] Command: {' '.join(command)}")
        
        log_file_path = workspace_dir / "analysis_log.txt"
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(workspace_dir)
            )
            
            log_lines = []
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
            
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                for line in iter(process.stdout.readline, ''):
                    line = line.rstrip()
                    log_lines.append(line)
                    log_file.write(line + "\n")
                    
                    logger.debug(f"[ANALYSIS] {line}")
                    
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
                
                logger.debug(f"[*] Copying analysis outputs from {output_dir} to {workspace_dir}")
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
                logger.debug(f"[*] Analysis outputs copied to workspace")
                
                db_in_workspace = workspace_dir / "database"
                if db_in_workspace.exists():
                    for db_file in db_in_workspace.glob("*.db"):
                        try:
                            db_file.chmod(0o644)
                        except Exception:
                            pass
                    logger.debug(f"[*] Set permissions on database files")
                
                logger.debug(f"[*] Final workspace contents:")
                for root, dirs, files in os.walk(workspace_dir):
                    level = root.replace(str(workspace_dir), '').count(os.sep)
                    indent = ' ' * 2 * level
                    logger.debug(f"{indent}{os.path.basename(root)}/")
                    subindent = ' ' * 2 * (level + 1)
                    for file in files[:10]:
                        file_path = Path(root) / file
                        if file_path.suffix == '.db':
                            logger.debug(f"{subindent}{file} (DATABASE)")
                        else:
                            logger.debug(f"{subindent}{file}")
            else:
                logger.debug("❌ ANALYSIS FAILED")
                logger.debug("[*] Analysis error log:")
                logger.debug("-" * 40)
                logger.debug("\n".join(log_lines[-40:]) if log_lines else "")
                logger.debug("-" * 40)
                
                logger.debug(f"[*] Copying analysis outputs from {output_dir} to {workspace_dir} (even on failure)")
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
                logger.debug(f"[*] Analysis outputs copied to workspace")
                
                ast_stderr_path = workspace_dir / "logs" / "ast_extraction.stderr"
                if ast_stderr_path.exists():
                    logger.debug("[*] AST extraction stderr content:")
                    logger.debug("-" * 40)
                    with open(ast_stderr_path, "r", encoding="utf-8", errors="ignore") as f:
                        logger.debug(f.read())
                    logger.debug("-" * 40)
                else:
                    logger.debug(f"[*] AST extraction stderr not found at {ast_stderr_path}")
                
                if progress_callback:
                    progress_callback(job_identifier, "error", f"Analysis failed with exit code {process.returncode}")
                
        except subprocess.TimeoutExpired:
            logger.debug("❌ ANALYSIS TIMEOUT")
            if progress_callback:
                progress_callback(job_identifier, "error", "Analysis timeout after 300 seconds")
        except Exception as e:
            logger.debug(f"❌ ANALYSIS EXCEPTION: {e}")
            if progress_callback:
                progress_callback(job_identifier, "error", str(e))

    def run_compilation(
        self,
        *,
        code_stream: BinaryIO,
        code_filename: str,
        config_stream: BinaryIO,
        config_filename: str,
        rules_stream: BinaryIO,
        rules_filename: str,
        notes: Optional[str] = None,
        protocol_name: Optional[str] = None,
        protocol_version: Optional[str] = None,
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> Dict[str, Any]:
        job_identifier = job_id or str(uuid.uuid4())
        
        if progress_callback:
            progress_callback(job_identifier, "init", "Preparing compiler inputs")
        
        workspace_dir = self.settings.workspace_root / job_identifier
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        code_bytes = code_stream.read()
        config_bytes = config_stream.read()
        rules_bytes = rules_stream.read()
        
        tar_path = workspace_dir / code_filename
        with open(tar_path, "wb") as f:
            f.write(code_bytes)
        
        config_content = config_bytes.decode("utf-8")
        rule_content = rules_bytes.decode("utf-8")
        
        inputs_dir = workspace_dir / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        rules_path = inputs_dir / "rules.json"
        with open(rules_path, "wb") as f:
            f.write(rules_bytes)
        
        if progress_callback:
            progress_callback(job_identifier, "compile", "Starting AI-assisted compilation")
        
        dockerfile = self.compiler.run(
            sol_tar=str(tar_path),
            config_content=config_content,
            rule_content=rule_content,
            output_dir=str(workspace_dir)
        )
        
        if dockerfile is None:
            bug_path = workspace_dir / "bug.txt"
            error_details = ""
            if bug_path.exists():
                with open(bug_path, "r") as f:
                    error_details = f.read()
            raise AgentExecutionError(
                f"Compilation failed after timeout ({self.settings.max_runtime}s)",
                logs=[],
                details={"workspace": str(workspace_dir), "error": error_details}
            )
        
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dockerfile_path = os.path.join(current_dir, "Dockerfile.txt")
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile)
        logger.debug(f"[*] Saved generated Dockerfile to {dockerfile_path}")
        
        project_dir = workspace_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        tar_path = workspace_dir / code_filename
        if tar_path.exists():
            import tarfile
            with tarfile.open(tar_path, "r:*") as tar:
                tar.extractall(project_dir)
            logger.debug(f"[*] Pre-extracted sol.tar to {project_dir}")
            
            cf_files = list(project_dir.rglob(".cf_*.json"))
            if cf_files:
                logger.debug(f"[*] Found {len(cf_files)} .cf_*.json files after pre-extraction")
                for cf_file in cf_files[:5]:
                    logger.debug(f"    - {cf_file.relative_to(project_dir)}")
                if len(cf_files) > 5:
                    logger.debug(f"    - ... and {len(cf_files) - 5} more")
            else:
                logger.debug(f"⚠️ WARNING: No .cf_*.json files found in {project_dir}")
        else:
            logger.debug(f"⚠️ sol.tar not found at {tar_path}")
        
        self._run_analysis_container(workspace_dir, job_identifier, progress_callback)
        
        bitcode_path = workspace_dir / "program.bc"
        build_log_path = workspace_dir / "build_log.txt"
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
        
        for db_candidate in [
            workspace_dir / "database" / "rule_code_snippet.db",
            workspace_dir / "database" / "analysis.db",
            workspace_dir / "database" / "protocolguard.db",
            workspace_dir / "project" / "sol" / "build" / "rule_code_snippet.db",
            workspace_dir / "project" / "sol" / "build" / "analysis.db",
            workspace_dir / "project" / "sol" / "build" / "protocolguard.db",
        ]:
            if db_candidate.exists() and _validate_db(db_candidate):
                database_path = str(db_candidate)
                logger.debug(f"[*] Found valid database file: {database_path}")
                break
        
        if database_path is None:
            for ext in [".db", ".sqlite"]:
                for path in workspace_dir.rglob(f"*{ext}"):
                    if _validate_db(path):
                        database_path = str(path)
                        logger.debug(f"[*] Found valid database file (search): {database_path}")
                        break
                if database_path:
                    break
        
        if database_path is None:
            for ext in [".db", ".sqlite"]:
                for path in workspace_dir.rglob(f"*{ext}"):
                    filename = path.name.lower()
                    if any(name in filename for name in standard_names):
                        database_path = str(path)
                        logger.debug(f"[*] Found database file by name (no validation): {database_path}")
                        break
                    elif "sqlite" in filename or "sol" in filename:
                        database_path = str(path)
                        logger.debug(f"[*] Found database file (fallback): {database_path}")
                        break
                if database_path:
                    break
        
        if database_path is None:
            database_dir = workspace_dir / "database"
            if database_dir.exists():
                for db_file in database_dir.glob("*.db"):
                    if _validate_db(db_file):
                        database_path = str(db_file)
                        logger.debug(f"[*] Found valid database in database dir: {database_path}")
                        break
            
            if database_path is None and database_dir.exists():
                for db_file in database_dir.glob("*.db"):
                    database_path = str(db_file)
                    logger.debug(f"[*] Using database file in database dir: {database_path}")
                    break
                
                if database_path is None:
                    logger.debug(f"[*] No database file found in database dir: {database_dir}")
            else:
                build_dir = workspace_dir / "project" / "sol" / "build"
                if build_dir.exists():
                    for db_file in build_dir.glob("*.db"):
                        if _validate_db(db_file):
                            database_path = str(db_file)
                            logger.debug(f"[*] Found valid database in build dir: {database_path}")
                            break
                
                if database_path is None and build_dir.exists():
                    for db_file in build_dir.glob("*.db"):
                        database_path = str(db_file)
                        logger.debug(f"[*] Using database file in build dir: {database_path}")
                        break
                
                if database_path is None:
                    database_path = str(workspace_dir / "database" / "rule_code_snippet.db")
                    logger.debug(f"[*] Using fallback database path: {database_path}")
        
        db_path_for_findings = database_path if (database_path and Path(database_path).is_file()) else None
        
        findings, summary_counts = self._extract_findings(
            db_path_for_findings,
            protocol_name or "unknown",
            protocol_version or "unknown",
        )
        overall_status = self._determine_overall_status(summary_counts)
        
        logger.debug(f"[*] Extracted {len(findings)} findings from database")
        logger.debug(f"[*] Summary counts: {summary_counts}")
        logger.debug(f"[*] Overall status: {overall_status}")
        
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
                "configFileName": config_filename,
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
