<!-- 
SYNC IMPACT REPORT
Version: 1.0.1 (Updated - Current Project Alignment)
Status: Constitution aligned with actual AI Project Template structure
Created: 2025-12-16
Updated: 2025-01-13
Previous Version: 1.0.0

Key Changes:
- Aligned service definitions with actual apps/ structure (api, ui, functions, common-py, ui-lib)
- Updated tech stack documentation to reflect actual project dependencies
- Corrected file paths and Azure service references
- Updated workspace structure documentation
- Aligned with actual azure.yaml and infrastructure definitions

Verified Components:
- ✅ apps/api (FastAPI backend)
- ✅ apps/ui (React + Vite frontend)
- ✅ apps/functions (Azure Functions container)
- ✅ apps/common-py (Shared Python utilities)
- ✅ apps/ui-lib (Shared TypeScript/React components)
- ✅ infra/ (Bicep infrastructure as code)
- ✅ .specify/templates (updated for monorepo examples)
- ✅ .github/agents (updated with correct paths)
-->

# AI Project Constitution (Master)

**Status**: Master document with links to service-specific constitutions  
**Last Updated**: 2025-01-13

## Service-Specific Constitutions

This document defines core principles. For detailed implementation guidance, see:

### Frontend (React + TypeScript)
- **[constitution-ui-react.md](constitution-ui-react.md)** - React UI project
  - Covers: `apps/ui/` (React app) + `apps/ui-lib/` (shared components)
  - Content: Component development, API integration, hooks, testing, TypeScript setup

### Backend (Python)
- **[constitution-python.md](constitution-python.md)** - All Python services
  - Covers: `apps/api/` (FastAPI), `apps/common-py/` (shared DTOs), `apps/functions/` (async), `apps/mcp/` (optional)
  - Content: DTO architecture, services, repositories, naming conventions, testing

> **Quick Start**: 
> - Building UI features? → Read [constitution-ui-react.md](constitution-ui-react.md)
> - Building API endpoints? → Read [constitution-python.md](constitution-python.md)
> - Adding shared services? → See both documents for consistency

## Core Principles

### I. Service Consolidation (Non-Negotiable)
Services MUST be consolidated to maximize coherence and minimize deployment complexity:
- **UI Services**: React app with Vite (`apps/ui`) + shared component library (`apps/ui-lib`)
- **API Services**: Single unified FastAPI application (`apps/api`)
- **Background Processing**: Azure Functions containerized in Python (`apps/functions`)
- **Shared Utilities**: Centralized Python package via uv workspace (`apps/common-py`)

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
Python and pnpm dependencies MUST be managed via workspace tooling:
- **Python**: uv workspace with members: `apps/api`, `apps/functions`, `apps/common-py` (see `pyproject.toml`)
- **JavaScript/TypeScript**: pnpm workspaces with members: `apps/ui`, `apps/ui-lib` (see `package.json`)
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

**Resources**:
- See `apps/common-py/NAMING_CONVENTIONS.md` for quick reference
- See `apps/common-py/USER_SERVICE_ARCHITECTURE.md` for complete examples
- See `apps/common-py/tests/test_dto_naming_conventions.py` for validation tests

## Development Workflow

