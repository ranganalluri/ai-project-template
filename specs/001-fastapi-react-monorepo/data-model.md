# Data Model & Architecture - Agentic AI Monorepo

**Version**: 1.0.0  
**Status**: Phase 1 - Design & Contracts  
**Date**: 2025-12-16

---

## 1. Project Structure Overview

### Folder Architecture
```
agentic-ai/                      # Root monorepo
├── apps/                        # Application services (3-service architecture)
│   ├── ui/                      # React 18 + Vite + TypeScript frontend
│   ├── api/                     # FastAPI backend + OpenAI integration
│   ├── functions/               # Azure Functions v2 (background jobs)
│   └── common/                  # Shared Python utilities & models
├── infra/                       # Infrastructure as Code (Bicep templates)
├── .github/                     # GitHub workflows & configuration
├── .specify/                    # Specification & planning system
├── .devcontainer/               # Development container configuration
├── docker-compose.yml           # Local dev environment (Docker Compose)
├── uv.lock                      # Python unified lock file (workspace-level)
├── pyproject.toml               # Python root workspace configuration
├── package.json                 # npm root workspace configuration
├── pnpm-workspace.yaml          # (Optional) pnpm workspace config
└── README.md                    # Project documentation
```

### Workspace Member Relationships

```
Root Workspace (uv)
├── apps/api (Python package: datalance-api)
│   └── Depends on: apps/common
├── apps/functions (Python package: datalance-functions)
│   └── Depends on: apps/common
└── apps/common (Python package: datalance-common)
    └── No internal dependencies

Root Workspace (npm)
├── apps/ui (Node package: @datalance/ui)
│   └── Depends on: (no internal deps, communicates via HTTP)
└── Other workspace members: None
```

---

## 2. Service Definitions & Entity Models

### 2.1 UI Service (`apps/ui/`)

**Purpose**: React frontend for user interaction  
**Technology**: React 18 + Vite + TypeScript 5.0+ + TailwindCSS  
**Dependencies**: FastAPI backend (HTTP calls to `http://api:8000/api`)

**Folder Structure**:
```
apps/ui/
├── src/
│   ├── components/            # Reusable React components
│   │   ├── common/            # Shared UI components (Button, Modal, etc.)
│   │   ├── features/          # Feature-specific components
│   │   │   ├── agents/        # Agent list, detail views
│   │   │   ├── content/       # Content management UI
│   │   │   └── catalog/       # Catalog browsing components
│   │   └── layout/            # Layout components (Header, Sidebar, etc.)
│   ├── pages/                 # Page-level components (routing)
│   ├── hooks/                 # Custom React hooks
│   ├── services/              # API client services
│   │   └── api-client.ts      # Axios/Fetch wrapper for /api/* endpoints
│   ├── store/                 # State management (Zustand/Redux)
│   ├── types/                 # TypeScript interfaces & types
│   ├── utils/                 # Utility functions
│   └── App.tsx                # Root component
├── public/                    # Static assets
├── vite.config.ts             # Vite configuration
├── tsconfig.json              # TypeScript configuration
├── package.json               # npm package definition
├── Dockerfile                 # Multi-stage build for production
└── .env.example               # Environment variables template
```

**Entity Models** (TypeScript):
```typescript
// Shared domain models (imported from API types)
interface Agent {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive';
  createdAt: ISO8601Date;
  updatedAt: ISO8601Date;
}

interface ContentItem {
  id: string;
  agentId: string;
  title: string;
  body: string;
  category: string;
  metadata: Record<string, unknown>;
  createdAt: ISO8601Date;
}

interface CatalogEntry {
  id: string;
  name: string;
  description: string;
  tags: string[];
  rating: number; // 0-5
  version: string;
}
```

**API Client Pattern**:
```typescript
// src/services/api-client.ts
const API_BASE = process.env.VITE_API_URL || 'http://localhost:8000/api';

export const apiClient = {
  async getAgents(): Promise<Agent[]> {
    const res = await fetch(`${API_BASE}/agents`);
    return res.json();
  },
  async getAgent(id: string): Promise<Agent> {
    const res = await fetch(`${API_BASE}/agents/${id}`);
    return res.json();
  },
  // ... other endpoints
};
```

