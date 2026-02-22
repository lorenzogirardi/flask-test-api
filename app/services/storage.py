"""Unified storage service with fallback chain: PostgreSQL -> Redis -> In-Memory."""

import json
import uuid
from datetime import datetime, timezone

from loguru import logger

from app.models.database import ContextDB, get_session_factory
from app.models.schemas import ContextCreate, ContextResponse, ContextUpdate
from app.services.cache import get_cache
from app.services.redis_client import get_redis, is_redis_available, redis_op_with_retry

# --- In-memory fallback store ---
_memory_store: dict[str, dict] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ctx_to_response(data: dict) -> ContextResponse:
    return ContextResponse(**data)


# ========== GET ALL ==========
async def get_all_contexts() -> list[ContextResponse]:
    # Try PostgreSQL
    sf = get_session_factory()
    if sf:
        try:
            from sqlalchemy import select

            async with sf() as session:
                result = await session.execute(select(ContextDB))
                rows = result.scalars().all()
                return [
                    ContextResponse(
                        id=r.id,
                        title=r.title,
                        description=r.description,
                        done=r.done,
                        created_at=r.created_at,
                        updated_at=r.updated_at,
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.warning("PG get_all failed: {}", e)

    # Try Redis (with per-item error handling)
    if is_redis_available():
        r = get_redis()
        if r:
            try:
                keys = await r.keys("context:*")
                contexts = []
                for key in keys:
                    try:
                        data = await r.get(key)
                        if data:
                            contexts.append(ContextResponse(**json.loads(data)))
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning("Skipping corrupt Redis key {}: {}", key, e)
                return contexts
            except Exception as e:
                logger.warning("Redis get_all failed: {}", e)

    # Fallback: in-memory
    return [_ctx_to_response(v) for v in _memory_store.values()]


# ========== GET ONE ==========
async def get_context(context_id: str) -> ContextResponse | None:
    # Check local cache first
    cache = get_cache()
    cached = cache.get(f"ctx:{context_id}")
    if cached:
        return _ctx_to_response(cached)

    # Try PostgreSQL
    sf = get_session_factory()
    if sf:
        try:
            async with sf() as session:
                row = await session.get(ContextDB, context_id)
                if row:
                    resp = ContextResponse(
                        id=row.id,
                        title=row.title,
                        description=row.description,
                        done=row.done,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                    cache.set(f"ctx:{context_id}", resp.model_dump(mode="json"))
                    return resp
                return None
        except Exception as e:
            logger.warning("PG get failed: {}", e)

    # Try Redis
    if is_redis_available():
        r = get_redis()
        if r:
            try:
                data = await r.get(f"context:{context_id}")
                if data:
                    parsed = json.loads(data)
                    cache.set(f"ctx:{context_id}", parsed)
                    return _ctx_to_response(parsed)
                return None
            except Exception as e:
                logger.warning("Redis get failed: {}", e)

    # Fallback: in-memory
    item = _memory_store.get(context_id)
    return _ctx_to_response(item) if item else None


# ========== CREATE ==========
async def create_context(data: ContextCreate) -> ContextResponse:
    context_id = str(uuid.uuid4())
    now = _now()
    ctx = {
        "id": context_id,
        "title": data.title,
        "description": data.description,
        "done": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    # Cache locally
    cache = get_cache()
    cache.set(f"ctx:{context_id}", ctx)

    pg_ok = False

    # Try PostgreSQL
    sf = get_session_factory()
    if sf:
        try:
            async with sf() as session:
                row = ContextDB(
                    id=context_id,
                    title=data.title,
                    description=data.description,
                    done=False,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                await session.commit()
                pg_ok = True
        except Exception as e:
            logger.warning("PG create failed: {}", e)

    # Try Redis (with retry) — best-effort secondary store
    if is_redis_available():
        await redis_op_with_retry(
            lambda: get_redis().set(f"context:{context_id}", json.dumps(ctx))
        )

    # Always store in memory as fallback
    _memory_store[context_id] = ctx
    return _ctx_to_response(ctx)


# ========== UPDATE ==========
async def update_context(context_id: str, data: ContextUpdate) -> ContextResponse | None:
    existing = await get_context(context_id)
    if not existing:
        return None

    updates = data.model_dump(exclude_unset=True)
    updated = existing.model_dump(mode="json")
    updated.update(updates)
    updated["updated_at"] = _now().isoformat()

    # Cache locally
    cache = get_cache()
    cache.set(f"ctx:{context_id}", updated)

    # Try PostgreSQL
    sf = get_session_factory()
    if sf:
        try:
            async with sf() as session:
                row = await session.get(ContextDB, context_id)
                if row:
                    for k, v in updates.items():
                        setattr(row, k, v)
                    row.updated_at = _now()
                    await session.commit()
        except Exception as e:
            logger.warning("PG update failed: {}", e)

    # Try Redis — best-effort sync
    if is_redis_available():
        await redis_op_with_retry(
            lambda: get_redis().set(f"context:{context_id}", json.dumps(updated))
        )

    _memory_store[context_id] = updated
    return _ctx_to_response(updated)


# ========== DELETE ==========
async def delete_context(context_id: str) -> bool:
    existing = await get_context(context_id)
    if not existing:
        return False

    cache = get_cache()
    cache.delete(f"ctx:{context_id}")

    # Try PostgreSQL
    sf = get_session_factory()
    if sf:
        try:
            async with sf() as session:
                row = await session.get(ContextDB, context_id)
                if row:
                    await session.delete(row)
                    await session.commit()
        except Exception as e:
            logger.warning("PG delete failed: {}", e)

    # Try Redis
    if is_redis_available():
        await redis_op_with_retry(lambda: get_redis().delete(f"context:{context_id}"))

    _memory_store.pop(context_id, None)
    return True


# ========== REDIS COUNTER (legacy) ==========
async def redis_incr(key: str) -> int | None:
    """Increment a Redis counter. Returns None if Redis unavailable."""
    if not is_redis_available():
        return None
    r = get_redis()
    if r:
        return await redis_op_with_retry(lambda: r.incr(key))
    return None
