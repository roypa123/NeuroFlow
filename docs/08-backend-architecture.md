# 08 — Backend Architecture

## 8.1 The layering contract

The brief specifies MVC + services. Spelled out precisely, with the rule that makes each layer
worth having:

```
HTTP request
    │
    ▼
┌──────────────┐  Router      — path, deps, response_model. ZERO logic.
├──────────────┤  Controller  — authorize, orchestrate services, map to response schema.
├──────────────┤  Service     — business rules. Framework-agnostic. Reusable by worker & CLI.
├──────────────┤  Repository  — SQL. No business rules.
└──────────────┘  Model       — SQLAlchemy ORM.
    │
    ▼
PostgreSQL
```

**The test for each layer:**

| Layer | It is wrong if… |
|---|---|
| Router | it contains an `if` that is not a dependency |
| Controller | it contains a `select()` or a domain rule |
| Service | it imports `fastapi`, raises `HTTPException`, or touches `Request` |
| Repository | it makes a decision the caller could not predict from the method name |
| Model | it contains business methods beyond trivial derived properties |

The service rule is the load-bearing one. **Services must be callable from the worker**, which has
no HTTP context at all. If a service raises `HTTPException`, the worker cannot use it, and the
whole "one engine" premise collapses.

### Why a controller layer at all

FastAPI teams often merge controller into router. We keep them separate because:

1. Routers become pure declaration, so the API surface is auditable by reading one file per module.
2. Authorization lives in one predictable place instead of being scattered.
3. Controllers are testable without an HTTP client.
4. An endpoint that orchestrates three services has somewhere to live that is not a service.

The cost is one extra file per module. The benefit is that "where does this go?" has one answer.

## 8.2 Directory structure

```
neuroflow-backend/
├── alembic/{env.py, versions/}
├── alembic.ini
├── app/
│   ├── main.py                 # FastAPI factory, middleware, router mounting, lifespan
│   ├── worker.py               # arq WorkerSettings — the second entrypoint
│   ├── scheduler.py            # cron ticker entrypoint
│   ├── core/                   # cross-cutting, framework-level
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── database.py         # async engine, session factory, get_session dep
│   │   ├── redis.py            # redis pool
│   │   ├── security.py         # JWT encode/decode, password hash/verify
│   │   ├── crypto.py           # envelope encryption for credentials
│   │   ├── permissions.py      # RBAC matrix + require() helper
│   │   ├── exceptions.py       # AppError hierarchy + FastAPI handlers
│   │   ├── pagination.py       # keyset + offset helpers
│   │   ├── logging.py          # structlog config
│   │   ├── middleware.py       # request id, timing, access log
│   │   └── types.py            # UUIDPk, TimestampMixin, JSONB alias
│   ├── modules/                # ← every domain is a vertical slice
│   │   ├── auth/  users/  organizations/  projects/
│   │   ├── credentials/  workflows/  executions/  nodes/
│   │   ├── agents/  webhooks/  schedules/  variables/  audit/
│   ├── engine/                 # execution engine — imported by worker, NOT by routers
│   │   ├── executor.py         # DAG orchestration
│   │   ├── context.py          # ExecutionContext
│   │   ├── data.py             # Item / NodeInput / NodeOutput
│   │   ├── expressions/        # tokenizer, evaluator, sandbox, builtins
│   │   ├── registry.py         # node type registry
│   │   └── errors.py
│   ├── nodes/                  # node implementations, one package per node
│   │   ├── base.py             # BaseNode, NodeTypeDescriptor
│   │   ├── triggers/  core/  data/  ai/  integrations/
│   ├── providers/              # LLM provider adapters over httpx
│   └── api/
│       ├── v1.py               # the only place routers are aggregated
│       └── deps.py             # shared dependencies
└── tests/{unit,integration,e2e,factories,conftest.py}
```

## 8.3 Module anatomy

Every module in `app/modules/` has the same eight files. Uniformity beats cleverness; an engineer
opening `agents/` should already know where everything is.

```
modules/workflows/
├── __init__.py
├── models.py         # SQLAlchemy: Workflow, WorkflowVersion, WorkflowTag
├── schemas.py        # Pydantic: WorkflowCreate/Update/Read/ListItem, GraphSchema
├── repository.py     # WorkflowRepository — all SQL
├── service.py        # WorkflowService — business rules
├── controller.py     # WorkflowController — orchestration + authz
├── router.py         # APIRouter — declarations only
├── exceptions.py     # WorkflowNotFound, WorkflowValidationError, VersionConflict
└── dependencies.py   # module-specific DI (e.g. get_workflow_or_404)
```

