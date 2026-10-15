#!/usr/bin/env python3
"""Deliver committed web sources and built ProtocolGuard images to Presentation."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SSH_OPTIONS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]
DEFAULT_IMAGES = ["protocolguard:main", "protocolguard-claude-builder:latest"]


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    stdin: str | None = None,
    stream: bool = False,
) -> str:
    result = subprocess.run(
        argv,
        cwd=cwd,
        input=stdin,
        text=True,
        check=True,
        stdout=None if stream else subprocess.PIPE,
    )
    return (result.stdout or "").strip()


def remote(
    args: argparse.Namespace,
    script: str,
    *,
    presentation: bool = False,
    stream: bool = False,
) -> str:
    # Both control traffic and image transfers use the build host's existing key.
    command = ["bash", "-seuo", "pipefail"]
    if presentation:
        command = ["ssh", *SSH_OPTIONS, args.presentation_host, shlex.join(command)]
    return run(
        ["ssh", *SSH_OPTIONS, args.build_host, shlex.join(command)],
        stdin=script,
        stream=stream,
    )


def python_script(source: str, *argv: str) -> str:
    return shlex.join(["python3", "-", *argv]) + " <<'PY'\n" + source + "\nPY\n"


SYNC_REPO = r"""
import pathlib, subprocess, sys
path, branch, revision = sys.argv[1:]
root = pathlib.Path(path).expanduser()
def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
if git('branch', '--show-current') != branch:
    raise SystemExit(f'{root}: expected branch {branch}; refusing to switch branches')
if git('status', '--porcelain', '--untracked-files=no'):
    raise SystemExit(f'{root}: tracked changes present; preserve or commit them before syncing')
print(f'{root}: {git("rev-parse", "--short", "HEAD")} -> {revision[:12]}', flush=True)
git('fetch', 'share', branch)
if git('rev-parse', 'FETCH_HEAD') != revision:
    raise SystemExit('share changed since the local push; rerun after reconciling revisions')
git('merge', '--ff-only', 'FETCH_HEAD')
if git('rev-parse', 'HEAD') != revision:
    raise SystemExit('Destination HEAD does not match the requested revision')
print(git('status', '--short', '--branch'))
"""


VERIFY_WEB = r"""
import base64, json, pathlib, re, sys, time, urllib.request
root = pathlib.Path(sys.argv[1]).expanduser()
frontend = sys.argv[2].rstrip('/')
backend = sys.argv[3].rstrip('/')
paths = sys.argv[4:]
def fetch(url):
    with urllib.request.urlopen(url, timeout=15) as response:
        return response.read().decode()
# Reloader startup can briefly interrupt HTTP after a backend update.
for attempt in range(30):
    try:
        for url in (backend + '/api/healthz', frontend + '/api/healthz'):
            if json.loads(fetch(url)).get('status') != 'ok':
                raise ValueError('Backend health response is not ok')
        break
    except Exception:
        if attempt == 29:
            raise
        time.sleep(2)
fetch(frontend + '/protocol-compliance/workbench')
for path in paths:
    source = root / 'apps/web-antd' / path.lstrip('/')
    module = fetch(frontend + '/' + path.lstrip('/'))
    match = re.search(r'sourceMappingURL=data:application/json;base64,([^\s]+)', module)
    if not match:
        raise SystemExit(f'{path}: expected the running Vite development server source map')
    mapping = json.loads(base64.b64decode(match[1]))
    if source.read_text() not in mapping.get('sourcesContent', []):
        raise SystemExit(f'{path}: served source differs from the destination checkout')
    print(f'Verified served source: {path}')
# Inspect only process names, cwd and reloader state; never print credentials.
reloader = False
for proc in pathlib.Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if (proc / 'cwd').resolve() != root / 'apps/backend-flask':
            continue
        command = (proc / 'cmdline').read_bytes().split(b'\0')
        if b'app.py' not in command:
            continue
        env = (proc / 'environ').read_bytes().split(b'\0')
        if b'WERKZEUG_RUN_MAIN=true' in env:
            reloader = True
            print(f'Flask debug reloader active: PID {proc.name}')
    except (PermissionError, FileNotFoundError, ProcessLookupError):
        continue
if not reloader:
    raise SystemExit('No Flask debug reloader found; restart the managed backend and verify it explicitly')
print('Frontend and backend HTTP checks passed')
"""


def sync_repo(
    args: argparse.Namespace,
    local: Path,
    destination: str,
    branch: str,
    *,
    presentation: bool = False,
) -> str:
    if run(["git", "branch", "--show-current"], cwd=local) != branch:
        raise ValueError(f"{local}: expected branch {branch}")
    dirty = run(["git", "status", "--short"], cwd=local)
    if dirty:
        print(
            f"{local.name}: uncommitted files remain local; delivering committed HEAD only",
            flush=True,
        )
    revision = run(["git", "rev-parse", "HEAD"], cwd=local)
    run(["git", "push", "share", f"{revision}:refs/heads/{branch}"], cwd=local)
    print(
        remote(
            args,
            python_script(SYNC_REPO, destination, branch, revision),
            presentation=presentation,
        )
    )
    return revision


def sync_web(args: argparse.Namespace) -> None:
    revision = sync_repo(args, ROOT, args.presentation_repo, "main", presentation=True)
    print(
        remote(
            args,
            python_script(
                VERIFY_WEB,
                args.presentation_repo,
                args.frontend_url,
                args.backend_url,
                *args.frontend_probe,
            ),
            presentation=True,
        )
    )
    print(f"Web delivery verified: {revision}", flush=True)


def image_ids(
    args: argparse.Namespace, tags: list[str], *, presentation: bool = False
) -> dict[str, str]:
    # Missing destination tags are expected on a first delivery.
    # Inspect individually so missing tags cannot shift the correspondence.
    source = r"""
