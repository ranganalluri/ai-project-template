# Implementation Plan: FastAPI + React Monorepo High-Level Structure

**Branch**: `001-fastapi-react-monorepo` | **Date**: 2025-12-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-fastapi-react-monorepo/spec.md`

## Summary

Create a high-level monorepo structure that consolidates the FastAPI backend and React frontend into a unified workspace using uv (Python) and npm (JavaScript) package managers. This structure enables local development, testing, and containerized deployment to Azure Container Apps with a single `npm run dev` command and `azd up` deployment workflow.

## Technical Context

**Language/Version**: Python 3.12+, Node.js 18+, TypeScript 5.0+  
**Primary Dependencies**: FastAPI, React 18, Vite, uv, npm workspaces  
**Storage**: Azure Cosmos DB (application data), Azure Blob Storage (files)  
**Testing**: pytest (Python), Vitest (React), integration test framework for E2E  
**Target Platform**: Linux containers (Azure Container Apps), local Docker  
**Project Type**: Web monorepo (backend + frontend + shared utilities)  
**Performance Goals**: API cold start <5s, UI load <3s, 70%+ test coverage  
**Constraints**: <500MB per container image, <10min dev setup time, <15min deployment to Azure  
**Scale/Scope**: 3 services (UI, API, Functions), 4 main directories, workspace-based configuration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Service Consolidation (Non-Negotiable) ✅
**Status**: PASS - Feature spec defines 3 consolidated services (UI, API, Functions) with shared common package
- UI consolidation: React app at `apps/ui/`
- API consolidation: FastAPI at `apps/api/`
- Functions consolidation: Azure Functions at `apps/functions/`
- Common package: Python utilities at `apps/common/`

### II. Containerization-First (Non-Negotiable) ✅
**Status**: PASS - Spec requires Dockerfiles for all services with <500MB size constraint
- FR-007: Each service directory MUST have Dockerfile
- SC-006: Each service builds into Docker container <500MB
- SC-007: Cold start <5 seconds for Python services

### III. Unified API Surface ✅
**Status**: PASS - Spec defines unified API routes under `/api/*` prefix
- FR-011: API exposes `/api/health` endpoint
- FR-010: Single development command (`npm run dev`) starts all services
- Workspace structure enables shared middleware and authentication

### IV. Test-First Development (Non-Negotiable) ✅
**Status**: PASS - Spec includes test requirements and coverage targets
- FR-013: System supports `uv run pytest` for API and `npm test` for UI
- SC-004/SC-005: Minimum 70% code coverage targets
- All user stories include acceptance scenarios suitable for TDD

### V. Workspace-Based Dependency Management ✅
**Status**: PASS - Spec explicitly requires uv and npm workspaces
- FR-002: uv workspace with members: `apps/api`, `apps/functions`, `apps/common`
- FR-003: npm workspaces with `apps/ui`
- FR-018/FR-019: Dependencies lockable via `uv sync` and `npm ci`

**Overall Constitution Compliance**: ✅ FULLY COMPLIANT - No violations, all 5 core principles addressed in specification

## Project Structure

### Documentation (this feature)

```text
specs/001-fastapi-react-monorepo/
├── spec.md                          # Feature specification (user stories, requirements)
├── plan.md                          # This file (technical approach, structure, phases)
├── research.md                      # Phase 0 output (research findings, decisions)
├── data-model.md                    # Phase 1 output (folder structure, entities)
├── quickstart.md                    # Phase 1 output (getting started guide)
├── contracts/                       # Phase 1 output (workspace configs, Dockerfiles)
│   ├── pyproject-root.toml         # Root Python workspace config
│   ├── package-root.json           # Root npm workspace config
│   ├── pyproject-api.toml          # API service config
│   ├── package-ui.json             # UI service config
│   └── Dockerfile-templates/       # Container build templates
└── tasks.md                         # Phase 2 output (implementation tasks)
```

### Source Code (repository root)

```text
datalance-ai-simple/
├── apps/                            # Main services directory
│   ├── ui/                          # React + Vite frontend
│   │   ├── src/
│   │   │   ├── agents/             # Agent chat feature (from agents-web)
│   │   │   ├── content/            # Content mgmt feature (from content-web)
│   │   │   ├── shared/             # Shared components
│   │   │   ├── App.tsx             # Main router
│   │   │   └── main.tsx            # Entry point
│   │   ├── public/                 # Static assets
│   │   ├── dist/                   # Build output (generated)
│   │   ├── Dockerfile              # Multi-stage container build
│   │   ├── package.json            # Dependencies: React, Vite, TypeScript
│   │   ├── tsconfig.json           # TypeScript config
│   │   ├── vite.config.ts          # Vite bundler config
│   │   └── eslint.config.js        # Linting config
│   │
│   ├── api/                         # FastAPI backend
│   │   ├── src/
│   │   │   ├── agents/             # Agent routes (from agents-api)
│   │   │   ├── content/            # Content routes (from content-api)
│   │   │   ├── catalog/            # Analytics/catalog routes
│   │   │   ├── shared/             # Shared middleware, models
│   │   │   ├── app.py              # FastAPI main app
│   │   │   └── config.py           # Configuration
│   │   ├── tests/
│   │   │   ├── unit/               # Unit tests (>70% coverage target)
│   │   │   ├── integration/        # API integration tests
│   │   │   └── conftest.py         # Pytest fixtures
│   │   ├── Dockerfile              # Multi-stage container build
│   │   ├── pyproject.toml          # Dependencies: FastAPI, uvicorn, Azure SDKs
│   │   └── requirements.txt         # Pinned versions (generated by uv)
│   │
│   ├── functions/                   # Azure Functions
│   │   ├── agents/                 # Agent functions
│   │   ├── content/                # Content functions
│   │   ├── function_app.py         # Main entry point
│   │   ├── host.json               # Azure Functions config
│   │   ├── Dockerfile              # Container build
│   │   └── pyproject.toml          # Dependencies
│   │
│   └── common/                      # Shared Python utilities
│       ├── src/
│       │   └── common/
│       │       ├── envs.py         # Environment config
│       │       ├── logs.py         # Structured logging
│       │       ├── storage/        # Azure SDK wrappers
│       │       └── models.py       # Shared data models
│       └── pyproject.toml          # Define as uv package
│
├── infra/                           # Bicep templates
│   ├── main.bicep                  # Entry point
│   └── resources/                  # Individual resource definitions
│       ├── container-apps.bicep    # UI, API, Functions apps
│       ├── cosmos.bicep            # Database
│       ├── storage.bicep           # Blob storage
│       └── networking.bicep        # Network config
│
├── .github/
│   └── workflows/                  # CI/CD pipelines
│       ├── test.yml                # Run tests
│       ├── build.yml               # Build containers
│       └── deploy.yml              # Deploy to Azure
│
├── .devcontainer/
│   ├── devcontainer.json           # Dev Container config
│   └── Dockerfile                  # Container with all tools
│
├── pyproject.toml                  # Python workspace root config
├── package.json                    # npm workspace root config
├── uv.lock                         # Python lock file (auto-generated)
├── package-lock.json               # npm lock file
├── azure.yaml                      # Azure Developer CLI config
├── .env.example                    # Template for local env vars
├── docker-compose.yml              # Local emulators (Azurite, Service Bus)
└── README.md                        # Getting started guide
```

**Structure Decision**: This monorepo uses a workspace-based structure with:
- **Root-level workspace configs**: `pyproject.toml` (uv) and `package.json` (npm) define all workspace members
- **Service isolation**: Each service (`ui`, `api`, `functions`) is independently deployable and testable
- **Shared utilities**: `apps/common/` provides shared Python code via uv workspace mechanism
- **Infrastructure as Code**: `infra/` contains Bicep templates for Azure resources
- **Container-first**: Each service has a Dockerfile for local and cloud deployment

## Complexity Tracking

### No Constitution Violations ✅

This feature fully complies with all 5 core principles from the Datalance AI Constitution. No complexity justification required.

---

## Implementation Phases

### Phase 0: Research & Clarification

**Objectives**: Resolve unknowns, validate technology choices, document decision rationale

**Research Tasks**:

1. **Validate uv Workspace Configuration**
   - Question: Can uv workspaces properly handle Python packages at `apps/api`, `apps/functions`, `apps/common`?
   - Decision: Yes - uv supports [tool.uv.workspace] with members array
   - Resource: [uv Documentation - Workspaces](https://docs.astral.sh/uv/concepts/workspaces/)

2. **Validate npm Workspace Support for Monorepo**
   - Question: Can npm workspaces properly handle `apps/ui` with shared types?
   - Decision: Yes - npm 7+ supports "workspaces" in package.json
   - Resource: [npm Workspaces Documentation](https://docs.npmjs.com/cli/v7/using-npm/workspaces)

3. **FastAPI Multi-Route Organization**
   - Question: How to merge agents-api and content-api into single FastAPI instance?
   - Decision: Use FastAPI router pattern with APIRouter for each module
   - Pattern: `from fastapi import APIRouter` → create routers in agents/, content/, catalog/ subdirectories → include in main app.py

4. **Azure Container Apps Python Cold Start**
   - Question: Can Python 3.12 FastAPI container achieve <5s cold start?
   - Decision: Yes with optimizations (slim base image, startup timeout tuning)
   - Best practices: Multi-stage Dockerfile, distroless runtime, pre-warm health checks

5. **Docker Image Size Optimization**
   - Question: How to keep container images <500MB with all dependencies?
   - Decision: Multi-stage builds, distroless runtime for production, exclude dev dependencies
   - Techniques: Builder stage (compile), runtime stage (execute)

6. **npm run dev Script for Monorepo**
   - Question: Can single `npm run dev` command start all services in parallel?
   - Decision: Yes using npm workspace scripting or concurrently package
   - Implementation: Root package.json defines dev script that starts ui dev server + api server + functions emulator

7. **Environment Variable Management**
   - Question: How to share .env across services in monorepo?
   - Decision: Root `.env` file + service-specific overrides in service directories
   - Pattern: Load root env first, then service-specific values override

**Deliverable**: research.md with decision rationale for each question

### Phase 1: Design & Contracts

**Objectives**: Define exact folder structure, workspace configurations, contract files (Dockerfiles, configs)

**Outputs**:

1. **data-model.md**: Detailed folder structure with descriptions
   - Each directory purpose and contents
   - Workspace member definitions
   - Dependency graph between services

2. **contracts/**: Template files for implementation
   - `pyproject-root.toml` - Python workspace root config
   - `pyproject-api.toml` - API service dependencies
   - `pyproject-functions.toml` - Functions service dependencies
   - `pyproject-common.toml` - Shared utilities dependencies
   - `package-root.json` - npm workspace root config
   - `package-ui.json` - UI service dependencies
   - `Dockerfile-ui.template` - React container build
   - `Dockerfile-api.template` - FastAPI container build
   - `Dockerfile-functions.template` - Azure Functions container build

3. **quickstart.md**: Getting started guide
   - Prerequisites (Docker, Node 18+, Python 3.12+)
   - Clone and setup: `npm ci && uv sync`
   - Run locally: `npm run dev`
   - Run tests: `npm test` (UI) + `uv run pytest` (API)
   - Build containers: `docker build` for each service
   - Deploy to Azure: `azd up`

### Phase 2: Implementation Tasks (Generated by /speckit.tasks)

Will be created by `/speckit.tasks` command after phase 1 completion

**High-level task grouping** (to be detailed):
- **Setup**: Initialize workspace configs, create folder structure
- **UI Service**: Create Vite project, merge agents-web + content-web, add tests
- **API Service**: Create FastAPI app, merge agents-api + content-api, add tests
- **Functions Service**: Containerize existing functions
- **Common Package**: Create shared Python utilities
- **Testing**: Write test suite infrastructure, target 70% coverage
- **Containerization**: Create Dockerfiles, test container builds
- **Azure Deployment**: Create azure.yaml, Bicep templates, test `azd up`
- **Documentation**: Create README, architecture diagrams, getting started guide

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Python version compatibility | Low | Medium | Pin Python 3.12+ in pyproject.toml, test in CI/CD |
| Workspace dependency conflicts | Medium | High | Comprehensive testing, lock files, dependency audit in CI |
| Container image size >500MB | Low | Medium | Multi-stage builds, distroless runtime, size monitoring |
| Azure cold start >5s | Low | Medium | Lazy imports, startup timeout tuning, pre-warming |
| npm workspace issues | Low | Medium | Test with multiple npm versions, fallback to manual dependency management |
| Docker daemon not available locally | Low | Low | Clear error messages, documentation, Docker Desktop verification |

---

## Success Gates (must pass before Phase 1)

- [x] Technical Context completed without NEEDS CLARIFICATION
- [x] Constitution Check shows full compliance
- [x] Project structure is concrete and detailed
- [x] All constraints are understood and documented
- [x] Risk assessment completed

**Status**: ✅ READY TO PROCEED TO PHASE 1

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
