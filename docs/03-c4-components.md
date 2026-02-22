# 3. C4 Components (Level 3)

## 3.1 Component Overview

The FastAPI application is structured into layers following clean architecture principles:

| Layer | Components | Responsibility |
|-------|-----------|----------------|
| **Routers** | `api.py`, `debug.py`, `mgmt.py` | HTTP request handling, validation |
| **Middleware** | `ErrorInjectionMiddleware`, GZip, RateLimit | Cross-cutting concerns |
| **Services** | `storage.py`, `redis_client.py`, `cache.py` | Business logic, data access |
| **Models** | `schemas.py`, `database.py` | Data structures, ORM |
| **Config** | `settings.py` | Environment-based configuration |
| **Auth** | `auth.py` | HTTP Basic authentication |

## 3.2 C4 Component Diagram (Level 3)

```mermaid
C4Component
    title pytbak — Component Diagram

    Container_Boundary(fastapi, "FastAPI Application") {

        Component(middleware, "Middleware Layer", "Starlette", "ErrorInjection, GZip,<br/>RateLimit (slowapi)")
        Component(auth, "Auth Module", "FastAPI Security", "HTTP Basic Auth<br/>secrets.compare_digest()")

        Component_Boundary(routers, "Routers") {
            Component(api_router, "API Router", "/api/*", "Contexts CRUD<br/>fib, sleep, count")
            Component(debug_router, "Debug Router", "/debug/*", "Network scan, CPU spike<br/>ping, dns, curl, echo")
            Component(mgmt_router, "Mgmt Router", "/mgmt/*", "Health, ready, info<br/>env, mappings, threaddump")
        }

        Component_Boundary(services, "Services") {
            Component(storage_svc, "Storage Service", "storage.py", "Unified CRUD<br/>PG→Redis→Memory fallback")
            Component(redis_svc, "Redis Client", "redis_client.py", "Async connection<br/>retry logic")
            Component(cache_svc, "TTL Cache", "cache.py", "In-memory dict<br/>thread-safe, TTL eviction")
        }

        Component_Boundary(models, "Models") {
            Component(schemas, "Pydantic Schemas", "schemas.py", "Request/response<br/>validation models")
            Component(db_models, "SQLAlchemy Models", "database.py", "ContextDB ORM<br/>async engine")
        }

        Component(config, "Settings", "Pydantic Settings", "Env-based config<br/>cached singleton")
    }

    ContainerDb(postgres, "PostgreSQL", "Primary store")
    ContainerDb(redis, "Redis", "Cache/secondary")

    Rel(middleware, api_router, "passes request")
    Rel(middleware, debug_router, "passes request")
    Rel(middleware, mgmt_router, "passes request")
    Rel(debug_router, auth, "requires auth")
    Rel(api_router, storage_svc, "CRUD operations")
    Rel(storage_svc, db_models, "SQLAlchemy queries")
    Rel(storage_svc, redis_svc, "Redis operations")
    Rel(storage_svc, cache_svc, "Local cache R/W")
    Rel(db_models, postgres, "asyncpg")
    Rel(redis_svc, redis, "aioredis")
    Rel(mgmt_router, redis_svc, "health check")
    Rel(mgmt_router, db_models, "health check")
```

## 3.3 Router Breakdown

### API Router (`/api`)

| Endpoint | Method | Handler | Storage |
|----------|--------|---------|---------|
| `/api/contexts` | GET | `list_contexts()` | `storage.get_all_contexts()` |
| `/api/contexts/{id}` | GET | `get_context()` | `storage.get_context()` |
| `/api/contexts` | POST | `create_context()` | `storage.create_context()` |
| `/api/contexts/{id}` | PUT | `update_context()` | `storage.update_context()` |
| `/api/contexts/{id}` | DELETE | `delete_context()` | `storage.delete_context()` |
| `/api/fib/{x}` | GET | `fibonacci()` | None (compute only) |
| `/api/sleep/{seconds}` | GET | `sleep_endpoint()` | None (asyncio.sleep) |
| `/api/count` | GET | `count()` | `storage.redis_incr()` |
| `/api/redisping` | GET | `redis_ping()` | httpx → webdis |

### Debug Router (`/debug`) — All require Basic Auth

| Endpoint | Method | Handler | Mechanism |
|----------|--------|---------|-----------|
| `/debug/network/scan` | GET | `network_scan()` | subprocess (ping, traceroute) + socket |
| `/debug/cpu/spike` | POST | `cpu_spike()` | multiprocessing.Process |
| `/debug/ping` | GET | `ping_host()` | subprocess (ping) |
| `/debug/dns` | GET | `dns_resolve()` | socket.getaddrinfo() |
| `/debug/curl` | GET | `curl()` | httpx.AsyncClient |
| `/debug/tcp-check` | GET | `tcp_check()` | socket.create_connection() |
| `/debug/headers` | GET/POST/PUT/DELETE | `echo_headers()` | request.headers |
| `/debug/echo` | POST/PUT | `echo_body()` | request.body() |
| `/debug/random-error` | GET | `random_error()` | random.choice() |

### Management Router (`/mgmt`)

| Endpoint | Method | Handler | Checks |
|----------|--------|---------|--------|
| `/mgmt/health` | GET | `health_check()` | Redis ping + PG `SELECT 1` |
| `/mgmt/ready` | GET | `readiness()` | Always 200 |
| `/mgmt/info` | GET | `app_info()` | Settings |
| `/mgmt/env` | GET | `app_env()` | Whitelisted env vars only |
| `/mgmt/mappings` | GET | `app_mappings()` | FastAPI route table |
| `/mgmt/threaddump` | GET | `app_threaddump()` | sys._current_frames() |

## 3.4 Service Layer Detail

### Storage Service — Fallback Chain

```
create_context(data):
  1. Generate UUID + timestamps
  2. Cache locally (TTLCache)
  3. Try PostgreSQL INSERT
     ├─ Success → return
     └─ Failure → log warning
  4. Try Redis SET (with retry)
     ├─ Success → continue
     └─ Failure → log warning
  5. Store in _memory_store dict
  6. Return ContextResponse
```

### Redis Client — Retry Logic

```
redis_op_with_retry(operation):
  for attempt in 1..max_retries:
    try:
      return await operation()
    except Exception:
      log warning
      sleep(retry_delay)
  return None  # caller handles fallback
```

### TTL Cache — Eviction Strategy

| Operation | Complexity | Thread-safe |
|-----------|-----------|-------------|
| `get(key)` | O(1) | Yes (Lock) |
| `set(key, value)` | O(1) amortized | Yes (Lock) |
| `delete(key)` | O(1) | Yes (Lock) |
| Eviction (on full) | O(n) scan expired, then LRU | Inline on set() |

## 3.5 Middleware Pipeline

Request processing order:

```
Client Request
    │
    ▼
┌─────────────────────┐
│  GZipMiddleware      │  Compresses responses > 500 bytes
├─────────────────────┤
│  ErrorInjection      │  ?inject_error= → short-circuit response
│  Middleware           │  ?delay_ms= → asyncio.sleep before processing
├─────────────────────┤
│  RateLimit (slowapi) │  100/minute default, 429 on exceed
├─────────────────────┤
│  OTEL Instrumentation│  Span creation, trace propagation
├─────────────────────┤
│  Router Dispatch     │  api / debug / mgmt
└─────────────────────┘
```
