# Project Status — pytbak FastAPI Rewrite

## Branch: `feat/fastapi-rewrite`

### Completed
- [x] FastAPI app structure (`app/main.py` with `create_app()` factory)
- [x] Pydantic Settings config (`app/config/settings.py`)
- [x] Pydantic v2 request/response models (`app/models/schemas.py`)
- [x] SQLAlchemy async models + engine (`app/models/database.py`)
- [x] Unified storage layer with PG→Redis→Memory fallback (`app/services/storage.py`)
- [x] Async Redis client with retry (`app/services/redis_client.py`)
- [x] In-memory TTL cache (`app/services/cache.py`)
- [x] API router — contexts CRUD + fib/sleep/count/redisping (`app/routers/api.py`)
- [x] Debug router — network scan, CPU spike, ping, dns, curl, tcp-check, echo, random-error (`app/routers/debug.py`)
- [x] Management router — health, ready, info, env, mappings, threaddump (`app/routers/mgmt.py`)
- [x] Error injection + delay middleware (`app/middleware/error_injection.py`)
- [x] Basic HTTP auth (`app/auth.py`)
- [x] OpenTelemetry integration (opt-in via OTEL_ENABLED)
- [x] Prometheus metrics (prometheus-fastapi-instrumentator)
- [x] Rate limiting (slowapi)
- [x] GZip compression
- [x] Structured logging (loguru + JSON)
- [x] Tests: test_api, test_debug, test_mgmt, test_middleware, test_storage
- [x] Dockerfile (python:3.12-slim + network tools)
- [x] docker-compose.yml (PG + Redis + Prometheus + OTEL Collector)
- [x] OTEL Collector + Prometheus config
- [x] Alembic setup for async migrations
- [x] Helm chart (deployment, service, ingress, HPA, configmap, secret, servicemonitor)
- [x] .env.example
- [x] README.md
- [x] CLAUDE.md
- [x] requirements.txt
- [x] pyproject.toml

### TODO
- [ ] Run tests and fix any failures
- [ ] Run black formatter
- [ ] Generate initial Alembic migration
- [ ] Build and test Docker image
- [ ] Validate Helm chart with `helm lint`
- [ ] Add HTML index template (currently inline HTML)
