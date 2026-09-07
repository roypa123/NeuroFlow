# 02 — Current State Audit

A factual inventory of the repository as of the start of Phase 0, plus the gap between what
exists and what the design requires. Everything here was verified by reading the files.

## 2.1 Repository layout

```
neuroflow/
├── .claude/CLAUDE.md          # project brief (the spec these docs expand)
├── p.md                       # original raw prompt
├── neuroflow-backend/
│   └── requirements.txt       # ONLY file. No application code exists.
└── neuroflow-frontend/        # Vite scaffold + full shadcn primitive set
```

Git: branch `main`, 4 commits, working tree clean. No CI, no Docker, no `.env.example`,
no `docs/` before this one.

## 2.2 Frontend — what exists

**Toolchain.** Vite 8.2, React 19.2, TypeScript 6.0 (`~6.0.2`), `@vitejs/plugin-react` 6.1,
ESLint 10 flat config with `react-hooks` and `react-refresh` plugins.

**Styling.** Tailwind CSS v4.3 via the `@tailwindcss/vite` plugin — CSS-first config, no
`tailwind.config.js`. `src/index.css` (129 lines) declares design tokens as an `@theme inline`
block mapping Tailwind color utilities to CSS custom properties, with `:root` and `.dark` token
sets in **OKLCH**. Dark mode uses a custom variant, `@custom-variant dark (&:is(.dark *))` —
class-based, driven by a `.dark` class on an ancestor. Font is Geist Variable via
`@fontsource-variable/geist`.

**Component library.** shadcn/ui, style `base-nova`, base color `neutral`, CSS variables on,
icon library `lucide`. **61 primitives are already vendored** into `src/components/ui/` —
including the full set this project needs (`sidebar`, `resizable`, `command`, `context-menu`,
`sheet`, `dialog`, `tabs`, `table`, `tooltip`, `popover`, `toast`, `chart`, `combobox`, `field`,
`empty`, `spinner`, `kbd`) plus a chat-oriented group (`message`, `message-scroller`, `bubble`,
`attachment`, `questionnaire`, `marker`) that is unusually well-suited to the agent builder's
test panel. Notably these are built on **`@base-ui/react`**, not Radix — a meaningful detail,
since API shapes differ from the Radix-era shadcn docs most engineers have memorised.

**Path alias.** `@/*` maps to `./src/*`, configured in both `tsconfig.app.json` and `vite.config.ts`.

**TS strictness.** `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`,
`verbatimModuleSyntax`, `erasableSyntaxOnly`, `moduleResolution: bundler`. Note that
`verbatimModuleSyntax` **requires `import type` for every type-only import** — a constant source
of build failures if the team is not told. `erasableSyntaxOnly` **bans TS enums and parameter
properties**; the codebase MUST use `as const` objects and union types instead.

**Application code.** Effectively none. `App.tsx` renders the stock shadcn demo Card.
`main.tsx` is the bare `createRoot` scaffold — no providers, no router. `src/lib/utils.ts` is a
one-line re-export, `export { cn } from "cn"`, i.e. the third-party `cn` package rather than the
usual local clsx + tailwind-merge helper. `src/hooks/use-mobile.ts` is the only hook.

**The eight domain folders — `api/`, `config/`, `context/`, `endpoints/`, `hooks/`, `lib/`,
`pages/`, `routing/`, `types/`, `utils/` — all exist and all are empty** except `hooks` (1 file)
and `lib` (1 file). The brief's folder contract is therefore an empty skeleton to be filled, not
an existing convention to be inferred. [04](./04-frontend-architecture.md) defines exactly what
belongs in each.

## 2.3 Frontend — dependency gap

Everything the design needs that is **not yet installed**:

| Package | Purpose | Doc |
|---|---|---|
| `zustand` | Client/UI state, canvas editor store | [05](./05-state-and-data-fetching.md) |
| `@tanstack/react-query` + devtools | All server state | [05](./05-state-and-data-fetching.md) |
| `react-router` v7 | Routing (declarative mode) | [04](./04-frontend-architecture.md) |
| `@xyflow/react` v12 | The node canvas | [06](./06-canvas-and-editor.md) |
| `axios` | HTTP client + interceptors | [05](./05-state-and-data-fetching.md) |
| `zod` | Runtime validation of API responses and node params | [04](./04-frontend-architecture.md) |
| `react-hook-form` + `@hookform/resolvers` | Parameter panel forms | [06](./06-canvas-and-editor.md) |
| `@monaco-editor/react` | Code node + expression editing | [06](./06-canvas-and-editor.md) |
| `elkjs` | Auto-layout ("tidy up") | [06](./06-canvas-and-editor.md) |
| `nanoid` | Client-side node/edge IDs | [06](./06-canvas-and-editor.md) |
| `vitest`, `@testing-library/react`, `msw`, `@playwright/test` | Testing | [17](./17-testing-strategy.md) |

