# 15 — Security & Credentials

NeuroFlow stores third-party secrets, executes user-authored code, and makes outbound requests to
arbitrary URLs. It is, structurally, a high-value target. This document is written for the
security reviewer who has to sign off before Persona D deploys it.

## 15.1 Threat model

| # | Threat | Mitigation | §|
|---|---|---|---|
| T1 | Credential theft from the database | Envelope encryption; master key never in the DB | 15.5 |
| T2 | Credential leak via API response | Secrets structurally absent from read schemas | 15.6 |
| T3 | Credential leak via logs/execution data | Central redaction at the sink | 15.6 |
| T4 | SSRF via HTTP node → cloud metadata / internal services | Deny-list + DNS rebinding protection | 15.7 |
| T5 | RCE via the Code node | Subprocess isolation, resource limits, no network by default | 15.8 |
| T6 | Privilege escalation across orgs/projects | Every query scoped by tenant; authorization in controllers | 15.4 |
| T7 | Session hijack / XSS | HttpOnly refresh cookie, in-memory access token, CSP | 15.3 |
| T8 | Webhook forgery | HMAC verification, per-registration secrets | 15.9 |
| T9 | Brute force / credential stuffing | Rate limits on IP + email, argon2 | 15.2 |
| T10 | Prompt injection → tool misuse | Tool permission scoping, human approval on destructive tools | 15.10 |
| T11 | Malicious workflow import | Validate on import; credentials never carried in the document | 15.11 |
| T12 | Denial of service via unbounded execution | Timeouts and quotas at every level | [12](./12-execution-engine.md) §12.9 |

## 15.2 Authentication

**Passwords** — argon2id via `passlib`, `time_cost=3, memory_cost=65536, parallelism=4`. Minimum
12 characters, checked against a breached-password list (k-anonymity range query to HIBP, or a
local bloom filter for air-gapped installs). No composition rules — they produce `Password1!` and
nothing else.

**Login** — constant-time comparison; identical response and timing for unknown user and wrong
password; rate-limited per IP **and** per email; failures audited.

**Tokens** — access JWT (HS256, 15 min) carrying `sub`, `org`, `role`, `jti`, `exp`. Refresh token
is a 32-byte random opaque string, stored as SHA-256, delivered as `HttpOnly; Secure;
SameSite=Strict; Path=/api/v1/auth`.

**Refresh rotation with reuse detection.** Every refresh issues a new token and revokes the old
one. Presenting an already-revoked token means it was stolen, so the entire token *family* is
revoked and the user is forced to re-authenticate. This is the mechanism that converts token theft
from silent persistent access into a detected, self-healing incident.

**Why not store the access token in `localStorage`:** any XSS reads it instantly. In memory, an
XSS must maintain persistence to keep using it, and a page reload evicts it. The refresh cookie is
`HttpOnly`, so script cannot read it at all.

**SSO/OIDC** — `TODO(phase-5)`, but the `users.password_hash` column is nullable from day one
specifically so SSO-only users need no migration.

## 15.3 Session and browser hardening

Response headers on every request:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy: default-src 'self'; img-src 'self' data: https:;
  style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self';
  frame-ancestors 'none'; base-uri 'self'; form-action 'self'
```

⚠️ Monaco needs web workers; use `worker-src 'self' blob:` rather than weakening `script-src`.
CSP without `unsafe-eval` also means the **expression evaluator cannot be a client-side `eval`** —
which is the right design anyway (§15.8), and here the platform enforces it.

CORS is an explicit origin allow-list. `Access-Control-Allow-Origin: *` with credentials is both
forbidden by browsers and a sign someone has misunderstood the model.

## 15.4 Authorization

Two-level RBAC: organization role, optionally narrowed by project membership.

| Permission | owner | admin | member | viewer |
|---|:--:|:--:|:--:|:--:|
| View workflows | ✓ | ✓ | ✓ | ✓ |
| Create/edit workflows | ✓ | ✓ | ✓ | — |
| Delete workflows | ✓ | ✓ | ✓ | — |
| Activate workflows | ✓ | ✓ | ✓ | — |
| Execute workflows | ✓ | ✓ | ✓ | — |
| View executions | ✓ | ✓ | ✓ | ✓ |
| **View execution data** | ✓ | ✓ | ✓ | configurable |
| Create/edit credentials | ✓ | ✓ | ✓ | — |
| **Use** credentials in a workflow | ✓ | ✓ | ✓ | — |
| Manage members / roles | ✓ | ✓ | — | — |
| Manage API keys | ✓ | ✓ | own only | — |
| View audit logs | ✓ | ✓ | — | — |
| Billing / delete org | ✓ | — | — | — |

**Credential values are never readable by anyone, at any role.** "Edit" means overwrite. There is
no permission that returns a stored secret to a browser, including for the owner.

**Enforcement points.** Authorization happens in **controllers**, never in services (a service is
called by the worker, which has no user) and never only in the UI. Every repository method that
lists takes a tenant scope; the base query for any resource is filtered by project/org
membership before any user-supplied filter is applied.

⚠️ Row-Level Security in Postgres was considered as defence-in-depth and deferred: it interacts
badly with connection pooling (the session variable must be set per checkout, and a leaked
setting is a cross-tenant read). Revisit if a dedicated connection-per-tenant model ever appears.
`TODO(phase-6)`

## 15.5 Credential encryption

**Envelope encryption, AES-256-GCM.** (ADR-013)

```
master key (env / KMS, 32 bytes, never in the database)
   └─wraps─▶ per-credential data key (DEK, random 32 bytes)
                └─encrypts─▶ credential JSON  →  ciphertext + nonce + tag
