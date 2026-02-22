# pytbak — Architecture Documentation

Enterprise-grade architecture documentation for the pytbak FastAPI debug API.
C4 Model compliant, OWASP-reviewed, PCI-DSS/GDPR annotated.

## Document Index

| # | Document | Audience | Description |
|---|----------|----------|-------------|
| 1 | [Overview & C4 Context](01-overview-c4-context.md) | All stakeholders | System purpose, boundaries, C4 Level 1 |
| 2 | [C4 Containers](02-c4-containers.md) | Architects, DevOps | Runtime containers, interactions, C4 Level 2 |
| 3 | [C4 Components](03-c4-components.md) | Developers, Architects | Internal modules, services, C4 Level 3 |
| 4 | [C4 Code](04-c4-code.md) | Developers | Key code snippets, patterns, C4 Level 4 |
| 5 | [Enterprise Architecture](05-enterprise-architecture.md) | DevOps, SRE, Management | Deployment, scaling, monitoring |
| 6 | [Security Analysis](06-security-analysis.md) | Security, Compliance | OWASP Top 10, STRIDE, PCI-DSS/GDPR |
| 7 | [Sequence Diagrams](07-sequence-diagrams.md) | Developers, QA | Request flows, fallbacks, error paths |
| 8 | [Diagrams & Graphs](08-diagrams.md) | All | Deployment, dependency, health flows |
| 9 | [ADR: Flask to FastAPI](09-adr-flask-to-fastapi.md) | Architects, Management | Migration decision record |
| 10 | [Datadog Integration](10-datadog-integration.md) | DevOps, SRE | APM auto-instrumentation, metrics, troubleshooting |

## How to View

- **GitHub**: Renders natively (Mermaid diagrams supported)
- **MkDocs**: Copy `docs/` as-is, add to `mkdocs.yml` nav
- **Confluence**: Paste markdown, Mermaid renders via plugin

## Conventions

- Diagrams: Mermaid (GitHub-native) — copy-paste ready
- C4 colors: Person (blue), System (green), External (orange), Database (red)
- Security ratings: Critical / High / Medium / Low / Info
