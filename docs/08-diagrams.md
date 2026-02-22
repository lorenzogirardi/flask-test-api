# 8. Diagrams & Graphs

## 8.1 Kubernetes Deployment Diagram

```mermaid
graph TB
    subgraph Internet
        Client[Client / Browser]
    end

    subgraph Cluster["Kubernetes Cluster"]
        subgraph Ingress["Ingress Controller"]
            ING[NGINX / ALB<br/>TLS Termination]
        end

        subgraph NS["Namespace: pytbak"]
            SVC[Service<br/>ClusterIP :8000]
            HPA[HPA<br/>min:2 max:10<br/>CPU target: 70%]

            subgraph Pods["Deployment: pytbak"]
                P1[Pod 1<br/>pytbak:8000]
                P2[Pod 2<br/>pytbak:8000]
                PN[Pod N<br/>pytbak:8000]
            end

            CM[ConfigMap<br/>pytbak-config]
            SEC[Secret<br/>pytbak-auth]
            SM[ServiceMonitor<br/>scrape /metrics]
        end

        subgraph Monitoring["Monitoring (DaemonSet)"]
            DD[Datadog Agent<br/>OpenMetrics scrape<br/>OTLP receiver :4317]
        end
    end

    subgraph External["External Services"]
        PG[(PostgreSQL<br/>RDS / Cloud SQL)]
        RD[(Redis<br/>ElastiCache / Memorystore)]
        DDC[Datadog Cloud<br/>APM + Metrics]
    end

    Client -->|HTTPS| ING
    ING -->|HTTP| SVC
    SVC --> P1 & P2 & PN
    HPA -.->|scale| Pods
    CM -.->|env| Pods
    SEC -.->|env| Pods
    SM -.->|scrape config| DD
    P1 & P2 & PN -->|asyncpg| PG
    P1 & P2 & PN -->|redis-py| RD
    P1 & P2 & PN -->|OTLP gRPC| DD
    DD -->|metrics + traces| DDC

    style PG fill:#336,color:#fff
    style RD fill:#633,color:#fff
    style DD fill:#63c,color:#fff
    style DDC fill:#63c,color:#fff
```

## 8.2 Component Dependency Graph

```mermaid
graph LR
    subgraph Entrypoint
        MAIN[main.py<br/>create_app]
    end

    subgraph Config
        SETTINGS[settings.py<br/>Pydantic Settings]
    end

    subgraph Routers
        API[api.py<br/>/api/*]
        DEBUG[debug.py<br/>/debug/*]
        MGMT[mgmt.py<br/>/mgmt/*]
    end

    subgraph Middleware
        ERR_INJ[error_injection.py<br/>ErrorInjectionMiddleware]
    end

    subgraph Services
        STORAGE[storage.py<br/>Unified CRUD]
        REDIS_C[redis_client.py<br/>Async Redis]
        CACHE[cache.py<br/>TTL Cache]
    end

    subgraph Models
        SCHEMAS[schemas.py<br/>Pydantic Models]
        DB[database.py<br/>SQLAlchemy]
    end

    subgraph Auth
        AUTH[auth.py<br/>BasicAuth]
    end

    MAIN --> API & DEBUG & MGMT
    MAIN --> ERR_INJ
    MAIN --> SETTINGS
    MAIN --> DB
    MAIN --> REDIS_C

    API --> STORAGE & SCHEMAS
    DEBUG --> AUTH & SCHEMAS
    MGMT --> REDIS_C & DB & SCHEMAS

    STORAGE --> DB & REDIS_C & CACHE & SCHEMAS
    REDIS_C --> SETTINGS
    CACHE --> SETTINGS
    DB --> SETTINGS
    AUTH --> SETTINGS

    style MAIN fill:#2a6,color:#fff
    style STORAGE fill:#26a,color:#fff
    style ERR_INJ fill:#a62,color:#fff
    style AUTH fill:#a26,color:#fff
```

