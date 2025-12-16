# Datalance AI - Project Analysis & Simplification Guide

**Date:** 2025-01-22  
**Purpose:** Extract current architecture, identify key tasks and flows, and provide simplified Azure Developer CLI template

---

## 1. System Capabilities & Required Tasks

### Current Architecture (5 Services)

#### 1.1 **agents-api** (FastAPI - Azure App Service)
**Purpose:** AI chat and agent management with Azure OpenAI integration

**Key Features:**
- **Assistants/Agents Management** (`/api/assistants/*`, `/api/agents/*`)
  - CRUD operations for AI assistants
  - File upload for agent context
  - Agent configuration and settings
- **Catalog Services** (`/api/catalog/*`)
  - Analytics endpoints (usage tracking, metrics)
  - Dashboard data aggregation
  - Governance policies
  - Use cases management
  - Deployment tracking
  - Events logging
- **Azure AI Foundry Integration** (`/api/foundry/*`)
  - Model deployments
  - AI project resources
  - Inference endpoints
- **Authentication:** Azure AD (Entra ID) + API Key fallback
- **Telemetry:** OpenTelemetry instrumentation for Application Insights

**Technology Stack:**
- FastAPI with Uvicorn
- Azure OpenAI SDK
- Azure Cosmos DB (NoSQL)
- Azure AI Foundry SDK
- Pydantic models
- OpenTelemetry

#### 1.2 **content-api** (Flask - Azure App Service)
**Purpose:** Document processing and form extraction

**Key Features:**
- **Document Management** (`/api/documents/*`)
  - Upload documents to Azure Storage
  - Queue documents for processing
  - Track processing status
  - Extract metadata and content
- **Form Extraction** (`/api/forms/*`)
  - Create form templates (JSON Schema)
  - Extract data from documents using AI
  - Validate extracted data against schemas
- **Download Services** (`/api/download/*`)
  - Generate SAS tokens for secure file access
  - Serve processed documents
- **Status Tracking** (`/api/status/*`)
  - Document processing queue status

**Technology Stack:**
- Flask + Flask-RESTx
- Azure Storage Blobs
- Azure Service Bus queues
- Azure Document Intelligence (Form Recognizer)
- Power Automate compatibility (OpenAPI 2.0 Swagger)

#### 1.3 **functions** (Azure Functions - Function App)
**Purpose:** Background processing and scheduled tasks

**Key Functions:**

**Agent Functions:**
- `ManualUpdateAgent` - Queue-triggered agent context updates
- `ScheduleUpdateAgent` - Timer-triggered (every 6 hours) agent maintenance

**Content Functions:**
- `FileUploadedFunc` - Service Bus trigger when document uploaded → chunk document
- `ProcessChunkFunc` - Process document chunks (OCR, text extraction)
- `ProcessImageFunc` - Extract images from documents
- `PollStatusFunc` - Check Azure Document Intelligence processing status
- `GenerateSchemaFunc` - Generate JSON schemas from processed documents
- `PollTimeoutDocumentsFunc` - Timer-triggered (every 5 min) - retry stuck documents

**Deployment Function:**
- `DeployAppTrigger` - HTTP-triggered deployment automation

**Technology Stack:**
- Azure Functions Python v2 programming model
- Azure Service Bus triggers
- Azure Queue Storage triggers
- Timer triggers
- Azure Document Intelligence SDK

#### 1.4 **agents-web** (React/Vite - Azure Static Web App or App Service)
**Purpose:** Interactive agent chat interface

**Key Features:**
- Chat UI for interacting with agents
- Agent selection and configuration
- File upload for agent context
- Real-time streaming responses
- Authentication integration

**Technology Stack:**
- React 18
- Vite build system
- TypeScript
- Shared types from `packages/shared-types`

#### 1.5 **content-web** (React/Vite - Azure Static Web App or App Service)
**Purpose:** Content management dashboard

**Key Features:**
- Document upload and management
- Form template creation
- Processing status monitoring
- Downloaded processed documents

**Technology Stack:**
- React 18
- Vite build system
- TypeScript
- Shared types from `packages/shared-types`

### Shared Packages

#### **apps/common** (Python package)
**Purpose:** Shared utilities across all Python services

