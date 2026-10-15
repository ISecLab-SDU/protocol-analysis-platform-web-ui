> Superseded runtime selection: Pi is now the sole Docker agent runtime. Claude models use Pi with `anthropic-messages`. See the core ProtocolGuard `docs/pi-runtime-migration.md`.

# Pi assertion instrumentation in the platform

The assertion workbench exposes **Claude** (default) and **Pi**, plus model, provider API, base URL, and an optional API key. Empty model/endpoint/key fields use server defaults. Pi supports OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages. Claude retains its Anthropic Messages SDK path.

The multipart `POST /api/protocol-compliance/assertion-generation` accepts an optional JSON `runtime` form field:

```json
{
  "agent": "pi",
  "api": "openai-completions",
  "model": "deepseek-flash",
  "baseUrl": "http://127.0.0.1:6872/v1"
}
```

Provider/model defaults and limits come from `[protocolguard.provider]` in `apps/backend-flask/config.toml` (or the file selected by the deployment path `PG_CONFIG_FILE`). UI fields override that configuration for one job; selecting "使用服务端配置" inherits the configured API. Model IDs are free-form and are sent unchanged to the provider. There is no DeepSeek model allowlist.

An API key may be supplied in `apiKey`; otherwise the configured provider uses `PG_PI_API_KEY`, then `OPENAI_API_KEY` for OpenAI-compatible APIs, or `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` for Anthropic. Switching API requires an explicit endpoint and model and uses the selected provider's credentials. Optional positive integers are `contextWindow`, `maxTokens`, `maxTurns`, and `timeoutSeconds`. The endpoint must be HTTP(S) without embedded credentials, query, or fragment. Unknown/invalid settings and missing credentials return HTTP 400 before creating an assertion job.

The builder and fuzz configuration agent use the same provider section. Native static analysis uses `[protocolguard.analysis]`, because it always calls Chat Completions; uploaded analysis TOML remains authoritative. Generated TOML retains the historical `llm_model_deepseek_v3` and `llm_model_deepseek_r1` keys for compatibility, with configurable values.

To migrate an installation, move the old base URL (including an existing cache URL), model and limits into those sections, retain the credential exports, and remove the legacy settings below. The shipped example uses `https://api.deepseek.com/v1` and `deepseek-flash`; it does not silently rewrite an explicitly supplied model ID.

| Removed server environment setting | Configuration replacement |
| --- | --- |
| `PG_PI_API`, `PG_PI_BASE_URL`, `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` | `protocolguard.provider.api`, `base_url` |
| `PG_PI_MODEL`, `PG_AGENT_MODEL`, `PG_CLAUDE_MODEL`, `ANTHROPIC_MODEL` | `protocolguard.provider.model` |
| `PG_PI_CONTEXT_WINDOW`, `PG_PI_MAX_TOKENS`, `PG_PI_MAX_TURNS`, `PG_CLAUDE_MAX_TURNS`, `PG_PI_TIMEOUT_SECONDS` | `context_window`, `max_tokens`, `max_turns`, `timeout_seconds` in the provider section |
| `PG_LLM_API_BASE`, `PG_LLM_MODEL_V3`, `PG_LLM_MODEL_R1` | `protocolguard.analysis.base_url`, `model`, `reasoning_model` |
| `PG_LLM_QUERY_REPEAT`, `PG_LLM_QUERY_MAX_ATTEMPTS`, `PG_LLM_VIOLATION_REPEAT`, `PG_LLM_MAX_THREADS` | `query_repeat`, `max_attempts`, `violation_repeat`, `max_threads` in the analysis section |

The backend serializes resolved settings into `PG_PI_*` for its internal container handoff. Direct container/worker invocations must supply `PG_PI_MODEL`, `PG_PI_BASE_URL`, and `PG_PI_API_KEY` explicitly. Container entrypoints preserve workflow budgets of 40 turns for builder jobs and 8000 for assertion/fuzz jobs unless configuration overrides them. Deployment paths, image selection and unrelated pipeline controls keep their existing interface.

The Flask adapter translates these settings to core environment variables once per job. It does not mutate the service environment. Assertion-task generation is unchanged; only the following instrumentation container receives the selected runtime. The result includes a credential-free `runtime` summary. The existing provider-independent progress contract, workflow stages, polling, failure state, and diff preview remain in use. Nonzero instrumentation exits retain their exit status and diagnostic details. The Docker CLI fallback does not publish credential-bearing command arguments in progress logs.

