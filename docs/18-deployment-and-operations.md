# 18 — Deployment & Operations

Goal G4 from [01](./01-product-overview.md): a working instance from `docker compose up`, with no
managed-service dependency. Everything here follows from that.

## 18.1 Topology

Five services, as established in [03](./03-system-architecture.md) §3.3:

```yaml
services:
  proxy:      # Caddy — TLS, static frontend, /api and /webhook reverse proxy
  api:        # uvicorn app.main:app
  worker:     # arq app.worker.WorkerSettings
  scheduler:  # python -m app.scheduler   (exactly one)
  postgres:   # 16-alpine
  redis:      # 7-alpine
  minio:      # optional; S3 in cloud deployments
```

`api`, `worker`, and `scheduler` run the **same image** with different commands. This eliminates
the "the worker has a different dependency set" class of bug outright, and halves build time.

⚠️ **This is the general-case reference topology.** The `docker-compose.yml` actually in this repo
takes a documented deviation from it, because the target host already has the infrastructure: it
omits `postgres`/`redis` (points `DATABASE_URL`/`REDIS_URL` at externally-provisioned instances —
e.g. Dokploy-managed — instead) and omits the `proxy` container (the host runs its own nginx,
config in `proxy/neuroflow.conf`, terminating TLS and reverse-proxying to the ports `api` and `web`
publish). Reasoning and instructions for reverting to the fully self-contained version live in the
compose file's own header comment. Both choices are legitimate per §18.1's own framing — Caddy vs.
nginx and managed vs. containerized datastores were never meant to be hard requirements.

## 18.2 Images

**Backend** — multi-stage, non-root, no build toolchain in the runtime layer:

```dockerfile
FROM python:3.13-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim AS runtime
RUN groupadd -r app && useradd -r -g app app \
 && apt-get update && apt-get install -y --no-install-recommends libpq5 nodejs \
 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app . .
USER app
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

`nodejs` is present solely for the Code node subprocess ([15](./15-security-and-credentials.md) §15.8).
In hardened deployments, run workers from a separate image that includes it and keep it out of the
API image entirely — the API never executes user code, so it should not carry a JS runtime.

**Frontend** — built to static files and served by a tiny static server. No Node in production:

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build          # tsc -b && vite build

FROM nginx:1.27-alpine     # or caddy:2-alpine -- either works; this repo uses nginx
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

⚠️ **The API base URL must be runtime-configurable, not baked in at build time.** Vite inlines
`import.meta.env` at build, which means a self-hosted user cannot point the same image at their own
host. Emit a `/config.js` at container start that sets `window.__NEUROFLOW_CONFIG__`, and have
`config/env.ts` read it with the build-time value as a fallback. Getting this wrong forces every
self-hoster to rebuild the frontend, which they will not do.

## 18.3 Compose (self-host reference)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment: [POSTGRES_DB=neuroflow, POSTGRES_USER=neuroflow, POSTGRES_PASSWORD=${DB_PASSWORD}]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: {test: ["CMD-SHELL","pg_isready -U neuroflow"], interval: 5s, retries: 10}

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy noeviction
    volumes: [redisdata:/data]

  migrate:
    image: neuroflow/backend:${TAG}
    command: alembic upgrade head
    depends_on: {postgres: {condition: service_healthy}}
    restart: "no"

  api:
    image: neuroflow/backend:${TAG}
    depends_on: {migrate: {condition: service_completed_successfully}}
    deploy: {replicas: 2}

  worker:
    image: neuroflow/backend:${TAG}
    command: arq app.worker.WorkerSettings
    depends_on: {migrate: {condition: service_completed_successfully}}
    deploy: {replicas: 2}

  scheduler:
    image: neuroflow/backend:${TAG}
    command: python -m app.scheduler
    deploy: {replicas: 1}     # MUST remain 1; also lock-guarded at runtime
```