**Key Modules:**
- `common.envs` - Environment variable management
- `common.logs` - Structured logging with OpenTelemetry
- `common.storage.cosmos` - Cosmos DB access with tenant-aware auth
- `common.storage.objects` - Data models (Citation, etc.)
- `common.util` - JSON encoders, helpers

**Technology Stack:**
- Pydantic for data validation
- Azure SDK (Cosmos, Storage, Identity)
- OpenTelemetry
- Loguru for enhanced logging

#### **packages/shared-types** (TypeScript package)
**Purpose:** TypeScript type definitions shared between React apps

**Usage:**
- API request/response types
- Domain models
- Shared interfaces

---

## 2. End-to-End Request Flows

### Flow 1: User Uploads Document for Processing

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ content-web  │────▶│ content-api  │────▶│Azure Storage │────▶│Service Bus   │
│  (React UI)  │     │  POST /docs  │     │  Blob Upload │     │Queue Message │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                        │
                                                                        ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│Cosmos DB     │◀────│  functions   │◀────│Service Bus   │     │              │
│Store Results │     │FileUploadFunc│     │Trigger       │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

**Detailed Steps:**

1. **User Action:** Upload file via [content-web](apps/content-web)
2. **API Request:** POST `/api/documents` to [content-api](apps/content-api)
3. **Storage:** content-api uploads blob to Azure Storage
4. **Queue:** content-api sends message to `document-queue` Service Bus queue
5. **Function Trigger:** [functions/FileUploadedFunc](apps/functions) triggered by queue message
6. **Processing:** Function chunks document, queues chunks to `document-chunk-queue`
7. **Chunk Processing:** [functions/ProcessChunkFunc](apps/functions) extracts text/images
8. **AI Extraction:** Azure Document Intelligence processes document
9. **Status Polling:** [functions/PollStatusFunc](apps/functions) checks completion
10. **Storage:** Results saved to Cosmos DB
11. **UI Update:** content-web polls `/api/status/list` for completion

### Flow 2: User Chats with AI Agent

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ agents-web   │────▶│ agents-api   │────▶│Azure OpenAI  │────▶│Response      │
│ (Chat UI)    │     │POST /chat    │     │GPT-4 Model   │     │Streaming     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                            │                     ▲
                            │                     │
                            ▼                     │
                     ┌──────────────┐             │
                     │Cosmos DB     │─────────────┘
                     │Agent Context │   (RAG: Retrieve context)
                     │Chat History  │
                     └──────────────┘
```

**Detailed Steps:**

1. **User Action:** Type message in [agents-web](apps/agents-web) chat interface
2. **API Request:** POST `/api/chat` or `/api/agents/{id}/chat` to [agents-api](apps/agents-api)
3. **Context Retrieval:** agents-api loads agent configuration from Cosmos DB
4. **RAG (Optional):** If agent has files, retrieve relevant context via Azure AI Search
5. **LLM Call:** agents-api calls Azure OpenAI with prompt + context
6. **Streaming:** Response streamed back to agents-web via SSE (Server-Sent Events)
7. **History Storage:** Chat messages saved to Cosmos DB

### Flow 3: Create Form Template and Extract Data

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ content-web  │────▶│ content-api  │────▶│Cosmos DB     │
│ Create Form  │     │POST /forms   │     │Store Template│
└──────────────┘     └──────────────┘     └──────────────┘

                     (Later: Document uploaded)
                              │
                              ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ functions    │────▶│Document Intel│────▶│Cosmos DB     │
│GenSchemaFunc │     │Extract Fields│     │Store Results │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Detailed Steps:**

1. **User Action:** Define form template (JSON Schema) in [content-web](apps/content-web)
2. **API Request:** POST `/api/forms` to [content-api](apps/content-api)
3. **Storage:** Form template saved to Cosmos DB
4. **Document Upload:** User uploads document to be extracted
5. **Function Trigger:** [functions/GenerateSchemaFunc](apps/functions) processes document
6. **AI Extraction:** Azure Document Intelligence uses template to extract fields
7. **Validation:** Extracted data validated against JSON Schema
8. **Storage:** Validated data saved to Cosmos DB

### Flow 4: Agent Context Update (Background Job)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Timer        │────▶│ functions    │────▶│Cosmos DB     │
│ (Every 6hrs) │     │Schedule      │     │Agent Context │
└──────────────┘     │UpdateAgent   │     └──────────────┘
                     └──────────────┘            │
                              │                  │
                              ▼                  ▼
                     ┌──────────────┐     ┌──────────────┐
                     │Azure AI      │     │Update Index  │
                     │Search        │     │Embeddings    │
                     └──────────────┘     └──────────────┘
```

