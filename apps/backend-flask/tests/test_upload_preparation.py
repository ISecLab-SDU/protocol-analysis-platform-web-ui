import io
import os
import stat
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from protocol_compliance.upload_preparation import prepare_uploaded_source  # noqa: E402


@pytest.mark.parametrize("kind", ["tar", "zip"])
def test_prepare_ownership_modes_and_generated_databases(tmp_path, kind):
    archive = tmp_path / f"input.{kind}"
    entries = {
        "sol/run.sh": b"#!/bin/sh\n",
        "sol/build/compile_commands.json": b"[]",
        "sol/build_pg/compile_commands.json": b"[]",
        "sol/build/sqlite_Sol.db": b"old results",
        "sol/build/1sqlite_Sol.db-wal": b"old journal",
        "sol/data/application.db": b"application data",
        "sol/CMakeLists.txt": b"project(sol)",
    }
    if kind == "tar":
        with tarfile.open(archive, "w") as output:
            for name, data in entries.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.uid = member.gid = 12345
                member.mode = 0o4700 if name.endswith(".sh") else 0
                output.addfile(member, io.BytesIO(data))
    else:
        with zipfile.ZipFile(archive, "w") as output:
            for name, data in entries.items():
                member = zipfile.ZipInfo(name)
                member.external_attr = (0o4700 if name.endswith(".sh") else 0) << 16
                output.writestr(member, data)
    project = tmp_path / "project"
    removed = prepare_uploaded_source(archive, project)
    assert len(removed) == 4
    assert (project / "sol/data/application.db").read_bytes() == b"application data"
    for path in [project, *project.rglob("*")]:
        info = path.stat()
        assert (info.st_uid, info.st_gid) == (os.getuid(), os.getgid())
        assert stat.S_IMODE(info.st_mode) == (0o755 if path.is_dir() or path.suffix == ".sh" else 0o644)


@pytest.mark.parametrize("kind", ["tar", "zip"])
def test_reject_archive_traversal(tmp_path, kind):
    archive = tmp_path / f"input.{kind}"
    if kind == "tar":
        with tarfile.open(archive, "w") as output:
            output.addfile(tarfile.TarInfo("../escape"), io.BytesIO(b""))
    else:
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("../escape", "")
    with pytest.raises(ValueError, match="unsafe archive"):
        prepare_uploaded_source(archive, tmp_path / "project")
    assert not (tmp_path / "escape").exists()


def test_reject_external_symlink(tmp_path):
    archive = tmp_path / "input.tar"
    with tarfile.open(archive, "w") as output:
        member = tarfile.TarInfo("link")
        member.type = tarfile.SYMTYPE
        member.linkname = "../../outside"
        output.addfile(member)
    with pytest.raises(ValueError, match="unsafe archive"):
        prepare_uploaded_source(archive, tmp_path / "project")


def test_flask_prepares_upload_before_builder_starts(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from protocol_compliance.compiler import ClaudeBuilderRunner

    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w") as output:
        for name in ["sol/main.c", "sol/build/compile_commands.json", "sol/build/sqlite_Sol.db", "sol/data/application.db"]:
            data = b"input"
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.uid = member.gid = 12345
            output.addfile(member, io.BytesIO(data))
    payload.seek(0)
    executor = ClaudeBuilderRunner.__new__(ClaudeBuilderRunner)
    executor.settings = SimpleNamespace(workspace_root=tmp_path / "jobs")

    def builder(workspace, *args):
        project = workspace / "project/sol"
        assert (project / "main.c").is_file()
        assert not (project / "build/compile_commands.json").exists()
        assert not (project / "build/sqlite_Sol.db").exists()
        assert (project / "data/application.db").is_file()
        assert (project / "main.c").stat().st_uid == os.getuid()
        raise RuntimeError("reached prepared builder")

    monkeypatch.setattr(executor, "_run_claude_builder_container", builder)
    with pytest.raises(RuntimeError, match="reached prepared builder"):
        executor.run_compilation(
            code_stream=payload, code_filename="input.tar",
            config_stream=io.BytesIO(b""), config_filename="config.toml",
            rules_stream=io.BytesIO(b"{}"), rules_filename="rules.json",
        )


def test_ownership_failure_is_not_ignored(tmp_path, monkeypatch):
    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("main.c", "source")
    real_getuid = os.getuid
    monkeypatch.setattr(os, "getuid", lambda: real_getuid() + 1)

    def denied(*args, **kwargs):
        raise PermissionError("ownership denied")

    monkeypatch.setattr(os, "chown", denied)
    with pytest.raises(PermissionError, match="ownership denied"):
        prepare_uploaded_source(archive, tmp_path / "project")
