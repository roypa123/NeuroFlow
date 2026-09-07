# 13 — Node Catalog & Node SDK

## 13.1 The central idea

**A node type is a declarative descriptor plus an `execute()` function.** The descriptor drives
everything the UI shows: the picker entry, the icon, the parameter form, conditional field
visibility, validation, and the node's on-canvas subtitle.

The frontend contains **zero per-node code**. This is the constraint that decides whether the
catalog can grow to 200 integrations or stalls at 20. Defend it: the first bespoke node panel is
the beginning of the end.

```
Adding a node type = 1 Python file. No frontend change. No migration. No API change.
```

## 13.2 The descriptor

```python
class NodeTypeDescriptor(BaseModel):
    key: str                     # "neuroflow.http" — stable forever, used in stored graphs
    version: int                 # bumped on breaking parameter changes
    name: str                    # "HTTP Request"
    group: Literal["trigger", "action", "flow", "ai", "data"]
    category: str                # "Core", "AI", "Communication", …
    description: str
    icon: str                    # lucide name or "logo:stripe"
    color: str                   # category token key
    aliases: list[str] = []      # picker search: ["api", "rest", "curl", "fetch"]
    subtitle: str | None         # expression: '={{ $parameter.method }} {{ $parameter.url }}'
    documentation_url: str | None

    inputs:  list[PortSpec]      # [PortSpec(type="main")]
    outputs: list[PortSpec]      # branch nodes declare several, each with a label
    credentials: list[CredentialRequirement] = []
    properties: list[NodeProperty]        # the parameter form
    idempotent: bool = False              # may the engine auto-retry this? (see 12.4)
    supports_error_output: bool = True
    max_items: int | None = None
```

`key` is the stored identifier in every saved graph in every customer's database. **It can never
change.** Renaming a node changes `name`, never `key`.

```python
class NodeProperty(BaseModel):
    name: str                    # parameter key
    display_name: str
    type: PropertyType           # string|number|boolean|options|multiOptions|json|code|
                                 # credential|collection|resourceLocator|dateTime|color|notice|hidden
    default: Any = None
    required: bool = False
    description: str | None
    placeholder: str | None
    options: list[PropertyOption] | None
    load_options_method: str | None      # dynamic dropdown, e.g. "getChannels"
    display_options: DisplayOptions | None   # conditional visibility
    type_options: dict[str, Any] | None      # rows, minValue, editorLanguage, …
    no_data_expression: bool = False         # forbid {{ }} in this field
```

### Conditional visibility

```python
NodeProperty(
    name="body", display_name="Body", type="json",
    display_options=DisplayOptions(show={"method": ["POST", "PUT", "PATCH"]}),
)
```

The frontend evaluates `show`/`hide` against current parameter values on every change. This is how
one HTTP node presents 40 possible parameters without ever showing more than 8 — and it is
entirely descriptor-driven.

## 13.3 Implementing a node

```python
class HttpRequestNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.http", version=2, name="HTTP Request",
        group="action", category="Core", icon="globe", color="cat-app",
        aliases=["api", "rest", "curl", "fetch", "webhook"],
        subtitle="={{ $parameter.method }} {{ $parameter.url }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        credentials=[CredentialRequirement(types=["httpBasicAuth", "httpHeaderAuth",
                                                  "oAuth2Api"], required=False)],
        idempotent=False,        # POST may create; do not auto-retry without opt-in
        properties=[
            NodeProperty(name="method", display_name="Method", type="options",
                         default="GET", options=[...]),
            NodeProperty(name="url", display_name="URL", type="string", required=True,
                         placeholder="https://api.example.com/v1/users"),
            NodeProperty(name="sendBody", display_name="Send Body", type="boolean",
                         default=False,
                         display_options=DisplayOptions(show={"method": ["POST","PUT","PATCH"]})),
            NodeProperty(name="body", display_name="Body", type="json",
                         display_options=DisplayOptions(show={"sendBody": [True]})),
            NodeProperty(name="timeout", display_name="Timeout (ms)", type="number",
                         default=30000),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        results: list[Item] = []
        for index, item in enumerate(ctx.input_items):
            p = ctx.params_for_item(index)          # expressions resolved against THIS item
            response = await ctx.http.request(
                p["method"], p["url"],
                json=p.get("body"), headers=ctx.auth_headers(),
                timeout=p["timeout"] / 1000,
            )
            ctx.log("info", f"{p['method']} {p['url']} → {response.status_code}")
            results.append(Item(json=self._parse(response), paired_item=PairedItem(index)))
        return {"main": [results]}
```

