<!-- 
SYNC IMPACT REPORT
Version: 1.0.0 (New - Initial Constitution)
Status: Initial constitution for simplified 3-service architecture
Created: 2025-12-16
Previous Version: None (first ratification)

Key Changes:
- Established 5 core principles for consolidated architecture
- Defined service consolidation strategy (5 services → 3 services)
- Established containerization requirements (Docker-first)
- Defined unified API and monorepo governance
- Specified Python/TypeScript stack with uv/npm workspace management

Files Requiring Updates:
- ✅ .specify/templates/plan-template.md (no changes needed - already generic)
- ✅ .specify/templates/spec-template.md (no changes needed - already generic)
- ⚠️ .specify/templates/tasks-template.md (update examples for Python/TypeScript tasks)
- ✅ README.md (verify Azure-specific documentation aligns)
- ⚠️ azure.yaml (verify service definitions align with 3-service model)

Follow-up Actions:
- Review and update task template examples to match Python/TypeScript stack
- Verify Azure Developer CLI configuration reflects 3 services
- Ensure all development docs reference uv workspace patterns
-->

# AI Project Constitution

## Core Principles

### I. Service Consolidation (Non-Negotiable)
Services MUST be consolidated to maximize coherence and minimize deployment complexity:
- **UI Services**: Agents-Web + Content-Web → Single unified React app (`apps/ui`)
- **API Services**: Agents-API + Content-API → Single unified FastAPI application (`apps/api`)
- **Background Processing**: Azure Functions → Containerized Python Functions (`apps/functions`)
- **Shared Utilities**: Centralized Python package via uv workspace (`apps/common`)

**Rationale**: Reduces deployment points from 5 to 3, simplifies routing, enables shared middleware and authentication, reduces operational overhead.

### II. Containerization-First (Non-Negotiable)
All services MUST be containerized and deployable to Azure Container Apps:
- Every service (`ui`, `api`, `functions`) requires a Dockerfile with multi-stage builds
- Container images MUST run without privileged access or host volume mounts
- Health checks MUST be implemented (liveness + readiness probes)
- Images MUST be optimized for cold start performance (<5s startup time for Python services)

**Rationale**: Ensures consistent deployment across environments, enables rapid scaling, supports both local Docker development and production Container Apps hosting.

### III. Unified API Surface
API MUST provide a single, coherent REST endpoint structure:
- All routes routed through `/api/*` prefix (agents, content, catalog endpoints co-located)
- CORS enabled for UI consumption (specific origin list in production)
- Authentication/authorization middleware applied consistently across all routes
- OpenAPI/Swagger documentation auto-generated from FastAPI models

**Rationale**: Simplifies frontend integration, enables shared auth/logging middleware, reduces CORS friction.

### IV. Test-First Development (Non-Negotiable)
Testing is mandatory and must precede implementation:
- **Unit Tests**: Minimum 70% code coverage for API routes and business logic
- **Integration Tests**: Required for inter-service communication (UI↔API, API↔Functions, Functions↔Azure services)
- **E2E Tests**: Required for critical user flows (document upload→processing, agent chat)
- Test execution MUST pass before PR merge (enforced via CI/CD gates)

**Rationale**: Ensures reliability of service consolidation and containerized deployments, catches breaking changes early.

### V. Workspace-Based Dependency Management
Python and npm dependencies MUST be managed via workspace tooling:
- **Python**: uv workspace with members: `apps/api`, `apps/functions`, `apps/common` (see `pyproject.toml`)
- **JavaScript/TypeScript**: npm workspaces with members: `apps/ui`, shared type definitions
- `uv sync` and `npm ci` MUST refresh all dependencies in consistent state
- Workspace root manages shared dev dependencies (pytest, ruff, prettier, ESLint)

**Rationale**: Enables monorepo development, shared type definitions, consistent tooling, efficient dependency resolution.

## Infrastructure & Deployment

### Azure Services (Required Stack)
- **Compute**: Azure Container Apps (all 3 services)
- **Database**: Azure Cosmos DB (NoSQL for agents, documents, forms, chat history)
- **Storage**: Azure Blob Storage (document uploads, processed artifacts)
- **Messaging**: Azure Service Bus (inter-service async communication)
- **AI**: Azure OpenAI (GPT models) + Azure Document Intelligence (form extraction)
- **Auth**: Azure Entra ID (OAuth 2.0 / OIDC for user authentication)
- **Observability**: Application Insights (telemetry) + Azure Monitor (logs/alerts)

