# Agentic AI - Quickstart Guide

**Version**: 1.0.0  
**Last Updated**: 2025-12-16

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Running Locally](#running-locally)
4. [Development Workflow](#development-workflow)
5. [API Documentation](#api-documentation)
6. [Deployment to Azure](#deployment-to-azure)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python**: 3.12 or higher
- **Node.js**: 18.0.0 or higher
- **npm**: 9.0.0 or higher
- **Docker**: Latest version (for containerized development)
- **Docker Compose**: Latest version (for local environment)
- **Azure CLI**: Latest version (for cloud deployment)
- **Azure Developer CLI (azd)**: Latest version (recommended)

### Recommended

- **Visual Studio Code** with extensions:
  - Python
  - Azure Account
  - Docker
  - REST Client (for API testing)
- **OpenAI API Key**: For AI integration features
- **Azure Subscription**: For cloud deployment

### Install Tools

**macOS (Homebrew)**:
```bash
brew install python@3.12 node docker azure-cli
brew install azure-cli-extensions  # Includes azd
```

**Windows (Chocolatey)**:
```powershell
choco install python nodejs docker azure-cli
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get update
sudo apt-get install python3.12 nodejs docker.io
# Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/datalance/ai_project.git
cd ai_project
```

### 2. Set Environment Variables

Create a `.env` file in the repository root:

```bash
# Application
APP_NAME=datalance-ai
ENVIRONMENT=development

# OpenAI Integration
OPENAI_API_KEY=sk-your-api-key-here

# Azure Resources (local emulators)
AZURE_COSMOSDB_ENDPOINT=https://localhost:8081
AZURE_COSMOSDB_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqwm+DJgzJ0EI3PU/DmVVCgdlKQslAL0z4Y==
AZURE_SERVICE_BUS_CONNECTION_STRING=Endpoint=sb://localhost/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=SAS_KEY_HERE

# API
API_PORT=8000
VITE_API_URL=http://localhost:8000/api
```

> **Note**: The Cosmos DB and Service Bus keys above are emulator defaults. For production, use actual Azure credentials.

### 3. Install Python Dependencies

Using **uv** (unified workspace):

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Synchronize all Python workspace members
uv sync
```

Or using **pip + venv**:

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate  # Windows

pip install -e ".[dev]"
pip install -e "apps/common[dev]"
pip install -e "apps/api[dev]"
pip install -e "apps/functions[dev]"
```

### 4. Install Node Dependencies

```bash
npm ci  # Installs exact versions from package-lock.json
```

### 5. Verify Installation

```bash
# Check Python workspace
uv venv --python 3.12
python --version  # Should be 3.12.x

# Check Node workspace
npm --version    # Should be 9.x or higher
node --version   # Should be 18.x or higher

# Check Docker
docker --version
docker-compose --version
```

---

## Running Locally

### Option A: Docker Compose (Recommended for Full Stack)

This approach runs all services in containers with local emulators.

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Services will be available at:**
- **UI**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Cosmos DB Emulator**: https://localhost:8081

### Option B: Native Development (Faster Iteration)

Run services directly on your machine with hot reload.

**Terminal 1 - Start all services in parallel:**
```bash
npm run dev
```

This runs:
- React UI dev server (port 5173)
- FastAPI backend (port 8000)
- Local emulators (Azurite, Cosmos DB)

**Or run individually:**

**Terminal 1 - React UI:**
```bash
npm run dev --workspace=@datalance/ui
# Available at http://localhost:5173
```

**Terminal 2 - FastAPI Backend:**
```bash
cd apps/api
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
# Available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Terminal 3 - Azure Emulators:**
```bash
docker-compose up cosmos azurite  # Cosmos DB + Storage emulator
```

---

## Development Workflow

### Creating a New Feature

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes** to UI, API, or both:
   - **Frontend**: `apps/ui/src/**/*`
   - **Backend**: `apps/api/src/api/**/*`
   - **Shared Code**: `apps/common/src/**/*`

3. **Test locally**:
   ```bash
   npm run test                    # Run all tests
   uv run pytest apps/api/tests   # Python unit tests
   npm run test --workspace=@datalance/ui  # React tests
   ```

4. **Format and lint**:
   ```bash
   npm run format && npm run lint
   uv run black . && uv run ruff check .
   ```

5. **Type checking**:
   ```bash
   npm run type-check
   uv run mypy apps/
   ```

6. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: add my feature"
   git push origin feature/my-feature
   ```

### Adding a New API Endpoint

1. **Define Pydantic model** in `apps/api/src/api/models/`:
   ```python
   # apps/api/src/api/models/mymodel.py
   from pydantic import BaseModel
   
   class MyModel(BaseModel):
       name: str
       value: int
   ```

2. **Create service logic** in `apps/api/src/api/services/`:
   ```python
   # apps/api/src/api/services/my_service.py
   class MyService:
       async def get_item(self, id: str) -> MyModel:
           # Business logic here
           pass
   ```

3. **Create route** in `apps/api/src/api/routes/`:
   ```python
   # apps/api/src/api/routes/myroute.py
   from fastapi import APIRouter
   from ..models.mymodel import MyModel
   from ..services.my_service import MyService
   
   router = APIRouter(prefix="/myroute")
   
   @router.get("/{id}", response_model=MyModel)
   async def get_item(id: str, service: MyService = Depends()):
       return await service.get_item(id)
   ```

4. **Register route** in `apps/api/src/api/main.py`:
   ```python
   from .routes.myroute import router as myroute_router
   
   app.include_router(myroute_router, prefix="/api", tags=["myroute"])
   ```

5. **Test in API docs**: http://localhost:8000/docs

### Calling OpenAI API

**Example: Chat Completion**

```python
# apps/api/src/api/routes/ai.py
from openai import AsyncOpenAI

@router.post("/api/ai/chat")
async def chat_completion(request: ChatCompletionRequest):
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=request.messages,
        temperature=request.temperature
    )
    
    return {
        "content": response.choices[0].message.content,
        "tokens_used": {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.total_tokens
        }
    }
```

### Queuing Background Jobs (Functions)

**Queue a job from API:**

```python
@router.post("/api/jobs/process")
async def queue_job(request: JobRequest):
    service_bus_client = ServiceBusClient.from_connection_string(
        settings.service_bus_connection_string
    )
    
    sender = service_bus_client.get_queue_sender("datalance-jobs")
    
    message = ServiceBusMessage(
        body=json.dumps(request.dict()),
        subject="content_processing"
    )
    
    await sender.send_messages(message)
    
    return {"job_id": "job-123", "status": "queued"}
```

**Process in Azure Functions:**

```python
# apps/functions/src/functions/queue_handler.py
import azure.functions as func
import json

@app.queue_trigger(arg_name="msg", queue_name="datalance-jobs")
def queue_handler(msg: func.InputStream):
    job_data = json.loads(msg.getvalue())
    
    # Process the job
    # ...
    
    # Store results in Cosmos DB
    # ...
```

---

## API Documentation

### Interactive Docs

When the API is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Example Requests

**List all agents:**
```bash
curl -X GET http://localhost:8000/api/agents
```

**Create a new agent:**
```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Data Analyzer",
    "description": "Analyzes datasets",
    "status": "active"
  }'
```

**Chat with OpenAI:**
```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "model": "gpt-4"
  }'
```

**Create embedding:**
```bash
curl -X POST http://localhost:8000/api/ai/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The quick brown fox"
  }'
```

### Full API Reference

See [contracts/openapi.yaml](./contracts/openapi.yaml) for complete OpenAPI specification.

---

## Deployment to Azure

### Prerequisites

```bash
# Login to Azure
az login

# Install Azure Developer CLI
curl -LsSf https://aka.ms/install-azd.sh | bash

# Verify
azd version
```

### Deploy with Azure Developer CLI

```bash
# Initialize (one-time)
azd init

# Set environment variables
export OPENAI_API_KEY=sk-your-key-here

# Deploy to Azure
azd up

# This will:
# 1. Provision Azure resources (Container Apps, Cosmos DB, Service Bus, etc.)
# 2. Build and push container images
# 3. Deploy services
# 4. Output URLs for accessing the application
```

### Manual Deployment Steps

**1. Build container images:**
```bash
# Build UI
docker build -t datalance-ui:latest -f Dockerfile.ui .

# Build API
docker build -t datalance-api:latest -f Dockerfile.api .

# Build Functions
docker build -t datalance-functions:latest -f Dockerfile.functions .
```

**2. Push to Azure Container Registry:**
```bash
# Login to ACR
az acr login --name <registry-name>

# Tag images
docker tag datalance-ui:latest <registry>.azurecr.io/datalance-ui:latest
docker tag datalance-api:latest <registry>.azurecr.io/datalance-api:latest
docker tag datalance-functions:latest <registry>.azurecr.io/datalance-functions:latest

# Push
docker push <registry>.azurecr.io/datalance-ui:latest
docker push <registry>.azurecr.io/datalance-api:latest
docker push <registry>.azurecr.io/datalance-functions:latest
```

**3. Deploy to Azure Container Apps:**
```bash
# Deploy UI
az containerapp create \
  --name datalance-ui \
  --resource-group my-rg \
  --image <registry>.azurecr.io/datalance-ui:latest \
  --target-port 3000

# Deploy API
az containerapp create \
  --name datalance-api \
  --resource-group my-rg \
  --image <registry>.azurecr.io/datalance-api:latest \
  --target-port 8000 \
  --env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

**4. Deploy Azure Functions:**
```bash
func azure functionapp publish datalance-functions
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port
lsof -i :8000              # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>              # macOS/Linux
taskkill /PID <PID> /F     # Windows
```

#### Cosmos DB Emulator Not Starting

```bash
# Restart Docker
docker restart datalance-cosmos

# Check logs
docker logs datalance-cosmos

# If using Windows, may need WSL2 enabled
```

#### Python Module Import Errors

```bash
# Ensure uv workspace is synchronized
uv sync

# Or manually install with correct path
export PYTHONPATH="${PWD}/apps/api/src:${PWD}/apps/common/src:$PYTHONPATH"
python -c "import datalance_common; print('OK')"
```

#### npm Workspace Not Resolving

```bash
# Clean and reinstall
npm ci

# Verify workspace setup
npm ls

# Link workspaces manually if needed
npm link @datalance/ui
```

#### CORS Issues When Calling API

Ensure API CORS settings in `apps/api/src/api/config.py`:
```python
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Production UI
]
```

#### OpenAI API Errors

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Check rate limiting
# Ensure API key has sufficient credits
# See OpenAI console: https://platform.openai.com/account/usage
```

### Getting Help

1. **Check logs**:
   ```bash
   docker-compose logs api     # API service logs
   docker-compose logs ui      # UI service logs
   docker logs datalance-cosmos  # Cosmos DB logs
   ```

2. **Verify environment variables**:
   ```bash
   cat .env
   env | grep OPENAI
   env | grep AZURE
   ```

3. **Test API endpoints**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health check: `curl http://localhost:8000/api/health`

4. **Check application status**:
   ```bash
   # Python workspace health
   uv venv --python 3.12
   
   # Node workspace health
   npm ls --depth=0
   
   # Docker status
   docker ps
   docker-compose ps
   ```

---

## Next Steps

- 📚 Read [data-model.md](./data-model.md) for detailed architecture overview
- 📖 See [contracts/openapi.yaml](./contracts/openapi.yaml) for complete API specification
- 🚀 Follow [Implementation Plan](./plan.md) for next phases
- 🧪 Review [Research Findings](./research.md) for technical deep-dives

---

## Resources

- **Python Workspace (uv)**: https://docs.astral.sh/uv/
- **npm Workspaces**: https://docs.npmjs.com/cli/v9/using-npm/workspaces
- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **Azure Container Apps**: https://learn.microsoft.com/en-us/azure/container-apps/
- **Azure Cosmos DB**: https://learn.microsoft.com/en-us/azure/cosmos-db/
- **Azure Functions**: https://learn.microsoft.com/en-us/azure/azure-functions/
- **OpenAI API**: https://platform.openai.com/docs/api-reference

---

**Happy coding! 🚀**
