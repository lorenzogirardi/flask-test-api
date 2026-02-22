# 6. Security Analysis

## 6.1 OWASP Top 10 Risk Assessment

| # | Vulnerability | Risk | Impact | Mitigation | Status |
|---|--------------|------|--------|------------|--------|
| A01 | **Broken Access Control** | Medium | Unauthorized access to debug endpoints | HTTP Basic Auth on `/debug/*`, `secrets.compare_digest()` timing-safe comparison | Mitigated |
| A02 | **Cryptographic Failures** | Low | Credential interception | TLS termination at Ingress/LB level; credentials via env vars (not hardcoded) | Mitigated (requires TLS at infra) |
| A03 | **Injection** | Medium | SQL injection, command injection | SQLAlchemy ORM (parameterized queries); subprocess uses list args (no shell=True); host validation regex `[a-zA-Z0-9.-]` | Mitigated |
| A04 | **Insecure Design** | Low | Debug tool misuse in prod | Documented as non-production tool; auth on destructive endpoints; rate limiting | Accepted (by design) |
| A05 | **Security Misconfiguration** | Medium | Default credentials, exposed env | Default creds in dev only; `/mgmt/env` whitelists safe vars; `.env` in `.gitignore` | Mitigated |
| A06 | **Vulnerable Components** | Low | Dependency CVEs | Renovate bot for automated updates; pinned versions in requirements.txt | Mitigated |
| A07 | **Auth Failures** | Medium | Brute force on Basic Auth | Rate limiting (100/min default); timing-safe comparison | Partially mitigated |
| A08 | **Software/Data Integrity** | Low | Tampered container image | Non-root user in Dockerfile (UID 10001); Trivy scan in CI pipeline | Mitigated |
| A09 | **Logging Failures** | Low | Missing audit trail | Structured JSON logging (loguru); request tracing (OTEL) | Mitigated |
| A10 | **SSRF** | High | `/debug/curl` fetches arbitrary URLs | Auth required; timeout (5s); intended feature for testing | Accepted (auth-gated) |

## 6.2 STRIDE Threat Model

### Sensitive Endpoints

| Endpoint | Threat | STRIDE | Severity | Mitigation |
|----------|--------|--------|----------|------------|
| `POST /debug/cpu/spike` | **DoS** — exhaust CPU resources | Denial of Service | **High** | Auth required; max duration=120s, max cores=16; process isolation |
| `GET /debug/network/scan` | **Information Disclosure** — internal network mapping | Info Disclosure | **High** | Auth required; host validation; Docker network isolation |
| `GET /debug/curl` | **SSRF** — fetch internal services | Spoofing, Elevation | **High** | Auth required; timeout 5s; no credential forwarding |
| `GET /debug/ping` | **Command Injection** — malicious host param | Tampering | **Medium** | Input validation `[a-zA-Z0-9.-]`; subprocess list args (no shell) |
| `?inject_error=` | **Tampering** — disrupt normal flow | Tampering | **Medium** | No auth required (by design); only affects single request |
| `?delay_ms=` | **DoS** — slow down responses | Denial of Service | **Medium** | Max delay bounded by client timeout; rate limiting |
| `GET /mgmt/env` | **Info Disclosure** — environment variables | Info Disclosure | **Low** | Whitelist filter; excludes secrets, passwords, tokens |
| `GET /mgmt/threaddump` | **Info Disclosure** — stack traces | Info Disclosure | **Low** | No auth (management endpoint); no sensitive data in frames |

### STRIDE Summary

```mermaid
graph LR
    S[Spoofing] -->|Basic Auth| A1[/debug/* endpoints]
    T[Tampering] -->|Pydantic validation| A2[Request bodies]
    T -->|Input sanitization| A3[Host/name params]
    R[Repudiation] -->|Structured logging| A4[All requests]
    R -->|OTEL traces| A5[Trace correlation]
    I[Info Disclosure] -->|Env whitelist| A6[/mgmt/env]
    I -->|Auth gate| A7[/debug/curl]
    D[DoS] -->|Rate limiting| A8[All endpoints]
    D -->|Resource limits| A9[CPU spike bounded]
    E[Elevation] -->|No admin roles| A10[Flat auth model]

    style S fill:#f66,color:#fff
    style T fill:#f96,color:#fff
    style R fill:#ff6,color:#000
    style I fill:#6af,color:#fff
    style D fill:#f6f,color:#fff
    style E fill:#666,color:#fff
```

