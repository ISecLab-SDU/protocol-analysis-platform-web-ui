# Sync to Presentation

Run from the local web repository after committing the intended changes:

```bash
# Sync frontend/backend commits, check Flask health, compare served Vite sources.
python3 scripts/deploy/sync-presentation.py web

# Transfer existing core and Agent-builder images; skip matching image IDs.
python3 scripts/deploy/sync-presentation.py images

# Deliver images first, then the web repository (the default).
python3 scripts/deploy/sync-presentation.py all

# Sync core source to the build host, rebuild, smoke-check, and deliver.
python3 scripts/deploy/sync-presentation.py all --build core

# Rebuild both core and the Agent builder that copies its Pi runtime.
python3 scripts/deploy/sync-presentation.py all --build core --build agent-builder

# Transfer an additional standalone builder image already built on MyServer-Local.
python3 scripts/deploy/sync-presentation.py images --image protocolguard-builder:latest
```

The script is Python standard library only. Local dependencies are Python 3, Git,
and SSH; remote dependencies are Bash, Python 3, Git, and Docker. SSH uses
`BatchMode=yes`, so missing access fails without a password prompt.

## Routes and defaults

| Item | Route or destination |
| --- | --- |
| Web source | local `share/main` → central bare repository on `ServerISecLab-Normal` → Presentation |
| Core source when building | local `share/master` → central bare repository → `MyServer-Local:~/ProtocolGuard` |
| Agent-builder source when building | local `share/main` → central bare repository → `MyServer-Local:~/protocolguard-pi-web` |
| Web destination | `ServerISecLab-Presentation:~/protocol-web-ui/protocol-analysis-platform-web-ui` |
| Control connection | local → `MyServer-Local` → `ServerISecLab-Presentation` |
| Image bytes | `MyServer-Local` Docker save → SSH → Presentation Docker load |
| Default images | `protocolguard:main`, `protocolguard-claude-builder:latest` |
| Backend analysis alias | `protocolguard:latest`, tagged from the delivered `protocolguard:main` |
| HTTP verification on Presentation | frontend port 5666, backend port 5000, `/api/healthz` directly and through the frontend proxy |

`--image` is repeatable and **replaces** the default image list. `--build` always
adds its built tag to the delivery list. Core builds precede Agent-builder builds.
All builds use the repository's host-network buildx command on MyServer-Local;
image data never passes through the local workstation. Standalone
`ProtocolGuard-Builder` sources are not managed by Git here: build them in their
existing remote directory before transferring that image with `--image`.

See `--help` for host, checkout, URL, tag, and frontend-probe overrides. For a
different backend analysis tag, pass `--analysis-tag` matching its configuration.

## What is verified

Only **committed HEAD** is delivered. Uncommitted local files are reported and
preserved; the script never auto-commits them. Each destination must be on the
expected branch without tracked changes. Untracked files are preserved, and Git
rejects a merge if it would overwrite them. Updates are fast-forward only, with
an exact revision check; divergence or a concurrently changed shared branch fails.

The current Presentation environment runs Vite and the Flask debug reloader.
The script checks both HTTP routes and confirms a Flask reloader process belongs
to the expected checkout. For the two workbench components, it compares the
served Vite source map's original source with the actual destination files.
Repeat `--frontend-probe src/path/to/changed-file.vue` to check other modules.
These checks are specific to this development deployment, not a production
bundle/restart workflow. No process is killed or restarted by the script. Flask
automatically reloads changed Python modules; its in-memory job registry follows
the existing reload lifecycle. Dependency installation and database migrations
are separate operations when a change requires them.

Image transfers use `pipefail`, skip unchanged IDs, and fail if a loaded tag's
full image ID differs from the source ID. Missing source images fail before
transfer. Already running containers retain their existing image; new jobs use
the delivered tags. No analysis/fuzz jobs are started during sync verification.

Run the script's focused regression checks with:

```bash
python3 -m unittest discover -s scripts/deploy/tests -v
```