**Detailed Steps:**

1. **Timer Trigger:** Azure Function timer fires every 6 hours
2. **Function Execution:** [functions/ScheduleUpdateAgent](apps/functions) runs
3. **Agent Discovery:** Retrieve all active agents from Cosmos DB
4. **Context Update:** For each agent, re-index files/context
5. **Embedding Generation:** Generate new embeddings for updated content
6. **Search Index:** Update Azure AI Search index with new embeddings

---

## 3. Architecture Mapping: Current → Target

### Current State (5 Services)

| Service | Type | Hosting | Purpose | Dependencies |
|---------|------|---------|---------|--------------|
| agents-api | Python/FastAPI | App Service | AI chat & agents | common, agents |
| content-api | Python/Flask | App Service | Document processing | common, content |
| agents-web | React/Vite | App Service (JS) | Agent UI | shared-types |
| content-web | React/Vite | App Service (JS) | Content UI | shared-types |
| functions | Python Functions | Function App | Background jobs | common, content, agents |

**Challenges:**
- **5 separate deployments** - complex orchestration
- **Mixed hosting models** - App Service (Python), App Service (JS), Function App
- **Inconsistent containerization** - Only partial Docker support
- **Dual API surface** - agents-api and content-api separate
- **Build complexity** - npm workspaces + Python + PowerShell + azd hooks

### Target State (3 Container Apps)

| Service | Type | Hosting | Purpose | Consolidation |
|---------|------|---------|---------|---------------|
| **ui-app** | React/Vite | Container Apps | Unified UI | agents-web + content-web merged |
| **api-app** | Python/FastAPI | Container Apps | Unified API | agents-api + content-api merged |
| **functions-app** | Python Functions | Container Apps | Background jobs | functions (containerized) |
| **common** | Python Package | uv workspace | Shared utilities | Unchanged, uv-managed |

**Benefits:**
- **3 services** instead of 5 - simpler deployment
- **Unified hosting** - All Container Apps (consistent scaling, networking, monitoring)
- **Single API** - One endpoint for UI, easier authentication
- **Containerization** - Full Docker support, faster cold starts
- **uv package manager** - Faster dependency resolution, workspace-based development
- **Simplified CI/CD** - Container builds vs. mixed App Service deployments

### Migration Strategy

#### Step 1: Merge UI Apps → **ui-app**

**Action:** Combine agents-web and content-web into single React app with routing

```
apps/ui/
├── src/
│   ├── agents/          # Agent chat features (from agents-web)
│   ├── content/         # Content management (from content-web)
│   ├── shared/          # Shared components
│   ├── App.tsx          # Main app with routing
│   └── main.tsx
├── Dockerfile
├── package.json
└── vite.config.ts
```

**Routing:**
- `/agents` → Agent chat interface
- `/content` → Content management dashboard
- `/` → Landing page or redirect

#### Step 2: Merge API Apps → **api-app**

**Action:** Combine agents-api (FastAPI) and content-api (Flask) into single FastAPI app

```
apps/api/
├── src/
│   ├── agents/          # Agent routes (from agents-api)
│   ├── content/         # Content routes (from content-api)
│   ├── catalog/         # Catalog routes (from agents-api)
│   ├── shared/          # Shared middleware, auth
│   ├── app.py           # Main FastAPI app
│   └── config.py
├── Dockerfile
└── pyproject.toml       # uv-based dependencies
```

**API Routes:**
- `/api/agents/*` → Agent endpoints
- `/api/content/*` → Content endpoints
- `/api/catalog/*` → Catalog endpoints
- `/api/foundry/*` → Azure AI Foundry endpoints

**Why FastAPI over Flask:**
- Modern async/await support
- Better OpenAPI (Swagger) generation
- Consistent with agents-api patterns
- Easier to migrate Flask-RESTx to FastAPI routers

#### Step 3: Containerize Functions → **functions-app**

**Action:** Add Dockerfile for Azure Functions (Python v2)

```
apps/functions/
├── agents/              # Agent-related functions
├── content/             # Content-related functions
├── function_app.py      # Main entry point
├── Dockerfile           # Container image
├── host.json
└── pyproject.toml       # uv-based dependencies
```