---

### 2.2 API Service (`apps/api/`)

**Purpose**: FastAPI backend serving REST endpoints + OpenAI integration  
**Technology**: FastAPI + Pydantic + uvicorn + OpenAI SDK  
**Dependencies**: apps/common (shared models), OpenAI API (external)

**Folder Structure**:
```
apps/api/
├── src/
│   ├── main.py                # FastAPI app initialization
│   ├── config.py              # Configuration & environment variables
│   ├── middleware.py          # CORS, logging, error handling
│   ├── routes/                # API route modules (APIRouter pattern)
│   │   ├── __init__.py
│   │   ├── agents.py          # /api/agents endpoints
│   │   ├── content.py         # /api/content endpoints
│   │   ├── catalog.py         # /api/catalog endpoints
│   │   ├── ai.py              # /api/ai/* OpenAI integration
│   │   └── health.py          # /api/health status endpoint
│   ├── models/                # Pydantic data models
│   │   ├── __init__.py
│   │   ├── agent.py           # Agent model definitions
│   │   ├── content.py         # Content model definitions
│   │   └── responses.py       # Shared response models
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── agent_service.py   # Agent management logic
│   │   ├── content_service.py # Content processing logic
│   │   ├── ai_service.py      # OpenAI integration (chat, embeddings)
│   │   └── catalog_service.py # Catalog operations
│   ├── dependencies.py        # FastAPI dependency injection
│   ├── exceptions.py          # Custom exception classes
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       └── validators.py      # Custom validators
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── conftest.py            # Pytest configuration
├── pyproject.toml             # Python package definition
├── Dockerfile                 # Multi-stage build
├── .env.example               # Environment template
└── README.md                  # API documentation
```

**Core Data Models** (Pydantic):
```python
# apps/api/src/api/models/agent.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., max_length=2000)
    status: str = Field(default='active', pattern='^(active|inactive)$')

class Agent(AgentBase):
    id: str
    created_at: datetime
    updated_at: datetime

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
```

**OpenAI Service Pattern**:
```python
# apps/api/src/api/services/ai_service.py
from openai import AsyncOpenAI
from typing import Optional

class AIService:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def chat_completion(
        self, 
        messages: list[dict],
        model: str = "gpt-4",
        temperature: float = 0.7
    ) -> str:
        """Call OpenAI chat completion API"""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    
    async def create_embedding(self, text: str) -> list[float]:
        """Create vector embedding from text"""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
```

**APIRouter Pattern** (modular routes):
```python
# apps/api/src/api/routes/agents.py
from fastapi import APIRouter, HTTPException, Depends
from ..models.agent import Agent, AgentCreate
from ..services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/", response_model=list[Agent])
async def list_agents(service: AgentService = Depends()):
    """GET /api/agents - List all agents"""
    return await service.list_agents()

@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, service: AgentService = Depends()):
    """GET /api/agents/{agent_id} - Get agent by ID"""
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("/", response_model=Agent)
async def create_agent(data: AgentCreate, service: AgentService = Depends()):
    """POST /api/agents - Create new agent"""
    return await service.create_agent(data)
```

---

### 2.3 Functions Service (`apps/functions/`)

**Purpose**: Azure Functions for background processing (async jobs)  
**Technology**: Azure Functions v2 (Python) + Durable Functions (optional)  
**Dependencies**: apps/common (shared models), Azure services (Service Bus, Cosmos DB)

**Folder Structure**:
```
apps/functions/
├── src/
│   ├── functions/
│   │   ├── __init__.py
│   │   ├── content_processor.py    # Timer trigger: process content batches
│   │   ├── agent_cleanup.py        # Timer trigger: cleanup stale agents
│   │   ├── queue_handler.py        # Queue trigger: handle async jobs from API
│   │   └── webhook_handler.py      # HTTP trigger: receive webhooks
│   ├── models/
│   │   ├── __init__.py
│   │   └── job.py                  # Job queue message models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── processor.py            # Business logic for processing
│   │   └── storage.py              # Cosmos DB operations
│   └── utils/
│       ├── __init__.py
│       └── logging.py              # Azure Application Insights logging
├── tests/
│   ├── unit/
│   └── conftest.py
├── pyproject.toml
├── Dockerfile
├── function_app.py              # Azure Functions entrypoint
├── .env.example
└── README.md
```