The whole node is one class. Parameter resolution, credential decryption, retry, timeout,
logging, and item pairing are the runtime's job, not the node author's — which is what keeps
node code short enough that a 200-node catalog is maintainable.

### `NodeExecutionContext`

```python
class NodeExecutionContext:
    input_items: list[Item]
    params: dict[str, Any]                     # resolved against item 0
    def params_for_item(self, i: int) -> dict[str, Any]: ...
    credentials: dict[str, dict[str, Any]]     # decrypted, and never logged
    http: AsyncHttpClient                      # SSRF-guarded, see 15.7
    storage: ObjectStorage                     # binary put/get
    def log(self, level: str, message: str) -> None: ...
    def helpers(self) -> NodeHelpers: ...      # pagination, batching, mime sniffing
    workflow: WorkflowInfo
    execution: ExecutionInfo
    run_index: int
```

`ctx.http` is deliberately not raw `httpx`: it enforces the SSRF allow/deny policy, per-node
timeouts, response size caps, and redaction of credential values from logged requests. A node that
reaches for `httpx` directly bypasses all of that and MUST fail review.

## 13.4 Versioning node types

Node types evolve; stored graphs must not break. The rules:

1. **Adding an optional parameter** — no version bump. Existing graphs get the default.
2. **Renaming or removing a parameter, or changing its meaning** — bump `version`, keep the old
   class registered.
3. The registry keys on `(key, version)`; a stored node records `typeVersion` and always executes
   against the version it was authored with.
4. A migration function may upgrade a node in place when the user opens the editor, with a visible
   "This node was updated" notice. Never silently, and never during an execution.

The old implementation stays until telemetry shows no graph uses it. In self-hosted deployments,
that is effectively forever — plan for it.

## 13.5 The v1 catalog

### Triggers

| Node | Purpose |
|---|---|
| Manual Trigger | Run from the editor |
| Webhook | HTTP ingress with auth modes and response modes |
| Schedule | Cron/interval |
| Workflow Trigger | Called as a sub-workflow by another workflow |
| Error Trigger | Fires when any workflow in the project fails (UC-6) |
| Form Trigger | Hosted form → execution; the cheapest way to get human input in |

### Flow control

| Node | Purpose |
|---|---|
| IF | Boolean condition → true/false outputs |
| Switch | N labelled outputs by rules |
| Merge | Combine branches: append, merge-by-key, wait-for-all |
| Loop (Split In Batches) | Explicit iteration with a back-edge |
| Wait | Delay, or suspend until a webhook/approval |
| Stop And Error | Fail deliberately with a message |
| No-Op | Structural clarity on the canvas |
| Execute Sub-workflow | Call another workflow, sync or async |
| Filter | Drop items failing a condition |

### Data

| Node | Purpose |
|---|---|
| Set / Edit Fields | Build or reshape item JSON |
| Code | JavaScript, sandboxed ([12](./12-execution-engine.md) §12.7) |
| HTTP Request | The universal escape hatch |
| Aggregate | Many items → one |
| Split Out | One item with an array field → many items |
| Sort · Limit · Remove Duplicates | Basic collection ops |
| Date & Time | Parse, format, arithmetic |
| Crypto | Hash, HMAC, UUID, base64 |
| XML / HTML / Markdown | Parse and convert |
| Compare Datasets | Diff two inputs — added/removed/changed |

