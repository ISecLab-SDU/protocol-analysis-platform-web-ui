## ProtocolGuard Docker Integration

Configure the following environment variables for the ProtocolGuard Docker integration:

- `PG_DOCKER_ENABLED=0` — opt-out flag; keep unset to enable Docker integration.
- `PG_ANALYSIS_IMAGE` — tag of the analysis container (defaults to `protocolguard:main`).
- `PG_BUILDER_IMAGE` — optional builder container tag; omit if artefacts are staged manually.
- `PG_WORKSPACE_ROOT`, `PG_OUTPUT_ROOT`, `PG_CONFIG_ROOT` — host directories used for per-job mounts.
- `PG_TEMPLATE_WORKSPACE` — optional directory with pre-built artefacts copied into each job workspace.
- `PG_ENV_VARS` — comma separated environment variable names to forward (defaults to `OPENAI_API_KEY`).
- `PG_WORKSPACE_SNAPSHOTS_ENABLED=1` — opt in to full workspace snapshots; snapshots are disabled by default.
- `PG_RUNTIME_CLEANUP_ENABLED=0` — opt out of runtime rotation; cleanup is enabled by default.
- `PG_RUNTIME_RETENTION_DAYS`, `PG_RUNTIME_RETENTION_MAX_JOBS` — rotation limits for runtime artefacts (defaults: `7` days and `20` jobs).
- `PG_ASSERT_KEEP_FULL_ARTIFACTS=1` — keep full assertion-generation workspaces and outputs after instrumentation; by default only deliverables such as logs, ZIPs, and diffs are retained.

Additional `PG_ARTIFACT_*` overrides let you map artefact filenames if your builder emits different names (e.g. `PG_ARTIFACT_BITCODE=sol.bc`). See `protocol_compliance/docker_runner.py` for the full list of tunables.

When Docker integration is active, API error responses include the underlying container status and the last log lines so trusted operators can diagnose issues quickly.

### Fuzz debug replay

For local Fuzz debugging, reuse an assertion-insertion output instead of rerunning static analysis and assertion generation. The backend looks for `instrumented_code.zip` under the ProtocolGuard runtime roots and launches the same artifact-backed Fuzz job used by `/api/protocol-compliance/fuzzing/jobs`.

Use the newest available assertion output:

```bash
curl -X POST http://localhost:5000/api/protocol-compliance/fuzzing/dev/jobs \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"protocol":"MQTT","protocolImplementations":["SOL"]}'
```

Or pin a known baseline input:

```bash
curl -X POST http://localhost:5000/api/protocol-compliance/fuzzing/dev/jobs \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "instrumentedCodeZipPath": "/tmp/protocolguard/outputs/c633123b-6ddd-489f-ae78-ae1645b5df66/instrumented_code.zip",
    "protocol": "MQTT",
    "protocolImplementations": ["SOL"]
  }'
```

Poll the returned `jobId` through `/api/protocol-compliance/fuzzing/jobs/<jobId>` and `/api/protocol-compliance/fuzzing/jobs/<jobId>/logs?fromPosition=0`.

### Multipart contract

`POST /api/protocol-compliance/static-analysis` expects a multipart request with the following parts:

- `codeArchive` — 压缩后的源码工程（zip/tar 等），会解包至 `/workspace/project` 并作为 Builder 镜像构建上下文。
- `builderDockerfile` — 用户提供的 Dockerfile，用于构建 ProtocolGuard Builder 镜像。
- `rules` — 协议规则提取结果（JSON），容器内映射到 `/workspace/inputs/rules.json`。
- `config` — ProtocolGuard 主容器的配置（TOML），系统会重写关键路径后挂载到 `/config/config.toml`。
- `notes`（可选）— 前端描述性备注，直接存入分析记录。