### Code Organization
```
ai-project-template/
├── apps/
│   ├── ui/              # React + Vite frontend
│   │   ├── src/
│   │   │   ├── main.tsx          # React entry point
│   │   │   ├── App.tsx           # Root component with routing
│   │   │   ├── pages/            # Page components
│   │   │   ├── components/       # Reusable UI components
│   │   │   ├── services/         # API client and utilities
│   │   │   ├── hooks/            # Custom React hooks
│   │   │   ├── types/            # TypeScript type definitions
│   │   │   ├── styles/           # CSS and Tailwind styles
│   │   │   └── __tests__/        # Component tests
│   │   ├── public/               # Static assets
│   │   ├── Dockerfile            # Container build for Azure
│   │   ├── vite.config.ts        # Vite configuration
│   │   ├── tsconfig.json         # TypeScript config
│   │   └── package.json
│   │
│   ├── ui-lib/          # Shared React component library
│   │   ├── src/
│   │   │   ├── index.ts          # Public exports
│   │   │   ├── components/       # Reusable components
│   │   │   ├── api/              # Shared API utilities
│   │   │   ├── types/            # Shared TypeScript types
│   │   │   └── utils/            # Shared utilities
│   │   ├── tsup.config.ts        # Library build config
│   │   └── package.json
│   │
│   ├── api/             # FastAPI backend service
│   │   ├── src/
│   │   │   └── api/
│   │   │       ├── main.py           # FastAPI app entrypoint
│   │   │       ├── config.py         # Configuration management
│   │   │       ├── middleware.py     # CORS, logging middleware
│   │   │       ├── dependencies.py   # Dependency injection
│   │   │       ├── routes/           # API route handlers
│   │   │       ├── models/           # Pydantic schemas
│   │   │       └── services/         # Business logic
│   │   ├── tests/
│   │   │   ├── conftest.py           # Pytest fixtures
│   │   │   ├── test_health.py        # Health endpoint tests
│   │   │   └── integration/          # Integration tests
│   │   ├── Dockerfile                # Container build for Azure
│   │   └── pyproject.toml            # Python dependencies
│   │
│   ├── functions/       # Azure Functions (containerized)
│   │   ├── src/
│   │   │   └── functions/            # Function definitions
│   │   ├── function_app.py           # Functions entry point
│   │   ├── host.json                 # Functions runtime config
│   │   ├── Dockerfile                # Container build for Azure
│   │   └── pyproject.toml
│   │
│   ├── common-py/       # Shared Python utilities
│   │   ├── src/
│   │   │   └── common/
│   │   │       ├── models/           # Shared data models
│   │   │       ├── services/         # Shared service logic
│   │   │       └── utils/            # Shared utilities
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   └── mcp/             # Model Context Protocol (optional)
│
├── infra/               # Infrastructure as Code (Bicep)
│   ├── main.bicep                    # Main orchestration
│   ├── main.parameters.json
│   ├── api.bicep                     # API service definition
│   ├── api.parameters.json
│   ├── ui.bicep                      # UI service definition
│   ├── ui.parameters.json
│   ├── functions.bicep               # Functions service definition
│   ├── functions.parameters.json
│   ├── cosmos.parameters.json        # Cosmos DB configuration
│   ├── modules/                      # Reusable Bicep modules
│   │   ├── ai-services.bicep
│   │   ├── container-app.bicep
│   │   ├── container-registry.bicep
│   │   ├── cosmos-db.bicep
│   │   ├── key-vault.bicep
│   │   └── storage-account.bicep
│   └── README.md
│
├── scripts/             # Deployment and automation scripts
│   ├── predeploy.ps1                 # Pre-deployment setup
│   ├── postdeploy.ps1                # Post-deployment config
│   ├── ui-postdeploy.ps1             # UI-specific post-deploy
│   └── write_env.ps1                 # Environment file generation
│
├── .specify/            # Project specifications and templates
│   ├── memory/
│   │   └── constitution.md           # Project constitution (this file)
│   ├── templates/
│   │   ├── spec-template.md
│   │   ├── plan-template.md
│   │   ├── tasks-template.md
│   │   └── checklist-template.md
│   └── scripts/
│       └── powershell/               # Automation scripts
│
├── .github/             # GitHub workflows and agents
│   ├── agents/                       # Speckit agent definitions
│   │   ├── copilot-instructions.md   # Development guidelines
│   │   └── speckit.*.agent.md        # Feature workflow agents
│   ├── prompts/                      # Agent prompts
│   └── workflows/                    # CI/CD workflows
│       ├── build.yml
│       ├── test.yml
│       └── lint.yml
│
├── docs/                # Project documentation
├── data/                # Local data storage (uploads, etc.)
├── specs/               # Feature specifications (generated)
├── hooks/               # Git hooks
├── .devcontainer/       # Dev container configuration
├── .vscode/             # VS Code workspace settings
│
├── pyproject.toml       # Root Python workspace config (uv)
├── package.json         # Root npm workspace config (pnpm)
├── pnpm-workspace.yaml  # pnpm workspace configuration
├── azure.yaml           # Azure Developer CLI configuration
├── docker-compose.yml   # Local development services
├── conftest.py          # Root pytest configuration
├── pytest.ini           # Pytest settings
├── .gitignore           # Git ignore patterns
└── README.md            # Project overview and getting started
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

**Version**: 1.0.1 | **Ratified**: 2025-12-16 | **Last Amended**: 2025-01-13