### AI

| Node | Purpose |
|---|---|
| LLM Chat | Single model call, structured-output capable |
| AI Agent | Tool-calling loop ([14](./14-agent-builder.md)) |
| Tool: HTTP / Code / Workflow | Expose capabilities to an agent |
| Memory: Buffer / Postgres | Conversation memory |
| Embeddings | Text → vectors |
| Vector Store | Insert/query (pgvector first) |
| Text Splitter | Chunking for RAG |
| Output Parser | Enforce a JSON schema on model output |
| Classifier | Route by LLM decision |

### Integrations (v1 set — chosen for coverage, not count)

Slack, Gmail, Google Sheets, Google Drive, Postgres, MySQL, MongoDB, Redis, S3, Notion, Airtable,
GitHub, Jira, Linear, Stripe, HubSpot, Salesforce, Twilio, SendGrid, Discord, Telegram, OpenAI,
Anthropic, Google AI, Azure OpenAI, Ollama, Webhook (outbound), FTP/SFTP, SSH, RSS.

**Selection principle:** breadth of *category* over depth of any one vendor. One good CRM node
beats four mediocre ones, and HTTP Request covers the long tail from day one.

## 13.6 Credential types

A credential type is also a descriptor:

```python
class CredentialTypeDescriptor(BaseModel):
    key: str                     # "slackOAuth2"
    name: str                    # "Slack account"
    properties: list[NodeProperty]     # same property system as nodes
    authenticate: AuthenticationSpec   # how it is applied to a request
    test: CredentialTestSpec | None    # a request that proves the credential works
    oauth: OAuth2Spec | None
```

`authenticate` is declarative so nodes never touch raw secrets:

```python
AuthenticationSpec(
    type="generic",
    properties={"headers": {"Authorization": "=Bearer {{ $credentials.apiKey }}"}},
)
```

The runtime injects these at request time inside `ctx.http`. The node author never sees the token
value, which means a node cannot accidentally log it — the protection is structural rather than
disciplinary.

## 13.7 The registry

```python
class NodeRegistry:
    def register(self, cls: type[BaseNode]) -> None: ...
    def get(self, key: str, version: int | None = None) -> BaseNode: ...
    def all_descriptors(self) -> list[NodeTypeDescriptor]: ...
    def load_custom(self, directory: Path) -> None: ...
```

Built-ins are discovered by walking `app/nodes/` at startup. Custom nodes load from a
configured server-side directory — an operator-controlled trust boundary, **not** a user upload
endpoint. Accepting user-uploaded Python is arbitrary remote code execution with extra steps
(non-goal N2 in [01](./01-product-overview.md)).

The registry is validated at boot: duplicate keys, missing required descriptor fields, and
properties referencing undefined `load_options_method`s fail startup loudly rather than at 3am
when a user opens that node.

## 13.8 Authoring checklist

For every new node, before merge:

- [ ] `key` is namespaced and final. It will outlive the code.
- [ ] `aliases` include what users actually type — the marketing name is rarely it
- [ ] `subtitle` shows the most identifying parameter, so 8 copies of the node are distinguishable
- [ ] Every parameter has a description; `placeholder` shows a real example
- [ ] `display_options` hide irrelevant fields — no node shows more than ~8 fields at once
- [ ] `idempotent` is set honestly; when in doubt, `False`
- [ ] Errors are wrapped in `NodeOperationError` with an actionable message
- [ ] Paired items are set, so provenance works in the data panel
- [ ] Pagination handled where the API pages, ideally via `ctx.helpers()`
- [ ] Unit tests with a mocked transport; one integration test against a sandbox or recorded cassette
- [ ] Credentials applied via `authenticate`, never read manually in `execute()`
- [ ] Verified in the UI in light and dark mode at 100% and 40% zoom
