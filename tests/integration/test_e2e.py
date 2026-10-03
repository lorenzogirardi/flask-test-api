"""E2E — full user flows. Pyramid tip: fewest tests, highest confidence."""

import pytest


def test_full_context_lifecycle(client):
    """Create → read → update → delete — full round-trip through PG."""
    # Create
    r = client.post("/api/contexts", json={"title": "e2e-lifecycle", "description": "full flow"})
    assert r.status_code == 201
    ctx_id = r.json()["id"]
    assert r.json()["done"] is False

    # Read
    r = client.get(f"/api/contexts/{ctx_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "e2e-lifecycle"

    # Update
    r = client.put(f"/api/contexts/{ctx_id}", json={"title": "e2e-done", "done": True})
    assert r.status_code == 200
    assert r.json()["done"] is True

    # Verify update persisted
    r = client.get(f"/api/contexts/{ctx_id}")
    assert r.json()["title"] == "e2e-done"

    # Delete
    r = client.delete(f"/api/contexts/{ctx_id}")
    assert r.status_code == 200

    # Verify gone
    r = client.get(f"/api/contexts/{ctx_id}")
    assert r.status_code == 404


def test_stack_observability_and_compute(client):
    """Health shows all backends UP, Redis counter works, Fibonacci computes."""
    # Stack health
    health = client.get("/api/mgmt/health")
    assert health.status_code == 200
    by_name = {c["name"]: c["status"] for c in health.json()["checks"]}
    assert by_name["redis"] == "UP"
    assert by_name["postgresql"] == "UP"

    # Redis counter is live
    r1 = client.get("/api/count")
    r2 = client.get("/api/count")
    assert r2.json()["counter"] == r1.json()["counter"] + 1

    # Compute is correct
    fib = client.get("/api/fib/15")
    assert fib.json()["result"] == "610"

    # Metrics endpoint is serving
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "python_gc" in metrics.text