**Container Support:**
- Azure Functions now supports Container Apps hosting
- Same Python v2 programming model
- Benefits: faster scaling, consistent networking with API

#### Step 4: Standardize Common Package with uv

**Action:** Ensure `apps/common` uses uv workspace configuration

```
apps/common/
├── src/
│   └── common/
│       ├── envs.py
│       ├── logs/
│       ├── storage/
│       └── util.py
└── pyproject.toml       # uv workspace member
```

**Root `pyproject.toml`:**
```toml
[tool.uv.workspace]
members = ["apps/api", "apps/functions", "apps/common"]
```

---

## 4. Simplified Azure Developer CLI Template

### New azure.yaml

```yaml
name: datalance-ai
metadata:
  template: datalance-ai-containerapp@0.0.1

services:
  # Unified React UI - Container App
  ui:
    project: ./apps/ui
    language: js
    host: containerapp
    docker:
      path: ./apps/ui/Dockerfile
      context: ./apps/ui
    env:
      VITE_API_URL: ${API_URL}
      VITE_APP_CLIENT_ID: ${APP_CLIENT_ID}

  # Unified FastAPI API - Container App
  api:
    project: ./apps/api
    language: python
    host: containerapp
    docker:
      path: ./apps/api/Dockerfile
      context: .  # Root context to include apps/common
    env:
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
      AZURE_STORAGE_ACCOUNT_NAME: ${AZURE_STORAGE_ACCOUNT_NAME}
      AZURE_COSMOS_ENDPOINT: ${AZURE_COSMOS_ENDPOINT}
      APPLICATIONINSIGHTS_CONNECTION_STRING: ${APPLICATIONINSIGHTS_CONNECTION_STRING}

  # Azure Functions - Container App (containerized)
  functions:
    project: ./apps/functions
    language: python
    host: containerapp  # Container Apps now supports Functions
    docker:
      path: ./apps/functions/Dockerfile
      context: .  # Root context to include apps/common
    env:
      AZURE_STORAGE_CONNECTION_STRING: ${AZURE_STORAGE_CONNECTION_STRING}
      AZURE_SERVICEBUS_NAMESPACE: ${AZURE_SERVICEBUS_NAMESPACE}
      APPLICATIONINSIGHTS_CONNECTION_STRING: ${APPLICATIONINSIGHTS_CONNECTION_STRING}

hooks:
  preprovision:
    posix:
      shell: sh
      run: |
        echo "Installing dependencies..."
        npm ci
        uv sync --all-packages
  
  prepackage:
    posix:
      shell: sh
      run: |
        echo "Building UI..."
        cd apps/ui && npm run build
        echo "Linting and testing..."
        npm run lint
        npm run test

  postdeploy:
    posix:
      shell: sh
      run: |
        echo "Deployment complete!"
        echo "UI URL: $(azd env get-values | grep UI_URL)"
        echo "API URL: $(azd env get-values | grep API_URL)"
```

### New Folder Structure

```
datalance-ai/
├── apps/
│   ├── ui/                      # Merged agents-web + content-web
│   │   ├── src/
│   │   │   ├── agents/
│   │   │   ├── content/
│   │   │   ├── shared/
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── api/                     # Merged agents-api + content-api
│   │   ├── src/
│   │   │   ├── agents/
│   │   │   ├── content/
│   │   │   ├── catalog/
│   │   │   ├── app.py
│   │   │   └── config.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── functions/               # Containerized Azure Functions
│   │   ├── agents/
│   │   ├── content/
│   │   ├── function_app.py
│   │   ├── Dockerfile
│   │   ├── host.json
│   │   └── pyproject.toml
│   │
│   └── common/                  # Shared Python utilities
│       ├── src/
│       │   └── common/
│       └── pyproject.toml
│
├── infra/                       # Bicep templates
│   ├── main.bicep               # Container Apps infrastructure
│   ├── modules/
│   │   ├── containerapp.bicep
│   │   ├── cosmos.bicep
│   │   ├── storage.bicep
│   │   ├── servicebus.bicep
│   │   └── openai.bicep
│   └── main.parameters.json
│
├── .github/
│   └── workflows/
│       ├── ci.yml               # Build and test
│       ├── deploy-dev.yml       # Deploy to dev environment
│       └── deploy-prod.yml      # Deploy to production
│
├── .devcontainer/               # Dev Container support
│   ├── devcontainer.json
│   └── Dockerfile
│
├── azure.yaml                   # Azure Developer CLI config
├── pyproject.toml               # uv workspace configuration
├── package.json                 # npm workspace configuration
└── README.md
```

