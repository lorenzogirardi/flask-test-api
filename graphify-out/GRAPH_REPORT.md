# Graph Report - flask-test-api  (2026-08-27)

## Corpus Check
- 106 files · ~53,143 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 782 nodes · 1449 edges · 84 communities (61 shown, 23 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 103 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- API/Debug/Storage Core
- Legacy Flask Business Logic
- Test Fixtures & Reset State
- Pydantic Schemas
- AI Pipeline Docs & Scripts
- MCP Tools (Core)
- MCP Context Tests
- Auth Rate Limiting
- FastAPI App Bootstrap
- In-Memory Storage Backend
- Legacy Flask Auth
- Context CRUD API
- Debug Network Tools
- MCP Server Setup
- MCP Network Diagnostics
- Helm Deployment Chart
- API Router Tests
- Redis Storage Backend
- App Settings Config
- API Router
- Debug Router Tests
- In-Memory TTL Cache
- PostgreSQL Storage Backend
- Dashboard Frontend JS
- API Integration Tests
- Dashboard Home Route
- Management Router Tests
- Error Injection Middleware
- MCP Auth Middleware
- C4 Component Docs
- Legacy Flask Dependencies
- Middleware Tests
- Prometheus Smoke Tests
- Alembic Migrations
- Debug Integration Tests
- Management Integration Tests
- Storage Backend Protocol
- C4 Container Docs
- End-to-End Tests
- MCP Integration Tests
- Middleware Integration Tests
- Storage Fallback Service
- AI Triage & Release Notes
- Multi-Cluster Helm Values
- Docker Test Script
- MCP Health Check
- Project Config Files
- Echo Debug Routes
- Renovate Config
- Legacy Flask Blueprints
- AI Code Review Workflow
- Alembic Env Module
- Redis URL Property
- Redis URL Masking
- Lifespan Closure
- Request Logging Middleware
- Schemas Component Doc
- Settings Component Doc
- Legacy Flask Deps File
- Legacy Flask Auth Module
- Legacy Diagnostics Blueprint
- Legacy Flask Entrypoint
- Legacy Management Blueprint
- Legacy Redis Helper
- Raw K8s Namespace
- Pytbak Project Root
- Black Formatting Config
- OWASP Injection Risk
- Anyio Backend Fixture
- Auth Header Fixture
- ASGI Client Fixture
- Live Auth Client Fixture
- Live HTTP Client Fixture

## God Nodes (most connected - your core abstractions)
1. `get_settings()` - 35 edges
2. `ContextResponse` - 29 edges
3. `_structured_errors() decorator` - 28 edges
4. `ContextCreate` - 19 edges
5. `tests/test_mcp.py — MCP tool functions, base layer` - 17 edges
6. `CLAUDE.md (project context for AI assistants)` - 17 edges
7. `verify_credentials()` - 16 edges
8. `create_app()` - 16 edges
9. `StorageService` - 16 edges
10. `STATUS.md (FastAPI rewrite status)` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Rationale: Flattened Tool Args Tradeoff` --rationale_for--> `_structured_errors() decorator`  [EXTRACTED]
  docs/11-mcp-server.md → app/mcp/tools.py
- `OWASP A10: SSRF via /debug/curl` --references--> `curl() route`  [EXTRACTED]
  docs/06-security-analysis.md → app/routers/debug.py
- `fastapi (Python package)` --conceptually_related_to--> `app/main.py (create_app() factory)`  [INFERRED]
  requirements.txt → app/main.py
- `loguru (Python package)` --conceptually_related_to--> `app/main.py (create_app() factory)`  [INFERRED]
  requirements.txt → app/main.py
- `opentelemetry-* (Python packages)` --conceptually_related_to--> `app/main.py (create_app() factory)`  [INFERRED]
  requirements.txt → app/main.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **PG -> Redis -> Memory Storage Fallback Chain** — app_services_storage_storageservice, app_services_storage_postgresqlbackend, app_services_storage_redisbackend, app_services_storage_inmemorybackend [EXTRACTED 1.00]
- **MCP Tools Reuse REST Layer In-Process** — app_mcp_tools_mcp, app_routers_api_fibonacci, app_routers_debug_network_scan, app_routers_mgmt_app_info, app_services_storage_get_all_contexts [EXTRACTED 1.00]
- **Shared Auth Rate-Limit Budget Across REST and MCP** — app_auth_check_rate_limit, app_auth_verify_credentials, app_middleware_mcp_auth_call, app_auth_fail_tracker [EXTRACTED 1.00]
- **Test pyramid for context/API flows (unit -> integration -> e2e)** — tests_test_api_py, tests_integration_test_api_py, tests_integration_test_e2e_py [EXTRACTED 1.00]
- **MCP Basic-Auth guard verified at both unit (deny body) and wire (reject creds) layers** — tests_test_mcp_test_deny_response_body_is_valid_json, tests_integration_test_mcp_py, app_middleware_mcp_auth_mcpbasicauthmiddleware [INFERRED 0.80]
- **Autouse fixtures giving every unit test a clean app/auth/storage state** — tests_conftest_app_fixture, tests_conftest_reset_auth_fixture, tests_conftest_reset_storage_fixture [EXTRACTED 1.00]
- **Legacy Context CRUD via Flask routes + business layer + Redis** — docker_src_app_main_module, docker_src_app_business_module, docker_src_app_utils_get_redis_connection [INFERRED 0.75]
- **HTTP Basic Auth gate applied across all diag endpoints** — docker_src_app_auth_requires_auth, docker_src_app_auth_check_auth, docker_src_app_diag_module [EXTRACTED 1.00]
- **Async Alembic migration execution chain** — alembic_env_run_migrations_online, alembic_env_run_async_migrations, alembic_env_do_run_migrations [EXTRACTED 1.00]
- **PR gate + main-branch pipeline + scheduled AI sweep form the CI/CD flow** — github_workflows_pr_checks_workflow, github_workflows_pipeline_workflow, github_workflows_ai_review_sweep_workflow [EXTRACTED 1.00]
- **AI_ENABLED-gated OpenRouter automations (review, sweep, triage, release notes)** — github_workflows_ai_review_workflow, github_workflows_ai_review_sweep_workflow, github_workflows_issue_triage_workflow, github_workflows_release_notes_workflow [INFERRED 0.85]
- **Storage layer implementing the PG->Redis->Memory fallback chain** — app_storage_py, app_database_py, app_redis_client_py, app_cache_py, fallback_chain_rationale [EXTRACTED 1.00]
- **PostgreSQL to Redis to In-Memory Storage Fallback** — component_storage_service, postgres_external, redis_external, container_local_cache [EXTRACTED 1.00]
- **MCP In-Process Server Architecture** — mcp_basicauth_middleware, mcp_tools_module, health_service_shared, doc_mcp_server [EXTRACTED 1.00]
- **AI Pipeline PR Gate System** — workflow_pr_checks, workflow_ai_review, workflow_ai_review_sweep, rationale_merge_gate_ci_not_ai [EXTRACTED 1.00]
- **Prometheus/OTel scrape to Grafana dashboard pipeline** — otel_prometheus, helm_pytbak_templates_servicemonitor, helm_pytbak_dashboards_pytbak [INFERRED 0.75]
- **Helm chart vs legacy raw K8s manifests for pytbak deployment** — helm_pytbak_templates_deployment, helm_pytbak_templates_service, helm_pytbak_templates_ingress, helm_pytbak_templates_hpa, kubernetes_deployment, kubernetes_service, kubernetes_ingress, kubernetes_hpa [INFERRED 0.85]
- **Multi-cluster Helm values overlay (base + itachi/izanami/milano)** — helm_pytbak_values_base, helm_pytbak_values_itachi, helm_pytbak_values_izanami, helm_pytbak_values_milano [EXTRACTED 1.00]

## Communities (84 total, 23 thin omitted)

### Community 0 - "API/Debug/Storage Core"
Cohesion: 0.05
Nodes (63): alembic/ (DB migrations), app/routers/api.py (/api CRUD + fib/sleep/count), app/auth.py (BasicAuth dependency), app/services/cache.py (in-memory TTL cache), app/models/database.py (SQLAlchemy async models), app/routers/debug.py (/debug network/CPU/diag), app/services/health.py (shared health-check logic), app/main.py (create_app() factory) (+55 more)

### Community 1 - "Legacy Flask Business Logic"
Cohesion: 0.06
Nodes (47): create_new_context(), delete_context_by_id(), get_all_contexts(), get_context_by_id(), business.py (legacy Redis-backed context storage), update_existing_context(), api_apidocs(), bad_request() (+39 more)

### Community 2 - "Test Fixtures & Reset State"
Cohesion: 0.08
Nodes (35): Clear all rate-limiting state. For tests only., reset_auth_state(), Clear in-memory fallback store. For tests only., reset_memory_store(), anyio_backend(), app(), auth_headers(), client() (+27 more)

### Community 3 - "Pydantic Schemas"
Cohesion: 0.10
Nodes (28): AppInfoResponse, CpuSpikeRequest, CpuSpikeResponse, ErrorResponse, HealthCheck, HealthResponse, MappingEntry, NetworkScanResult (+20 more)

### Community 4 - "AI Pipeline Docs & Scripts"
Cohesion: 0.11
Nodes (30): ADR-001: Migrate pytbak from Flask to FastAPI, ai_append_cost.py (cost footer), ai_sanitize.py (redaction/sizing), VSDD Slash-Command Workflow, AI Pipeline (GitHub Actions + OpenCode Zen), C4 Components (Level 3), C4 Containers (Level 2), Datadog Integration (+22 more)

### Community 5 - "MCP Tools (Core)"
Cohesion: 0.14
Nodes (27): count() MCP tool, cpu_spike() MCP tool, delete_context() MCP tool, echo_body() MCP tool, fibonacci() MCP tool, get_context() MCP tool, list_contexts() MCP tool, Delete a context by ID. (+19 more)

### Community 6 - "MCP Context Tests"
Cohesion: 0.16
Nodes (23): create_context() MCP tool, Create a new context. Title must be 1-255 characters., anyio, parametrize, Base layer — MCP tool functions called directly, in-memory backend. Same tier…, The mount advertises Content-Type: application/json — the body must actually…, test_app_env_only_returns_allowlisted_vars(), test_app_info() (+15 more)

### Community 7 - "Auth Rate Limiting"
Cohesion: 0.16
Nodes (20): check_rate_limit(), _cleanup_old(), clear_failures(), _fail_tracker (module state), Request, Basic HTTP authentication with incremental rate limiting after failed attempts., Remove entries older than the tracking window., Check if IP is rate limited due to failed attempts. Public: also used by… (+12 more)

### Community 8 - "FastAPI App Bootstrap"
Cohesion: 0.17
Nodes (19): get_settings(), create_app(), _make_lifespan(), FastAPI application entry point., Build the lifespan context manager. mcp_server is None when MCP is disabled.…, _setup_logging(), mcp (FastMCP instance), close_db() (+11 more)

### Community 9 - "In-Memory Storage Backend"
Cohesion: 0.18
Nodes (8): ContextResponse, get_cache(), _dict_to_response(), InMemoryBackend, Composes PG + Redis + Memory with the fallback chain. Read path: local cache →…, Dict-backed store. Always available, always last resort. Instance state (not…, Clear all stored contexts. For tests only., StorageService

### Community 10 - "Legacy Flask Auth"
Cohesion: 0.16
Nodes (20): authenticate(), check_auth(), Sends a 401 response that enables basic auth, This function is called to check if a username / password combination is valid., requires_auth(), curl(), dns_resolve(), echo_body() (+12 more)

### Community 11 - "Context CRUD API"
Cohesion: 0.23
Nodes (20): ContextCreate, ContextUpdate, update_context() route, create_context(), delete_context(), get_all_contexts(), get_context(), update_context() (+12 more)

### Community 12 - "Debug Network Tools"
Cohesion: 0.18
Nodes (20): curl() route, dns_resolve() route, _guard_ssrf(), _host_to_ip(), _is_blocked_ip(), network_scan() route, ping_host() route, get (+12 more)

### Community 13 - "MCP Server Setup"
Cohesion: 0.17
Nodes (17): app (FastAPI instance), app_env() MCP tool, app_info() MCP tool, app_mappings() MCP tool, MCP tools exposing pytbak's capabilities to LLM callers. Mounted at /api/mcp…, Check pytbak's readiness probe., Get pytbak's app name/version/environment., Get pytbak's allowlisted environment variables. (+9 more)

### Community 14 - "MCP Network Diagnostics"
Cohesion: 0.14
Nodes (18): curl() MCP tool, dns_resolve() MCP tool, network_scan() MCP tool, ping() MCP tool, random_error() MCP tool, Run ping+dns+tcp+traceroute against target ('host' or 'host:port')., Ping a host from the server (count 1-20)., Resolve a hostname from the server. (+10 more)

### Community 15 - "Helm Deployment Chart"
Cohesion: 0.15
Nodes (17): Helm Chart.yaml (pytbak), Grafana Dashboard: pytbak, Helm ConfigMap Template, Helm Deployment Template, Helm HorizontalPodAutoscaler Template, Helm Ingress Template, Helm NetworkPolicy Template, Helm PodDisruptionBudget Template (+9 more)

### Community 16 - "API Router Tests"
Cohesion: 0.23
Nodes (15): anyio, Tests for the core API router (contexts CRUD + legacy)., test_count_without_redis(), test_create_and_get_context(), test_create_context(), test_delete_context(), test_delete_context_not_found(), test_fibonacci() (+7 more)

### Community 17 - "Redis Storage Backend"
Cohesion: 0.26
Nodes (9): get_redis(), Execute a Redis coroutine with retry logic. Returns None on failure., redis_op_with_retry(), BackendError, Redis backend. JSON-serialised context dicts under key 'context:{id}'., Raised when a backend operation fails. StorageService catches this to fall…, RedisBackend, Exception (+1 more)

### Community 18 - "App Settings Config"
Cohesion: 0.17
Nodes (8): Application configuration via Pydantic Settings (env-based)., Return redis_url if set, otherwise build from host/port/db., Return Redis URL with password masked for logging., All config is driven by environment variables with sane defaults., Fail fast in production when the default credentials are still set. The report:…, Settings (class), BaseSettings, model_validator

### Community 19 - "API Router"
Cohesion: 0.22
Nodes (12): count() route, create_context() route, delete_context() route, fibonacci() route, get_context() route, list_contexts() route, get, post (+4 more)

### Community 20 - "Debug Router Tests"
Cohesion: 0.26
Nodes (12): anyio, Tests for the debug router., After 3 failed attempts, subsequent requests should be rate limited (429)., test_auth_rate_limit(), test_cpu_spike(), test_debug_requires_auth(), test_dns_invalid(), test_dns_valid() (+4 more)

### Community 21 - "In-Memory TTL Cache"
Cohesion: 0.21
Nodes (4): Any, Local in-memory cache with TTL and LRU eviction., Thread-safe dict-based cache with per-item TTL and LRU eviction., TTLCache

### Community 22 - "PostgreSQL Storage Backend"
Cohesion: 0.29
Nodes (7): ContextDB (SQLAlchemy model), get_session_factory(), _db_row_to_response(), PostgreSQLBackend, SQLAlchemy async backend. Uses merge() for upsert (handles both create and…, async_sessionmaker, AsyncSession

### Community 23 - "Dashboard Frontend JS"
Cohesion: 0.35
Nodes (11): fetchJSON(), handleCopy(), init(), initTheme(), poll(), showToast(), statusColor(), statusColorClass() (+3 more)

### Community 24 - "API Integration Tests"
Cohesion: 0.24
Nodes (11): created_context(), anyio, fixture, Integration — API endpoints with real PostgreSQL and Redis persistence., Create a context and clean it up after the test., test_create_context_persists_in_pg(), test_delete_removes_from_pg(), test_fibonacci_known_values() (+3 more)

### Community 25 - "Dashboard Home Route"
Cohesion: 0.27
Nodes (10): dashboard() route, dashboard_status() route, _get_infra_status(), get, Request, Home dashboard router — serves the DebugKnife UI., Map a status string to a CSS dot color class., Collect infrastructure status for dashboard and API. (+2 more)

### Community 26 - "Management Router Tests"
Cohesion: 0.33
Nodes (9): anyio, Tests for the management router., test_env(), test_health(), test_info(), test_mappings(), test_ready(), test_threaddump() (+1 more)

### Community 27 - "Error Injection Middleware"
Cohesion: 0.22
Nodes (7): ErrorInjectionMiddleware, Request, Middleware for error injection and delay via query params., Inject errors and delays via query params on ANY endpoint. ?inject_error=500 ->…, BaseHTTPMiddleware, FastAPI, Response

### Community 28 - "MCP Auth Middleware"
Cohesion: 0.28
Nodes (6): MCPBasicAuthMiddleware, Wraps an ASGI app (the MCP streamable-HTTP app) with HTTP Basic Auth., ASGIApp, Receive, Scope, Send

### Community 29 - "C4 Component Docs"
Cohesion: 0.28
Nodes (9): API Router Component, Auth Module Component, Debug Router Component, Management Router Component, Middleware Layer Component, Redis Client Component, SQLAlchemy Models Component, Storage Service Component (+1 more)

### Community 30 - "Legacy Flask Dependencies"
Cohesion: 0.25
Nodes (9): Legacy Flask app (docker/, preserved), Legacy pytbak index page (docker/src/app/templates/index.html), ddtrace (Python package, legacy), flasgger (Python package, legacy), Flask (Python package, legacy), flask-compress (Python package, legacy), flask_zipkin (Python package, legacy), prometheus-flask-exporter (Python package, legacy) (+1 more)

### Community 31 - "Middleware Tests"
Cohesion: 0.36
Nodes (8): anyio, Tests for error injection and delay middleware., test_delay_ms(), test_index_page(), test_inject_custom_error(), test_inject_error_429(), test_inject_error_500(), test_inject_validation_error()

### Community 32 - "Prometheus Smoke Tests"
Cohesion: 0.22
Nodes (7): prometheus_app(), fixture, parametrize, The app must actually serve requests with Prometheus instrumentation on.…, Instrumentation is wired up, not merely importable without crashing., test_request_is_actually_counted(), test_requests_succeed_with_instrumentation_enabled()

### Community 33 - "Alembic Migrations"
Cohesion: 0.32
Nodes (6): do_run_migrations(), Alembic env — async migration runner., run_async_migrations(), run_migrations_online(), Base (DeclarativeBase), DeclarativeBase

### Community 34 - "Debug Integration Tests"
Cohesion: 0.39
Nodes (7): anyio, Integration — debug endpoints: auth enforcement, DNS, echo., test_debug_requires_auth(), test_dns_invalid_host_rejected(), test_dns_resolve_localhost(), test_echo_body(), test_echo_headers()

### Community 35 - "Management Integration Tests"
Cohesion: 0.36
Nodes (7): anyio, Integration — management endpoints with real PG + Redis backends., Both PostgreSQL and Redis must report UP (not just NOT_CONFIGURED)., test_health_backends_up(), test_info(), test_mappings_non_empty(), test_ready()

### Community 37 - "C4 Container Docs"
Cohesion: 0.38
Nodes (7): Local Cache Container (in-memory TTL), FastAPI App Container (Uvicorn, :8000), Datadog Agent (External System), Kubernetes (External System), PostgreSQL (External System), pytbak API (System), Redis (External System)

### Community 38 - "End-to-End Tests"
Cohesion: 0.33
Nodes (6): anyio, E2E — full user flows. Pyramid tip: fewest tests, highest confidence., Health shows all backends UP, Redis counter works, Fibonacci computes., Create → read → update → delete — full round-trip through PG., test_full_context_lifecycle(), test_stack_observability_and_compute()

### Community 39 - "MCP Integration Tests"
Cohesion: 0.43
Nodes (6): anyio, Mid/tip layer — MCP server over the real streamable-HTTP transport. Requires…, test_full_context_lifecycle_over_real_transport(), test_tool_list_and_call_over_real_transport(), test_unauthenticated_request_is_rejected(), test_wrong_credentials_rejected()

### Community 40 - "Middleware Integration Tests"
Cohesion: 0.43
Nodes (6): anyio, Integration — error injection and delay middleware over real HTTP., test_delay_ms_timing(), test_inject_custom_message(), test_inject_http_error(), test_x_request_id_header_present()

### Community 41 - "Storage Fallback Service"
Cohesion: 0.40
Nodes (5): _now(), Unified storage service with fallback chain: PostgreSQL -> Redis -> In-Memory.…, Increment a Redis counter. Returns None if Redis unavailable., redis_incr(), datetime

### Community 42 - "AI Triage & Release Notes"
Cohesion: 0.33
Nodes (6): ai_sanitize.py (ci-shared script), openrouter_ai.py (ci-shared script), triage job (issue-triage.yml), AI Issue Triage workflow (issue-triage.yml), release-notes job (release-notes.yml), AI Release Notes workflow (release-notes.yml)

### Community 43 - "Multi-Cluster Helm Values"
Cohesion: 0.33
Nodes (6): Grafana Dashboard: k3s-node, Grafana Dashboard: traefik, Helm values.yaml (base defaults), Helm values-itachi.yaml (itachi cluster override), Helm values-izanami.yaml (izanami cluster override), Helm values-milano.yaml (milano k3s cluster override)

### Community 44 - "Docker Test Script"
Cohesion: 0.60
Nodes (5): fail(), header(), info(), pass(), test-docker.sh script

### Community 45 - "MCP Health Check"
Cohesion: 0.40
Nodes (5): health() MCP tool, Check pytbak's health (Redis/Postgres backend status)., MCP Server, Shared Health-Check Service, OpenCode MCP Tool Call Example

### Community 46 - "Project Config Files"
Cohesion: 0.40
Nodes (5): Claude Code local permissions settings, pytbak project definition (pyproject.toml), pytest config (asyncio_mode, testpaths, integration marker), Renovate bot config (config:recommended), test-docker.sh (full test pyramid runner)

### Community 47 - "Echo Debug Routes"
Cohesion: 0.67
Nodes (4): api_route, echo_body() route, echo_headers() route, Request

### Community 48 - "Renovate Config"
Cohesion: 0.50
Nodes (3): config:recommended, extends, $schema

### Community 49 - "Legacy Flask Blueprints"
Cohesion: 0.67
Nodes (3): diag_bp Blueprint, Flask app instance, mgmt_bp Blueprint

### Community 50 - "AI Code Review Workflow"
Cohesion: 0.67
Nodes (3): review job (ai-review.yml), AI Code Review workflow (ai-review.yml), reusable_pr-diff-review.yml (ci-shared)

## Ambiguous Edges - Review These
- `index()` → `favicon.png (legacy app favicon image)`  [AMBIGUOUS]
  docker/src/app/static/favicon.png · relation: conceptually_related_to
- `integration/conftest.py` → `tests/integration/test_mcp.py — MCP over real streamable-HTTP transport`  [AMBIGUOUS]
  tests/integration/conftest.py · relation: conceptually_related_to
- `AI Pipeline (GitHub Actions + OpenCode Zen)` → `VSDD Slash-Command Workflow`  [AMBIGUOUS]
  .claude/commands/vsdd.md · relation: conceptually_related_to

## Knowledge Gaps
- **84 isolated node(s):** `pytbak`, `$schema`, `config:recommended`, `effective_redis_url (property)`, `sanitized_redis_url (property)` (+79 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `index()` and `favicon.png (legacy app favicon image)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `integration/conftest.py` and `tests/integration/test_mcp.py — MCP over real streamable-HTTP transport`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `AI Pipeline (GitHub Actions + OpenCode Zen)` and `VSDD Slash-Command Workflow`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Architecture Documentation Index` connect `AI Pipeline Docs & Scripts` to `Context CRUD API`, `MCP Health Check`?**
  _High betweenness centrality (0.166) - this node is a cross-community bridge._
- **Why does `ai-review-sweep.yml (Renovate sweep + autofix)` connect `AI Pipeline Docs & Scripts` to `API/Debug/Storage Core`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `ContextResponse` (e.g. with `create_context()` and `get_all_contexts()`) actually correct?**
  _`ContextResponse` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ContextCreate` (e.g. with `create_context() MCP tool` and `create_context() route`) actually correct?**
  _`ContextCreate` has 8 INFERRED edges - model-reasoned connections that need verification._