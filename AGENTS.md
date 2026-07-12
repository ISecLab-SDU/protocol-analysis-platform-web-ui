# AGENTS.md

## Local Repositories

- `~/ProtocolGuard` is the core logic repository. Compiler behavior, assertion generation, fuzz configuration, AFLNet orchestration, Docker image logic, and seed handling belong there.
- `~/ProtocolGuard-Sample-Input` contains test inputs and temporary debugging credentials. Use it for local smoke tests and replay; do not copy credentials from it into commits, docs, logs, screenshots, or PR text.

## Repository Scope

- This repository is the ProtocolGuard web UI and Flask integration layer.
- Use this repository for workflow orchestration, request validation, input staging, job registries, log streaming, artifact exposure, and frontend display.
- Do not reimplement ProtocolGuard core algorithms here. If behavior depends on compiler, assertion insertion, fuzz configuration, AFLNet launch semantics, seeds, or Docker entrypoints, inspect `~/ProtocolGuard`.

## Main Surfaces

- `apps/backend-flask/protocol_compliance/*`: Protocol Compliance API routes, job state, Docker command construction, artifact staging, and log streaming.
- `apps/backend-flask/tests/*`: backend regression tests for Protocol Compliance routes and jobs.
- `apps/web-antd/src/views/protocol-compliance/*`: Protocol Compliance UI and workbench orchestration.
- `apps/web-antd/src/api/protocol-compliance.ts`: frontend API contract for Protocol Compliance workflows.

## Protocol Compliance Workflow

- Assertion generation, fuzz configuration, and fuzzing are separate job stages. Keep job IDs, status, logs, and artifacts explicit between stages.
- A formal AFLNet fuzz job should consume a completed fuzz configuration bundle, not a raw source tree alone.
- Fuzzing requires `PG_FUZZ_TARGET_BINARY`, `PG_FUZZ_TARGET_ARGS`, `PG_FUZZ_SEED_DIR`, and `PG_FUZZ_NETSPEC` from the completed fuzz configuration artifact or explicit overrides.
- Prefer deterministic code/config for stable runtime parameters such as protocol defaults, seed catalog selection, target args, ports, and AFLNet net specs.
- Use Agents only for source-dependent work, such as identifying how to build and copy a target binary from an instrumented source tree.

## Local Validation

- Backend validation should use `apps/backend-flask/.venv`.
- Prefer focused checks for changed surfaces, for example:
  - `apps/backend-flask/.venv/bin/python -m pytest apps/backend-flask/tests/<test_file>.py -q`
  - `apps/backend-flask/.venv/bin/python -m ruff check <paths>`
  - `pnpm exec eslint <paths>`
  - `pnpm exec prettier --check <paths>`