**`maxmemory-policy noeviction` is deliberate.** The default `allkeys-lru` would silently evict
queued jobs under memory pressure, losing executions with no error anywhere. Failing loudly on a
full Redis is far better than losing work quietly.

Migrations run as a **separate one-shot service** that other services wait on, rather than in an
API entrypoint. Running migrations from N API replicas means N concurrent `alembic upgrade` calls
racing for the same advisory lock.

## 18.4 Configuration

| Variable | Required | Default | Notes |
|---|:--:|---|---|
| `ENVIRONMENT` | | `local` | `local`\|`test`\|`staging`\|`production` |
| `DATABASE_URL` | ✓ | — | `postgresql+psycopg://…` |
| `REDIS_URL` | ✓ | — | |
| `SECRET_KEY` | ✓ | — | JWT signing. **No default in production** |
| `CREDENTIAL_MASTER_KEY` | ✓ | — | base64 32 bytes. **Losing it loses every credential** |
| `CORS_ORIGINS` | ✓ | `[]` | Explicit list; never `*` |
| `PUBLIC_URL` | ✓ | — | Used to build webhook URLs |
| `S3_ENDPOINT` / `S3_BUCKET` / keys | | — | Falls back to inline-only payloads |
| `WORKER_MAX_JOBS` | | `10` | Concurrent executions per worker |
| `MAX_EXECUTION_SECONDS` | | `3600` | |
| `MAX_PAYLOAD_MB` | | `16` | |
| `EXECUTION_RETENTION_DAYS` | | `30` | |
| `CODE_NODE_ENABLED` | | `true` | Set `false` in untrusted multi-tenant deployments |
| `CODE_NODE_NETWORK` | | `false` | |
| `SSRF_ALLOW_CIDRS` | | `[]` | Explicit escape hatch for internal APIs |
| `LOG_LEVEL` | | `info` | |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | | — | Tracing off when unset |

Generate secrets with `openssl rand -base64 32`. The startup banner must print which required
secrets are missing and exit non-zero — a service that boots with a default signing key is a
vulnerability that nobody notices for months.

## 18.5 Environments

| | Local | Staging | Production |
|---|---|---|---|
| Deploy | compose | compose / k8s | k8s or compose + HA |
| Postgres | container | managed, small | managed, HA, PITR |
| Replicas | 1/1/1 | 2/2/1 | 3+/4+/1 |
| Migrations | manual | automatic | automatic, gated |
| Docs UI | on | on | **off** |
| Log level | debug | info | info |
| Tracing | off | 10% | 1% + all errors |

Staging must run the **same image** as production and hold a sanitised copy of production-shaped
data. Staging with 40 rows tests nothing that matters.

## 18.6 Deployment procedure

Rolling, zero-downtime, assuming the expand/contract discipline from
[10](./10-database-schema.md) §10.12:

1. Build and tag images; run the full CI suite against them.
2. Run `alembic upgrade head` as a one-shot job. **Migrations must be backward-compatible with the
   currently running code** — this is what makes step 4 possible.
3. Roll `api` replicas one at a time, gated on `/health/ready`.
4. Roll `worker` replicas with graceful drain: stop accepting jobs, finish in-flight executions
   (up to a 5-minute grace), then exit.
5. Restart `scheduler` last — it is a singleton, so this is a brief gap; cron fires within its
   tick window afterwards.
6. Watch error rate and queue wait for 15 minutes.

**Rollback:** redeploy the previous image tag. This works only because migrations are
backward-compatible; a schema change that breaks the previous release is *not rollable-back*, which
is precisely why contract migrations are deferred by a release.

**Worker graceful shutdown is load-bearing.** `SIGTERM` must stop job intake and let running
executions finish. Killing a worker mid-execution is recoverable
([12](./12-execution-engine.md) §12.11) but will fail non-idempotent nodes, which users experience
as "the deploy broke my workflow."

## 18.7 Scaling