### Dockerfiles

#### apps/ui/Dockerfile

```dockerfile
# Build stage
FROM node:18-alpine AS build
WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### apps/api/Dockerfile

```dockerfile
FROM python:3.11-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy workspace config and common package
COPY pyproject.toml uv.lock ./
COPY apps/common ./apps/common
COPY apps/api ./apps/api

# Install dependencies using uv
WORKDIR /app/apps/api
RUN uv sync --frozen --no-dev

# Set Python path to include workspace
ENV PYTHONPATH=/app/apps/api/src:/app/apps/common/src

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### apps/functions/Dockerfile

```dockerfile
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Install uv
RUN pip install uv

# Copy workspace config and common package
COPY pyproject.toml uv.lock ./
COPY apps/common /home/site/wwwroot/apps/common
COPY apps/functions /home/site/wwwroot/apps/functions

# Install dependencies
WORKDIR /home/site/wwwroot/apps/functions
RUN uv sync --frozen --no-dev

# Set Python path
ENV PYTHONPATH=/home/site/wwwroot/apps/functions:/home/site/wwwroot/apps/common/src
ENV AzureWebJobsScriptRoot=/home/site/wwwroot/apps/functions
```

### GitHub Workflows

#### .github/workflows/ci.yml

```yaml
name: CI - Build and Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-ui:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: |
          cd apps/ui
          npm ci
          npm run lint
          npm run test
          npm run build

  build-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install uv
        run: curl -Ls https://astral.sh/uv/install.sh | sh
      - name: Build and test
        run: |
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"
          cd apps/api
          uv sync
          uv run pytest
      - name: Build Docker image
        run: |
          docker build -t datalance-api:${{ github.sha }} -f apps/api/Dockerfile .

  build-functions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install uv
        run: curl -Ls https://astral.sh/uv/install.sh | sh
      - name: Build Docker image
        run: |
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"
          docker build -t datalance-functions:${{ github.sha }} -f apps/functions/Dockerfile .
```

#### .github/workflows/deploy-dev.yml

```yaml
name: Deploy to Development

on:
  workflow_dispatch:
  push:
    branches: [develop]

env:
  AZURE_ENV_NAME: dev

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Azure Developer CLI
        run: curl -fsSL https://aka.ms/install-azd.sh | bash
      
      - name: Install uv
        run: curl -Ls https://astral.sh/uv/install.sh | sh
      
      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy with azd
        run: |
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"
          azd auth login --client-id ${{ secrets.AZURE_CLIENT_ID }} \
            --client-secret ${{ secrets.AZURE_CLIENT_SECRET }} \
            --tenant-id ${{ secrets.AZURE_TENANT_ID }}
          azd env select ${{ env.AZURE_ENV_NAME }}
          azd up --no-prompt
```

### Root pyproject.toml (uv workspace)

```toml
[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]

[tool.uv.workspace]
members = ["apps/api", "apps/functions", "apps/common"]

[tool.ruff]
line-length = 120
target-version = "py311"
```

### Dev Container Configuration

#### .devcontainer/devcontainer.json

```json
{
  "name": "Datalance AI",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace",
  "features": {
    "ghcr.io/devcontainers/features/azure-cli:1": {},
    "ghcr.io/devcontainers/features/node:1": {
      "version": "18"
    },
    "ghcr.io/devcontainers/features/python:1": {
      "version": "3.11"
    }
  },
  "postCreateCommand": "npm ci && uv sync",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-azuretools.vscode-azurefunctions",
        "ms-azuretools.vscode-docker",
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode"
      ]
    }
  }
}
```

---

## 5. Migration Checklist

### Phase 1: Prepare Workspace Structure

- [ ] Create new `apps/ui` directory
- [ ] Create new `apps/api` directory
- [ ] Add Dockerfiles to all apps
- [ ] Configure root `pyproject.toml` with uv workspace
- [ ] Set up `.devcontainer/` for local development

### Phase 2: Merge UI Applications

