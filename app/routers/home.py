"""Home dashboard router — serves the DebugKnife UI."""

import pathlib

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.models.database import get_session_factory
from app.services.redis_client import is_redis_available

_TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["Dashboard"])


def _status_dot(status: str) -> str:
    """Map a status string to a CSS dot color class."""
    s = status.upper()
    if s in ("UP", "CONNECTED", "ENABLED"):
        return "green"
    if s in ("DEGRADED", "NOT_CONFIGURED", "DISABLED"):
        return "yellow"
    if s in ("DOWN", "ERROR"):
        return "red"
    return "gray"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request):
    settings = get_settings()

    # Determine base path from request (handles reverse proxy prefix)
    # If behind ingress at /api, request.scope["root_path"] will be "/api"
    base_path = request.scope.get("root_path", "").rstrip("/")

    # PostgreSQL status
    sf = get_session_factory()
    if sf:
        try:
            from sqlalchemy import text
            async with sf() as session:
                await session.execute(text("SELECT 1"))
            pg_status = "Connected"
        except Exception:
            pg_status = "Down"
    else:
        pg_status = "Not Configured"

    # Redis status
    if is_redis_available():
        from app.services.redis_client import get_redis
        try:
            await get_redis().ping()
            redis_status = "Connected"
        except Exception:
            redis_status = "Down"
    else:
        redis_status = "Not Configured"

    # OTEL / Prometheus status
    otel_status = "Enabled" if settings.otel_enabled else "Disabled"
    prom_status = "Enabled" if settings.prometheus_enabled else "Disabled"

    return templates.TemplateResponse(request, "index.html", {
        "base_path": base_path,
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "pg_status": pg_status,
        "pg_color": "green" if pg_status == "Connected" else "yellow",
        "pg_dot": _status_dot(pg_status),
        "redis_status": redis_status,
        "redis_color": "green" if redis_status == "Connected" else "yellow",
        "redis_dot": _status_dot(redis_status),
        "otel_status": otel_status,
        "otel_dot": _status_dot(otel_status),
        "prom_status": prom_status,
        "prom_dot": _status_dot(prom_status),
    })
