import os
import json
import re
import tarfile
import subprocess
import time
from openai import OpenAI


# =========================
# 🧠 LLM CLIENT (DeepSeek)
# =========================
class LLMClient:

    def __init__(self):

        self.client = OpenAI(
            api_key="sk-ws-H.RXPLPYI.MArk.MEQCIGW0ofo65Q7_P0sq1rjf4UF716X5V44XwvtI7NHIdv5PAiBdtdg8-nhAt5o9JPSfG9OwgwBwwDz66SMFeFmLhnGblQ",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        self.model = "qwen3.7-plus"

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
You are an expert DevOps + system builder for program analysis.

Your task is to build the project using gclang (Google LLVM compiler) and extract LLVM bitcode artifacts.

========================
AVAILABLE FILES IN BUILD CONTEXT
========================
- sol.tar (source code archive)
- config.toml (project configuration)
- rule_config.json (rule configuration)

========================
sol.tar CONTENTS
========================
{structure}

========================
config.toml
========================
{config}

========================
rule_config.json
========================
{json.dumps(rule, indent=2)}

========================
REQUIREMENTS
========================
- Base image: ubuntu:22.04
- Install: git, build-essential, cmake, llvm-14, clang-14, libclang-14-dev, llvm-14-dev, golang-1.18-go
- Install gllvm (go install github.com/SRI-CSL/gllvm/cmd/...@latest)
- Set CC=gclang, CXX=gclang++
- Build the project with cmake using gclang compiler
- Capture build output to build_log.txt
- Use get-bc to extract LLVM bitcode from the compiled binary
- Use llvm-dis-14 to disassemble bitcode to LLVM IR text

========================
OUTPUT FILES IN /output
========================
The /output directory MUST contain these exact files:
1. sol - the compiled executable binary
2. sol.bc - LLVM bitcode file (extracted using get-bc)
3. program.bc - copy of sol.bc
4. program.ll - LLVM IR text (disassembled from program.bc)
5. build_log.txt - compilation log

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


# =========================
# 🐳 DOCKER TESTER
# =========================
class DockerTester:

    def __init__(self, timeout=300):
        self.timeout = timeout

    def build(self, dockerfile_path, tag, dockerfile_content=None):

        try:
            if dockerfile_content is not None:
                r = subprocess.run(
                    ["docker", "build", "-f", dockerfile_path, "-t", tag, "."],
                    input=dockerfile_content,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
            else:
                r = subprocess.run(
                    ["docker", "build", "-f", dockerfile_path, "-t", tag, "."],
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
                ["docker", "run", "--rm", tag, "ls", "-la", "/output"],
                capture_output=True,
                text=True,
                timeout=60
            )

            log = (r.stdout or "") + "\n" + (r.stderr or "")

            if r.returncode != 0:
                return False, f"Failed to check /output: {log}"

            missing_files = []
            for f in required_files:
                if f not in log:
                    missing_files.append(f)

            if missing_files:
                return False, f"Missing required files: {', '.join(missing_files)}\n/output contents:\n{log}"

            return True, f"/output contains all required files:\n{log}"

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
                r = subprocess.run(
                    ["docker", "cp", f"{container_id}:/output/.", dest_path],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if r.returncode != 0:
                    return False, f"Failed to copy output: {r.stderr}"

                return True, f"Output copied to {dest_path}"

            finally:
                subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, timeout=30)

        except Exception as e:
            return False, f"Error copying output: {str(e)}"


# =========================
# 🧠 CONTROLLER
# =========================
class CompilerController:

    def __init__(self, max_runtime=3600):
        self.llm = LLMClient()
        self.docker = DockerTester()
        self.max_runtime = max_runtime

    # -------------------------
    def load(self, config_path, rule_path):
        with open(config_path) as f:
            config = f.read()
        with open(rule_path) as f:
            rule = json.load(f)
        return config, rule

    # -------------------------
    def parse_tar(self, tar_path):
        with tarfile.open(tar_path) as tar:
            return "\n".join([m.name for m in tar.getmembers()])

    # -------------------------
    def write(self, content, path):
        with open(path, "w") as f:
            f.write(content)

    # =========================
    # 🚀 MAIN LOOP (FIXED)
    # =========================
    def run(self, sol_tar, config_path, rule_path):

        config, rule = self.load(config_path, rule_path)
        structure = self.parse_tar(sol_tar)

        last_dockerfile = None
        error_log = None

        start_time = time.time()
        i = 0

        print("🚀 START SELF-HEALING DOCKER LOOP")

        while True:

            i += 1
            print(f"\n========== ROUND {i} ==========")

            # ⛔ timeout protection
            if time.time() - start_time > self.max_runtime:
                print("❌ TIME LIMIT REACHED")
                break

            # =========================
            # 🧠 generate dockerfile
            # =========================
            dockerfile = self.llm.generate(
                config=config,
                rule=rule,
                structure=structure,
                error_log=error_log,
                last_dockerfile=last_dockerfile
            )

            print("[+] building docker...")

            ok, log = self.docker.build("-", tag=f"build-{i}", dockerfile_content=dockerfile)

            # =========================
            # ✅ BUILD SUCCESS - CHECK OUTPUT
            # =========================
            if ok:
                print("🎉 BUILD SUCCESS")
                print("[+] Checking /output directory...")

                output_ok, output_log = self.docker.check_output(f"build-{i}")

                if output_ok:
                    print("✅ OUTPUT VALIDATED")
                    print(output_log)

                    self.write(dockerfile, "Dockerfile")

                    with open("build_log.txt", "w") as f:
                        f.write(log)

                    output_dir = os.path.join(os.path.dirname(os.path.abspath(config_path)), "output")
                    print(f"[+] Copying output to {output_dir}...")
                    copy_ok, copy_log = self.docker.copy_output(f"build-{i}", output_dir)

                    if copy_ok:
                        print("✅ OUTPUT COPIED")
                        print(copy_log)
                    else:
                        print("❌ FAILED TO COPY OUTPUT")
                        print(copy_log)

                    return dockerfile
                else:
                    print("❌ OUTPUT INVALID -", output_log)
                    last_dockerfile = dockerfile
                    error_log = f"BUILD_SUCCESS_BUT_OUTPUT_EMPTY\n{output_log}"
                    continue

            # =========================
            # ❌ BUILD FAILURE
            # =========================
            print("❌ BUILD FAILED")

            last_dockerfile = dockerfile
            error_log = log
        # =========================
        # FINAL BUG REPORT
        # =========================
        print("💥 FAILED AFTER TIME LIMIT")

        with open("bug.txt", "w") as f:
            f.write("==== FINAL ERROR LOG ====\n\n")
            f.write(error_log or "")
            f.write("\n\n==== LAST DOCKERFILE ====\n")
            f.write(last_dockerfile or "")
            f.write("\n\n==== STRUCTURE ====\n")
            f.write(structure)
            f.write("\n\n==== CONFIG ====\n")
            f.write(config)
            f.write("\n\n==== RULE ====\n")
            f.write(json.dumps(rule, indent=2))


# =========================
# ENTRY
# =========================
if __name__ == "__main__":

    controller = CompilerController(max_runtime=3600)

    controller.run(
        sol_tar="sol.tar",
        config_path="config.toml",
        rule_path="rule_config.json"
    )