- [ ] Copy `agents-web/src` → `apps/ui/src/agents`
- [ ] Copy `content-web/src` → `apps/ui/src/content`
- [ ] Create unified `App.tsx` with React Router
- [ ] Merge `package.json` dependencies
- [ ] Update environment variable references
- [ ] Test merged UI locally

### Phase 3: Merge API Applications

- [ ] Copy `agents-api/src/agents_api` → `apps/api/src/agents`
- [ ] Copy `content-api/src/content_api` → `apps/api/src/content`
- [ ] Migrate Flask-RESTx routes to FastAPI routers
- [ ] Merge authentication middleware
- [ ] Consolidate `pyproject.toml` dependencies
- [ ] Update environment variable references
- [ ] Test merged API locally

### Phase 4: Containerize Functions

- [ ] Create `apps/functions/Dockerfile`
- [ ] Update `pyproject.toml` for uv
- [ ] Test container build locally
- [ ] Verify function triggers work in container

### Phase 5: Infrastructure as Code

- [ ] Create new `infra/modules/containerapp.bicep`
- [ ] Update `infra/main.bicep` for Container Apps
- [ ] Remove App Service modules
- [ ] Test infrastructure provisioning in dev environment

### Phase 6: CI/CD Migration

- [ ] Create `.github/workflows/ci.yml`
- [ ] Create `.github/workflows/deploy-dev.yml`
- [ ] Create `.github/workflows/deploy-prod.yml`
- [ ] Configure GitHub secrets (AZURE_CREDENTIALS)
- [ ] Test workflow execution

### Phase 7: Testing & Validation

- [ ] Run integration tests on merged API
- [ ] Verify all Function triggers work
- [ ] Test UI routing and features
- [ ] Load test Container Apps vs. App Service
- [ ] Validate monitoring and telemetry

### Phase 8: Deployment

- [ ] Deploy to dev environment
- [ ] Smoke test all features
- [ ] Deploy to staging environment
- [ ] Production deployment
- [ ] Monitor performance and errors

---

## 6. Key Differences: Current vs. Simplified

| Aspect | Current | Simplified |
|--------|---------|------------|
| **Services** | 5 (agents-api, content-api, agents-web, content-web, functions) | 3 (ui, api, functions) |
| **Hosting** | Mixed (App Service Python, App Service JS, Function App) | Unified (All Container Apps) |
| **Deployment** | azd with prepackage hooks (npm + PowerShell) | azd with container builds |
| **Python Mgmt** | pip + requirements.txt files | uv workspace with pyproject.toml |
| **Containers** | Partial (only for special cases) | Full (all services containerized) |
| **API Surface** | 2 endpoints (agents, content) | 1 unified endpoint |
| **UI Apps** | 2 separate React apps | 1 app with routing |
| **CI/CD** | Complex (5 services, mixed types) | Simplified (3 container builds) |
| **Local Dev** | Azurite + npm scripts + Python venv | Dev Container + uv + Docker Compose |
| **Auth** | Separate per API | Unified authentication |

---

## 7. Benefits of Simplified Architecture

### Developer Experience
- **Single UI codebase** - Easier to maintain shared components
- **Unified API** - One authentication layer, consistent patterns
- **uv package manager** - Faster dependency resolution (10-100x faster than pip)
- **Dev Container** - Consistent development environment across team
- **Container-first** - Parity between local dev and production

### Operations
- **3 deployments** instead of 5 - Reduced complexity
- **Container Apps autoscaling** - Better resource utilization
- **Unified networking** - Simpler VNet integration, private endpoints
- **Consistent monitoring** - All services emit same telemetry format
- **Faster deployments** - Container builds vs. zip deployments

### Cost Optimization
- **Container Apps consumption plan** - Pay only for active requests
- **Resource consolidation** - Fewer App Service plans
- **Better scaling** - Scale to zero for dev environments

### Security
- **Reduced attack surface** - Fewer endpoints to secure
- **Unified authentication** - Single Azure AD integration
- **Container security** - Scan images for vulnerabilities
- **Network isolation** - Container Apps VNet integration

---

## 8. Next Steps

1. **Review this analysis** with your team
2. **Prioritize features** - Decide which current features are critical
3. **Create pilot environment** - Test simplified architecture in isolated subscription
4. **Migrate incrementally** - Start with UI merge, then API, then Functions
5. **Monitor and iterate** - Compare performance, cost, and developer productivity

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-22  
**Maintained By:** AI Architecture Team
