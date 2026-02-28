# pytbak — Python REST API Test & Debug (FastAPI v2)

Production-ready FastAPI application for API testing, debugging, and observability demos.
Migrated from Flask v1 — all original features preserved + major new capabilities.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    FastAPI App                        │
│  ┌──────┐  ┌───────┐  ┌──────┐  ┌────────────────┐  │
│  │ /api │  │/debug │  │/mgmt │  │  Middleware     │  │
│  │ CRUD │  │ diag  │  │health│  │  error_inject  │  │
│  └──┬───┘  └───┬───┘  └──┬───┘  │  delay         │  │
│     │          │          │      └────────────────┘  │
│  ┌──▼──────────▼──────────▼───┐                      │
│  │    Unified Storage Layer   │                      │
│  │  PG → Redis → In-Memory   │                      │
│  └────────────────────────────┘                      │
└──────────────────────────────────────────────────────┘
         │              │              │
    PostgreSQL       Redis        Prometheus
    (optional)     (optional)     + OTEL
```

**Fallback strategy**: PostgreSQL → Redis → In-Memory (automatic, zero-downtime).

- **Development**: PG + Redis run in docker-compose
- **Production**: PG + Redis are external HTTP/S endpoints (env vars). If not configured, the app runs fully in-memory.

## Quick Start

### Local development (docker-compose)
```bash
cp .env.example .env
docker compose up -d
# App at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
# ReDoc at http://localhost:8000/redoc
# Prometheus at http://localhost:9090
```

### Local development (bare metal)
```bash
pip install -r requirements.txt
# Without PG/Redis (in-memory only):
APP_ENV=development uvicorn app.main:app --reload --port 8000
```

### Production (Kubernetes + Helm)

```bash
helm install pytbak ./helm/pytbak \
  --set postgresql.url="postgresql+asyncpg://user:pass@pg-host:5432/db" \
  --set redis.url="redis://redis-host:6379/0" \
  --set auth.username=admin \
  --set auth.password=secure123
```

### izanami cluster (192.168.1.14) — Redis + PostgreSQL dedicati

Redis e PostgreSQL sono deployati come chart indipendenti (fuori da questo repo):

```bash
# 1. Redis + Webdis (~/Storage/home/helm-redis)
helm upgrade --install redis ~/Storage/home/helm-redis \
  --kube-context izanami \
  --set redis.password=<REDIS_PASSWORD>

# 2. PostgreSQL (~/Storage/home/helm-postgresql)
helm upgrade --install postgresql ~/Storage/home/helm-postgresql \
  --kube-context izanami \
  --set postgresql.password=<PG_PASSWORD>

# 3. pytbak con override izanami
helm upgrade pytbak ./helm/pytbak \
  -f helm/pytbak/values.yaml \
  -f helm/pytbak/values-izanami.yaml \
  --kube-context izanami -n pytbak \
  --set auth.password=<AUTH_PASSWORD> \
  --set redis.url="redis://:REDIS_PASSWORD@redis.redis.svc.cluster.local:6379/0" \
  --set postgresql.url="postgresql+asyncpg://pytbak:PG_PASSWORD@postgresql.postgresql.svc.cluster.local:5432/pytbak"
```

> **Nota microk8s**: il provisioner hostpath non funziona con K8s 1.20+.
> Creare i PV manuali prima del deploy — vedere i README dei rispettivi chart.

## API Endpoints

### Core API (`/api`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/contexts` | List all contexts |
| GET | `/api/contexts/{id}` | Get context by ID |
| POST | `/api/contexts` | Create context |
| PUT | `/api/contexts/{id}` | Update context |
| DELETE | `/api/contexts/{id}` | Delete context |
| GET | `/api/fib/{n}` | Fibonacci |
| GET | `/api/sleep/{n}` | Delay endpoint |
| GET | `/api/count` | Redis counter |
| GET | `/api/redisping` | Webdis ping |

### Debug (`/debug`) — requires Basic Auth
| Method | Path | Description |
|--------|------|-------------|
| GET | `/debug/network/scan?target=host:port` | Network diagnostics (ping, dns, tcp, traceroute) |
| POST | `/debug/cpu/spike` | Simulate CPU load |
| GET | `/debug/ping?host=...` | Ping host |
| GET | `/debug/dns?name=...` | DNS resolve |
| GET | `/debug/curl?url=...` | HTTP GET |
| GET | `/debug/tcp-check?host=...&port=...` | TCP check |
| GET/POST/PUT/DELETE | `/debug/headers` | Echo headers |
| POST/PUT | `/debug/echo` | Echo body |
| GET | `/debug/random-error` | Random error |

