"""Management router — health, ready, info, env, mappings, threaddump."""

import os
import sys
import traceback

from fastapi import APIRouter, Request
from loguru import logger

from app.config import get_settings
from app.models.database import get_session_factory
from app.models.schemas import AppInfoResponse, HealthCheck, HealthResponse
from app.services.redis_client import get_redis, is_redis_available

router = APIRouter(prefix="/mgmt", tags=["Management"])


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check():
    checks: list[HealthCheck] = []
    overall = "UP"

    # Redis check
    if is_redis_available():
        r = get_redis()
        try:
            await r.ping()
            checks.append(HealthCheck(name="redis", status="UP"))
        except Exception as e:
            checks.append(HealthCheck(name="redis", status="DOWN", error=str(e)))
            overall = "DEGRADED"
    else:
        checks.append(HealthCheck(name="redis", status="NOT_CONFIGURED"))

    # PostgreSQL check
    sf = get_session_factory()
    if sf:
        try:
            from sqlalchemy import text

            async with sf() as session:
                await session.execute(text("SELECT 1"))
            checks.append(HealthCheck(name="postgresql", status="UP"))
        except Exception as e:
            checks.append(HealthCheck(name="postgresql", status="DOWN", error=str(e)))
            overall = "DEGRADED"
    else:
        checks.append(HealthCheck(name="postgresql", status="NOT_CONFIGURED"))

    status_code = 200 if overall == "UP" else 503 if all(c.status == "DOWN" for c in checks if c.status != "NOT_CONFIGURED") else 200
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content=HealthResponse(status=overall, checks=checks).model_dump(),
        status_code=status_code,
    )


@router.get("/ready", summary="Readiness probe")
async def readiness():
    """Returns 200 when app is ready to serve traffic (always true once started)."""
    return {"status": "READY"}


@router.get("/info", response_model=AppInfoResponse, summary="Application info")
async def app_info():
    settings = get_settings()
    return {
        "app": {
            "name": settings.app_name,
            "description": "Python REST API Test Application (FastAPI)",
            "version": settings.app_version,
            "environment": settings.app_env,
        }
    }


@router.get("/env", summary="Whitelisted environment variables")
async def app_env():
    safe_vars = [
        "PATH", "HOSTNAME", "REDIS_HOST", "REDIS_PORT", "REDIS_DB",
        "REDIS_URL", "DATABASE_URL", "OTEL_ENABLED", "APP_ENV",
        "DD_PROFILING_ENABLED", "DD_LOGS_INJECTION",
    ]
    return {k: v for k, v in os.environ.items() if k in safe_vars}


@router.get("/mappings", summary="All URL route mappings")
async def app_mappings(request: Request):
    routes = []
    for route in request.app.routes:
        info = {
            "path": getattr(route, "path", str(route)),
            "methods": sorted(getattr(route, "methods", set())),
            "name": getattr(route, "name", None),
        }
        routes.append(info)
    return {"mappings": routes}


@router.get("/threaddump", summary="Thread dump")
async def app_threaddump():
    dump = []
    for thread_id, stack in sys._current_frames().items():
        dump.append(f"\n# Thread: {thread_id}")
        for filename, lineno, name, line in traceback.extract_stack(stack):
            dump.append(f'  File: "{filename}", line {lineno}, in {name}')
            if line:
                dump.append(f"    {line.strip()}")
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse("\n".join(dump))
