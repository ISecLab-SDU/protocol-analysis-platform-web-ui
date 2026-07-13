from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
BUILDER_SCRIPT = BACKEND_ROOT / "protocol_compliance" / "claude_builder" / "pg-claude-builder"


def _run_extract(workspace: Path) -> subprocess.CompletedProcess[str]:
    command = (
        'PG_BUILDER_WORKSPACE="$1" source "$2"; '
        "extract_source_archives"
    )
    return subprocess.run(
        ["bash", "-c", command, "_", str(workspace), str(BUILDER_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_claude_builder_extracts_tar_tgz_and_zip_archives(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")

    with tarfile.open(tmp_path / "plain.tar", "w") as archive:
        archive.add(source / "main.c", arcname="plain/main.c")
    with tarfile.open(tmp_path / "compressed.tgz", "w:gz") as archive:
        archive.add(source / "main.c", arcname="compressed/main.c")
    with zipfile.ZipFile(tmp_path / "source.zip", "w") as archive:
        archive.writestr("zip/main.c", "int main(void) { return 0; }\n")
    (tmp_path / "config.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "rule_config.json").write_text("{}\n", encoding="utf-8")

    result = _run_extract(tmp_path)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "project" / "plain" / "main.c").is_file()
    assert (tmp_path / "project" / "compressed" / "main.c").is_file()
    assert (tmp_path / "project" / "zip" / "main.c").is_file()
    assert "Extracting tar archive" in result.stdout
    assert "Extracting zip archive" in result.stdout


def test_claude_builder_rejects_unsafe_tar_members(tmp_path: Path) -> None:
    payload = tmp_path / "payload.txt"
    payload.write_text("escape\n", encoding="utf-8")
    with tarfile.open(tmp_path / "unsafe.tar", "w") as archive:
        archive.add(payload, arcname="../escape.txt")

    result = _run_extract(tmp_path)

    assert result.returncode != 0
    assert "unsafe tar member path" in result.stderr
    assert not (tmp_path / "escape.txt").exists()


def test_claude_builder_rejects_unsafe_zip_members(tmp_path: Path) -> None:
    with zipfile.ZipFile(tmp_path / "unsafe.zip", "w") as archive:
        archive.writestr("../escape.txt", "escape\n")

    result = _run_extract(tmp_path)

    assert result.returncode != 0
    assert "unsafe zip member path" in result.stderr
    assert not (tmp_path / "escape.txt").exists()
