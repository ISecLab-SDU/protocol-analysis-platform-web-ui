# Impact Analysis

The fifth workbench module invokes ProtoXploit Phase 1 independently using the
same configured provider and credentials as assertion generation. No new API
key or service-wide environment mutation is required.

Authenticated API (`Authorization: Bearer ...`):

- `POST /api/protocol-compliance/impact-analysis`: multipart `code` (tar/ZIP)
  and `analysis` (portable `protocolguard.analysis` JSON), optional `runtime`
  JSON using the existing assertion-runtime settings. Returns HTTP 202 and a
  job with `jobId`.
- `GET .../impact-analysis/<jobId>/progress?offset=0`: job state and bounded log
  bytes; pass `nextOffset` on the next request.
- `GET .../impact-analysis/<jobId>/result`: validated assessments after completion.
- `GET .../impact-analysis/<jobId>/download`: ZIP of the assessment, Planning,
  Collect, tool audit and run manifests.
- `GET .../impact-analysis/history`: newest 100 persisted jobs.

Source hashes and relative evidence locations must match the uploaded archive.
Only eligible non-compliant findings are assessed. Findings retain their input
IDs. Non-security, unsupported-security, and uncertain outcomes are valid
assessments; infrastructure failure is a failed job, never a fabricated result.

Select source-only or native LLVM/SVF analysis with multipart
`heavyStaticAnalysis=false|true` (default false). The selected mode is explicit
in job/result metadata. Native mode requires paired whole-module `.bc`/`.ll`
artifacts and retains the mandatory static-analysis tool gate. Source-only
evidence limitations remain explicit. The worker image defaults to `protoxploit-phase1:main` and must
be built on MyServer-Local, transferred directly, and loaded on Presentation.
Source and input mounts are read-only; artifacts are writable by the service
UID. Provider credentials travel only in the container environment, with names
rather than secret values in Docker's command arguments.

Jobs are persisted outside the application checkout at
`~/.local/share/protocolguard/impact-analysis` (override with
`PROTOXPLOIT_STATE_DIR`). This keeps uploaded Python source from triggering the
Flask development server's source reloader.

Running jobs survive a backend reload. Container exit status is retained until
recorded, and progress/result/history reads reconcile completed workers against
Docker's exit state and the validated result manifest. Pre-migration workers
that used automatic container removal can be recovered from Docker's retained
`die` event. A transient Docker observation error never completes or fails a
job. If no worker or exit evidence remains, the job fails explicitly.
