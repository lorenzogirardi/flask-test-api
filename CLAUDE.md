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
- **Deployment**: Docker + docker-compose (dev), Helm chart (prod K8s)

### Key Architecture Decisions
1. **Graceful fallback chain**: PG → Redis → In-Memory. All backends are optional. App starts and works with zero external deps.
2. **Dev vs Prod**: In development, PG and Redis run in docker-compose. In production, they are external HTTP/S endpoints configured via env vars. If missing, fallback to in-memory.
3. **Middleware-based debug features**: Error injection (`?inject_error=`) and delay (`?delay_ms=`) work on ANY endpoint via middleware.
4. **Single `create_app()` factory** in `app/main.py` for testability.

### Project Layout
```
app/
├── main.py              # create_app() + lifespan
├── auth.py              # BasicAuth dependency
├── config/settings.py   # Pydantic Settings
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
│   └── cache.py         # In-memory TTL cache
└── middleware/
    └── error_injection.py
```

### Running Tests
```bash
pytest -v
pytest --cov=app --cov-report=term-missing
```

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
- `DIAG_USERNAME` / `DIAG_PASSWORD` — auth for /debug endpoints

### Conventions
- Type hints on all functions
- Black formatting (line-length=120)
- Loguru for logging (structured JSON)
- Error responses always return `{"error": "message"}`
- Tests use pytest + anyio with httpx AsyncClient