### Management (`/mgmt`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/mgmt/health` | Health check (PG + Redis status) |
| GET | `/mgmt/ready` | Readiness probe |
| GET | `/mgmt/info` | App info |
| GET | `/mgmt/env` | Safe env vars |
| GET | `/mgmt/mappings` | Route mappings |
| GET | `/mgmt/threaddump` | Thread dump |

### Observability
| Path | Description |
|------|-------------|
| `/metrics` | Prometheus metrics (scrape-ready) |
| `/docs` | Swagger UI (OpenAPI v3) |
| `/redoc` | ReDoc |

**Datadog integration** (production):
- **Metrics**: Datadog Agent scrapes `/metrics` via openmetrics autodiscovery (annotations in Helm deployment)
- **Traces**: App exports OTEL traces via OTLP to Datadog Agent (`OTEL_EXPORTER_OTLP_ENDPOINT=http://datadog-agent:4317`)
- No sidecar containers needed — both are code libraries in the app

## Debug Features

### Error Injection (any endpoint)
```bash
# Inject HTTP 500
curl http://localhost:8000/api/contexts?inject_error=500

# Inject 429 Too Many Requests
curl http://localhost:8000/mgmt/info?inject_error=429

# Validation error
curl http://localhost:8000/api/contexts?inject_error=validation_error

# Custom error message
curl http://localhost:8000/api/contexts?inject_error=custom:database_timeout
```

### Delay Injection (any endpoint)
```bash
# Fixed delay 3 seconds
curl http://localhost:8000/api/contexts?delay_ms=3000

# Random delay 0-5 seconds
curl http://localhost:8000/api/contexts?delay_ms=random
```

### CPU Spike
```bash
curl -X POST http://localhost:8000/debug/cpu/spike \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"duration": 30, "cores": 2}'
```

### Network Scan
```bash
curl "http://localhost:8000/debug/network/scan?target=google.com:443" \
  -u admin:password
```

## curl Examples

```bash
# Create context
curl -X POST http://localhost:8000/api/contexts \
  -H "Content-Type: application/json" \
  -d '{"title": "My Task", "description": "Do something"}'

# List contexts
curl http://localhost:8000/api/contexts

# Update context
curl -X PUT http://localhost:8000/api/contexts/{id} \
  -H "Content-Type: application/json" \
  -d '{"done": true}'

# Delete context
curl -X DELETE http://localhost:8000/api/contexts/{id}

# Health check
curl http://localhost:8000/mgmt/health

# Prometheus metrics
curl http://localhost:8000/metrics

# Fibonacci
curl http://localhost:8000/api/fib/10

# Sleep
curl http://localhost:8000/api/sleep/3

# Ping (auth required)
curl -u admin:password "http://localhost:8000/debug/ping?host=google.com&count=3"

# DNS resolve (auth required)
curl -u admin:password "http://localhost:8000/debug/dns?name=google.com"

# TCP check (auth required)
curl -u admin:password "http://localhost:8000/debug/tcp-check?host=google.com&port=443"

# Echo headers (auth required)
curl -u admin:password http://localhost:8000/debug/headers

# Random error (auth required)
curl -u admin:password http://localhost:8000/debug/random-error
```

## Usage — Verified Docker Test Session

Full test session executed against the docker-compose stack (`docker compose up -d`).
All 5 containers running: **web**, **postgres**, **redis**, **prometheus**, **otel-collector**.

### 1. Health Check — PostgreSQL & Redis connected

```bash
$ curl -s http://localhost:8000/mgmt/health | python3 -m json.tool
{
    "status": "UP",
    "checks": [
        { "name": "redis", "status": "UP", "error": null },
        { "name": "postgresql", "status": "UP", "error": null }
    ]
}
```

### 2. Readiness & App Info

```bash
$ curl -s http://localhost:8000/mgmt/ready
{"status": "READY"}

$ curl -s http://localhost:8000/mgmt/info | python3 -m json.tool
{
    "app": {
        "name": "pytbak",
        "description": "Python REST API Test Application (FastAPI)",
        "version": "2.0.0",
        "environment": "development"
    }
}
```

