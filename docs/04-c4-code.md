# 4. C4 Code (Level 4)

Key code patterns and snippets from the application.

## 4.1 Pydantic Models — Request Validation

```python
# app/models/schemas.py
class ContextCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")

class ContextUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    done: bool | None = None

class ContextResponse(BaseModel):
    id: str
    title: str
    description: str
    done: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

**Pattern**: `ContextUpdate` uses `Optional` fields with `exclude_unset=True` in storage to support partial updates (PATCH semantics on PUT).

## 4.2 Error Injection Middleware

```python
# app/middleware/error_injection.py
class ErrorInjectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        params = request.query_params

        # Delay injection
        delay = params.get("delay_ms")
        if delay:
            ms = random.uniform(0, 5000) if delay.lower() == "random" else float(delay)
            if ms > 0:
                await asyncio.sleep(ms / 1000.0)

        # Error injection — short-circuits the entire pipeline
        error = params.get("inject_error")
        if error:
            if error.isdigit():
                return JSONResponse(status_code=int(error),
                    content={"error": f"Injected error {error}", "injected": True})
            if error.startswith("custom:"):
                return JSONResponse(status_code=500,
                    content={"error": error[7:], "injected": True})

        return await call_next(request)
```

**Key**: Middleware runs BEFORE routing — errors can be injected on any endpoint without modifying handlers.

## 4.3 Storage Fallback Chain

```python
# app/services/storage.py — simplified create flow
async def create_context(data: ContextCreate) -> ContextResponse:
    context_id = str(uuid.uuid4())
    ctx = {"id": context_id, "title": data.title, ...}

    # 1. Always cache locally
    cache = get_cache()
    cache.set(f"ctx:{context_id}", ctx)

    # 2. Try PostgreSQL
    sf = get_session_factory()
    if sf:
        try:
            async with sf() as session:
                session.add(ContextDB(**ctx))
                await session.commit()
                return _ctx_to_response(ctx)
        except Exception as e:
            logger.warning("PG create failed: {}", e)

    # 3. Try Redis (with retry)
    if is_redis_available():
        await redis_op_with_retry(
            lambda: get_redis().set(f"context:{context_id}", json.dumps(ctx))
        )

    # 4. Always store in memory as ultimate fallback
    _memory_store[context_id] = ctx
    return _ctx_to_response(ctx)
```

**Pattern**: Write-through to all available backends. Read uses cache-first, then PG, then Redis, then memory.

## 4.4 Async Redis with Retry

```python
# app/services/redis_client.py
async def redis_op_with_retry(coro_factory, retries=None):
    settings = get_settings()
    max_retries = retries or settings.redis_retry_attempts  # default: 3
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except Exception as e:
            logger.warning("Redis op failed (attempt {}/{}): {}", attempt+1, max_retries, e)
            if attempt < max_retries - 1:
                await asyncio.sleep(settings.redis_retry_delay)  # default: 0.5s
    return None  # caller handles gracefully
```

**Pattern**: Factory function `coro_factory` is called each attempt (not a pre-built coroutine) to ensure fresh execution.

## 4.5 Auth — Timing-Safe Comparison

```python
# app/auth.py
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    settings = get_settings()
    correct_user = secrets.compare_digest(credentials.username, settings.diag_username)
    correct_pass = secrets.compare_digest(credentials.password, settings.diag_password)
    if not (correct_user and correct_pass):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return credentials.username
```

**Security**: Uses `secrets.compare_digest()` to prevent timing attacks on credential comparison.

## 4.6 Configuration — Pydantic Settings

```python
# app/config/settings.py
class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    app_env: Literal["development", "production", "test"] = "development"
    database_url: str | None = None     # empty = no PostgreSQL
    redis_url: str | None = None        # empty = no Redis
    otel_enabled: bool = False           # opt-in
    prometheus_enabled: bool = True      # opt-out
    rate_limit: str = "100/minute"
    cache_ttl: int = 300
    diag_username: str = "admin"
    diag_password: str = "password"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Pattern**: `@lru_cache` ensures settings are parsed once. All config is env-driven with sensible defaults.

## 4.7 OTEL Instrumentation

```python
# app/main.py — inside create_app()
if settings.otel_enabled:
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(
        OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    ))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
```

**Pattern**: Conditional import — OTEL packages are only loaded if `OTEL_ENABLED=true`. App works fine without them installed.

## 4.8 CPU Spike — Process Isolation

```python
# app/routers/debug.py
def _cpu_burn(duration: int) -> None:
    """Burn CPU for N seconds — runs in separate process."""
    end = time.monotonic() + duration
    while time.monotonic() < end:
        _ = sum(i * i for i in range(10000))

@router.post("/cpu/spike", dependencies=[Depends(verify_credentials)])
async def cpu_spike(params: CpuSpikeRequest):
    for _ in range(params.cores):
        p = multiprocessing.Process(target=_cpu_burn, args=(params.duration,))
        p.start()
    return CpuSpikeResponse(status="started", ...)
```

**Pattern**: Uses `multiprocessing.Process` (not threads) — actual CPU load on separate cores, won't block the async event loop.
