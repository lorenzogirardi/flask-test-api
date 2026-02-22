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