### Layer examples

```python
# repository.py — SQL only
class WorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workflow_id: UUID) -> Workflow | None:
        stmt = (select(Workflow)
                .where(Workflow.id == workflow_id, Workflow.deleted_at.is_(None))
                .options(selectinload(Workflow.active_version)))
        return await self._session.scalar(stmt)

    async def list_by_project(
        self, project_id: UUID, *, cursor: Cursor | None, limit: int
    ) -> Sequence[Workflow]: ...
```

```python
# service.py — business rules, framework-agnostic
class WorkflowService:
    def __init__(self, repo: WorkflowRepository, versions: WorkflowVersionRepository,
                 audit: AuditService) -> None: ...

    async def update_graph(
        self, *, workflow_id: UUID, graph: Graph, actor_id: UUID, base_version_id: UUID | None
    ) -> WorkflowVersion:
        """Create a new immutable version.

        Raises VersionConflict if base_version_id is not the current active version,
        which is how concurrent editors are detected (optimistic concurrency).
        """
        workflow = await self._repo.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFound(workflow_id)
        if base_version_id and workflow.active_version_id != base_version_id:
            raise VersionConflict(expected=base_version_id, actual=workflow.active_version_id)
        GraphValidator(registry).validate(graph)          # cycles, unknown types, required params
        version = await self._versions.create(workflow_id, graph, actor_id)
        await self._repo.set_active_version(workflow_id, version.id)
        await self._audit.record("workflow.updated", actor_id, workflow_id)
        return version
```

```python
# controller.py — authorize + orchestrate + map
class WorkflowController:
    async def update(self, ctx: RequestContext, workflow_id: UUID,
                     payload: WorkflowUpdate) -> WorkflowRead:
        await self._authz.require(ctx, Permission.WORKFLOW_WRITE, workflow_id)
        version = await self._service.update_graph(
            workflow_id=workflow_id, graph=payload.graph,
            actor_id=ctx.user_id, base_version_id=payload.base_version_id,
        )
        return WorkflowRead.from_domain(version.workflow, version)
```

```python
# router.py — declaration only
router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    controller: Annotated[WorkflowController, Depends(get_workflow_controller)],
) -> WorkflowRead:
    return await controller.update(ctx, workflow_id, payload)
```

That router function is the *maximum* amount of code a route is allowed to contain.

## 8.4 Dependency injection

FastAPI's `Depends`, wired bottom-up, with no global singletons for anything stateful:

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

def get_workflow_repository(s: SessionDep) -> WorkflowRepository: return WorkflowRepository(s)
def get_workflow_service(r: WorkflowRepoDep, v: VersionRepoDep, a: AuditDep) -> WorkflowService: ...
def get_workflow_controller(s: WorkflowServiceDep, az: AuthzDep) -> WorkflowController: ...
```

Type aliases (`SessionDep = Annotated[AsyncSession, Depends(get_session)]`) keep signatures
readable. This structure makes every layer trivially replaceable in tests: override one provider.

**Transaction boundary is the request.** `get_session` commits on success and rolls back on any
exception. Services never call `commit()` — a service that commits cannot be composed with another
service in the same unit of work, which is exactly the flexibility we are paying the layering tax
to get.

The worker builds the same objects manually through a `session_scope()` context manager, since it
has no `Depends` machinery. Same services, same repositories, different wiring.

## 8.5 Error handling

One exception hierarchy, translated to HTTP in exactly one place:

```python
class AppError(Exception):
    code: str = "internal_error"
    http_status: int = 500
    def __init__(self, message: str, *, details: Any = None) -> None: ...

class NotFoundError(AppError):      http_status = 404; code = "not_found"
class ValidationError(AppError):    http_status = 422; code = "validation_error"
class PermissionError(AppError):    http_status = 403; code = "forbidden"
class ConflictError(AppError):      http_status = 409; code = "conflict"
class RateLimitError(AppError):     http_status = 429; code = "rate_limited"
class ExternalServiceError(AppError): http_status = 502; code = "external_service_error"
```

Module exceptions subclass these with specific codes (`WorkflowNotFound.code =
"workflow.not_found"`). A single handler in `core/exceptions.py` renders the wire format from
[11](./11-api-design.md) §11.4 and logs with the request id.

**Services raise `AppError` subclasses, never `HTTPException`.** This is what keeps them usable
from the worker. The `500` handler logs the traceback and returns a generic message plus the
request id — internal detail never reaches a client.

## 8.6 Models and conventions

```python
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s", "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })

