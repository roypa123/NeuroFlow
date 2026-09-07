Project: n8n-style Workflow Builder + OpenAI Agent Builder

Phase 0 — Research & Documentation (before writing any code)

Fully study the current project directory structure, existing code, configs, and dependencies before planning anything.
Produce a comprehensive design document (~100 pages) inside a docs/ folder, covering:
Product overview and goals (what this tool does, target users, core use cases)
Feature breakdown: workflow canvas, node types, agent builder, execution engine, credentials/auth, triggers, logging/monitoring
System architecture (high-level diagram + component responsibilities)
Frontend architecture: folder structure, state management strategy, data-fetching strategy, routing strategy, component hierarchy
Backend architecture: layered structure (models/schemas, views/routers, controllers, services, repositories), request lifecycle
Database schema design (entities, relationships, ER diagram) with PostgreSQL + Alembic migration strategy
API design (REST endpoint list, request/response contracts)
UI/UX design principles (visual style, canvas interaction patterns, node design, inspired by n8n's UI)
Security considerations (auth, credential storage/encryption, API key handling)
Testing strategy, deployment strategy, and a phased implementation roadmap
This document should be detailed enough that implementation can proceed directly from it.

Frontend

Stack: React + TypeScript, shadcn/ui for components, Zustand for state management, TanStack Query for server state/data fetching.
Visual style: closely modeled on n8n's UI (node-based canvas, drag-and-drop, side panels, minimal/clean aesthetic) but should look extremely polished and modern — not a rough clone.
Must include a visual agent-builder mode (comparable to OpenAI's Agent Builder) alongside the general workflow canvas.
Folder structure (modularized):
  src/
    api/
    components/
    config/
    context/
    endpoints/
    hooks/
    lib/
    pages/
    routing/
    types/
    utils/
Each domain feature (workflows, nodes, agents, credentials, etc.) should have clearly separated concerns across these folders — no business logic inside components.

Backend

Stack: FastAPI, PostgreSQL, Alembic for migrations.
Architecture: layered MVC + service pattern —
Models — SQLAlchemy ORM models / DB schema
Schemas — Pydantic request/response models
Views/Routers — route definitions only, no business logic
Controllers — request handling/orchestration
Services — core business logic, reusable across controllers
Repositories (optional but recommended) — DB access layer, isolated from services
Fully modular: each domain (workflows, nodes, executions, agents, auth, credentials) should be its own module with its own models/schemas/routers/controllers/services.
Use Alembic for all schema migrations — no manual DB changes.

Non-functional requirements

Code must be clean, typed, and consistently structured across both frontend and backend.
No monolithic files — enforce separation of concerns everywhere.
Document key architectural decisions inline (docstrings/comments) in addition to the docs/ folder.