# 17 — Testing Strategy

## 17.1 What we are actually protecting

Test effort should follow risk, not code volume. The three things that must never break:

1. **The engine produces correct results.** A workflow that silently computes the wrong thing is
   worse than one that fails — users trust output they do not verify.
2. **Secrets do not leak.** One incident is existential.
3. **Tenants are isolated.** Cross-org data access is the same category.

Everything else — a misaligned button, a wrong empty state — is a bug you fix on Monday. The
budget follows that ordering.

## 17.2 The shape of the pyramid

```
        ╱ E2E ╲          ~30 tests    Playwright, critical journeys only
      ╱─────────╲        ~400         Integration: API + real Postgres/Redis
    ╱─────────────╲      ~1200        Unit: services, engine, utils, components
```

Targets: **85% on `app/engine/`, `app/nodes/`, and every `service.py`**; 70% overall; no coverage
target on routers or components (coverage there measures rendering, not correctness).

Coverage is a diagnostic, not a goal. A 100%-covered service with no assertion about behaviour is
worthless, and everyone knows it. Review asks "what would break if this test were deleted?"

## 17.3 Backend unit tests

`pytest` + `pytest-asyncio`. No database, no network, no Redis. Milliseconds each.

```python
async def test_update_graph_rejects_stale_base_version() -> None:
    repo = FakeWorkflowRepository(active_version_id=UUID("…aaa"))
    service = WorkflowService(repo, FakeVersionRepository(), FakeAuditService())

    with pytest.raises(VersionConflict) as exc:
        await service.update_graph(
            workflow_id=WORKFLOW_ID, graph=VALID_GRAPH,
            actor_id=USER_ID, base_version_id=UUID("…bbb"),
        )
    assert exc.value.actual == UUID("…aaa")
```

Services are testable in isolation precisely because they take repositories as constructor
arguments and never touch FastAPI ([08](./08-backend-architecture.md) §8.1). If a service is hard
to unit test, the layering is wrong — that is the useful signal.

### Engine tests get the most attention

This is where correctness lives:

| Area | Cases |
|---|---|
| DAG construction | cycles rejected, orphans detected, unknown node types, multi-trigger |
| Scheduling | topological order, parallel branches, IF skips the untaken branch, Merge waits correctly, Merge does **not** wait on a skipped branch |
| Item flow | fan-out, pairing/provenance, empty input, single item, 10k items |
| Loops | iteration count, `maxIterations` ceiling, `run_index` increments, back-edge validation |
| Errors | `stop` / `continue` / `continueErrorOutput`, retry counts, backoff timing, non-idempotent nodes not auto-retried |
| Suspension | suspend, resume by token, resume by time, resume after worker restart |
| Expressions | every builtin, `$node` refs, nulls, type coercion, **sandbox escapes rejected**, timeout enforced |

**Sandbox escape tests are non-negotiable** and belong in this suite as a table of known attack
strings (`__class__.__bases__`, `import os`, comprehension bombs, `getattr` chains), each asserted
to raise rather than execute.

## 17.4 Backend integration tests

Real Postgres and Redis via `testcontainers` — never SQLite. SQLite lacks JSONB operators,
`citext`, partial indexes, `FOR UPDATE SKIP LOCKED`, and array types, so tests would pass against
a database that does not resemble production.

```python
@pytest.fixture
async def client(db_engine, redis) -> AsyncIterator[AsyncClient]:
    app = create_app(settings_for_test(db_engine, redis))
    async with AsyncClient(transport=ASGITransport(app), base_url="http://t") as c:
        yield c

async def test_member_cannot_read_other_org_workflow(client, factories) -> None:
    other = await factories.workflow(org="acme")
    token = await factories.token(org="globex", role="admin")
    r = await client.get(f"/api/v1/workflows/{other.id}",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404       # 404, not 403 — 403 confirms existence
```

Schema is created by running **Alembic migrations**, not `metadata.create_all()`. This tests the
migrations, which are otherwise only ever exercised in production — the worst place to discover
they are broken.

Each test runs in a transaction rolled back afterwards; tests are independent and order-agnostic.

**Mandatory integration coverage:**

- Every endpoint: happy path, 401, 403, 404, 422.
- **Tenant isolation for every resource type.** A parameterised test over all resources asserting
  cross-org access returns 404. This is the highest-value test file in the repo.
- Migration up/down/up on a fresh database.
- The full webhook → execution → result path.
- Concurrent `PATCH` producing exactly one 409.
- The **secret-leak sentinel test**: create a credential whose value is `SENTINEL_A1B2C3`, run a
  workflow using it, then assert the string appears in no execution data, no log capture, and no
  API response body.

## 17.5 Node tests

Every node gets two tiers:

1. **Unit** — mocked transport, asserting request shape and output items. Covers parameter
   mapping, pagination, error translation, and item pairing.
2. **Recorded integration** — one cassette-based test per node against a real recorded response,
   so schema drift in a third-party API is detectable.

Plus a **registry conformance test** that runs over every registered descriptor asserting: unique
`key`, non-empty description on every property, `subtitle` parses, referenced
`load_options_method`s exist, and icons resolve. One test, whole catalog, catches most authoring
mistakes at CI time rather than in the UI.

## 17.6 Frontend tests

**Unit (Vitest)** — `utils/` gets real coverage: graph algorithms (topological sort, cycle
detection, reachability), expression parsing, formatting. These are pure and cheap, and graph bugs
are expensive.

**Component (Testing Library)** — behaviour, not implementation. Query by role and label, never by
class name or test id where a role exists.