## 6.3 Attack Surface

```mermaid
graph TD
    subgraph External["External Attack Surface"]
        A[HTTP :8000]
    end

    subgraph AuthGated["Auth-Gated (Basic Auth)"]
        B[/debug/ping]
        C[/debug/dns]
        D[/debug/curl]
        E[/debug/tcp-check]
        F[/debug/network/scan]
        G[/debug/cpu/spike]
        H[/debug/headers]
        I[/debug/echo]
    end

    subgraph Public["Public Endpoints"]
        J[/api/contexts CRUD]
        K[/api/fib, /api/sleep]
        L[/mgmt/health, /ready]
        M[/mgmt/info, /env]
        N[/metrics]
        O[/docs, /redoc]
    end

    subgraph Middleware["Middleware (all endpoints)"]
        P["?inject_error="]
        Q["?delay_ms="]
    end

    A --> AuthGated
    A --> Public
    A --> Middleware

    style External fill:#f66,color:#fff
    style AuthGated fill:#f96,color:#fff
    style Public fill:#6f6,color:#000
    style Middleware fill:#ff6,color:#000
```

## 6.4 Security Controls Implemented

| Control | Implementation | Layer |
|---------|---------------|-------|
| **Authentication** | HTTP Basic Auth (`secrets.compare_digest`) | Application |
| **Rate Limiting** | slowapi (100/minute default) | Middleware |
| **Input Validation** | Pydantic models (type, length, range) | Application |
| **SQL Injection Prevention** | SQLAlchemy ORM (parameterized queries) | Data |
| **Command Injection Prevention** | subprocess with list args, host char validation | Application |
| **SSRF Mitigation** | Auth required, 5s timeout, no credential forwarding | Application |
| **Secret Management** | Environment variables, K8s Secrets | Infrastructure |
| **Non-root Container** | Dockerfile USER pytbak (UID 10001) | Container |
| **Resource Limits** | K8s requests/limits (500m CPU, 256Mi RAM) | Infrastructure |
| **Dependency Scanning** | Renovate bot, Trivy in CI | CI/CD |
| **Timing-safe Auth** | `secrets.compare_digest()` | Application |
| **Env Var Filtering** | `/mgmt/env` whitelist (no secrets exposed) | Application |

## 6.5 Compliance Notes

### PCI-DSS

| Requirement | Applicability | Notes |
|-------------|--------------|-------|
| Req 1: Network Segmentation | N/A | Debug tool, not in cardholder data environment |
| Req 6: Secure Development | Partial | Input validation, dependency management |
| Req 8: Authentication | Partial | Basic Auth (not sufficient for PCI scope) |
| Req 10: Logging | Yes | Structured JSON logging, OTEL traces |

> **Note**: pytbak is a debug/testing tool and should NOT be deployed in PCI-DSS Zone 1 environments. It is suitable for development and staging environments only.

### GDPR

| Aspect | Status | Notes |
|--------|--------|-------|
| Personal Data Storage | **No PII by design** | Contexts store title/description only |
| Data Retention | Ephemeral (in-memory fallback) | No long-term PII retention |
| Right to Erasure | DELETE endpoint available | Contexts can be deleted via API |
| Data Processing Records | Logging covers access | Structured logs + OTEL traces |

## 6.6 Recommendations

| Priority | Recommendation | Effort |
|----------|---------------|--------|
| **High** | Add TLS (HTTPS) at Ingress for all environments | Low (infra config) |
| **High** | Rotate default credentials before any shared environment | Low (env var change) |
| **Medium** | Add CORS configuration for browser-based access | Low (FastAPI middleware) |
| **Medium** | Add request body size limit for echo/POST endpoints | Low (Uvicorn config) |
| **Low** | Add API key auth as alternative to Basic Auth | Medium (new auth module) |
| **Low** | Network policies to restrict `/debug/curl` SSRF scope | Medium (K8s NetworkPolicy) |
