# Claude Builder Work Board

## Current

- [x] No active implementation task.

## Remaining

- [x] No remaining items for this branch goal.

## Verified

- [x] Created an isolated worktree at `/home/xinrui/GitHub/vue-vben-admin-claude-builder`.
- [x] Identified the current backend contract: Flask expects builder output under the job workspace, including `program.bc`, `program.ll`, `build_log.txt`, `inputs/rules.json`, and project artefacts for later ProtocolGuard analysis.
- [x] Confirmed `/home/xinrui/ProtocolGuard` installs LLVM 14, gllvm, Node 20, and `@anthropic-ai/claude-code` for agent-driven assertion work.
- [x] Added a fixed `protocolguard-claude-builder:latest` Docker image definition with LLVM 14, gllvm, Node 20, and Claude Code.
- [x] Replaced the live compiler executor path with a builder-container run that streams logs to Flask progress callbacks and `build_log.txt`.
- [x] Confirmed root-mode Claude execution works with `IS_SANDBOX=1` and `--dangerously-skip-permissions`.
- [x] Smoke-tested `/home/xinrui/ProtocolGuard-Sample-Input`: produced `program.bc`, `program.ll`, `build_log.txt`, `inputs/rules.json`, `inputs/config.toml`, source-tree `.cf_*.json`, and database/report artefacts in `/tmp/protocolguard-claude-builder-smoke-root`.
- [x] Committed the scoped implementation on `feat/claude-agent-builder`.
