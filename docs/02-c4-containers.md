# 2. C4 Containers (Level 2)

## 2.1 Container Overview

| Container | Technology | Purpose | Required |
|-----------|-----------|---------|----------|
| **pytbak API** | FastAPI + Uvicorn | Main application, all endpoints | Yes |
| **PostgreSQL** | PostgreSQL 16 | Primary persistent storage | Optional |
| **Redis** | Redis 7 | Cache, counters, secondary storage | Optional |
| **Datadog Agent** | Datadog | Metrics scraping + trace ingestion | Optional |
| **Local Fallback** | In-memory dict + TTL cache | Zero-dependency storage | Built-in |

## 2.2 Fallback Strategy

```
Priority:  PostgreSQL  →  Redis  →  In-Memory
              ▲              ▲           ▲
          DATABASE_URL    REDIS_URL    always on
          (env var)       (env var)
```

- If `DATABASE_URL` is set and reachable → PostgreSQL is primary store
- If `REDIS_URL` is set and reachable → Redis is secondary/cache
- If both are down or unconfigured → In-memory dict (thread-safe, TTL cache)
- **No startup failure**: app always starts, degrades gracefully

## 2.3 Environment Differences

| Aspect | Development | izanami (192.168.1.14) | itachi (prod) |
|--------|-------------|------------------------|---------------|
| PostgreSQL | docker-compose container | Helm chart `helm-postgresql` ns `postgresql` | External managed service |
| Redis | docker-compose container | Helm chart `helm-redis` ns `redis` | External managed service |
| Webdis | Not used | Deployed (`:7379` HTTP interface) | Not used |
| Observability | Libraries only | Datadog Agent in cluster | Datadog Agent in cluster |
| Config | `.env` file | `values-izanami.yaml` + K8s secrets | Helm values + K8s secrets |
| Scaling | Single instance | 1 replica, no HPA | HPA (2-10 replicas) |
| Storage | In-memory/local | hostPath PV (Retain) `/mnt/` | Managed storage |

## 2.4 C4 Container Diagram (Level 2)

```mermaid
C4Container
    title pytbak — Container Diagram

    Person(user, "Developer / QA / SRE")

    Container_Boundary(app_boundary, "pytbak Application") {
        Container(api, "FastAPI App", "Python 3.12, Uvicorn", "REST API + debug tools<br/>Port 8000")
        Container(cache, "Local Cache", "In-memory dict + TTL", "Thread-safe fallback<br/>Built into app process")
    }

    Container_Boundary(data_boundary, "Data Stores (optional)") {
        ContainerDb(postgres, "PostgreSQL", "v16", "Primary context storage<br/>Async SQLAlchemy + asyncpg")
        ContainerDb(redis, "Redis", "v7", "Cache, counters<br/>Async redis-py + hiredis")
    }

    Container_Boundary(obs_boundary, "Observability") {
        Container_Ext(datadog, "Datadog Agent", "DaemonSet", "Scrapes /metrics<br/>Receives OTLP traces")
    }

    Rel(user, api, "HTTP/JSON", "REST API (8000)")
    Rel(api, postgres, "CRUD", "asyncpg (5432)")
    Rel(api, redis, "Cache/Counters", "redis-py (6379)")
    Rel(api, cache, "Fallback R/W", "in-process")
    Rel(datadog, api, "Scrape metrics", "HTTP /metrics")
    Rel(api, datadog, "Export traces", "OTLP gRPC (4317)")
```

## 2.5 Container Communication Matrix

| From | To | Protocol | Port | Auth | Encryption | Async |
|------|-----|----------|------|------|-----------|-------|
| User | pytbak API | HTTP | 8000 | Basic (debug only) | TLS at ingress | - |
| pytbak API | PostgreSQL | TCP | 5432 | Password | SSL optional | Yes (asyncpg) |
| pytbak API | Redis | TCP | 6379 | None (internal) | TLS optional | Yes (aioredis) |
| pytbak API | Datadog Agent | gRPC | 4317 | None (internal) | No | Yes (batch export) |
| Datadog Agent | pytbak API | HTTP | 8000 | None | No | Pull-based |

## 2.6 Port Map

| Port | Service | Protocol | Exposure |
|------|---------|----------|----------|
| 8000 | FastAPI (Uvicorn) | HTTP | ClusterIP / Ingress |
| 5432 | PostgreSQL | TCP | Internal only (ns: postgresql) |
| 6379 | Redis | TCP | Internal only (ns: redis) |
| 7379 | Webdis HTTP | HTTP | Internal only (ns: redis) |
| 4317 | OTLP gRPC (Datadog) | gRPC | Internal only |
