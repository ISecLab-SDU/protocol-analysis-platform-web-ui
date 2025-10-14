# Repository Guidelines

## Project Structure & Module Organization

This pnpm/Turbo monorepo hosts several Vue 3 applications. The main admin UI lives in `apps/web-antd`, following the standard Vite layout (`src`, `public`, `.env*`). The mock backend for local API development resides in `apps/backend-mock`; start it for Playwright or manual QA flows. Shared domains, composables, stores, and styles are under `packages/*` (`@core`, `stores`, `styles`, etc.), while reusable build tooling lives in `internal/*` (Vite, ESLint, Tailwind configs). Documentation sources are maintained in `docs`.

## Build, Test, and Development Commands

Install dependencies with `pnpm install` (Node >=20.10, pnpm >=9.12). Use `pnpm dev` for the full workspace loop or `pnpm dev:antd` to focus on the main app; both rely on `@vben/turbo-run` for hot reload. Create production bundles via `pnpm build`, or `pnpm build:docs` for the docs site, and verify the output with `pnpm preview`. Run `pnpm check` to execute circular dependency, type, and spell checks in one pass.

## Coding Style & Naming Conventions

TypeScript and Vue SFCs use two-space indentation and single quotes. Components, composables, and stores follow PascalCase (`UserTable.vue`, `useAuthStore.ts`), while directories and routes stay kebab-case. Formatting and linting run through `pnpm lint` or `pnpm format`, invoking the shared `@vben/eslint-config`, `@vben/stylelint-config`, and Prettier rules enforced by Lefthook pre-commit hooks.

## Testing Guidelines

Unit tests rely on Vitest with a DOM environment; place `*.spec.ts` files beside the code and run them with `pnpm test:unit` or `pnpm vitest -- --ui` for watch mode. End-to-end coverage uses Playwright; execute `pnpm test:e2e` after starting the mock backend (`pnpm --filter @vben/backend-mock dev`) and the target web app. Cover new routes, stores, and critical flows, and update fixtures under `apps/backend-mock` when APIs change.

## Commit & Pull Request Guidelines

Commits follow Conventional Commit syntax and are linted via `commitlint`; launch the guided prompt with `pnpm commit`. Scope names should reference the affected package or app (for example, `feat(web-antd): add audit log`). For pull requests, supply a concise summary, link related issues, list validation steps (`pnpm test:unit`, `pnpm lint`), and attach before/after screenshots when UI changes are present. Ensure CI is green and request review from the domain owner before merging.

## Environment & Configuration Tips

Scripts assume pnpm workspace awareness; avoid npm or yarn to prevent lockfile drift. Environment variables are layered in `apps/web-antd/.env*`; copy `.env.development` when creating a new setup and keep secrets out of version control. When adding dependencies, prefer `pnpm add <pkg> -F <target>` so shared graphs stay consistent.
