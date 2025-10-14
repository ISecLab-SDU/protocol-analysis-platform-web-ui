# Repository Orientation

## Mission & Context

- Vue 3 admin UI that showcases the protocol security lab's capabilities to potential collaborators. It is currently front-end heavy and used mainly for guided demos.
- Forked and heavily modified from `vbenjs/vue-vben-admin`; expect to encounter template-era naming, utilities, and layout choices that can be repurposed or trimmed.
- Delivery pace is aggressive. Favor production-ready patterns (clean separation of view layer, state, and API calls) even for demo flows.

## Primary Surface Areas

- `Protocol Compliance` (`apps/web-antd/src/views/protocol-compliance/*`): real feature work starts here. Key routes include Extract, Static Analysis, and Fuzz Testing. The Extract view is live; the rest still point at placeholders.
- `Password/Cryptanalysis` (`apps/web-antd/src/views/placeholders` for now): menu placeholders for future cryptographic misuse analysis and formal verification flows. Keep route names stable while wiring new modules.
- `LLM Automated Penetration` (`apps/web-antd/src/views/placeholders`): three scaffolded slots for LLM prompt templates, execution logs, etc. Replace placeholders with main-view modules as specs arrive.
- Each top-level page is exposed through `apps/web-antd/src/router/routes/modules/*.ts`. New modules should register there and live under matching `views` subdirectories.

## Data & Backend Strategy

- A Nitro-based mock backend (`apps/backend-mock`) supplies API contracts during UI work. Treat it as the source of truth for demo data and teed-up integration.
- Prefer pulling mock data through typed API clients in `apps/web-antd/src/api`. Hard-coded fixtures inside `.vue` files are acceptable only as a temporary bridge; migrate them into the mock backend once an endpoint shape stabilizes.
- Keep request/response models, stores, and composables in `packages/*` when they are shared across tools.

## Monorepo Layout

- Applications live under `apps/*`; `apps/web-antd` is the primary UX target, while `apps/backend-mock` mirrors expected backend contracts.
- Shared domains, composables, and styling primitives live under `packages/*` (`@core`, `stores`, `styles`, etc.). Reuse before re-creating.
- Internal developer tooling (Vite, ESLint, Tailwind configs) is under `internal/*`. Documentation sources reside in `docs`.

## Build & Development

- Install: `pnpm install` (Node >= 20.10, pnpm >= 9.12).
- Dev servers: `pnpm dev` for the workspace loop or `pnpm dev:antd` for the admin UI. Start the mock backend with `pnpm --filter @vben/backend-mock dev` when exercising API flows or Playwright specs.
- Bundles: `pnpm build` for the workspace, `pnpm build:docs` for docs, and `pnpm preview` to inspect production output.
- Checks: `pnpm check` aggregates circular dependency, type, and spell checks.

## Coding & Style Guardrails

- Vue SFCs and TypeScript use two-space indentation and single quotes. Directories/routes stay kebab-case; components, composables, and stores follow PascalCase.
- Share utilities through packages instead of relative imports inside apps. Remove leftover vben demo pages as the new flows mature.
- Formatting and linting go through `pnpm lint` or `pnpm format`, powered by the shared `@vben` configs and Lefthook hooks.

## Testing Expectations

- Unit: colocate `*.spec.ts` with source and run via `pnpm test:unit` or `pnpm vitest -- --ui`.
- E2E: launch both the target app and the mock backend before executing `pnpm test:e2e`. Keep Playwright fixtures in sync with mock API responses.
- Prefer writing tests against real API mocks instead of stubbed components to keep parity with eventual backend integration.

## Collaboration Hygiene

- Commits follow Conventional Commit syntax, preferably scoped to the affected package/app (e.g., `feat(web-antd): ...`). Use `pnpm commit` for the guided workflow.
- For PRs: summarize scope, link issues, list validation commands (`pnpm test:unit`, `pnpm lint`, etc.), and include before/after screenshots for UI changes. Ensure CI is green and the relevant domain owner reviews before merge.