### Local Development
- **Docker Compose**: Azurite (blob storage), Service Bus emulator for local testing
- **Dev Container**: Optional, provides pre-configured environment (Python 3.11+, Node.js 20+, Azure CLI, Docker)
- `azure.yaml`: Azure Developer CLI configuration for `azd up` provisioning

## Development Workflow

### Code Organization
```
datalance-ai-simple/
├── apps/
│   ├── ui/              # React + Vite (merged: agents-web + content-web)
│   ├── api/             # FastAPI (merged: agents-api + content-api)
│   ├── functions/       # Azure Functions (containerized)
│   └── common/          # Shared Python utilities (uv package)
├── infra/               # Bicep templates for Azure resources
├── .github/workflows/   # CI/CD pipelines (build, test, deploy)
├── .devcontainer/       # Dev Container config
├── azure.yaml           # Azure Developer CLI configuration
├── pyproject.toml       # Python workspace root config (uv)
├── package.json         # npm workspace root config
└── README.md            # Getting started guide
```

### Local Development Commands
```bash
npm ci && uv sync              # Install all dependencies
docker compose up -d            # Start emulators (local dev only)
npm run dev                    # Start all services in dev mode
cd apps/api && uv run pytest   # Run API tests
cd apps/ui && npm test         # Run UI tests
npm run build                  # Build all services for production
```

### Deployment
```bash
azd auth login           # Authenticate with Azure
azd up                   # Provision infrastructure + deploy all services
azd deploy               # Re-deploy after code changes
azd monitor --logs       # View real-time logs and metrics
```

## Quality Gates & Code Review

### Pre-Merge Requirements (All PRs)
1. **All tests pass**: `npm test` + API unit tests + integration tests must succeed
2. **Linting passes**: Ruff (Python), ESLint + Prettier (TypeScript/React)
3. **Code coverage**: 70%+ for new/modified code (measured by pytest + Istanbul)
4. **Type checking**: TypeScript strict mode, Python type hints required
5. **Documentation**: Docstrings for functions, README updates for new features

### Service-Specific Reviews
- **API Routes**: Must include request/response schema validation (Pydantic models)
- **UI Components**: Must include Storybook stories and accessibility checks (WCAG 2.1 AA)
- **Functions**: Must include input validation and error handling (structured logging)
- **Database Changes**: Must include migration strategy (Cosmos DB schema versioning)

### Breaking Changes
- Major version bump required for any breaking API changes
- Changelog updated (CHANGELOG.md) with migration instructions
- Deprecated endpoints must remain functional for 1 major version before removal
- Function signature changes require coordination across affected services

## Governance

### Constitution as Law
This constitution supersedes all other project practices and documentation. When a conflict arises between this document and any process/guidance document, this constitution takes precedence.

### Amendment Process
1. **Proposal**: Describe proposed change with rationale (issue or PR comment)
2. **Review**: Technical leads verify alignment with project goals
3. **Migration Plan**: Define how existing code will comply with new principle
4. **Approval**: Consensus required from core team before amendment
5. **Documentation**: Update constitution with new version, dated amendment
6. **Implementation**: All new code follows amended version; legacy code refactored incrementally

### Compliance Verification
- **Code Review**: Every PR reviewed against applicable constitutional principles
- **Architecture Reviews**: Quarterly reviews to ensure service consolidation / containerization principles remain intact
- **Dependency Audits**: Monthly audits of `pyproject.toml` and `package.json` to identify security/maintenance issues

### Development Guidance
For runtime development questions not addressed in this constitution, refer to:
- **Azure Setup**: [SIMPLIFIED-TEMPLATE.md](.github/SIMPLIFIED-TEMPLATE.md) - Quick start and common Azure patterns
- **Architecture Details**: [PROJECT-ANALYSIS.md](.github/PROJECT-ANALYSIS.md) - System flows and service dependencies
- **API Contracts**: `specs/*/contracts/` - Request/response schemas

**Version**: 1.0.0 | **Ratified**: 2025-12-16 | **Last Amended**: 2025-12-16
