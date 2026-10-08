"""Tests for the core API router (contexts CRUD + legacy)."""

import pytest

from app.services import storage


@pytest.mark.anyio
async def test_list_contexts_empty(client):
    resp = await client.get("/api/contexts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_create_context(client):
    resp = await client.post("/api/contexts", json={"title": "Test", "description": "Desc"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test"
    assert data["description"] == "Desc"
    assert data["done"] is False
    assert "id" in data


@pytest.mark.anyio
async def test_create_and_get_context(client):
    create = await client.post("/api/contexts", json={"title": "CTX1"})
    ctx_id = create.json()["id"]
    resp = await client.get(f"/api/contexts/{ctx_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "CTX1"


@pytest.mark.anyio
async def test_get_context_not_found(client):
    resp = await client.get("/api/contexts/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_context(client):
    create = await client.post("/api/contexts", json={"title": "Old"})
    ctx_id = create.json()["id"]
    resp = await client.put(f"/api/contexts/{ctx_id}", json={"title": "New", "done": True})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
    assert resp.json()["done"] is True


@pytest.mark.anyio
async def test_update_context_not_found(client):
    resp = await client.put("/api/contexts/nonexistent", json={"title": "X"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_context(client):
    create = await client.post("/api/contexts", json={"title": "Del"})
    ctx_id = create.json()["id"]
    resp = await client.delete(f"/api/contexts/{ctx_id}")
    assert resp.status_code == 200
    assert resp.json()["result"] is True
    # Verify it's gone
    resp2 = await client.get(f"/api/contexts/{ctx_id}")
    assert resp2.status_code == 404


@pytest.mark.anyio
async def test_delete_context_not_found(client):
    resp = await client.delete("/api/contexts/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_fibonacci(client):
    resp = await client.get("/api/fib/10")
    assert resp.status_code == 200
    assert resp.json()["result"] == "55"


@pytest.mark.anyio
async def test_fibonacci_too_large(client):
    resp = await client.get("/api/fib/30000")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_sleep_endpoint(client):
    resp = await client.get("/api/sleep/1")
    assert resp.status_code == 200
    assert "Delayed" in resp.json()["message"]


@pytest.mark.anyio
async def test_sleep_too_long(client):
    resp = await client.get("/api/sleep/26")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Sleep time too long, max 25 seconds"


@pytest.mark.anyio
async def test_sleep_up_to_25_seconds_allowed(client, monkeypatch):
    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    resp = await client.get("/api/sleep/25")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Delayed by 25 seconds"}


@pytest.mark.anyio
async def test_bad_request_keeps_http_exception_detail(client):
    """No generic 400 handler may swallow the HTTPException detail body."""
    resp = await client.get("/api/sleep/-1")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Sleep time must be non-negative"


@pytest.mark.anyio
async def test_count_without_redis(client):
    resp = await client.get("/api/count")
    assert resp.status_code == 200
    assert resp.json()["counter"] is None


@pytest.mark.anyio
async def test_count_increments_by_one_per_request(client, monkeypatch):
    """Warming the key must not advance the counter: each request adds exactly one."""
    state = {"value": 0}

    async def fake_get(_key):
        return str(state["value"])

    async def fake_incr(_key):
        state["value"] += 1
        return state["value"]

    monkeypatch.setattr(storage, "redis_get", fake_get)
    monkeypatch.setattr(storage, "redis_incr", fake_incr)

    r1 = await client.get("/api/count")
    r2 = await client.get("/api/count")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["counter"] is not None
    assert r2.json()["counter"] == r1.json()["counter"] + 1


@pytest.mark.anyio
async def test_count_warms_connection_before_incrementing(client, monkeypatch):
    """The counter key is read once before the increment that produces the result."""
    calls = []

    async def fake_get(key):
        calls.append(("get", key))
        return None

    async def fake_incr(key):
        calls.append(("incr", key))
        return 1

    monkeypatch.setattr(storage, "redis_get", fake_get)
    monkeypatch.setattr(storage, "redis_incr", fake_incr)

    resp = await client.get("/api/count")
    assert resp.status_code == 200
    assert resp.json()["counter"] == 1
    assert calls == [("get", "hits"), ("incr", "hits")]