class UUIDPrimaryKey:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

The **naming convention is not cosmetic**: without it Alembic autogenerates unnamed constraints
that cannot be dropped in a later migration without raw SQL. Set it before the first migration.

Rules: tables plural snake_case; **UUIDv7 primary keys** (time-ordered, so they index like
sequential integers while staying non-enumerable — ADR-003); `timestamptz` always, UTC always;
soft delete via `deleted_at` only where restore is a real requirement (workflows, credentials),
hard delete elsewhere; every FK has an index; `Mapped[...]` annotations on every column so mypy
is meaningful.

## 8.7 Schemas

Three schema flavours per resource, and the distinction matters:

- `XCreate` — what a client may send on POST. Excludes server-owned fields entirely, so
  mass-assignment is impossible by construction.
- `XUpdate` — all fields optional; `model_fields_set` distinguishes "set to null" from "not sent".
- `XRead` / `XListItem` — what the server returns. `ListItem` is deliberately lighter: list
  endpoints do not return graphs or execution payloads.

```python
class WorkflowBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True,
                              alias_generator=to_camel)
```

⚠️ **camelCase on the wire, snake_case in Python.** Decided in ADR-019: it keeps both languages
idiomatic and costs one config line. It must be applied consistently from the first endpoint —
mixed conventions are far worse than either choice.

Secrets are structurally unrepresentable in read schemas: `CredentialRead` has no `data` field at
all. Not redacted — absent. You cannot leak a field that does not exist on the model.

## 8.8 Configuration

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    environment: Literal["local", "test", "staging", "production"] = "local"
    database_url: PostgresDsn
    redis_url: RedisDsn
    secret_key: SecretStr                 # JWT signing
    credential_master_key: SecretStr      # base64, 32 bytes — see 15
    access_token_ttl: timedelta = timedelta(minutes=15)
    refresh_token_ttl: timedelta = timedelta(days=30)
    cors_origins: list[AnyHttpUrl] = []
    max_execution_seconds: int = 3600
    max_payload_mb: int = 16
    ...

@lru_cache
def get_settings() -> Settings: return Settings()
```

Settings are validated at import time, so a missing or malformed variable fails at boot with a
readable Pydantic error rather than at 3am inside a request. In production, `secret_key` and
`credential_master_key` MUST NOT have defaults — a default secret that ships is a vulnerability.

## 8.9 Middleware order

Order is behaviour, not preference:

```
1. RequestIDMiddleware      # generate/propagate X-Request-Id; bind to structlog context
2. TimingMiddleware         # duration + X-Response-Time
3. CORSMiddleware           # explicit origins; never "*" with credentials
4. GZipMiddleware           # min 1000 bytes
5. RateLimitMiddleware      # redis token bucket, per-user and per-IP
6. AccessLogMiddleware      # structured line at response time
```

The request ID is generated first so every downstream log line — including panics in middleware
below it — carries it.

## 8.10 The `engine/` boundary

`app/engine/` and `app/nodes/` are imported by the **worker only**. The API's sole contact with
them is `engine/registry.py`, which it reads to serve the node-type catalog to the frontend, and
`GraphValidator`, which it uses to validate graphs on save.

This is enforced by an import-linter rule in CI (ADR-002 / [17](./17-testing-strategy.md) §17.7).
The reason is blunt: if a router can import a node, someone will eventually execute one inside a
request, and the entire isolation guarantee of [03](./03-system-architecture.md) evaporates.

## 8.11 Async discipline

Everything is async: `create_async_engine` with `postgresql+psycopg://`, async sessions, `httpx.AsyncClient`.

**The one rule that actually matters:** a blocking call in an async function stalls the entire
event loop, which in a worker means every concurrently-running execution. Any sync library call —
a synchronous SDK, a CPU-heavy transform, `time.sleep` — MUST be wrapped in
`anyio.to_thread.run_sync()`. The Code node, which runs arbitrary user JavaScript, runs in a
subprocess with hard CPU and memory limits, not in a thread ([15](./15-security-and-credentials.md) §15.8).

Connection pools: API `pool_size=20, max_overflow=10`; worker sized to concurrency; both with
`pool_pre_ping=True` so a recycled Postgres connection surfaces as a reconnect rather than a
random 500.
