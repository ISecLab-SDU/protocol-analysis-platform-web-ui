# Agent progress events

ProtocolGuard keeps Claude Agent SDK as its default runtime and offers Pi as an
experimental assertion-only option. Progress consumers use a
small SDK-independent contract, implemented in
`dynamic_verification/agent_progress/src/pg_agent_progress/events.py`.
`claude.py` interprets SDK messages; `legacy.py` reads earlier event formats.
The assertion CLI selects Claude or Pi directly; there is no runtime registry.
Pi maps SDK activities into this same contract and archives normalized records
before stdout; raw Pi source/tool inputs and thinking signatures are omitted.

## Contract

A stdout record is `PG_PROGRESS_JSON ` followed by one JSON object:

```json
{"ts_ms":123,"type":"progress","stage":"instrumentation","message":"Bash: make","metadata":{"activity":"command","tool":"Bash","tool_id":"call-1","primary":"make"}}
```

- `stage` is the business phase. Assertion agent events use `instrumentation`,
  builder events use `builder`, and fuzz-config agent events use
  `fuzz-config-build`. Existing workflow stages remain unchanged.
- `message` is readable progress text. `ts_ms` is the producer's epoch timestamp.
- `type` is `progress`, `error`, or `result`. Workflow results and agent results
  are separate: `type: result` alone does not identify an agent result.
- `metadata.activity` distinguishes agent activity from workflow progress. It is
  one of `status`, `message`, `thinking`, `command`, `inspect`, `write`, `plan`,
  `tool`, `tool_result`, or `result`. Its absence means workflow progress.
- Optional display fields are `tool`, `tool_id`, `primary`, `description`,
  `is_error`, `status` (`completed` or `failed` for results), and `result`.
  `tool` is a label, never a discriminator. `quiet` keeps noisy records in the
  archive/copyable timeline while omitting them from the visible timeline.
- Optional metrics are `model`, `duration_ms`, `cost_usd`, `input_tokens`,
  `output_tokens`, and `cache_read_tokens`. Missing metrics remain absent.

Flask retains its existing event envelope (`id` where available, `timestamp`,
`stage`, `message`, and optional `metadata`). It normalizes old `claude-*` stages,
SDK metadata, and recognizable old thinking/tool-result representations before
returning events. Storage is not rewritten. Three-argument progress callbacks
remain supported, but only metadata-aware callbacks receive activity details.

Agent events never change job status, business stage, or business status message.
The enclosing workflow still determines whether its artifacts are complete.
Agent errors/results retain critical queue priority. Ordinary agent activity may
be dropped under existing builder backpressure; JSONL is written before stdout.

## Diagnostics and bounds

SDK messages remain available as sanitized `{"raw": ...}` JSONL records at the
existing archive paths. Thinking-token bookkeeping remains filtered. Tool source
payloads and thinking signatures are excluded from normalized progress; tool
input is restricted to existing display fields. Stdout and normalized archive
records use the same serialized JSON. Archive-write failures remain nonfatal.

Progress JSON is limited to 3,500 UTF-8 bytes, excluding prefix and newline.
Oversized events retain the message prefix, stage, type, activity, correlation,
and error/outcome flags and include `truncated` and `original_bytes`. Metrics and
other optional detail can be omitted under this bound. Raw diagnostics are not
transported to the frontend. Generic unknown messages remain readable; old
reprs that cannot be recognized are shown as generic text.

## Packaging and synchronization

Install the neutral package alongside either core workflow; for example, from
`dynamic_verification/assert_instrumentation`:

```sh
pip install ../agent_progress .
```

The main Dockerfile installs all three packages together. The web repository
vendors the same package under `apps/backend-flask/pg_agent_progress` so it has no
checkout or PyPI dependency at runtime. Its contract tests are also copied.
From the web repository, check parity with
`python scripts/sync-agent-progress.py`; refresh with `--write`. Use
`--source /path/to/ProtocolGuard` for another checkout location.

The standalone builder's Docker build context is now `apps/backend-flask`, so
it can copy the same package without a second vendored copy. On the builder build
host, from that directory:

```sh
docker build -f protocol_compliance/claude_builder/Dockerfile \
  -t protocolguard-claude-builder:latest .
```

This changes source packaging only; the image entrypoint, runtime, workspace,
and deployment remain the same. Existing deployed images continue to produce
legacy events, which the updated backend accepts. Deploy the backend and UI
together because the UI expects normalized API events. Container behavior must
be verified on the appropriate build host; ProtocolGuard image builds and core
compilation belong on `MyServer-Local`.
