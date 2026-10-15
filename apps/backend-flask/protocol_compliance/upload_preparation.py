"""Prepare uploaded source archives without importing historical build databases."""

import logging
import os
from pathlib import Path
import re
import shutil
import stat
import tarfile
import zipfile

LOGGER = logging.getLogger(__name__)
GENERATED_DATABASE = re.compile(r"(?:\d+)?sqlite_.*\.db(?:-wal|-shm|-journal)?$")


def _target(root: Path, name: str) -> Path:
    path = root / name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"unsafe archive member path: {name}")
    return path


def prepare_uploaded_source(archive: Path, project: Path) -> list[str]:
    """Extract as the service account, then remove prior generated databases."""
    project.mkdir(parents=True, exist_ok=False)
    modes = {}
    if tarfile.is_tarfile(archive):
        hardlinks = []
        with tarfile.open(archive, "r:*") as source:
            for member in source:
                path = _target(project, member.name)
                path.parent.mkdir(parents=True, exist_ok=True)
                if member.isdir():
                    path.mkdir(exist_ok=True)
                elif member.isfile():
                    with source.extractfile(member) as content, path.open("wb") as output:
                        shutil.copyfileobj(content, output)
                    modes[path] = bool(member.mode & 0o111)
                elif member.issym():
                    _target(project, str(path.parent.relative_to(project) / member.linkname))
                    path.symlink_to(member.linkname)
                elif member.islnk():
                    hardlinks.append((path, _target(project, member.linkname)))
                else:
                    raise ValueError(f"unsupported archive member type: {member.name}")
            for path, target in hardlinks:
                if not target.is_file() or target.is_symlink():
                    raise ValueError(f"invalid archive hard link: {path.relative_to(project)}")
                # Copy so later normalization cannot alter an unrelated inode.
                shutil.copyfile(target, path)
                modes[path] = modes.get(target, False)
    elif zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                path = _target(project, member.filename)
                path.parent.mkdir(parents=True, exist_ok=True)
                mode = member.external_attr >> 16
                if member.is_dir():
                    path.mkdir(exist_ok=True)
                elif stat.S_ISLNK(mode):
                    link = source.read(member).decode("utf-8")
                    _target(project, str(path.parent.relative_to(project) / link))
                    path.symlink_to(link)
                else:
                    with source.open(member) as content, path.open("wb") as output:
                        shutil.copyfileobj(content, output)
                    modes[path] = bool(mode & 0o111)
    else:
        raise ValueError("Source upload must be a tar or ZIP archive")

    removed = []
    # os.walk does not recurse through directory symlinks.
    for folder, directories, files in os.walk(project, followlinks=False):
        for name in directories + files:
            path = Path(folder) / name
            if name == "compile_commands.json" or GENERATED_DATABASE.fullmatch(name):
                if path.is_symlink() or path.is_file():
                    path.unlink()
                    removed.append(path.relative_to(project).as_posix())
                    continue
            info = path.lstat()
            if (info.st_uid, info.st_gid) != (os.getuid(), os.getgid()):
                os.chown(path, os.getuid(), os.getgid(), follow_symlinks=False)
            if not path.is_symlink():
                path.chmod(0o755 if path.is_dir() or modes.get(path, False) else 0o644)
    project.chmod(0o755)
    LOGGER.info("Prepared uploaded source; removed %d generated databases: %s", len(removed), removed)
    return removed