| Symptom | Action |
|---|---|
| `execution_queue_wait_seconds` climbing | Add worker replicas |
| API p95 climbing, queue flat | Add API replicas |
| DB pool saturated | Raise pool size, then add read replicas for list endpoints |
| `executions` table huge | Enable partitioning + shorten retention |
| One tenant starving others | Per-org queue sharding ([12](./12-execution-engine.md) §12.8) |
| Redis memory pressure | Shorten stream retention; move caches to a second instance |

Scale workers **before** API in almost every case. Execution is the expensive path; the API mostly
serves small reads.

**Vertical first.** A single 8-core Postgres handles this workload to a scale most self-hosted
deployments never reach. Sharding is not on the roadmap and should not be designed for.

## 18.8 Backup and recovery

**Postgres** — nightly `pg_dump` plus continuous WAL archiving for PITR. Test the restore monthly;
an untested backup is a belief, not a backup.

**Object store** — versioning enabled, lifecycle rules matching execution retention.

**Redis** — AOF for queue durability across restarts. Not backed up: it holds nothing durable.

**Encryption keys** — `CREDENTIAL_MASTER_KEY` and `SECRET_KEY` backed up **separately** from the
database, ideally in a different trust domain. A backup containing both the ciphertext and the key
is a backup of plaintext.

Targets: RPO 5 minutes (WAL), RTO 1 hour.

**Restore drill (quarterly):** restore the latest backup to a scratch environment, run migrations,
boot the app, decrypt one credential, run one workflow. Anything less does not prove the backup is
usable — the credential decryption step in particular is the one people discover is broken at the
worst possible time.

## 18.9 Runbooks

**Queue backing up.** Check worker replica count and health → check for a single workflow
monopolising slots (per-workflow concurrency) → check for a stuck execution past its timeout →
scale workers → investigate the slow node type via `node_execution_duration_seconds`.

**Executions stuck in `running`.** The watchdog marks them `error` after timeout + grace. If many
are stuck, a worker died without draining: confirm the sweeper is running, then check whether the
visibility timeout is longer than the execution timeout (it must not be).

**Credential decryption failures.** Almost always a wrong or rotated `CREDENTIAL_MASTER_KEY`.
Check `key_version` on the failing rows against the deployed key set. Never "fix" this by
re-encrypting with a new key — that destroys the originals.

**Database connection exhaustion.** Look for long-running transactions
(`pg_stat_activity WHERE state = 'idle in transaction'`) before raising the pool size; the usual
cause is a code path holding a session open across an await on a slow external call.

**A tenant is being rate-limited unfairly.** Check per-org queue depth; raise their quota or shard
their queue rather than lifting global limits.

## 18.10 Upgrade guidance for self-hosters

- Read the release notes; breaking changes are called out with a migration path.
- Back up the database **and the key file** before upgrading.
- Never skip more than one minor version — migrations are tested for `N-1 → N` only.
- Upgrade during a quiet window; active executions finish under a graceful drain.
- Verify after: run one workflow, decrypt one credential, check the scheduler fired.

## 18.11 Operational maturity checklist

Before a deployment can be called production:

- [ ] TLS terminated, HSTS on, certificates auto-renewing
- [ ] `SECRET_KEY` and `CREDENTIAL_MASTER_KEY` generated per-install, stored in a secret manager
- [ ] Backups running **and a restore verified**
- [ ] Encryption keys backed up separately from the database
- [ ] Health checks wired to the orchestrator; liveness does not check dependencies
- [ ] Metrics scraped, the four page-level alerts configured
- [ ] Log aggregation with at least 30 days retention
- [ ] Execution retention configured; the pruning job verified as running
- [ ] Resource limits set on every container
- [ ] `CODE_NODE_ENABLED` reviewed against the deployment's trust model
- [ ] SSRF allow-list reviewed
- [ ] `/docs` disabled in production
