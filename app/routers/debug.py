"""Debug router — network diagnostics, CPU spike, error injection, echo tools."""

import asyncio
import multiprocessing
import random
import socket
import subprocess
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from loguru import logger

from app.auth import verify_credentials
from app.models.schemas import CpuSpikeRequest, CpuSpikeResponse, NetworkScanResult

router = APIRouter(prefix="/debug", tags=["Debug"])


# ========== NETWORK SCAN (netshoot-like) ==========
@router.get(
    "/network/scan",
    response_model=NetworkScanResult,
    summary="Network diagnostic scan (ping, dns, tcp, traceroute)",
    dependencies=[Depends(verify_credentials)],
)
async def network_scan(target: str = Query(..., description="host:port or hostname")):
    host, port_str = (target.rsplit(":", 1) + [None])[:2]

    # Validate host
    if not all(c.isalnum() or c in ".-_" for c in host):
        raise HTTPException(status_code=400, detail="Invalid host")

    result = NetworkScanResult(target=target)

    # Ping
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "3", "-W", "2", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        result.ping = {
            "output": stdout.decode(),
            "returncode": proc.returncode,
        }
    except Exception as e:
        result.ping = {"error": str(e)}

    # DNS
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        addresses = list({res[4][0] for res in infos})
        result.dns = {"addresses": addresses}
    except socket.gaierror as e:
        result.dns = {"error": str(e)}

    # TCP check
    if port_str:
        try:
            port = int(port_str)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.close()
            result.tcp_check = {"status": "open", "port": port}
        except Exception as e:
            result.tcp_check = {"status": "closed", "port": port_str, "error": str(e)}

    # Traceroute
    try:
        proc = await asyncio.create_subprocess_exec(
            "traceroute", "-m", "10", "-w", "2", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        result.traceroute = {"output": stdout.decode(), "returncode": proc.returncode}
    except FileNotFoundError:
        result.traceroute = {"error": "traceroute not installed"}
    except Exception as e:
        result.traceroute = {"error": str(e)}

    return result


# ========== CPU SPIKE ==========
def _cpu_burn(duration: int) -> None:
    """Burn CPU for `duration` seconds."""
    end = time.monotonic() + duration
    while time.monotonic() < end:
        _ = sum(i * i for i in range(10000))


@router.post(
    "/cpu/spike",
    response_model=CpuSpikeResponse,
    summary="Simulate CPU load",
    dependencies=[Depends(verify_credentials)],
)
async def cpu_spike(params: CpuSpikeRequest):
    procs = []
    for _ in range(params.cores):
        p = multiprocessing.Process(target=_cpu_burn, args=(params.duration,))
        p.start()
        procs.append(p)

    return CpuSpikeResponse(
        status="started",
        duration=params.duration,
        cores=params.cores,
        message=f"CPU spike started on {params.cores} core(s) for {params.duration}s",
    )


# ========== DIAG ENDPOINTS (from original) ==========
@router.get("/ping", summary="Ping a host", dependencies=[Depends(verify_credentials)])
async def ping_host(host: str = Query(...), count: int = Query(default=3, ge=1, le=20)):
    if not all(c.isalnum() or c in ".-" for c in host):
        raise HTTPException(status_code=400, detail="Invalid host")
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", str(count), host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return Response(content=stdout.decode(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dns", summary="DNS resolve", dependencies=[Depends(verify_credentials)])
async def dns_resolve(name: str = Query(...)):
    if not all(c.isalnum() or c in ".-" for c in name):
        raise HTTPException(status_code=400, detail="Invalid name")
    try:
        results = socket.getaddrinfo(name, None, proto=socket.IPPROTO_TCP)
        addresses = list({res[4][0] for res in results})
        return {"addresses": addresses}
    except socket.gaierror as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/curl", summary="HTTP GET a URL", dependencies=[Depends(verify_credentials)])
async def curl(url: str = Query(...)):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tcp-check", summary="TCP connection check", dependencies=[Depends(verify_credentials)])
async def tcp_check(host: str = Query(...), port: int = Query(..., ge=1, le=65535)):
    if not all(c.isalnum() or c in ".-" for c in host):
        raise HTTPException(status_code=400, detail="Invalid host")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.close()
        return {"status": "success", "message": f"Successfully connected to {host}:{port}"}
    except (socket.timeout, socket.error) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.api_route(
    "/headers",
    methods=["GET", "POST", "PUT", "DELETE"],
    summary="Echo request headers",
    dependencies=[Depends(verify_credentials)],
)
async def echo_headers(request: Request):
    return dict(request.headers)


@router.api_route(
    "/echo",
    methods=["POST", "PUT"],
    summary="Echo request body",
    dependencies=[Depends(verify_credentials)],
)
async def echo_body(request: Request):
    body = await request.body()
    return Response(content=body, media_type=request.headers.get("content-type", "application/octet-stream"))


@router.get("/random-error", summary="Random HTTP error", dependencies=[Depends(verify_credentials)])
async def random_error():
    error_codes = [400, 401, 403, 404, 500, 502, 503, 504]
    code = random.choice(error_codes)
    raise HTTPException(status_code=code, detail=f"Randomly generated error: {code}")
