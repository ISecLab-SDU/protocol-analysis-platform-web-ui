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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Sequence, Tuple
from openai import OpenAI

from protocol_compliance.job_logging import JobStageLogger

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
    builder_image: str

    @classmethod
    def from_env(cls) -> "AgentExecutorSettings":
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


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
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

        import json
        config_str = str(config) if not isinstance(config, str) else config
        rule_str = json.dumps(rule, indent=2) if isinstance(rule, dict) else str(rule)

        prompt = f"""
You are an expert DevOps engineer specializing in protocol compliance analysis.

Your task is to create a Dockerfile that rebuilds a pre-compiled project using gclang and extracts LLVM bitcode.

The sol.tar contains pre-compiled artifacts including .cf_*.json AST files. Do NOT modify or recreate these files.

========================
AVAILABLE FILES
========================
- sol.tar (pre-compiled source code archive with .cf_*.json AST files)
- config.toml (analysis configuration file - READ THIS CAREFULLY)
- rule_config.json (rule configuration)

========================
sol.tar CONTENTS
========================
{structure}

========================
config.toml CONTENT
========================
{config_str}

========================
rule_config.json CONTENT
========================
{rule_str}

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
1. Extract sol.tar to /workspace/project/
2. Note: /workspace/project/sol/ contains pre-compiled artifacts including .cf_*.json files
3. Removes and recreates /workspace/project/sol/build ONLY (keep src/ directory intact)
4. Runs cmake from /workspace/project/sol/build with:
   - DCMAKE_C_COMPILER=gclang
   - DCMAKE_CXX_COMPILER=gclang++
   - DCMAKE_BUILD_TYPE=Debug
   - DCMAKE_C_FLAGS_DEBUG="-g -O0 -Xclang -disable-O0-optnone -fno-discard-value-names"
   - DCMAKE_CXX_FLAGS_DEBUG="-g -O0 -Xclang -disable-O0-optnone -fno-discard-value-names"
-  - DCMAKE_VERBOSE_MAKEFILE=ON
5. Runs make with CC=gclang and CFLAGS="-g -Xclang -disable-O0-optnone -fno-discard-value-names", output to build_log.txt
6. Runs get-bc ./sol to extract bitcode
7. Copies sol.bc to program.bc
8. Runs llvm-dis-14 program.bc -o program.ll

CRITICAL POST-BUILD STEPS:
1. Copy all build artifacts to /workspace/:
   - cp /workspace/project/sol/build/* /workspace
   - cp /workspace/project/sol/build/sol /workspace/
   - cp /workspace/project/sol/build/sol.bc /workspace/
   - cp /workspace/project/sol/build/sol.bc /workspace/program.bc
   - llvm-dis-14 /workspace/program.bc -o /workspace/program.ll
   - cp /workspace/project/sol/build/build_log.txt /workspace/

2. Copy configuration files:
   - mkdir -p /workspace/inputs
   - cp /workspace/rule_config.json /workspace/inputs/rules.json
   - cp /workspace/config.toml /workspace/inputs/config.toml

3. LLVM PRODUCTS TO src/ DIRECTORY:
   - Copy ALL .cf_*.json files from build directory to /workspace/project/sol/src/
   - cp /workspace/project/sol/build/*.cf_*.json /workspace/project/sol/src/ 2>/dev/null || true
   - Ensure .cf_ref.json is present in /workspace/project/sol/src/
   - If .cf_ref.json doesn't exist in build/, copy it from /workspace/project/sol/src/ backup if available

4. IMPORTANT: Preserve all .cf_*.json files in /workspace/project/sol/src/
   - These files are LLVM AST extraction products and required for analysis

OUTPUT VERIFICATION:
Before exiting, run:
- ls -la /workspace/project/sol/src/*.cf_*.json
- ls -la /workspace/project/sol/src/*.json
- ls -la /workspace/

Use COPY to bring sol.tar, config.toml and rule_config.json from the build context into /workspace/.
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

        content = resp.choices[0].message.content
        if content is None:
            raise AgentExecutionError("LLM response did not include Dockerfile content")
        return self._clean(content)


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
                    logs_result = subprocess.run(
                        ["docker", "logs", container_id],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    logs_stdout = logs_result.stdout
                    logs_stderr = logs_result.stderr

                    inspect_result = subprocess.run(
                        ["docker", "inspect", container_id],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    return False, f"Container exited with code {exit_code}\nSTDOUT:\n{logs_stdout}\nSTDERR:\n{logs_stderr}\nINSPECT:\n{inspect_result.stdout[:500]}"

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

    def run(
        self,
        sol_tar,
        config_content,
        rule_content,
        output_dir,
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ):
        job_logger = JobStageLogger(
            job_id=job_id or "compiler",
            logger=logger,
            progress_callback=progress_callback if job_id else None,
        )
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
        logger.debug("[*] Build context: %s", build_context)
        job_logger.info(
            "Prepared AI compiler build context",
            stage="compile",
            build_context=build_context,
            input_archive=sol_tar,
            output_dir=output_dir,
            structure_entries=len(structure.splitlines()),
        )

        while True:
            i += 1
            elapsed_seconds = time.time() - start_time
            logger.debug("\n%s", "=" * 60)
            logger.debug("ROUND %d", i)
            logger.debug("%s", "=" * 60)

            if elapsed_seconds > self.max_runtime:
                logger.debug("❌ TIME LIMIT REACHED")
                job_logger.error(
                    "AI compiler loop reached time limit after %.1f seconds",
                    elapsed_seconds,
                    stage="compile",
                    round=i,
                    elapsed_seconds=round(elapsed_seconds, 3),
                    max_runtime_seconds=self.max_runtime,
                    frontend_message="AI compiler loop reached time limit",
                )
                break

            logger.debug("[*] Generating Dockerfile with AI...")
            job_logger.info(
                "Round %d: generating Dockerfile with AI",
                i,
                stage="compile",
                round=i,
                elapsed_seconds=round(elapsed_seconds, 3),
            )
            dockerfile = self.llm.generate(
                config=config,
                rule=rule,
                structure=structure,
                error_log=error_log,
                last_dockerfile=last_dockerfile
            )
            job_logger.info(
                "Round %d: generated Dockerfile",
                i,
                stage="compile",
                round=i,
                dockerfile_chars=len(dockerfile),
                had_previous_error=bool(error_log),
            )
            logger.debug("[*] Generated Dockerfile:")
            logger.debug("-" * 40)
            logger.debug(dockerfile[:1000] + "..." if len(dockerfile) > 1000 else dockerfile)
            logger.debug("-" * 40)

            logger.debug("[*] Building Docker image: build-%d", i)
            logger.debug("[*] Build context: %s", build_context)
            image_tag = f"build-{i}"
            job_logger.info(
                "Round %d: building generated Dockerfile",
                i,
                stage="compile",
                round=i,
                image_tag=image_tag,
                build_context=build_context,
            )

            ok, log = self.docker.build("-", tag=image_tag, dockerfile_content=dockerfile, build_context=build_context)

            if ok:
                logger.debug("🎉 BUILD SUCCESS")
                job_logger.info(
                    "Round %d: Docker image build succeeded",
                    i,
                    stage="compile",
                    round=i,
                    image_tag=image_tag,
                    build_log_chars=len(log),
                )
                logger.debug("[*] Build log:")
                logger.debug("-" * 40)
                logger.debug(log[-3000:] if len(log) > 3000 else log)
                logger.debug("-" * 40)

                logger.debug("[+] Checking /workspace directory...")
                job_logger.info(
                    "Round %d: validating builder output",
                    i,
                    stage="compile",
                    round=i,
                    image_tag=image_tag,
                )

                output_ok, output_log = self.docker.check_output(image_tag)

                if output_ok:
                    logger.debug("✅ OUTPUT VALIDATED")
                    logger.debug(output_log)
                    job_logger.info(
                        "Round %d: builder output validated",
                        i,
                        stage="compile",
                        round=i,
                        image_tag=image_tag,
                        output_log_chars=len(output_log),
                    )

                    logger.debug("[+] Copying output to %s...", output_dir)
                    job_logger.info(
                        "Round %d: copying builder output",
                        i,
                        stage="compile",
                        round=i,
                        image_tag=image_tag,
                        output_dir=output_dir,
                    )
                    copy_ok, copy_log = self.docker.copy_output(image_tag, output_dir)

                    if copy_ok:
                        logger.debug("✅ OUTPUT COPIED")
                        logger.debug(copy_log)
                        job_logger.info(
                            "Round %d: builder output copied",
                            i,
                            stage="compile",
                            round=i,
                            image_tag=image_tag,
                            output_dir=output_dir,
                            copy_log_chars=len(copy_log),
                        )
                    else:
                        logger.debug("❌ FAILED TO COPY OUTPUT")
                        logger.debug(copy_log)
                        job_logger.warning(
                            "Round %d: failed to copy builder output",
                            i,
                            stage="compile",
                            round=i,
                            image_tag=image_tag,
                            output_dir=output_dir,
                            copy_log_tail=copy_log[-1000:],
                        )

                    logger.debug("Success")
                    return dockerfile
                else:
                    logger.debug("❌ OUTPUT INVALID")
                    logger.debug("-" * 40)
                    logger.debug(output_log)
                    logger.debug("-" * 40)
                    last_dockerfile = dockerfile
                    error_log = f"BUILD_SUCCESS_BUT_OUTPUT_INVALID\n{output_log}"
                    job_logger.warning(
                        "Round %d: builder output validation failed",
                        i,
                        stage="compile",
                        round=i,
                        image_tag=image_tag,
                        output_log_tail=output_log[-1000:],
                    )
                    continue

            logger.debug("❌ BUILD FAILED")
            job_logger.warning(
                "Round %d: Docker image build failed",
                i,
                stage="compile",
                round=i,
                image_tag=image_tag,
                build_log_tail=log[-1000:],
            )
            logger.debug("[*] Build error log:")
            logger.debug("-" * 40)
            logger.debug(log[-3000:] if len(log) > 3000 else log)
            logger.debug("-" * 40)

            last_dockerfile = dockerfile
            error_log = log

        logger.debug("💥 FAILED AFTER TIME LIMIT")
        job_logger.error(
            "AI compiler loop failed after %.1f seconds",
            time.time() - start_time,
            stage="compile",
            elapsed_seconds=round(time.time() - start_time, 3),
            max_runtime_seconds=self.max_runtime,
            frontend_message="AI compiler loop failed after time limit",
        )

        bug_report = f"""==== FINAL ERROR LOG ====\n\n{error_log or ""}\n\n==== LAST DOCKERFILE ====\n{last_dockerfile or ""}\n\n==== STRUCTURE ====\n{structure}\n\n==== CONFIG ====\n{config}\n\n==== RULE ====\n{json.dumps(rule, indent=2)}"""

        bug_path = os.path.join(output_dir, "bug.txt")
        with open(bug_path, "w") as f:
            f.write(bug_report)
        job_logger.info(
            "Wrote AI compiler failure report",
            stage="compile",
            bug_report_path=bug_path,
            emit_progress=False,
        )

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
            raise AgentExecutionError(f"Failed to start command: {exc}") from exc

        if process.stdout is None:
            raise AgentExecutionError("Command did not expose stdout")

        lines: List[str] = []
        with log_path.open("a", encoding="utf-8") as log_file:
            for raw_line in iter(process.stdout.readline, ""):
                line = raw_line.rstrip()
                lines.append(line)
                log_file.write(line + "\n")
                if line:
                    progress_stage = stage_selector(line, stage) if stage_selector else stage
                    logger.debug("[%s] %s", progress_stage.upper(), line)
                    if progress_callback:
                        progress_callback(job_identifier, progress_stage, line[:500])

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            raise AgentExecutionError(
                f"{stage} command timed out after {timeout} seconds",
                logs=lines,
                details={"command": list(command), "workspace": str(cwd)},
            ) from exc

        if process.returncode != 0:
            raise AgentExecutionError(
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
            raise AgentNotAvailableError("Docker is required for the Claude builder compiler")

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
            raise AgentExecutionError(
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
        resolved_project = project_name or os.environ.get("PG_PROJECT_NAME", "Sol")
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
                "project_path": "/workspace/project/sol",
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
        bitcode_path = self._first_existing(
            workspace_dir,
            [
                "program.bc",
                "sol.bc",
                "project/sol/build/sol.bc",
            ],
        ) or self._find_workspace_file(
            workspace_dir,
            suffixes=(".bc",),
            exclude_suffixes=("_ssa.bc",),
        ) or (workspace_dir / "program.bc")
        original_ir_path = self._first_existing(
            workspace_dir,
            [
                "program.ll",
                "project/sol/build/sol.ll",
            ],
        ) or self._find_workspace_file(workspace_dir, suffixes=(".ll",)) or bitcode_path
        build_log_path = self._first_existing(
            workspace_dir,
            [
                "build_log.txt",
                "project/sol/build/build_log.txt",
            ],
        ) or self._find_workspace_file(workspace_dir, suffixes=("build_log.txt",)) or (
            workspace_dir / "build_log.txt"
        )
        bitcode_binary = bitcode_path.with_suffix("")
        binary_path = self._first_existing(
            workspace_dir,
            [
                "program",
                "sol",
                "project/sol/build/sol",
            ],
        ) or (bitcode_binary if bitcode_binary.exists() else workspace_dir / "program")

        resolved_protocol = protocol_name or os.environ.get("PG_PROTOCOL_NAME", "MQTT")
        resolved_version = protocol_version or os.environ.get("PG_PROTOCOL_VERSION", "3.1.1")
        resolved_project = project_name or os.environ.get("PG_PROJECT_NAME", "Sol")

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
        progress_callback=None,
        *,
        protocol_name: Optional[str] = None,
        protocol_version: Optional[str] = None,
        project_name: Optional[str] = None,
    ):
        if not self._docker_available:
            logger.debug("⚠️ Docker not available, skipping analysis container")
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

        project_build_dir = workspace_dir / "project" / "sol" / "build"
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

        src_dir = project_dir / "sol" / "src"
        cf_files = list(src_dir.glob(".cf_*.json")) if src_dir.exists() else []

        if cf_files:
            logger.debug("[*] Found %d .cf_*.json files from compiler.py output", len(cf_files))
            for cf_file in cf_files[:5]:
                logger.debug("    - %s", cf_file.name)
            if len(cf_files) > 5:
                logger.debug("    - ... and %d more", len(cf_files) - 5)
        else:
            logger.debug("[*] No .cf_*.json files found from compiler.py, extracting sol.tar manually")
            tar_path = workspace_dir / "sol.tar"
            if tar_path.exists():
                with tarfile.open(tar_path, "r") as tar:
                    tar.extractall(project_dir)
                logger.debug("[*] sol.tar extracted successfully")

                cf_files = list(src_dir.glob(".cf_*.json")) if src_dir.exists() else []
                if cf_files:
                    logger.debug("[*] Found %d .cf_*.json files after manual extraction", len(cf_files))
                else:
                    logger.warning("No .cf_*.json files found in %s", src_dir)
            else:
                logger.warning("sol.tar not found at %s", tar_path)

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

        log_file_path = workspace_dir / "analysis_log.txt"

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(workspace_dir)
            )
            if process.stdout is None:
                raise AgentExecutionError("Analysis container did not expose stdout")

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

                    logger.debug("[ANALYSIS] %s", line)

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
                    build_dir = workspace_dir / "project" / "sol" / "build"
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

        except subprocess.TimeoutExpired:
            logger.debug("❌ ANALYSIS TIMEOUT")
            if progress_callback:
                progress_callback(job_identifier, "error", "Analysis timeout after 300 seconds")
        except Exception as e:
            logger.exception("Analysis execution raised an exception")
            if progress_callback:
                progress_callback(job_identifier, "error", str(e))

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

        tar_path = workspace_dir / code_filename
        with open(tar_path, "wb") as f:
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

        project_dir = workspace_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)

        tar_path = workspace_dir / code_filename
        if tar_path.exists():
            import tarfile
            with tarfile.open(tar_path, "r:*") as tar:
                tar.extractall(project_dir)
            logger.debug("[*] Pre-extracted sol.tar to %s", project_dir)

            cf_files = list(project_dir.rglob(".cf_*.json"))
            if cf_files:
                logger.debug("[*] Found %d .cf_*.json files after pre-extraction", len(cf_files))
                for cf_file in cf_files[:5]:
                    logger.debug("    - %s", cf_file.relative_to(project_dir))
                if len(cf_files) > 5:
                    logger.debug("    - ... and %d more", len(cf_files) - 5)
            else:
                logger.warning("No .cf_*.json files found in %s", project_dir)
        else:
                logger.warning("sol.tar not found at %s", tar_path)

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
                    elif "sqlite" in filename or "sol" in filename:
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
                build_dir = workspace_dir / "project" / "sol" / "build"
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
