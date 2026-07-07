"""Auto-generate Dockerfile from source code archive, config, and rules."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional

from openai import OpenAI

LOGGER = logging.getLogger(__name__)


class LLMClient:
    """LLM client for Dockerfile generation."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        api_key = api_key or os.environ.get("OPENAI_API_KEY", "sk-7GHq4pK8H4BS4nlDXCUQvYKAmJWh4ox9Bj2oB9ihHcUUjfZb")
        base_url = base_url or os.environ.get("OPENAI_BASE_URL", "http://10.102.32.6:47860/v1")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for compiler")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = os.environ.get("COMPILER_MODEL", "qwen3.7-plus")

    def _clean(self, text: str) -> str:
        m = re.search(r"```(?:\w*)\n(.*?)```", text, re.DOTALL)
        return m.group(1).strip() if m else text.strip()

    def generate(
        self,
        config: str,
        rule: dict,
        structure: str,
        error_log: Optional[str] = None,
        last_dockerfile: Optional[str] = None,
    ) -> str:
        error_block = ""
        if error_log:
            error_block = f"""
## ❌ BUILD ERROR
{error_log[-4000:]}

## LAST FAILED DOCKERFILE
{last_dockerfile}
"""

        prompt = f"""
You are an expert DevOps + system builder.

Generate a WORKING Dockerfile for ANY software/protocol project.

========================
INPUT 1: Source Code Structure
========================
{structure}

========================
INPUT 2: config.toml
========================
{config}

========================
INPUT 3: rule_config.json
========================
{json.dumps(rule, indent=2)}

========================
FILE STRUCTURE IN BUILD CONTEXT
========================
The Docker build context contains these files at the ROOT level:
- config.toml (analysis configuration)
- inputs/rules.json (protocol rules)
- Source code archive (like sol.tar or extracted source directory)

========================
REQUIREMENTS
========================
- ubuntu:22.04 base image
- COPY config.toml to /workspace/config.toml
- COPY inputs/rules.json to /workspace/inputs/rules.json
- build project successfully
- output ALL artifacts to /workspace
- detect build system automatically (cmake/make/go/python)
- do NOT assume fixed structure
- If source is provided as a tar archive (like sol.tar), extract it first
- Set WORKDIR to appropriate build directory
- Final build artifacts should be in /workspace/project/<name>/build/

========================
EXAMPLE DOCKERFILE STRUCTURE
========================
```dockerfile
FROM ubuntu:22.04 AS builder
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ... && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY config.toml /workspace/config.toml
COPY inputs/rules.json /workspace/inputs/rules.json

# Extract source archive if needed
COPY sol.tar /workspace/sol.tar
RUN tar -xf sol.tar -C /workspace

# Build project
WORKDIR /workspace/project/<project_name>
RUN cmake -S . -B build ... && cmake --build build

# Output artifacts
RUN cp /workspace/project/<project_name>/build/*.bc /workspace/
```

========================
SELF-HEAL MODE
========================
{error_block}

If failed:
- fix root cause only
- minimal change preferred

========================
OUTPUT
========================
Return ONLY Dockerfile content
"""

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You generate robust Docker build environments."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=4096,
        )

        return self._clean(resp.choices[0].message.content)


class DockerTester:
    """Docker build tester."""

    def __init__(self, timeout: int = 300):
        self.timeout = timeout

    def build(self, dockerfile_content: str, tag: str, context_dir: Path) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                ["docker", "build", "-f", "-", "-t", tag, "."],
                input=dockerfile_content,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(context_dir),
            )
            log = (r.stdout or "") + "\n" + (r.stderr or "")
            return r.returncode == 0, log
        except Exception as e:
            return False, str(e)


class CompilerController:
    """Controller for auto-generating Dockerfile."""

    def __init__(
        self,
        max_runtime: int = 3600,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.llm = LLMClient(api_key=api_key, base_url=base_url)
        self.docker = DockerTester()
        self.max_runtime = max_runtime

    def parse_tar(self, tar_data: bytes) -> str:
        with tarfile.open(fileobj=BytesIO(tar_data)) as tar:
            return "\n".join([m.name for m in tar.getmembers()])

    def _create_build_context(self, code_data: bytes, config_data: bytes, rules_data: bytes) -> Path:
        context_dir = Path(tempfile.mkdtemp(prefix="protocolguard-compiler-"))
        
        (context_dir / "inputs").mkdir(parents=True, exist_ok=True)
        
        code_filename = "sol.tar"
        code_path = context_dir / code_filename
        with open(code_path, "wb") as f:
            f.write(code_data)
        
        config_path = context_dir / "config.toml"
        with open(config_path, "wb") as f:
            f.write(config_data)
        
        rules_path = context_dir / "inputs" / "rules.json"
        with open(rules_path, "wb") as f:
            f.write(rules_data)
        
        LOGGER.debug(f"Created build context at {context_dir} with files: sol.tar, config.toml, inputs/rules.json")
        return context_dir

    def run(
        self,
        code_data: bytes,
        config_data: bytes,
        rules_data: bytes,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> str:
        config = config_data.decode("utf-8")
        rule = json.loads(rules_data.decode("utf-8"))
        structure = self.parse_tar(code_data)

        context_dir = self._create_build_context(code_data, config_data, rules_data)

        last_dockerfile = None
        error_log = None

        start_time = time.time()
        i = 0

        LOGGER.info("Starting Dockerfile auto-generation loop")

        try:
            while True:
                i += 1
                LOGGER.info(f"Round {i} of Dockerfile generation")

                if time.time() - start_time > self.max_runtime:
                    LOGGER.error("Dockerfile generation timeout reached")
                    raise RuntimeError("Dockerfile generation timeout reached")

                if progress_callback:
                    progress_callback("compiler", f"Generating Dockerfile (round {i})")

                dockerfile = self.llm.generate(
                    config=config,
                    rule=rule,
                    structure=structure,
                    error_log=error_log,
                    last_dockerfile=last_dockerfile,
                )

                LOGGER.info(f"Building Docker image (round {i})")
                ok, log = self.docker.build(dockerfile, tag=f"protocolguard-build-{i}", context_dir=context_dir)

                if ok:
                    LOGGER.info("Dockerfile generation successful")
                    if progress_callback:
                        progress_callback("compiler", "Dockerfile generation successful")
                    return dockerfile

                LOGGER.warning(f"Docker build failed (round {i}): {log[-500:]}")
                if progress_callback:
                    progress_callback("compiler", f"Docker build failed, retrying (round {i})")

                last_dockerfile = dockerfile
                error_log = log
        finally:
            shutil.rmtree(context_dir, ignore_errors=True)
            LOGGER.debug(f"Cleaned up build context at {context_dir}")

        raise RuntimeError("Dockerfile generation failed after timeout")