**Already present and worth keeping:** `recharts` (execution metrics charts), `cmdk` (command
palette — the canvas node-search UX depends on it), `react-resizable-panels` (the three-pane
editor layout), `date-fns` (relative timestamps), `lucide-react`, `class-variance-authority`.

⚠️ **`@shadcn/react` and `shadcn` are both listed as runtime `dependencies`.** `shadcn` is a CLI
and belongs in `devDependencies`; but `src/index.css` does `@import "shadcn/tailwind.css"`, so the
package is load-bearing for styles and must not simply be deleted. Resolve during Phase 1 setup —
verify which import path the CSS actually needs before moving anything.

⚠️ **React 19 + Vite 8 + TS 6 is a very fresh stack.** `@xyflow/react` is the highest-risk
dependency against React 19's stricter effect and ref semantics. Phase 1 MUST begin with a
throwaway spike rendering 200 React Flow nodes under `StrictMode` before any real canvas work.

## 2.4 Backend — what exists

`neuroflow-backend/requirements.txt` and nothing else. **The file is UTF-16LE encoded with a
BOM**, which `pip install -r` will typically fail to parse — it must be rewritten as UTF-8 as the
first backend task.

Pinned versions, all current:

```
fastapi==0.141.1        starlette==1.6.0        uvicorn==0.52.4
SQLAlchemy==2.0.52      alembic==1.19.2         psycopg==3.3.5 (+binary)
pydantic==2.13.5        pydantic-settings==2.15.0
python-dotenv==1.2.3    PyYAML==6.0.3           websockets==17.1
anyio, click, greenlet, h11, httptools, watchfiles, Mako, MarkupSafe, idna, tzdata
```

**What the pins tell us.** `psycopg` v3 plus `greenlet` plus SQLAlchemy 2.0 means the **async ORM
path is intended** (`postgresql+psycopg://` with `create_async_engine`). `websockets` and
`httptools` mean real-time push was anticipated. `PyYAML` suggests YAML config or workflow
import/export. These align with the architecture in [03](./03-system-architecture.md); no pin
contradicts it.

## 2.5 Backend — dependency gap

| Package | Purpose | Doc |
|---|---|---|
| `httpx` | Outbound HTTP (HTTP Request node, model providers, OAuth) | [13](./13-node-catalog-and-sdk.md) |
| `cryptography` | AES-256-GCM credential envelope encryption | [15](./15-security-and-credentials.md) |
| `pyjwt` | Access/refresh tokens | [15](./15-security-and-credentials.md) |
| `argon2-cffi` (via `passlib[argon2]`) | Password hashing | [15](./15-security-and-credentials.md) |
| `redis` | Queue transport, pub/sub for log streaming, rate limits | [12](./12-execution-engine.md) |
| `arq` | Async job queue on Redis (chosen over Celery — ADR-007) | [12](./12-execution-engine.md) |
| `croniter` | Cron schedule parsing / next-fire computation | [12](./12-execution-engine.md) |
| `jsonschema` | Node parameter and agent-tool schema validation | [13](./13-node-catalog-and-sdk.md) |
| `structlog` | Structured JSON logging | [16](./16-observability.md) |
| `prometheus-client` | Metrics endpoint | [16](./16-observability.md) |
| `opentelemetry-*` | Tracing (optional, Phase 4) | [16](./16-observability.md) |
| `python-multipart` | File upload endpoints | [11](./11-api-design.md) |
| `email-validator` | Pydantic `EmailStr` | — |
| `tenacity` | Retry/backoff for provider calls | [12](./12-execution-engine.md) |
| `pytest`, `pytest-asyncio`, `pytest-cov`, `factory-boy`, `testcontainers` | Testing | [17](./17-testing-strategy.md) |
| `ruff`, `mypy` | Lint and type gate | [21](./21-glossary-and-conventions.md) |

Deliberately **not** added: an LLM SDK per provider. Provider calls go through a thin internal
`ProviderClient` over `httpx` (ADR-014), so adding a provider does not add a dependency.

## 2.6 Consequences for the plan

1. **The backend is greenfield.** No legacy to accommodate; [08](./08-backend-architecture.md)
   can be followed literally.
2. **The frontend is scaffolded but hollow.** The valuable part — 61 vetted, themed primitives on
   a coherent OKLCH token system — is exactly the part that is tedious to build. Phase 1 keeps all
   of it and adds only the state, routing, and canvas layers.
3. **Three latent traps to brief the team on before day one:** UTF-16 `requirements.txt`;
   `verbatimModuleSyntax` demanding `import type`; `erasableSyntaxOnly` banning enums.
4. **The riskiest unknown is React Flow on React 19.** It gates the canvas, which gates the
   product. Spike it first.