### 3. CRUD Contexts (stored in PostgreSQL)

```bash
# Create
$ curl -s -X POST http://localhost:8000/api/contexts \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Task", "description": "Created from Docker"}'
{
    "id": "ff0aa92e-92bc-43f3-99a7-f44449384bed",
    "title": "Test Task",
    "description": "Created from Docker",
    "done": false,
    "created_at": "2026-02-22T11:22:51.532107Z",
    "updated_at": "2026-02-22T11:22:51.532107Z"
}

# List
$ curl -s http://localhost:8000/api/contexts
[{"id": "ff0aa92e-...", "title": "Test Task", "done": false, ...}]

# Update
$ curl -s -X PUT http://localhost:8000/api/contexts/ff0aa92e-... \
  -H "Content-Type: application/json" \
  -d '{"done": true, "title": "Updated Task"}'
{
    "id": "ff0aa92e-...",
    "title": "Updated Task",
    "done": true,
    "updated_at": "2026-02-22T11:22:57.750375Z"
}

# Delete
$ curl -s -X DELETE http://localhost:8000/api/contexts/ff0aa92e-...
{"result": true}

# Verify empty
$ curl -s http://localhost:8000/api/contexts
[]
```

### 4. Legacy Endpoints

```bash
# Fibonacci
$ curl -s http://localhost:8000/api/fib/10
{"result": "55"}

# Sleep
$ curl -s http://localhost:8000/api/sleep/1
{"message": "Delayed by 1 seconds"}

# Redis counter
$ curl -s http://localhost:8000/api/count
{"counter": 1}
```

### 5. Error Injection (any endpoint)

```bash
$ curl -s http://localhost:8000/mgmt/info?inject_error=500
{"error": "Injected error 500", "injected": true}
```

### 6. Delay Injection

```bash
$ time curl -s http://localhost:8000/mgmt/ready?delay_ms=200
{"status": "READY"}
real    0m0.222s   # ~200ms delay confirmed
```

### 7. Debug Endpoints (Basic Auth required)

```bash
# Echo headers
$ curl -s -u admin:password http://localhost:8000/debug/headers
{
    "host": "localhost:8000",
    "authorization": "Basic YWRtaW46cGFzc3dvcmQ=",
    "user-agent": "curl/8.7.1",
    "accept": "*/*"
}

# DNS resolve
$ curl -s -u admin:password "http://localhost:8000/debug/dns?name=google.com"
{"addresses": ["2a00:1450:4002:407::200e", "142.251.209.46"]}

# Without auth → 401
$ curl -s http://localhost:8000/debug/headers
{"detail": "Not authenticated"}   # HTTP 401
```

### 8. Environment Variables (whitelisted)

```bash
$ curl -s http://localhost:8000/mgmt/env | python3 -m json.tool
{
    "PATH": "/usr/local/bin:...",
    "HOSTNAME": "7b26593a447f",
    "OTEL_ENABLED": "true",
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+asyncpg://pytbak:pytbak@postgres:5432/pytbak",
    "REDIS_URL": "redis://redis:6379/0"
}
```

### 9. Swagger UI & Prometheus Metrics

```bash
# Swagger UI
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
200

# Prometheus metrics
$ curl -s http://localhost:8000/metrics | head -3
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 728.0
```

### 10. Route Mappings

```bash
$ curl -s http://localhost:8000/mgmt/mappings | python3 -c \
  "import sys,json; print(f'{len(json.load(sys.stdin)[\"mappings\"])} routes registered')"
31 routes registered
```

### Test Summary

| Test | Endpoint | Result |
|------|----------|--------|
| Health (PG + Redis) | `GET /mgmt/health` | UP |
| Readiness | `GET /mgmt/ready` | READY |
| App Info | `GET /mgmt/info` | v2.0.0 |
| Create context | `POST /api/contexts` | 201 |
| List contexts | `GET /api/contexts` | 200 |
| Update context | `PUT /api/contexts/{id}` | 200 |
| Delete context | `DELETE /api/contexts/{id}` | 200 |
| Fibonacci | `GET /api/fib/10` | 55 |
| Sleep | `GET /api/sleep/1` | 200 |
| Redis counter | `GET /api/count` | 1 |
| Error injection | `?inject_error=500` | 500 injected |
| Delay injection | `?delay_ms=200` | ~222ms |
| Echo headers (auth) | `GET /debug/headers` | 200 |
| DNS resolve (auth) | `GET /debug/dns` | resolved |
| Auth denied | `GET /debug/headers` (no auth) | 401 |
| Env vars | `GET /mgmt/env` | whitelisted |
| Swagger UI | `GET /docs` | 200 |
| Prometheus | `GET /metrics` | scrape-ready |
| Route count | `GET /mgmt/mappings` | 31 routes |

