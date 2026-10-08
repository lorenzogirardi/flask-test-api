# CLAUDE.md — Project Context for AI Assistants

## Project: pytbak (Python REST API Test & Debug)

### Overview
FastAPI-based debug/test API application. Migrated from Flask v1. Serves as a debugging Swiss Army knife for microservice environments.

### Tech Stack
- **Framework**: FastAPI 0.115+ with async/await
- **Python**: 3.11+
- **Storage**: PostgreSQL (async SQLAlchemy) → Redis (async redis-py) → In-Memory (dict with TTL)
- **Validation**: Pydantic v2 models
- **Config**: Pydantic Settings (env-based, `.env` file)
- **Observability**: OpenTelemetry (traces/metrics), Prometheus, loguru (structured JSON)
- **Auth**: HTTP Basic Auth on `/debug` endpoints
- **Rate Limiting**: slowapi
- **MCP**: In-process MCP server (official `mcp` SDK, `FastMCP`) mounted at `/api/mcp`, Basic Auth protected — see `docs/11-mcp-server.md`
- **Deployment**: Docker + docker-compose (dev), Helm chart (prod K8s)

### Key Architecture Decisions
1. **Graceful fallback chain**: PG → Redis → In-Memory. All backends are optional. App starts and works with zero external deps.
2. **Dev vs Prod**: In development, PG and Redis run in docker-compose. In production, they are external HTTP/S endpoints configured via env vars. If missing, fallback to in-memory.
3. **Middleware-based debug features**: Error injection (`?inject_error=`) and delay (`?delay_ms=`) work on ANY endpoint via middleware.
4. **Single `create_app()` factory** in `app/main.py` for testability.

### Project Layout
```
app/
├── main.py              # create_app() + lifespan (also starts MCP session manager)
├── auth.py              # BasicAuth dependency
├── config/settings.py   # Pydantic Settings
├── mcp/
│   └── tools.py         # MCP server (FastMCP) mounted at /api/mcp — see docs/11-mcp-server.md
├── models/
│   ├── schemas.py       # Request/response Pydantic models
│   └── database.py      # SQLAlchemy async models
├── routers/
│   ├── api.py           # /api — CRUD + fib/sleep/count
│   ├── debug.py         # /debug — network scan, cpu spike, diag
│   └── mgmt.py          # /mgmt — health, ready, info, env
├── services/
│   ├── storage.py       # Unified storage with PG→Redis→Memory fallback
│   ├── redis_client.py  # Async Redis with retry
│   ├── health.py        # Shared health-check logic (REST /mgmt/health + MCP health tool)
│   └── cache.py         # In-memory TTL cache
└── middleware/
    ├── error_injection.py
    └── mcp_auth.py       # ASGI Basic Auth guard for the /api/mcp mount
```

### Running Tests
```bash
pytest -v
pytest --cov=app --cov-report=term-missing
```

### Testing Policy — Run Tests Every Change
Run the test suite after every code change, before considering a change done.

- Minimum: `pytest tests/ -v` (base layer — in-memory, no external deps, fast).
- If the change touches `app/services/storage.py`, `app/models/database.py`,
  `app/services/redis_client.py`, or anything PG/Redis-facing: also run the
  integration layer against the live stack —
  `docker compose up -d && pytest tests/integration -v`.
  (Most integration test files self-skip via the `live_service` fixture rather
  than the `integration` pytest marker — don't filter with `-m integration`,
  it only currently matches `tests/integration/test_mcp.py`.)
- If the change touches multiple routers or a full request lifecycle: also run
  `tests/integration/test_e2e.py` (requires the live stack, same as above).
- A change is not done until its test layer is green. Do not skip this because
  a test "looks unrelated" — the fallback-chain architecture means changes in
  one backend can silently break another.

### Running Locally
```bash
# In-memory only (no deps):
uvicorn app.main:app --reload --port 8000

# With docker-compose (full stack):
docker compose up -d
```

### Environment Variables
See `.env.example` for full list. Key ones:
- `DATABASE_URL` — PostgreSQL connection string (empty = disabled)
- `REDIS_URL` — Redis connection string (empty = disabled)
- `APP_ENV` — development/production/test
- `DIAG_USERNAME` / `DIAG_PASSWORD` — auth for /debug endpoints and /api/mcp
- `MCP_ENABLED` — mount the MCP server at /api/mcp (default true)

### Conventions
- Type hints on all functions
- Black formatting (line-length=120)
- Loguru for logging (structured JSON)
- Error responses always return `{"error": "message"}`
- Tests use pytest + anyio with httpx AsyncClient
