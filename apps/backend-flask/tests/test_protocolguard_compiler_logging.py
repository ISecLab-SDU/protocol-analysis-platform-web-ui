from __future__ import annotations

import sys
import tarfile
from pathlib import Path
from typing import Any, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance.compiler import CompilerController  # noqa: E402


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        *,
        config: str,
        rule: dict[str, Any],
        structure: str,
        error_log: str | None = None,
        last_dockerfile: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "config": config,
                "rule": rule,
                "structure": structure,
                "error_log": error_log,
                "last_dockerfile": last_dockerfile,
            }
        )
        return "FROM scratch\n"


class FakeDocker:
    def __init__(self) -> None:
        self.build_calls: list[tuple[str, str]] = []
        self.check_calls: list[str] = []
        self.copy_calls: list[tuple[str, str]] = []

    def build(
        self,
        _path: str,
        *,
        tag: str,
        dockerfile_content: str,
        build_context: str,
    ) -> tuple[bool, str]:
        self.build_calls.append((tag, build_context))
        return True, "build ok"

    def check_output(self, image_tag: str) -> tuple[bool, str]:
        self.check_calls.append(image_tag)
        return True, "workspace ok"

    def copy_output(self, image_tag: str, dest_path: str) -> tuple[bool, str]:
        self.copy_calls.append((image_tag, dest_path))
        return True, "copy ok"


def _controller() -> CompilerController:
    controller = cast(Any, CompilerController.__new__(CompilerController))
    controller.llm = FakeLLM()
    controller.docker = FakeDocker()
    controller.max_runtime = 60
    return cast(CompilerController, controller)


def _tar_file(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    tar_path = tmp_path / "sol.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(source / "main.c", arcname="main.c")
    return tar_path


def test_compiler_controller_reports_ai_compilation_progress(tmp_path: Path) -> None:
    controller = _controller()
    tar_path = _tar_file(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    events: list[tuple[str, str, str]] = []

    dockerfile = controller.run(
        sol_tar=str(tar_path),
        config_content='protocol = "demo"\n',
        rule_content='{"rules": []}',
        output_dir=str(output_dir),
        job_id="job-compiler",
        progress_callback=lambda job_id, stage, message: events.append((job_id, stage, message)),
    )

    assert dockerfile == "FROM scratch\n"
    assert events == [
        ("job-compiler", "compile", "Prepared AI compiler build context"),
        ("job-compiler", "compile", "Round 1: generating Dockerfile with AI"),
        ("job-compiler", "compile", "Round 1: generated Dockerfile"),
        ("job-compiler", "compile", "Round 1: building generated Dockerfile"),
        ("job-compiler", "compile", "Round 1: Docker image build succeeded"),
        ("job-compiler", "compile", "Round 1: validating builder output"),
        ("job-compiler", "compile", "Round 1: builder output validated"),
        ("job-compiler", "compile", "Round 1: copying builder output"),
        ("job-compiler", "compile", "Round 1: builder output copied"),
    ]
