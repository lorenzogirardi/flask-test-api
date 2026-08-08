# 11. MCP Server

## 11.1 What It Is

pytbak mounts an [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server at
`/api/mcp`, exposing its own capabilities — context CRUD, network diagnostics, CPU load
generation, health checks — as **tools** an LLM can call directly. Built with the official
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)'s `FastMCP` class.

It is **not** a separate service. It runs in the same FastAPI process, same container, same
pod, same Helm release as the rest of pytbak. Wherever pytbak is deployed — dev, itachi,
izanami, milano — the MCP endpoint is deployed with it, at no extra infrastructure cost.

## 11.2 Why In-Process, Not a Standalone Client

An earlier design considered a standalone MCP server: a separate process, talking to a
running pytbak instance over its REST API as an HTTP client. That was rejected in favor of
mounting the MCP server inside pytbak itself, for one reason: **zero deployment overhead**.

| | Standalone (rejected) | In-process (built) |
|---|---|---|
| Extra process to deploy/run | Yes | No |
| Extra Helm chart / K8s manifests | Yes | No |
| Network hop per tool call | REST round-trip | Direct function call |
| Auth | Reuses REST `Depends(verify_credentials)` per-endpoint | Uniform Basic Auth over the whole mount (§11.5) |
| Ships with `docker compose up` / `helm install pytbak` | No — needs its own lifecycle | Yes — it's already part of `app/` |

Tools call the same service-layer functions the REST routers call
(`app.services.storage`, `app.routers.debug`, `app.services.health`) directly — no HTTP
client, no serialization round-trip back into the same process.

## 11.3 Why FastMCP (and why it fits FastAPI)

### Disambiguation first

Two different things are called "FastMCP", and online examples mix them freely:

| | What pytbak uses | The other one |
|---|---|---|
| Import | `from mcp.server.fastmcp import FastMCP` | `import fastmcp` |
| Package | `mcp` (official Anthropic SDK) | `fastmcp` (standalone, currently 3.x) |
| Origin | FastMCP 1.0, absorbed into the official SDK | Continued independently by its original author |

We use the **official SDK's** `FastMCP`, pinned in `requirements.txt` as `mcp==1.28.1`.
When copying snippets from the web, check the import line first — the two projects have
diverged and their APIs are not interchangeable.

### Why the high-level `FastMCP` and not the low-level `Server`

The SDK also exposes `mcp.server.lowlevel.Server`, where you register a `list_tools()`
handler returning hand-written `types.Tool` objects (each with a hand-written JSON Schema)
plus a separate `call_tool()` dispatcher that switches on the tool name. For 23 tools that
is 23 hand-maintained schemas that can silently drift from the functions they describe.

`FastMCP` derives all of it from the function itself:

```python
@mcp.tool()
async def create_context(title: str, description: str = "") -> object:
    """Create a new context. Title must be 1-255 characters."""
```

- the **type hints** become the JSON Schema for the arguments,
- the **docstring** becomes the tool description the model reads,
- the **function name** becomes the tool name,
- defaults become schema defaults, and non-defaulted params become `required`.

Exactly the deal FastAPI offers for HTTP routes — write a typed function, get the OpenAPI
schema for free — applied to MCP tools. Same mental model, no second schema to maintain.

### Concrete synergies with FastAPI

**1. Same Pydantic engine.** FastMCP generates tool schemas through Pydantic, the same
library FastAPI uses for request models. So a model already defined for the REST API works
verbatim as a tool argument, constraints and all:

```python
@mcp.tool()
async def make(data: ContextCreate) -> object:   # ContextCreate is app/models/schemas.py
    ...
```
```jsonc
// generated automatically — note minLength/maxLength carried over from the model
{"$defs": {"ContextCreate": {"properties": {
    "title": {"type": "string", "minLength": 1, "maxLength": 255}, ...}}}}
```

**2. It is a Starlette app, so `app.mount()` just works.** `mcp.streamable_http_app()`
returns a plain Starlette application. FastAPI *is* Starlette, so the MCP server mounts as a
sub-app with no adapter, no bridge process, no second port:

```python
app.mount("/api/mcp", MCPBasicAuthMiddleware(mcp_asgi_app))
```

Because it is ordinary ASGI, ordinary ASGI middleware wraps it — which is exactly how auth
is applied (§11.5).

**3. Async all the way down.** Tools are `async def` and run on the same event loop as the
FastAPI routes, so they can await the same async service functions (`storage.py`,
`health.py`) with no thread hand-off or separate connection pool.

### The one tradeoff we hit

pytbak's tools take **flattened primitive arguments** (`title: str, description: str = ""`)
rather than the model (`data: ContextCreate`). Flattened arguments give the model a simpler
call shape — no nested object — but the model's constraints then live only inside
`ContextCreate`, not in the tool schema, so they are not visible to the caller upfront and
only fire when the tool actually constructs the model.