The workbench offers downloads for assertion tasks and instrumented source. The existing download API defaults to assertion tasks; adding `?artifact=instrumented-code` returns the completed job's instrumented-source ZIP. Downloads require authentication and a completed job.

## Deployment and verification, 2026-10-14

The existing development checkout on `ServerISecLab-Presentation` was updated through the `share` remote on `ServerISecLab-Normal`. Its Flask debug reloader and Vite server served the changed backend and assertion module. Health, checkout revision, served Vite module, and running container image were inspected.

The previously built and validated Pi image was transferred directly from `MyServer-Local` to Presentation, with matching image ID:

```
sha256:ebe8a8dc9537ff47241a697dfcb421346aff420595b263a45fdd1d5817576a34
```

It is available as `protocolguard:main` and the backend's existing configured tag `protocolguard:latest`. The former Presentation image is retained as `protocolguard:pre-platform-pi`. No new core image build was needed.

| Check | Evidence |
| --- | --- |
| Backend regression suite | 205 tests passed, including request-local settings, provider fallback, HTTP lifecycle, failure details, and artifact downloads. |
| Frontend | 22 focused tests passed; Vue type checking, production Vite build, focused ESLint and Prettier checks passed. |
| Container SDK | All 9 Pi SDK tests passed inside the image on MyServer-Local with the repository tests mounted explicitly. The packaged image omits the tests; bare `npm test` inside it alone executes zero tests. |
| Progress contract | Vendored package and canonical contract-test parity check passed. Flask/unit tests and live Pi events retain neutral activity metadata. |
| Live Pi platform job | `24bbdc9e-7443-460e-bc4e-62f72d000f1d`: HTTP 202 submission, completed status, 611 events, `deepseek-flash` via the existing DeepSeek Cache at port 6872, four generated tasks, one instrumented task under the existing default limit. |
| API artifacts | Task ZIP: 11,166 bytes / 6 files; instrumented-source ZIP: 1,988,017 bytes / 230 files; source diff: 2,763 characters. Both ZIPs and the diff were fetched through authenticated API routes. |
| Independent artifact verification | The API-downloaded source was transferred to MyServer-Local, compiled inside the same image with AFLNet gcc wrappers using a Clang backend, and tested in a network-isolated container. AFL symbols and unconditional MQTT-3.1.0-1 assertion verified; valid CONNECT/PING passed; a first-packet PINGREQ triggered SIGABRT with the requested rule message. |
| Failure API | Unsupported runtime returned 400. `8288ae0a-58e4-486d-95cc-46a47e3a99ff` used an intentionally unavailable Pi endpoint and reached failed status with exit code 1 and neutral result/status events. |
| Claude fallback | `b9ccc9ff-d14f-4148-8afb-e7c3c341b3ba` launched the retained Claude SDK path and propagated its failure. The configured endpoint returned `API Error: Failed to parse JSON`; successful live Claude instrumentation with this endpoint is unverified. Unit tests cover successful Claude job lifecycle and forwarding. |
| Credential handling | Recorded job states and both downloaded ZIPs had zero matches for configured provider credential values. Credentials were not committed. |

The SOL fixture came from the existing sample input. Validation used a disposable archive without old build outputs and added build instructions for its Clang-specific flags; original sample inputs were preserved. Independent rebuild also supplied `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` for the fixture's old CMake minimum. These are fixture-specific validation choices, not platform defaults.

Private API evidence and downloaded artifacts remain on Presentation under `~/pg-platform-pi-validation/`; independent build/packet-check evidence remains under that path on MyServer-Local. The Pi source ZIP SHA-256 is `eb2d08296edc5392f7a221a448e1300c12c9267a7d0c59550f699c428941f4f7`.

GUI acceptance remains with the user. This validates one MQTT assertion and the platform integration boundaries, not every rule/provider API. The existing instrumentation limit defaults to one unless `PG_INSTRUMENTATION_LIMIT` is set. Job registries remain in memory, so a Flask restart/reload clears their API lookup state; artifacts remain on disk. Cache reuse remains best effort; the run used ordinary upstream misses without changing cache policy. Fuzz configuration and the standalone protocol-consistency builder were not migrated to Pi. Existing progress-contract foundation changes were delivered with the integration.