```

Stored per credential: `encrypted_data`, `encrypted_dek`, `nonce`, `key_version`.

```python
def encrypt_credential(plaintext: dict, master: bytes) -> EncryptedBlob:
    dek = os.urandom(32)
    nonce = os.urandom(12)
    ct = AESGCM(dek).encrypt(nonce, json.dumps(plaintext).encode(), aad=b"credential:v1")
    return EncryptedBlob(data=ct, dek=AESGCM(master).encrypt(os.urandom(12), dek, None),
                         nonce=nonce, key_version=CURRENT_KEY_VERSION)
```

**Why envelope rather than encrypting directly with the master key:**

1. **Rotation without re-encrypting payloads.** Rotating the master key re-wraps DEKs — a few
   hundred bytes per credential — instead of decrypting and re-encrypting every secret.
2. **Blast radius.** A leaked DEK exposes one credential.
3. **KMS compatibility.** AWS KMS, Vault, and GCP KMS all wrap data keys natively, so moving from
   an env-var master key to a KMS is a config change, not a redesign.

The AAD (`credential:v1`) binds ciphertexts to their context, preventing a ciphertext from being
transplanted into another field.

**Master key handling.** Base64, 32 bytes, from `CREDENTIAL_MASTER_KEY`. **No default. The
application refuses to start in production without it.** Losing it means every credential is
unrecoverable — documented prominently in the deployment guide, with `key_version` making rotation
a background job rather than an outage.

**Decryption happens only in workers**, only via `CredentialService.get_decrypted`, and every call
is audited with the actor, credential, workflow, and execution.

## 15.6 Preventing secret leakage

Encryption at rest is the easy half. Secrets escape through logs and payloads far more often.

1. **Structural absence.** `CredentialRead` has no `data` field. Not masked — absent.
2. **A central redaction filter.** The worker registers every decrypted secret value in an
   execution-scoped `SecretRegistry`. All log output and all persisted execution data passes
   through a filter that replaces any registered value with `[REDACTED]`. Redaction at the sink,
   not at each call site, because per-call-site discipline always fails eventually.
3. **Declarative auth injection.** Nodes never see raw tokens; `ctx.http` applies credentials from
   the `authenticate` spec ([13](./13-node-catalog-and-sdk.md) §13.6), so a node cannot log what
   it never holds.
4. **Header scrubbing.** `Authorization`, `Cookie`, `X-Api-Key`, and anything matching
   `(?i)(secret|token|password|key)` are stripped from stored request/response metadata.
5. **Error sanitisation.** Provider errors frequently echo the request, including headers. Node
   errors are scrubbed before persistence.
6. **A CI test** asserts that a workflow using a credential with a known sentinel value produces
   no execution data, log line, or API response containing that sentinel.

Item 6 is the one that actually keeps this true over time.

## 15.7 SSRF protection

The HTTP Request node takes a user-supplied URL. Without controls, this is a proxy into the host's
private network and, on any cloud provider, into the instance metadata service.

`ctx.http` enforces, on **every** request and **every redirect hop**:

1. Scheme allow-list: `http`, `https` only.
2. Resolve DNS **first**, then check every resolved IP against the deny-list:
   - `169.254.0.0/16` (cloud metadata — the single most important entry)
   - `127.0.0.0/8`, `::1`, `10/8`, `172.16/12`, `192.168/16`, `0.0.0.0/8`, `100.64/10`, `fc00::/7`
3. **Connect to the validated IP with the Host header preserved**, which closes the DNS-rebinding
   window between check and connect. Re-resolving after validation is the classic bug.
4. Redirects are capped at 5 and re-validated at each hop.
5. Response size cap (default 32 MB) and timeout on every request.

An operator allow-list (`SSRF_ALLOW_CIDRS`) exists for the legitimate case of calling an internal
service, and it is explicit and audited rather than a global off-switch.

## 15.8 Code execution sandbox

The Code node runs arbitrary JavaScript. Layers, in order of importance:

1. **Process isolation** — a separate Node.js subprocess, never the worker's event loop.
2. **Resource limits** — 30 s wall clock, 128 MB heap, CPU limit via `RLIMIT_CPU`; killed with
   `SIGKILL` on breach.
3. **No network by default.** Opt-in per instance, off in shared deployments.
4. **No filesystem.** No `fs`, no `child_process`, no `process.env`; module allow-list only.
5. **Unprivileged user**, non-root container, read-only root filesystem.
6. **Recommended in production:** seccomp profile or gVisor. Documented in
   [18](./18-deployment-and-operations.md).

The **server-side expression evaluator** is a restricted AST interpreter, not `eval`
([12](./12-execution-engine.md) §12.6) — expressions are evaluated far more often than Code nodes,
so a fast, safe path matters as much as a strong slow one.

⚠️ Honest statement of residual risk: a JS sandbox in-process is not a security boundary against a
determined attacker. **The real boundary is the container plus the OS.** Deployments that allow
untrusted users to author Code nodes should run workers in a dedicated, network-restricted node
pool. This should be said plainly in the docs rather than implied.

## 15.9 Webhook security

Per registration: `none`, `basic`, `headerAuth`, or `hmac`.

HMAC verification compares `hmac_sha256(secret, raw_body)` against the provider's signature header
using `hmac.compare_digest`. Two details that are easy to get wrong and both fatal:

- Verify against the **raw body bytes**, before JSON parsing. Re-serialising changes whitespace
  and key order, and the signature will never match.
- Include the timestamp header in the signed payload and reject anything older than 5 minutes, or
  a captured request is replayable forever.

Test webhooks expire after 120 seconds. Paths are UUIDs by default — guessable slugs are opt-in.

## 15.10 Agent-specific security

Prompt injection is unsolved in general; the mitigations are architectural, not prompt-based:

1. **Tools are the security boundary, not the prompt.** An agent can only do what its tools allow.
   "Ignore previous instructions" cannot invent a `delete_database` tool.
2. **Least privilege per tool.** Each tool gets its own credential with minimum scope. Do not give
   an agent an admin API key and rely on instructions.
3. **Human approval on destructive tools.** A tool may be marked `requiresApproval`, suspending the
   execution for confirmation ([12](./12-execution-engine.md) §12.5). This is the only genuinely
   reliable control for irreversible actions.
4. **Untrusted content is labelled.** Tool results and retrieved documents are wrapped so the
   system prompt can distinguish instructions from data. Partial mitigation, honestly labelled.
5. **Output guardrails** run before any downstream node consumes agent output.
6. **Cost ceilings** bound the damage of an injection that induces a loop.

## 15.11 Supply chain and operations

- Dependencies pinned exactly; `pip-audit` and `npm audit` in CI, failing on high severity.
- Dependabot/Renovate weekly, with a human review gate.
- Images built from digest-pinned bases, scanned with Trivy, non-root, minimal.
- **Imported workflows never carry credential values** — only type and name references. An import
  is validated against the node registry and rejected if it references unknown node types.
- Secrets in deployment come from the orchestrator's secret store, never from an image or a
  committed `.env`.
- Static analysis: `ruff` (with `bandit` rules) and `mypy --strict` on the backend; ESLint with
  `security` rules on the frontend.

## 15.12 Security checklist per release

- [ ] No new endpoint returns secret material
- [ ] Every new endpoint has an explicit authorization check, with a test asserting 403 for a
      non-member
- [ ] Every new query is tenant-scoped
- [ ] New outbound HTTP goes through `ctx.http`, not raw `httpx`
- [ ] New log statements cannot emit credential values (sentinel test passes)
- [ ] Dependency audit clean at high severity
- [ ] Migrations do not weaken a constraint
- [ ] Rate limits considered for any new unauthenticated route
