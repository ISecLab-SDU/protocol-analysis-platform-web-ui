## ProtocolGuard Docker Integration

Set the following environment variables before launching the Flask backend to enable the real ProtocolGuard workflow:

- `PG_DOCKER_ENABLED=1` — opt-in flag; keep unset to continue serving mock data.
- `PG_ANALYSIS_IMAGE` — tag of the analysis container (defaults to `protocolguard:main`).
- `PG_BUILDER_IMAGE` — optional builder container tag; omit if artefacts are staged manually.
- `PG_WORKSPACE_ROOT`, `PG_OUTPUT_ROOT`, `PG_CONFIG_ROOT` — host directories used for per-job mounts.
- `PG_TEMPLATE_WORKSPACE` — optional directory with pre-built artefacts copied into each job workspace.
- `PG_ENV_VARS` — comma separated environment variable names to forward (defaults to `OPENAI_API_KEY`).

Additional `PG_ARTIFACT_*` overrides let you map artefact filenames if your builder emits different names (e.g. `PG_ARTIFACT_BITCODE=sol.bc`). See `protocol_compliance/docker_runner.py` for the full list of tunables.

When Docker integration is active, API error responses include the underlying container status and the last log lines so trusted operators can diagnose issues quickly.