**Function Definitions**:
```python
# apps/functions/src/function_app.py
import azure.functions as func
from azure.identity import DefaultAzureCredential
from src.functions.content_processor import process_content
from src.functions.queue_handler import handle_queue_message

app = func.FunctionApp()

# Timer trigger: Run every 5 minutes
@app.function_name("ContentProcessor")
@app.schedule_trigger(arg_name="mytimer", schedule="0 */5 * * * *")
def content_processor(mytimer: func.TimerRequest):
    """Background job: Process accumulated content items"""
    process_content()

# Queue trigger: Azure Service Bus
@app.function_name("QueueHandler")
@app.queue_trigger(arg_name="msg", queue_name="datalance-jobs")
def queue_handler(msg: func.InputStream):
    """Handle async job messages from API"""
    handle_queue_message(msg.getvalue())

# HTTP trigger: Webhook endpoint
@app.function_name("WebhookReceiver")
@app.route(route="webhooks/openai", methods=["POST"])
def webhook_receiver(req: func.HttpRequest) -> func.HttpResponse:
    """Receive webhooks (e.g., OpenAI batch completion notifications)"""
    # Process webhook payload
    return func.HttpResponse("OK", status_code=200)
```

---

### 2.4 Common Package (`apps/common/`)

**Purpose**: Shared Python code (models, utilities, validators)  
**Technology**: Pure Python package (no framework dependencies)  
**Dependencies**: Pydantic, python-dotenv

**Folder Structure**:
```
apps/common/
├── src/
│   ├── datalance_common/
│   │   ├── __init__.py
│   │   ├── models.py            # Shared Pydantic models
│   │   ├── enums.py             # Shared enumerations
│   │   ├── validators.py        # Shared validation logic
│   │   ├── exceptions.py        # Shared exception classes
│   │   ├── config.py            # Shared config classes
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logging.py       # Shared logging setup
│   │       ├── timestamps.py    # DateTime utilities
│   │       └── serialization.py # JSON serialization helpers
├── tests/
├── pyproject.toml
└── README.md
```

**Shared Models Pattern**:
```python
# apps/common/src/datalance_common/models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROCESSING = "processing"

class BaseEntity(BaseModel):
    """Base model for all entities with audit fields"""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

class Agent(BaseEntity):
    name: str = Field(..., min_length=1, max_length=255)
    description: str
    status: Status = Status.ACTIVE
    configuration: dict = {}

class JobMessage(BaseModel):
    """Message model for async queue processing"""
    job_id: str
    job_type: str
    payload: dict
    retry_count: int = 0
    max_retries: int = 3
```

---

## 3. Data Flow Diagrams

