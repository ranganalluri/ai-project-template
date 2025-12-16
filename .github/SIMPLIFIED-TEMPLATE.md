# Simplified Datalance AI - Quick Start Template

This is a minimal template structure for the simplified 3-service architecture.

## Folder Structure

```
datalance-ai-simple/
├── apps/
│   ├── ui/                      # React app (agents + content merged)
│   ├── api/                     # FastAPI app (agents-api + content-api merged)
│   ├── functions/               # Azure Functions (containerized)
│   └── common/                  # Shared Python utilities
├── infra/                       # Bicep infrastructure
├── .github/workflows/           # CI/CD pipelines
├── .devcontainer/              # Dev Container config
├── azure.yaml                   # Azure Developer CLI config
├── pyproject.toml              # uv workspace config
└── package.json                # npm workspace config
```

## Quick Commands

### Setup (First Time)

```bash
# Install dependencies
npm ci
uv sync

# Start local development
docker compose up -d  # Azurite, Service Bus emulator
npm run dev           # All services
```

### Development

```bash
# UI development
cd apps/ui
npm run dev

# API development
cd apps/api
uv run uvicorn app:app --reload

# Functions development
cd apps/functions
func start
```

### Build Containers

```bash
# Build all containers
docker compose build

# Build specific service
docker build -t datalance-ui -f apps/ui/Dockerfile .
docker build -t datalance-api -f apps/api/Dockerfile .
docker build -t datalance-functions -f apps/functions/Dockerfile .
```

### Deploy to Azure

```bash
# Login and provision
azd auth login
azd up

# Deploy specific service
azd deploy ui
azd deploy api
azd deploy functions
```

## Migration from Current Project

### Step 1: Copy Common Package

```bash
# Copy shared utilities
cp -r ../datalance-ai/apps/common ./apps/common
```

### Step 2: Merge UI Applications

```bash
# Create unified UI structure
mkdir -p apps/ui/src/{agents,content,shared}

# Copy agents-web
cp -r ../datalance-ai/apps/agents-web/src/* apps/ui/src/agents/

# Copy content-web
cp -r ../datalance-ai/apps/content-web/src/* apps/ui/src/content/
```

### Step 3: Merge API Applications

```bash
# Create unified API structure
mkdir -p apps/api/src/{agents,content,catalog,shared}

# Copy agents-api routes
cp -r ../datalance-ai/apps/agents-api/src/agents_api/api/* apps/api/src/agents/

# Copy content-api routes
cp -r ../datalance-ai/apps/content-api/src/content_api/api_resources/* apps/api/src/content/
```

### Step 4: Copy Functions

```bash
# Copy Azure Functions
cp -r ../datalance-ai/apps/functions/* apps/functions/
```

## New Files to Create

### apps/ui/App.tsx

```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AgentChat from './agents/AgentChat';
import ContentDashboard from './content/ContentDashboard';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/agents" element={<AgentChat />} />
        <Route path="/content" element={<ContentDashboard />} />
        <Route path="/" element={<Navigate to="/agents" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### apps/api/src/app.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from agents.routers import agents_router
from content.routers import content_router
from catalog.routers import catalog_router

app = FastAPI(title="Datalance AI API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
app.include_router(content_router, prefix="/api/content", tags=["content"])
app.include_router(catalog_router, prefix="/api/catalog", tags=["catalog"])

@app.get("/health")
def health():
    return {"status": "healthy"}
```

### pyproject.toml (workspace root)

```toml
[tool.uv.workspace]
members = ["apps/api", "apps/functions", "apps/common"]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
]

[tool.ruff]
line-length = 120
target-version = "py311"
```

### apps/api/pyproject.toml

```toml
[project]
name = "datalance-api"
version = "2.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "azure-identity>=1.15.0",
    "azure-cosmos>=4.5.0",
    "azure-storage-blob>=12.19.0",
    "openai>=1.10.0",
    "pydantic>=2.6.0",
    "python-dotenv>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Environment Variables

Create `.env` file in root:

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_API_KEY=your-key-here

# Azure Storage
AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
AZURE_STORAGE_CONNECTION_STRING=your-connection-string

# Azure Cosmos DB
AZURE_COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
AZURE_COSMOS_KEY=your-key-here

# Azure Service Bus
AZURE_SERVICEBUS_NAMESPACE=your-servicebus.servicebus.windows.net
AZURE_SERVICEBUS_CONNECTION_STRING=your-connection-string

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=your-app-insights-connection

# Azure AD Authentication
AZURE_CLIENT_ID=your-client-id
AZURE_TENANT_ID=your-tenant-id
```

## Testing

```bash
# API tests
cd apps/api
uv run pytest

# UI tests
cd apps/ui
npm test

# Integration tests
npm run test:integration
```

## Production Deployment

```bash
# Provision infrastructure
azd provision

# Deploy all services
azd deploy

# Monitor deployment
azd monitor --logs
```

## Troubleshooting

### Container build fails

```bash
# Check Docker daemon
docker info

# Clean build cache
docker builder prune

# Rebuild with no cache
docker build --no-cache -t datalance-api -f apps/api/Dockerfile .
```

### uv sync fails

```bash
# Clear cache
uv cache clean

# Reinstall
rm -rf .venv
uv sync
```

### Azure deployment fails

```bash
# Check authentication
azd auth login
az account show

# View deployment logs
azd deploy --debug
```

## Resources

- [Azure Developer CLI Docs](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Azure Functions Python](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
