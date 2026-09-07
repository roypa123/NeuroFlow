# 01 — Product Overview

## 1.1 One-sentence definition

NeuroFlow is a self-hostable platform where a technical user builds an automation by dragging
nodes onto a canvas, wiring them together, and pressing Run — and where the same canvas can be
switched into an *agent* mode for building LLM-driven systems with tools, memory, and routing.

## 1.2 The problem

Automation tooling today splits into three camps, each with a real gap:

| Camp | Examples | Gap |
|---|---|---|
| Consumer no-code | Zapier, Make | Linear, opaque, expensive at volume, weak branching/looping, no self-hosting, no real code escape hatch |
| Developer workflow engines | Airflow, Temporal, Prefect | Powerful and correct, but code-only. A non-Python-fluent operator cannot author or even read a pipeline |
| Agent frameworks | LangGraph, CrewAI, OpenAI Agents SDK | Code-first, and the *graph* — the thing you most want to see — is invisible until you draw it yourself |

n8n closed the first two gaps well. The remaining gap, and NeuroFlow's wedge, is that **agent
building and workflow building are still two different products with two different mental
models**, even though an agent is structurally just a graph with LLM nodes and a loop. Teams end
up running an automation tool *and* an agent framework, gluing them with webhooks, and losing
unified observability at the seam.

NeuroFlow's answer: **one graph engine, one execution log, one credential vault, two authoring
surfaces tuned to two different kinds of thinking.**

## 1.3 Goals

**G1 — Legible.** A person who did not build the workflow can open it and understand what it
does in under a minute. This constrains node visual design, edge routing, and naming more than
any other goal.

**G2 — Debuggable.** Every execution answers, without guesswork: which nodes ran, in what order,
what data entered and left each one, what failed, and why. Data inspection is a first-class
surface, not a log dump.

**G3 — Escape-hatchable.** Anything the node catalog does not cover is reachable via an HTTP
Request node, a Code node, or a custom node — without leaving the canvas.

**G4 — Self-hostable in one command.** `docker compose up` yields a working instance with
Postgres, Redis, API, worker, and web. No managed-service dependency is required to run.

**G5 — Agent-native.** Building an agent — model, system prompt, tools, memory, guardrails,
handoffs — is a canvas activity with the same run/inspect/replay loop as any other workflow.

**G6 — Extremely polished.** The visual bar is "a product people screenshot," not "a functional
clone." See [07 — UI/UX Design System](./07-ui-ux-design-system.md). This is treated as a
functional requirement, not decoration: the canvas is the product.

## 1.4 Explicit non-goals (v1)

Naming these prevents scope drift; each is revisitable later via ADR.

- **N1 — Not a general-purpose ETL/big-data engine.** Executions carry thousands of items, not
  millions of rows. Bulk data belongs in a warehouse; NeuroFlow orchestrates, it does not batch-process.
- **N2 — No marketplace / community node registry in v1.** Custom nodes are loaded from a
  server-side directory by an operator. A signed, sandboxed third-party registry is a large
  security surface and is deferred. `TODO(phase-6)`
- **N3 — No multi-region active-active.** Single-region, single Postgres primary with replicas.
- **N4 — No visual debugger with breakpoints/step-through.** Pin data + partial execution covers
  ~90% of the need at ~10% of the cost. `TODO(phase-5)`
- **N5 — No white-label/embedded SDK.** `TODO(phase-6)`
- **N6 — Not a model host.** NeuroFlow calls model providers; it does not serve models.

## 1.5 Target users

**Persona A — "Priya", the automation engineer.** *Primary.* Ops or platform engineer at a
50–500-person company. Comfortable with HTTP, JSON, and light JS; not necessarily a backend
developer. Owns 20–100 internal workflows. Her pain is *maintenance*: inheriting workflows and
debugging 3am failures. She optimizes for legibility and observability, and she is the reason
G1 and G2 outrank feature count.

**Persona B — "Marcus", the AI application developer.** Building a support triage agent or an
internal research assistant. Fluent in Python and LLM APIs. He *could* write LangGraph, but wants
the graph visible, the prompt iterable without a redeploy, and traces his PM can read. He needs
the Code node and the custom-node SDK to exist, or he will not adopt.

**Persona C — "Dana", the technical operator.** Support lead or RevOps. Does not write code but
reads JSON fine. Duplicates and tweaks workflows built by Priya, and watches the executions list
daily. She is the reason templates, clear error copy, and a good executions view matter.

**Persona D — "Sam", the platform admin.** *Secondary but blocking.* Owns the self-hosted
deployment. Cares about SSO, RBAC, audit logs, credential encryption, backups, and upgrade
safety. Sam does not use the canvas; Sam vetoes the purchase if [15 — Security](./15-security-and-credentials.md)
is not satisfied.

## 1.6 Core use cases

Each is a concrete acceptance target for the roadmap in [19](./19-roadmap.md).

**UC-1 — Webhook → transform → API call.** Inbound webhook, reshape payload, POST to a CRM,
respond 200. Exercises: trigger, expressions, HTTP node, credentials, sync response.
*The v1 smoke test.*

**UC-2 — Scheduled sync with pagination.** Every hour, pull paginated records since a cursor,
upsert into Postgres, alert Slack on failure. Exercises: cron trigger, loop, DB node, error
branch, static workflow-scoped state for the cursor.

**UC-3 — Branching approval flow.** New record → LLM classifies risk → high risk routes to a
human-approval wait node → resumes on click. Exercises: IF/Switch, LLM node, long-lived
suspended executions, resume-by-token.

**UC-4 — Support triage agent.** Ticket in → agent with `search_docs`, `lookup_order`, and
`escalate` tools loops until it answers → posts a reply and logs the trace. Exercises: the whole
agent surface — tool calling, loop control, token accounting, guardrails.

**UC-5 — Multi-agent research pipeline.** Planner agent decomposes a question, N researcher
agents run in parallel over web search, a writer agent synthesizes. Exercises: sub-workflows,
parallel fan-out/fan-in, handoffs, cost ceilings.

**UC-6 — Error-handling workflow.** A dedicated workflow that runs whenever any other workflow
fails, enriching and routing the alert. Exercises: the error-trigger, execution metadata API.

## 1.7 What "done" means for v1

A v1 release ships when UC-1, UC-2, UC-3, and UC-4 are demonstrable end-to-end on a fresh
`docker compose up`, by a user who has read nothing but the in-app onboarding, with:

- 25+ built-in node types including HTTP, Code, IF, Switch, Merge, Loop, Wait, Set, Filter, and
  the LLM/Agent/Tool family;
- credential storage that a security reviewer signs off on;
- an executions view that makes a failure diagnosable without server access;
- p95 UI interaction latency under 100 ms on a 150-node canvas.

## 1.8 Positioning summary

> NeuroFlow is n8n's legibility and self-hostability, plus a real agent builder that shares the
> same engine — so the automation *around* your agent and the agent itself live in one graph,
> one log, and one vault.

The bet is that the boundary between "workflow" and "agent" is an artifact of tooling history,
not of the problems users actually have, and that collapsing it is worth more than matching any
competitor's integration count.
