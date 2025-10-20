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

### Multipart contract

`POST /api/protocol-compliance/static-analysis` expects a multipart request with the following parts:

- `codeArchive` — 压缩后的源码工程（zip/tar 等），会解包至 `/workspace/project` 并作为 Builder 镜像构建上下文。
- `builderDockerfile` — 用户提供的 Dockerfile，用于构建 ProtocolGuard Builder 镜像。
- `rules` — 协议规则提取结果（JSON），容器内映射到 `/workspace/inputs/rules.json`。
- `config` — ProtocolGuard 主容器的配置（TOML），系统会重写关键路径后挂载到 `/config/config.toml`。
- `notes`（可选）— 前端描述性备注，直接存入分析记录。