## Configuration

All configuration via environment variables (Pydantic Settings). See [.env.example](.env.example).

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | development | Environment (development/production/test) |
| `DATABASE_URL` | _(empty)_ | PostgreSQL async connection string |
| `REDIS_URL` | _(empty)_ | Redis connection string |
| `DIAG_USERNAME` | admin | Basic auth user for /debug |
| `DIAG_PASSWORD` | password | Basic auth pass for /debug |
| `OTEL_ENABLED` | false | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | http://localhost:4317 | OTLP endpoint |
| `PROMETHEUS_ENABLED` | true | Enable /metrics endpoint |
| `RATE_LIMIT` | 100/minute | Global rate limit |
| `CACHE_TTL` | 300 | Local cache TTL (seconds) |
| `CACHE_MAX_SIZE` | 1000 | Max local cache entries |

## Tests

```bash
pip install -r requirements.txt
pytest -v --tb=short
pytest --cov=app --cov-report=term-missing
```

## Project Structure

```
├── app/
│   ├── main.py                  # FastAPI app + lifespan + create_app()
│   ├── auth.py                  # Basic auth dependency
│   ├── config/
│   │   └── settings.py          # Pydantic Settings (env-based)
│   ├── models/
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── database.py          # SQLAlchemy async models + engine
│   ├── routers/
│   │   ├── api.py               # /api — contexts CRUD + legacy
│   │   ├── debug.py             # /debug — network, CPU, diag tools
│   │   └── mgmt.py              # /mgmt — health, ready, info, env
│   ├── services/
│   │   ├── storage.py           # Unified PG→Redis→Memory fallback
│   │   ├── redis_client.py      # Async Redis with retry
│   │   └── cache.py             # In-memory TTL cache
│   └── middleware/
│       └── error_injection.py   # ?inject_error & ?delay_ms
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_debug.py
│   ├── test_mgmt.py
│   ├── test_middleware.py
│   └── test_storage.py
├── helm/pytbak/                 # Helm chart (production K8s)
│   ├── values.yaml              # Default values
│   └── values-izanami.yaml      # Override per cluster izanami (1 replica, Redis+PG endpoints)
├── otel/                        # Prometheus + OTEL Collector config
├── alembic/                     # DB migrations
├── docker/                      # Legacy Flask app (preserved)
├── Dockerfile
├── docker-compose.yml           # Dev: PG + Redis + Prometheus + OTEL
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Middleware
    participant Storage
    participant PostgreSQL
    participant Redis
    participant InMemory

    Client->>FastAPI: POST /api/contexts
    FastAPI->>Middleware: error_inject / delay check
    Middleware->>FastAPI: pass through
    FastAPI->>Storage: create_context(data)
    Storage->>PostgreSQL: INSERT (if available)
    alt PG unavailable
        Storage->>Redis: SET context:id (if available)
        alt Redis unavailable
            Storage->>InMemory: store in dict
        end
    end
    Storage-->>FastAPI: ContextResponse
    FastAPI-->>Client: 201 Created
```

## Migration from Flask v1

| Feature | Flask v1 | FastAPI v2 |
|---------|----------|------------|
| Framework | Flask + Flasgger | FastAPI (native OpenAPI) |
| Storage | Redis only | PG → Redis → In-Memory |
| Async | No | Yes (async/await) |
| Validation | Manual | Pydantic models |
| Docs | Flasgger Swagger 2.0 | OpenAPI v3 (/docs + /redoc) |
| Tracing | Datadog (ddtrace) | OpenTelemetry (vendor-neutral) |
| Metrics | prometheus-flask-exporter | prometheus-fastapi-instrumentator |
| Config | os.getenv() | Pydantic Settings |
| Deployment | Docker + K8s manifests | Docker + Helm chart |
| Debug tools | Basic diag | + error inject, delay, CPU spike, network scan |