import json, subprocess, sys
images = {}
for tag in sys.argv[1:]:
    p = subprocess.run(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'],
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    images[tag] = p.stdout.strip() if p.returncode == 0 else ''
print(json.dumps(images))
"""
    return json.loads(
        remote(args, python_script(source, *tags), presentation=presentation)
    )


def build_images(args: argparse.Namespace) -> None:
    for target in args.build:
        if target == "core":
            local = args.core_repo
            destination = args.build_core_repo
            sync_repo(args, local, destination, "master")
            context = destination
            dockerfile = "Dockerfile"
            tag = "protocolguard:main"
            smoke = ["docker", "run", "--rm", "--network=none", tag, "--help"]
        else:
            sync_repo(args, ROOT, args.build_web_repo, "main")
            context = args.build_web_repo + "/apps/backend-flask"
            dockerfile = "protocol_compliance/claude_builder/Dockerfile"
            tag = "protocolguard-claude-builder:latest"
            smoke = [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--entrypoint",
                "node",
                tag,
                "--input-type=module",
                "-e",
                "import('/opt/protocolguard/pi-agent/runner.mjs')",
            ]
        build = [
            "docker",
            "buildx",
            "build",
            "--load",
            "--progress=plain",
            "--network=host",
            "--allow=network.host",
        ]
        for proxy in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "FTP_PROXY",
            "ftp_proxy",
        ):
            build.extend(["--build-arg", proxy + "="])
        build.extend(["-f", dockerfile, "-t", tag, "."])
        # Expand the remote home without interpolating shell code from a path.
        source = r"""
import pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1]).expanduser()
subprocess.run(sys.argv[2:], cwd=root, check=True)
"""
        print(f"Building {tag} on {args.build_host}", flush=True)
        remote(args, python_script(source, context, *build), stream=True)
        print(remote(args, shlex.join(smoke)))


def sync_images(args: argparse.Namespace) -> None:
    build_images(args)
    tags = list(dict.fromkeys(args.image))
    source = image_ids(args, tags)
    missing = [tag for tag, identity in source.items() if not identity]
    if missing:
        raise ValueError(f"Images missing on {args.build_host}: {', '.join(missing)}")
    destination = image_ids(args, tags, presentation=True)
    changed = [tag for tag in tags if source[tag] != destination[tag]]
    if changed:
        print(
            f"Transferring directly from {args.build_host}: {', '.join(changed)}",
            flush=True,
        )
        load = shlex.join(
            ["ssh", *SSH_OPTIONS, args.presentation_host, "docker image load"]
        )
        remote(
            args,
            shlex.join(["docker", "image", "save", *changed]) + " | " + load,
            stream=True,
        )
    else:
        print("Image IDs already match; no image transfer needed", flush=True)
    # The running backend currently defaults to protocolguard:latest.
    if "protocolguard:main" in tags:
        print(
            remote(
                args,
                "docker image tag protocolguard:main " + shlex.quote(args.analysis_tag),
                presentation=True,
            )
        )
        tags = list(dict.fromkeys([*tags, args.analysis_tag]))
        source[args.analysis_tag] = source["protocolguard:main"]
    verified = image_ids(args, tags, presentation=True)
    for tag in tags:
        if verified[tag] != source[tag]:
            raise ValueError(f"Destination image ID mismatch: {tag}")
        print(f"Verified image: {tag} {verified[tag]}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scope", choices=["web", "images", "all"], nargs="?", default="all"
    )
    parser.add_argument("--build-host", default="MyServer-Local")
    parser.add_argument("--presentation-host", default="ServerISecLab-Presentation")
    parser.add_argument(
        "--presentation-repo",
        default="~/protocol-web-ui/protocol-analysis-platform-web-ui",
    )
    parser.add_argument("--build-web-repo", default="~/protocolguard-pi-web")
    parser.add_argument("--build-core-repo", default="~/ProtocolGuard")
    parser.add_argument("--core-repo", type=Path, default=ROOT.parent / "ProtocolGuard")
    parser.add_argument(
        "--image",
        action="append",
        help="Transfer this tag (repeatable; replaces default image list)",
    )
    parser.add_argument(
        "--analysis-tag",
        default="protocolguard:latest",
        help="Presentation backend's analysis image tag",
    )
    parser.add_argument(
        "--build",
        action="append",
        choices=["core", "agent-builder"],
        default=[],
        help="Sync committed source and build on MyServer-Local before transfer",
    )
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5666")
    parser.add_argument("--backend-url", default="http://127.0.0.1:5000")
    parser.add_argument(
        "--frontend-probe",
        action="append",
        help="Vite source path to compare with the destination file (repeatable)",
    )
    args = parser.parse_args()
    if args.scope == "web" and args.build:
        parser.error("--build requires images or all")
    args.image = args.image or DEFAULT_IMAGES.copy()
    for target in args.build:
        tag = (
            "protocolguard:main"
            if target == "core"
            else "protocolguard-claude-builder:latest"
        )
        if tag not in args.image:
            args.image.append(tag)
    # The Agent builder copies the Pi runtime from the core image.
    args.build = [
        target for target in ("core", "agent-builder") if target in args.build
    ]
    args.frontend_probe = args.frontend_probe or [
        "src/views/protocol-compliance/workbench/modules/CodeLocateModule.vue",
        "src/views/protocol-compliance/workbench/components/StageCodeLocate.vue",
    ]
    try:
        if args.scope in ("images", "all"):
            sync_images(args)
        if args.scope in ("web", "all"):
            sync_web(args)
    except (subprocess.CalledProcessError, ValueError) as error:
        print(f"Sync failed: {error}", file=sys.stderr)
        return 1
    print("Presentation synchronization verified", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