```tsx
it('shows a version conflict dialog when saving stale changes', async () => {
  server.use(http.patch('/api/v1/workflows/:id', () =>
    HttpResponse.json({ error: { code: 'workflow.version_conflict', … } }, { status: 409 })));

  render(<WorkflowEditorPage />, { wrapper: TestProviders });
  await userEvent.click(await screen.findByRole('button', { name: /save/i }));

  expect(await screen.findByRole('dialog', { name: /modified by someone else/i }))
    .toBeInTheDocument();
});
```

**MSW for all network mocking**, with handlers derived from the same fixtures the backend tests
use — this is the cheap approximation of contract testing described in §17.8.

**Canvas testing** is deliberately shallow at the component level: React Flow's rendering is not
ours to test. We test the **store** (add/remove/connect/undo/redo, cycle rejection) as pure logic,
and cover the canvas interactively in E2E.

**What we do not test:** shadcn primitives, styling, exact snapshot output. Snapshot tests on UI
produce churn and catch almost nothing; they are banned.

## 17.7 Architecture tests

Rules from [04](./04-frontend-architecture.md) §4.5 and [08](./08-backend-architecture.md) §8.10,
enforced mechanically. A layering rule that is not checked by CI is a comment.

Backend, via `import-linter`:

```ini
[importlinter:contract:api-does-not-execute]
name = API layer must not import the execution engine or nodes
type = forbidden
source_modules = app.api, app.modules.*.router, app.modules.*.controller
forbidden_modules = app.engine.executor, app.nodes

[importlinter:contract:services-are-framework-free]
source_modules = app.modules.*.service
forbidden_modules = fastapi, starlette

[importlinter:contract:repository-encapsulation]
name = A module may not import another module's repository
type = independence
modules = app.modules.workflows.repository, app.modules.executions.repository, …
```

Plus an explicit test asserting `CredentialService.get_decrypted` is unreachable from any router
module. Frontend equivalents run through `eslint-plugin-boundaries`.

## 17.8 Contract testing

Frontend and backend are separate deployables, so drift is a real risk and integration tests on
either side alone will not catch it.

**v1 approach (pragmatic):** the backend's integration tests emit response fixtures to
`tests/fixtures/api/`. The frontend's MSW handlers load those same files, and a CI job fails if a
fixture changes without the frontend's zod schemas still parsing it.

This is not Pact. It is roughly 5% of the work and catches the overwhelming majority of real
drift, which is the right trade at this size. Revisit if the team splits across repos.

## 17.9 E2E tests

Playwright, against a full Docker Compose stack. **Thirty tests, maximum.** E2E suites rot in
proportion to their size, and a flaky suite is worse than no suite because it teaches people to
re-run rather than investigate.

The journeys that earn a slot:

1. Sign up → verify → land on an empty workflow list
2. Create workflow → add Manual Trigger + Set → run → see success on canvas
3. UC-1: webhook → transform → HTTP call, triggered by a real HTTP POST
4. Add a credential → use it in a node → run → confirm the secret is absent from every response
5. Failing workflow → inspect error → fix → retry from failed node → success
6. Branching: IF with both paths, verified via node statuses
7. Agent: configure model + one tool → chat in the test panel → tool call visible in trace
8. Version history: edit → save → restore a previous version
9. Concurrent edit → 409 → reload → save
10. Schedule a workflow → confirm it fires

Rules: no `waitForTimeout` — wait for state; every test creates its own data and cleans up;
tests run in parallel against isolated orgs; a flaky test is quarantined **and fixed within one
sprint or deleted**, never left to erode trust in the suite.

## 17.10 Performance tests

| Test | Tool | Gate |
|---|---|---|
| Canvas @ 150 nodes | Playwright + CDP tracing | interaction p95 < 100 ms |
| API load | k6 | p95 < 120 ms @ 100 rps |
| Execution throughput | k6 | 100 concurrent executions, queue wait p95 < 5 s |
| Executions list @ 1M rows | pytest + seeded DB | < 200 ms |
| Bundle size | `vite build` + size-limit | initial chunk < 300 KB gzip |

These run nightly, not per-PR, except bundle size, which is cheap and catches accidental imports
of a large library into the entry chunk — a very common regression.

## 17.11 CI pipeline

```
PR:
  lint          ruff · mypy --strict · eslint · tsc --noEmit          ~2 min
  arch          import-linter · eslint boundaries                     ~30 s
  test:unit     pytest -m unit · vitest                               ~3 min
  test:integration  testcontainers pg+redis                           ~5 min
  security      pip-audit · npm audit · secret scan (gitleaks)        ~1 min
  build         docker build api+worker · vite build                  ~4 min
main:
  + e2e         playwright against compose stack                      ~8 min
  + migrations  up/down/up on a fresh database
nightly:
  + performance · dependency updates · full E2E matrix
```

**Merge gates:** every PR job green; coverage must not drop more than 1%; no new high-severity
advisories. Unit and integration run in parallel; nothing blocks on the nightly suite.

## 17.12 Test data

Factories (`factory-boy`), never fixtures-as-JSON-blobs. Factories compose, express intent, and do
not rot:

```python
workflow = await factories.workflow(
    project=project,
    graph=GraphFactory.linear(["manualTrigger", "set", "http"]),
)
execution = await factories.execution(workflow=workflow, status="error",
                                      failed_node="http")
```

`GraphFactory` offers named topologies — `linear`, `branching`, `with_loop`, `with_agent`,
`diamond`, `cyclic` (for rejection tests). Engine tests are unreadable without it, and readable
engine tests are what keep the engine correct as it changes.