### 3.1 Architecture Flow (UI → API → OpenAI)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER BROWSER                              │
│  (React 18 + TypeScript + TailwindCSS)                      │
│  [apps/ui]                                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST calls
                       │ GET /api/agents
                       │ POST /api/content
                       │ POST /api/ai/chat
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  FASTAPI BACKEND                             │
│  (FastAPI + Pydantic + uvicorn)                             │
│  [apps/api] - Port 8000                                      │
│                                                              │
│  Routes:                                                     │
│  ├─ /api/agents (CRUD)                                      │
│  ├─ /api/content (CRUD)                                     │
│  ├─ /api/catalog (Read)                                     │
│  └─ /api/ai/* (OpenAI integration)                          │
│                                                              │
│  Dependencies: [apps/common] (shared models)                │
└──────────────────────┬──────────────────────────────────────┘
         │                                      │
         │ Queue Job Messages                   │ OpenAI API calls
         │ (async background work)              │ (chat, embeddings)
         ▼                                      ▼
    ┌──────────────┐               ┌─────────────────────┐
    │   FUNCTIONS  │               │  OPENAI API         │
    │ (Azure Fns)  │               │  gpt-4, embeddings  │
    │  [apps/fn]   │               │  (external service) │
    │ Background   │               └─────────────────────┘
    │   jobs       │
    └──────────────┘
         │
         ▼
    ┌──────────────────────────────────────────────────────┐
    │          DATA PERSISTENCE LAYER                      │
    │  Azure Cosmos DB (NoSQL)                             │
    │  - Collections: agents, content, catalog, jobs       │
    └──────────────────────────────────────────────────────┘
```

### 3.2 OpenAI Integration Detail

```
API Handler
    │
    ├─ /api/ai/chat (POST)
    │  ├─ Input: { messages: [], model: "gpt-4", ... }
    │  ├─ AIService.chat_completion()
    │  └─ Response: { content: "...", tokens: 123, ... }
    │
    ├─ /api/ai/embeddings (POST)
    │  ├─ Input: { text: "..." }
    │  ├─ AIService.create_embedding()
    │  └─ Response: { embedding: [...], model: "text-embedding-3-small" }
    │
    └─ /api/ai/batch (POST)
       ├─ Input: { tasks: [...] }
       ├─ Queue job to Functions
       └─ Return: { job_id: "...", status: "queued" }
           │
           └─→ Functions async processes batch
               └─→ Stores results in Cosmos DB
```

### 3.3 Background Processing Flow

```
API Service
    │
    └─ POST /api/jobs → Queue Message
       │
       └─→ Azure Service Bus Queue
          │
          └─→ Azure Functions (Queue Trigger)
             │
             ├─ Retrieve job from queue
             ├─ Process (call AI, compute, etc.)
             ├─ Store results → Cosmos DB
             └─ Update job status
                │
                └─→ Optional: Send webhook back to API
                    └─→ UI polling /api/jobs/{job_id} → gets result
```

---

## 4. Dependencies & Relationships

### 4.1 Python Workspace Dependencies (uv)

```
Root Workspace
├── Workspace Members:
│   ├── datalance-api (apps/api/)
│   │   ├── Depends: datalance-common ✓
│   │   ├── External: FastAPI, Pydantic, OpenAI, uvicorn
│   │   └── Optional: SQLAlchemy (if using relational DB)
│   │
│   ├── datalance-functions (apps/functions/)
│   │   ├── Depends: datalance-common ✓
│   │   ├── External: azure-functions, azure-storage-queue, azure-cosmos
│   │   └── Optional: durable-functions
│   │
│   └── datalance-common (apps/common/)
│       ├── Depends: None (internal)
│       └── External: Pydantic, python-dotenv
```

### 4.2 npm Workspace Dependencies

```
Root Workspace
├── Workspace Members:
│   └── @datalance/ui (apps/ui/)
│       ├── Devs: Vite, TypeScript, ESLint
│       ├── Runtime: React, React Router, TailwindCSS
│       ├── HTTP: Axios (or Fetch API)
│       └── Testing: Vitest, Testing Library
```

### 4.3 Service Communication

| From | To | Method | Protocol | Examples |
|------|-----|--------|----------|----------|
| UI | API | HTTP/REST | REST JSON | GET /api/agents, POST /api/content |
| API | OpenAI | HTTPS | REST JSON | POST https://api.openai.com/v1/chat/completions |
| API | Cosmos DB | SDK | Native | Query, Insert, Update documents |
| Functions | Cosmos DB | SDK | Native | Read/write job results |
| Functions | Service Bus | SDK | Native | Receive queued messages |
| API | Service Bus | SDK | Native | Queue background jobs |

---

## 5. Configuration & Environment Variables

### 5.1 Environment Variable Hierarchy

**Root `.env` (development defaults)**:
```bash
# Application
APP_NAME=datalance-ai
ENVIRONMENT=development

# API Server
API_PORT=8000
API_WORKERS=4
API_LOG_LEVEL=info

# UI
VITE_API_URL=http://localhost:8000/api
VITE_LOG_LEVEL=debug

# OpenAI
OPENAI_API_KEY=${OPENAI_API_KEY}  # Set via secret
OPENAI_ORG_ID=
OPENAI_DEFAULT_MODEL=gpt-4

# Azure
AZURE_COSMOSDB_ENDPOINT=https://localhost:8081
AZURE_COSMOSDB_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqwm+DJgzJ0EI3PU/DmVVCgdlKQslAL0z4Y==
AZURE_SERVICE_BUS_CONNECTION_STRING=
AZURE_STORAGE_ACCOUNT=
AZURE_CONTAINER_REGISTRY=

# Database
DATABASE_NAME=datalance
```

**Service-specific overrides** (`apps/api/.env`):
```bash
# Inherits from root, overrides:
PYTHONPATH=/app/src:/app/../common/src
PYDANTIC_ENV_FILE=.env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 6. Validation Rules & Constraints

### 6.1 Agent Entity Constraints
- **Name**: 1-255 characters, required
- **Description**: Max 2000 characters
- **Status**: One of [active, inactive, processing]
- **Configuration**: Valid JSON object
- **Created/Updated timestamps**: ISO 8601 format

### 6.2 Content Entity Constraints
- **Title**: 1-500 characters, required
- **Body**: Max 10,000 characters
- **Category**: Predefined categories only
- **Agent ID**: Must reference existing agent
- **Metadata**: Max 10 KB JSON

### 6.3 API Rate Limiting
- **Per IP**: 100 requests/minute
- **Per user**: 1000 requests/hour
- **OpenAI API calls**: Throttled per pricing tier
- **Response times**: Target <500ms for 95th percentile

---

## 7. State Transitions

### 7.1 Agent Lifecycle
```
[inactive] ──create──→ [active] ──disable──→ [inactive]
                         │
                         ├──→ [processing] (during batch operations)
                         └──→ [inactive] (cleanup)
```

### 7.2 Job Processing Lifecycle
```
[queued] → [processing] → [completed] ✓
    ↓          ↓
[failed] ← [error]
    │
    └─→ [retrying] (if retry_count < max_retries)
```

---

## 8. Design Decisions Summary

| Decision | Rationale | Implementation |
|----------|-----------|-----------------|
| uv workspace | Single lock file, fast resolution, monorepo-native | Root uv.lock, pyproject.toml with [tool.uv.workspace] |
| npm workspaces | Native npm 7+ support, automatic symlinking | Root package.json with workspaces array |
| FastAPI + APIRouter | Modular routing, async-first, OpenAPI auto-docs | Separate route files, dependency injection |
| Pydantic models | Type-safe, validation, JSON schema generation | Shared models in apps/common |
| Azure Cosmos DB | Flexible schema, global distribution, serverless | NoSQL collections for each domain entity |
| Azure Functions | Serverless background jobs, cost-effective | Queue triggers, timer triggers for batch work |
| OpenAI Integration | Industry-standard LLM, multiple model options | AsyncOpenAI client, chat/embedding endpoints |
| Docker Compose (local) | Replicate prod services locally | Services: api, ui, functions, azurite, service-bus-emulator |
| Bicep infrastructure | Infrastructure-as-code, Azure-native | Templates in infra/ folder, deployed via azd |

---

## 9. Next Steps (Phase 1 Continuation)

1. **Contract Generation**: Create OpenAPI spec for API endpoints
2. **Configuration Templates**: Generate sample pyproject.toml, package.json, Dockerfiles
3. **Quickstart Guide**: Step-by-step setup instructions
4. **Agent Context Update**: Register technologies with agent framework

**Phase 1 Output Files**:
- ✅ `data-model.md` (this file)
- 📝 `contracts/openapi.yaml`
- 📝 `contracts/pyproject.toml.template`
- 📝 `contracts/package.json.template`
- 📝 `contracts/Dockerfile.api`
- 📝 `contracts/Dockerfile.ui`
- 📝 `contracts/Dockerfile.functions`
- 📝 `quickstart.md`