## 8.3 Storage Read Flow

```mermaid
flowchart TD
    A[get_context id] --> B{TTL Cache hit?}
    B -->|Yes| C[Return cached]
    B -->|No| D{PostgreSQL configured?}

    D -->|Yes| E[PG: SELECT by ID]
    E -->|Found| F[Cache result + Return]
    E -->|Not found| G[Return None]
    E -->|Error| H{Redis configured?}

    D -->|No| H
    H -->|Yes| I[Redis: GET context:id]
    I -->|Found| J[Cache result + Return]
    I -->|Not found| K[Return None]
    I -->|Error| L[Check memory store]

    H -->|No| L
    L -->|Found| M[Return from memory]
    L -->|Not found| N[Return None]

    style C fill:#6f6,color:#000
    style F fill:#6f6,color:#000
    style J fill:#6f6,color:#000
    style M fill:#6f6,color:#000
    style G fill:#f66,color:#fff
    style K fill:#f66,color:#fff
    style N fill:#f66,color:#fff
```

## 8.4 Storage Write Flow

```mermaid
flowchart TD
    A[create_context data] --> B[Generate UUID + timestamps]
    B --> C[Cache locally TTL Cache]

    C --> D{PostgreSQL available?}
    D -->|Yes| E[INSERT INTO contexts]
    E -->|Success| F[Return Response]
    E -->|Failure| G[Log warning]

    D -->|No| G
    G --> H{Redis available?}
    H -->|Yes| I[SET with retry 3x]
    I -->|Success| J[Continue]
    I -->|All retries failed| K[Log warning]

    H -->|No| K
    K --> L[Store in _memory_store]
    J --> L
    L --> F

    style C fill:#ff6,color:#000
    style E fill:#36f,color:#fff
    style I fill:#f63,color:#fff
    style L fill:#999,color:#fff
    style F fill:#6f6,color:#000
```

## 8.5 Application Startup Flow

```mermaid
flowchart TD
    A[uvicorn app.main:app] --> B[create_app]
    B --> C[Load Settings .env]
    C --> D[Register Middleware]
    D --> D1[GZipMiddleware]
    D --> D2[ErrorInjectionMiddleware]
    D --> D3[slowapi RateLimiter]

    D --> E{PROMETHEUS_ENABLED?}
    E -->|Yes| F[Instrumentator.expose /metrics]
    E -->|No| G[Skip]

    D --> H{OTEL_ENABLED?}
    H -->|Yes| I[TracerProvider + BatchSpanProcessor<br/>FastAPIInstrumentor]
    H -->|No| J[Skip]

    D --> K[Register Routers]
    K --> K1[/api]
    K --> K2[/debug]
    K --> K3[/mgmt]

    B --> L[Lifespan: startup]
    L --> M[init_db]
    M -->|DATABASE_URL set| N[Create engine + tables]
    M -->|Not set| O[PG disabled]
    L --> P[init_redis]
    P -->|REDIS_URL set| Q[Connect + ping]
    P -->|Not set| R[Redis disabled]

    N & O & Q & R --> S[App Ready]
    S --> T[Serving on :8000]

    style T fill:#6f6,color:#000
    style O fill:#999,color:#fff
    style R fill:#999,color:#fff
```

## 8.6 Request Lifecycle

```mermaid
flowchart LR
    A[HTTP Request] --> B[Uvicorn]
    B --> C[GZip MW]
    C --> D[ErrorInjection MW]
    D --> E[RateLimit MW]
    E --> F[OTEL Span]
    F --> G[Route Match]
    G --> H[Dependency Injection<br/>Auth if needed]
    H --> I[Handler]
    I --> J[Service Layer]
    J --> K[Response]
    K --> L[OTEL Span Close]
    L --> M[Prometheus Counter]
    M --> N[GZip Compress]
    N --> O[HTTP Response]

    style A fill:#36f,color:#fff
    style O fill:#6f6,color:#000
```