That is precisely why `_structured_errors` exists (§11.7): it catches the resulting
`ValidationError` and returns it as a readable 422 result. Passing the Pydantic model
directly is the alternative — constraints become self-documenting in the schema, at the cost
of a nested argument object. Either is defensible; the flattened form was chosen for call
ergonomics, with the decorator covering the gap.

## 11.4 Architecture

```mermaid
graph TB
    subgraph Client["LLM / MCP Client"]
        C[Claude, or any MCP-compatible client]
    end

    subgraph Pod["pytbak Pod (single container)"]
        subgraph FastAPI["FastAPI app (app/main.py)"]
            REST["REST routers<br/>/api/*, /api/debug/*, /api/mgmt/*"]
            AUTH["MCPBasicAuthMiddleware<br/>(app/middleware/mcp_auth.py)"]
            MCPAPP["MCP streamable-HTTP app<br/>mounted at /api/mcp"]
            TOOLS["app/mcp/tools.py<br/>23 @mcp.tool() functions"]
        end
        SVC["Service layer<br/>storage.py, health.py, debug logic"]
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        MEM[[In-Memory fallback]]
    end

    C -->|"HTTP POST /api/mcp<br/>(Basic Auth + JSON-RPC)"| AUTH
    AUTH -->|"authorized"| MCPAPP
    AUTH -->|"401 / 429"| C
    MCPAPP --> TOOLS
    TOOLS -->|"direct function calls,<br/>no HTTP hop"| SVC
    REST --> SVC
    SVC --> PG
    SVC --> REDIS
    SVC --> MEM

    style AUTH fill:#b91c1c,color:#fff
    style TOOLS fill:#1d4ed8,color:#fff
```

Key points:

- **`app/mcp/tools.py`** — the `FastMCP("pytbak")` instance and every `@mcp.tool()` function.
- **`app/middleware/mcp_auth.py`** — a raw ASGI middleware wrapping the mounted sub-app.
  `app.mount()` sub-apps don't participate in FastAPI's `Depends()` system, so this is where
  auth is enforced instead — see §11.5.
- **`app/services/health.py`** — health-check logic extracted out of `app/routers/mgmt.py`
  so both the REST `/api/mgmt/health` endpoint and the MCP `health` tool share one
  implementation instead of two.
- **Mount wiring in `app/main.py`** — `streamable_http_app()` is built *before* the FastAPI
  app itself, so its lifespan-managed `session_manager` can be started from pytbak's own
  `lifespan()` via `AsyncExitStack`. Mounted sub-apps don't get their lifespan events
  forwarded automatically by Starlette — without this, requests to `/api/mcp` would hang
  forever waiting on a session manager that never started.

## 11.5 Authentication

The whole `/api/mcp` mount requires HTTP Basic Auth — same `DIAG_USERNAME` /
`DIAG_PASSWORD` credentials as `/api/debug/*`. `MCPBasicAuthMiddleware` reuses the exact
same failure-tracking rate limiter as `app/auth.py` (`check_rate_limit`, `record_failure`,
`clear_failures`), so brute-forcing either surface counts against the same backoff.

This is **stricter than the REST API**, which leaves some endpoints (contexts CRUD,
`/mgmt/info`) unauthenticated. The MCP mount gates everything uniformly — including tools
like `list_contexts` and `fibonacci` that have no auth requirement over REST — because MCP
aggregates many capabilities behind one entry point for an autonomous LLM caller, which
warrants the stricter boundary rather than mirroring each REST endpoint's individual rule.

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant MW as MCPBasicAuthMiddleware
    participant RL as app.auth rate limiter
    participant MCP as MCP streamable-HTTP app
    participant Tool as app/mcp/tools.py
    participant Svc as Service layer (storage, health, ...)

    Client->>MW: POST /api/mcp (Authorization: Basic ...)
    MW->>RL: check_rate_limit(ip)
    alt too many recent failures
        RL-->>MW: HTTPException 429
        MW-->>Client: 429 Too Many Requests
    else under threshold
        MW->>MW: parse + compare credentials (secrets.compare_digest)
        alt invalid credentials
            MW->>RL: record_failure(ip)
            MW-->>Client: 401 Unauthorized
        else valid credentials
            MW->>RL: clear_failures(ip)
            MW->>MCP: forward request
            MCP->>MCP: negotiate session (JSON-RPC over streamable HTTP)
            MCP->>Tool: dispatch tool call, e.g. create_context(title, description)
            Tool->>Svc: storage.create_context(ContextCreate(...))
            Svc-->>Tool: ContextResponse
            Tool-->>MCP: dict (model_dump)
            MCP-->>Client: 200 OK + JSON-RPC result
        end
    end
