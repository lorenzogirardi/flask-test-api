"""FastAPI application entry point."""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger

from app.config import get_settings
from app.middleware.error_injection import ErrorInjectionMiddleware
from app.models.database import close_db, init_db
from app.services.redis_client import close_redis, init_redis


# --- Structured logging (loguru + JSON) ---
def _setup_logging() -> None:
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="{time:YYYY-MM-DDTHH:mm:ss.SSS}Z | {level:<8} | {name}:{function}:{line} | {message}",
        serialize=True,
    )


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    settings = get_settings()

    # Init backends (graceful: failures are logged, not fatal)
    db_ok = await init_db()
    redis_ok = await init_redis()
    logger.info(
        "Startup complete | pg={} redis={} env={}",
        "connected" if db_ok else "fallback",
        "connected" if redis_ok else "fallback",
        settings.app_env,
    )

    yield

    await close_redis()
    await close_db()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="pytbak API",
        description="Python REST API Test & Debug Application (FastAPI)",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- Middleware ---
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(ErrorInjectionMiddleware)

    # --- Rate limiting ---
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except ImportError:
        logger.warning("slowapi not installed, rate limiting disabled")

    # --- Prometheus metrics ---
    if settings.prometheus_enabled:
        try:
            from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
            from prometheus_fastapi_instrumentator import Instrumentator

            Instrumentator().instrument(app).expose(app, endpoint="/metrics")
        except ImportError:
            logger.warning("prometheus-fastapi-instrumentator not installed, /metrics disabled")

    # --- OpenTelemetry ---
    if settings.otel_enabled:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create({"service.name": settings.otel_service_name})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            FastAPIInstrumentor.instrument_app(app)
            logger.info("OpenTelemetry tracing enabled -> {}", settings.otel_exporter_otlp_endpoint)
        except ImportError:
            logger.warning("OpenTelemetry packages not installed, tracing disabled")

    # --- Routers ---
    from app.routers.api import router as api_router
    from app.routers.debug import router as debug_router
    from app.routers.mgmt import router as mgmt_router

    app.include_router(api_router)
    app.include_router(debug_router)
    app.include_router(mgmt_router)

    # --- Error handlers ---
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(status_code=404, content={"error": "Not found"})

    @app.exception_handler(400)
    async def bad_request_handler(request: Request, exc):
        return JSONResponse(status_code=400, content={"error": "Bad request"})

    # --- Root / index ---
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/api/", response_class=HTMLResponse, include_in_schema=False)
    async def index():
        return """<!DOCTYPE html>
<html>
<head><title>pytbak API</title></head>
<body>
<h1>pytbak API v2</h1>
<ul>
  <li><a href="/docs">Swagger UI</a></li>
  <li><a href="/redoc">ReDoc</a></li>
  <li><a href="/mgmt/health">Health</a></li>
  <li><a href="/metrics">Metrics</a></li>
</ul>
</body>
</html>"""

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
