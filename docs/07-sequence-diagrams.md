# 7. Sequence Diagrams

## 7.1 Happy Path — POST /api/contexts (with fallback)

```mermaid
sequenceDiagram
    actor User
    participant MW as Middleware
    participant Router as API Router
    participant Storage as Storage Service
    participant Cache as TTL Cache
    participant PG as PostgreSQL
    participant Redis as Redis
    participant Mem as In-Memory Dict

    User->>MW: POST /api/contexts {"title": "Test"}
    MW->>MW: Check inject_error / delay_ms
    MW->>Router: Pass through

    Router->>Router: Validate ContextCreate (Pydantic)
    Router->>Storage: create_context(data)

    Storage->>Storage: Generate UUID + timestamps
    Storage->>Cache: cache.set("ctx:{id}", data)
    Note over Cache: Always cached locally

    alt PostgreSQL available
        Storage->>PG: INSERT INTO contexts
        PG-->>Storage: OK
        Storage-->>Router: ContextResponse
    else PostgreSQL unavailable
        Storage->>Storage: log.warning("PG create failed")

        alt Redis available
            Storage->>Redis: SET context:{id} (with retry)
            Redis-->>Storage: OK
        else Redis unavailable
            Storage->>Storage: log.warning("Redis failed")
        end

        Storage->>Mem: _memory_store[id] = data
        Storage-->>Router: ContextResponse
    end

    Router-->>User: 201 Created + JSON body
```

## 7.2 Error Injection + Delay

```mermaid
sequenceDiagram
    actor User
    participant MW as ErrorInjectionMiddleware
    participant Router as Any Router
    participant Handler as Endpoint Handler

    User->>MW: GET /api/contexts?delay_ms=3000&inject_error=500

    Note over MW: Step 1: Process delay
    MW->>MW: Parse delay_ms=3000
    MW->>MW: await asyncio.sleep(3.0)
    Note over MW: 3 seconds pass...

    Note over MW: Step 2: Process error injection
    MW->>MW: Parse inject_error=500
    MW-->>User: 500 {"error": "Injected error 500", "injected": true}

    Note over Router,Handler: Router and Handler are NEVER called<br/>Middleware short-circuits the pipeline

    rect rgb(255, 240, 240)
        Note over User,Handler: Alternative: delay_ms=random
        User->>MW: GET /mgmt/info?delay_ms=random
        MW->>MW: random.uniform(0, 5000) → e.g. 2847ms
        MW->>MW: await asyncio.sleep(2.847)
        MW->>Router: No inject_error → pass through
        Router->>Handler: app_info()
        Handler-->>User: 200 {"app": {...}}
    end
```

## 7.3 Network Scan (/debug/network/scan)

```mermaid
sequenceDiagram
    actor User
    participant Auth as BasicAuth
    participant Router as Debug Router
    participant Ping as subprocess: ping
    participant DNS as socket.getaddrinfo
    participant TCP as socket.connect
    participant TR as subprocess: traceroute

    User->>Auth: GET /debug/network/scan?target=google.com:443<br/>Authorization: Basic YWRtaW46cGFzc3dvcmQ=
    Auth->>Auth: secrets.compare_digest(user, pass)
    Auth->>Router: Authenticated

    Router->>Router: Parse target → host="google.com", port=443
    Router->>Router: Validate host chars [a-zA-Z0-9.-_]

    par Parallel diagnostics
        Router->>Ping: ping -c 3 -W 2 google.com
        Note over Ping: asyncio.create_subprocess_exec<br/>timeout: 15s
        Ping-->>Router: {output: "...", returncode: 0}

        Router->>DNS: getaddrinfo("google.com", TCP)
        DNS-->>Router: {addresses: ["142.251.x.x", "2a00:..."]}

        Router->>TCP: connect(google.com, 443, timeout=5)
        TCP-->>Router: {status: "open", port: 443}

        Router->>TR: traceroute -m 10 -w 2 google.com
        Note over TR: asyncio.create_subprocess_exec<br/>timeout: 30s
        TR-->>Router: {output: "...", returncode: 0}
    end

    Router-->>User: 200 NetworkScanResult {ping, dns, tcp_check, traceroute}
```

## 7.4 Health Check Flow

```mermaid
sequenceDiagram
    actor Probe as K8s Liveness Probe
    participant Router as Mgmt Router
    participant Redis as Redis Client
    participant PG as PostgreSQL

    Probe->>Router: GET /mgmt/health

    par Check backends
        Router->>Redis: is_redis_available()?
        alt Redis configured
            Redis->>Redis: await redis.ping()
            alt Ping OK
                Redis-->>Router: HealthCheck(name="redis", status="UP")
            else Ping failed
                Redis-->>Router: HealthCheck(name="redis", status="DOWN", error="...")
            end
        else Not configured
            Redis-->>Router: HealthCheck(name="redis", status="NOT_CONFIGURED")
        end

        Router->>PG: get_session_factory()?
        alt PG configured
            PG->>PG: SELECT 1
            alt Query OK
                PG-->>Router: HealthCheck(name="postgresql", status="UP")
            else Query failed
                PG-->>Router: HealthCheck(name="postgresql", status="DOWN", error="...")
            end
        else Not configured
            PG-->>Router: HealthCheck(name="postgresql", status="NOT_CONFIGURED")
        end
    end

    Router->>Router: Compute overall status
    Note over Router: UP = all checks UP or NOT_CONFIGURED<br/>DEGRADED = some DOWN<br/>503 = all configured backends DOWN

    Router-->>Probe: 200/503 HealthResponse {status, checks[]}
```

## 7.5 CPU Spike Flow

```mermaid
sequenceDiagram
    actor User
    participant Auth as BasicAuth
    participant Router as Debug Router
    participant P1 as Process 1
    participant P2 as Process 2
    participant OS as OS Scheduler

    User->>Auth: POST /debug/cpu/spike<br/>{"duration": 30, "cores": 2}
    Auth->>Router: Authenticated

    Router->>Router: Validate CpuSpikeRequest (1≤duration≤120, 1≤cores≤16)

    Router->>P1: multiprocessing.Process(target=_cpu_burn, args=(30,))
    Router->>P2: multiprocessing.Process(target=_cpu_burn, args=(30,))
    P1->>P1: start()
    P2->>P2: start()

    Router-->>User: 200 {"status": "started", "duration": 30, "cores": 2}
    Note over User: Response is immediate<br/>CPU burn runs in background

    par Background CPU burn
        P1->>OS: while time < 30s: sum(i*i for i in range(10000))
        P2->>OS: while time < 30s: sum(i*i for i in range(10000))
    end

    Note over P1,P2: Processes terminate after 30s<br/>No cleanup needed (fire-and-forget)
```