```

## 11.6 Configuration

| Setting | Env var | Default | Purpose |
|---|---|---|---|
| `mcp_enabled` | `MCP_ENABLED` | `false` | Mount `/api/mcp` at all (opt-in) |
| `debug_endpoints_enabled` | `DEBUG_ENDPOINTS_ENABLED` | `false` | Independent of MCP — gates `/api/debug/*` REST routes only (opt-in) |
| `diag_username` / `diag_password` | `DIAG_USERNAME` / `DIAG_PASSWORD` | `admin` / `password` | Same credentials used for MCP Basic Auth. In `APP_ENV=production` the defaults are rejected at startup; real credentials are mandatory |
| `ssrf_protection_enabled` | `SSRF_PROTECTION_ENABLED` | `false` | When true, blocks loopback/private/link-local/metadata targets in the network tools (`curl`, `network_scan`, `ping`, `dns`, `tcp_check`) |

Set `MCP_ENABLED=false` (the default) to keep the mount off entirely in a locked-down
production deployment that only wants the plain REST API. The helm chart ships with both
flags off; the dev docker-compose and test suite enable them explicitly.

## 11.7 Available Tools

23 tools, mirroring the REST API's capabilities minus `echo_headers` (no per-call HTTP
request to introspect when a tool call isn't itself an HTTP request from the caller's
perspective):

| Category | Tools |
|---|---|
| Contexts CRUD | `list_contexts`, `get_context`, `create_context`, `update_context`, `delete_context` |
| Load / legacy | `fibonacci`, `sleep`, `count`, `redis_ping` |
| Debug / diagnostics | `network_scan`, `cpu_spike`, `ping`, `dns_resolve`, `curl`, `tcp_check`, `echo_body`, `random_error` |
| Mgmt / observability | `health`, `ready`, `app_info`, `app_env`, `app_mappings`, `threaddump` |

Tools never raise exceptions back to the MCP transport for expected failure cases. The
`_structured_errors` decorator in `app/mcp/tools.py` wraps every tool and converts them into
a result the caller can read:

| Raised inside a tool | Returned to the caller |
|---|---|
| `HTTPException` (router 4xx, e.g. bad host, input too large) | `{"error": true, "status_code": <4xx>, "detail": "..."}` |
| `ValidationError` (argument fails a Pydantic request model) | `{"error": true, "status_code": 422, "detail": [ ...pydantic errors... ]}` |
| Not-found paths (no exception, checked explicitly) | `{"error": true, "status_code": 404, "detail": "Context not found"}` |

The `ValidationError` case matters because the constraints live on the request models
(`ContextCreate.title` is 1-255 chars, `CpuSpikeRequest.duration` is 1-120) rather than on
the tool signatures, so they only fire at call time. Without the decorator, an LLM passing
`title=""` would get a broken tool call instead of a result explaining what was wrong:

```json
{"error": true, "status_code": 422,
 "detail": [{"type": "string_too_short", "loc": ["title"], "msg": "String should have at least 1 character"}]}
```

MCP reports these with `isError=false` — they are legitimate results describing a failure,
not transport faults, which is what lets the model reason about them and retry.

## 11.8 Usage Example

Real example from OpenCode Desktop — natural-language prompt, tool calls resolved
automatically, no manual tool selection needed:

![pytbak MCP tools called from OpenCode Desktop: create_context, health, and get_context](images/opencode-mcp-example.png)

Any MCP-compatible client works. Using the official Python SDK directly:

```python
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

auth = httpx.BasicAuth("admin", "password")

async with streamablehttp_client("http://localhost:8000/api/mcp", auth=auth) as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        print([t.name for t in tools.tools])  # 23 tools

        result = await session.call_tool(
            "create_context", {"title": "from-mcp", "description": "created via MCP"}
        )
        print(result.content[0].text)

        health = await session.call_tool("health", {})
        print(health.content[0].text)
```

Wiring it into an MCP-aware client config (e.g. Claude Desktop / Claude Code) as a remote
streamable-HTTP server:

```json
{
  "mcpServers": {
    "pytbak": {
      "url": "http://localhost:8000/api/mcp",
      "headers": {
        "Authorization": "Basic YWRtaW46cGFzc3dvcmQ="
      }
    }
  }
}
```

(`YWRtaW46cGFzc3dvcmQ=` is `base64("admin:password")` — the dev default. Use real
`DIAG_USERNAME`/`DIAG_PASSWORD` for any non-dev deployment.)

## 11.9 Testing

Follows the same test pyramid as the rest of pytbak (see `CLAUDE.md` → Testing Policy):

- **Base** (`tests/test_mcp.py`) — calls `app.mcp.tools` functions directly, in-memory
  backend, no network. Fast, always runs.
- **Mid/tip** (`tests/integration/test_mcp.py`) — drives the *real* streamable-HTTP wire
  protocol against a live `docker compose up -d` stack: session negotiation, JSON-RPC tool
  calls, and the Basic Auth middleware, including negative tests (missing/wrong
  credentials rejected). Requires the live stack; self-skips otherwise.

```bash
pytest tests/test_mcp.py -v                                  # base layer
docker compose up -d && pytest tests/integration/test_mcp.py -v -m integration
```
