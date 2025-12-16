# Agentic AI - FastAPI + React Monorepo

**Version**: 0.1.0  
**Status**: Phase 1 & 2 Complete (Setup & Foundational), Phase 3 In Progress (US1 - Local Development)

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- uv (Python package manager)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/agentic-ai.git
cd agentic-ai

# Install Python dependencies
uv sync

# Install Node dependencies
npm ci

# Create local environment file
cp .env.example .env.local
# Edit .env.local with your OpenAI API key and Azure credentials
```

### Running Locally

#### Option 1: Using Docker Compose (Recommended for full stack)

```bash
# Copy environment file
cp .env.development .env

# Start all services (API, UI, emulators)
docker-compose up
```

Services will be available at:
- **UI**: http://localhost:5173 (Vite dev server)
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Cosmos DB Emulator**: http://localhost:8081 (Data Explorer)

#### Option 2: Native Development (Faster iteration)

```bash
# Terminal 1: Start API
cd apps/api
uv run uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Start UI
cd apps/ui
npm run dev

# Terminal 3 (Optional): Start Docker emulators only
docker-compose up cosmos azurite
```

## Project Structure

```
agentic-ai/
├── apps/
│   ├── api/                    # FastAPI backend service
│   │   ├── src/
│   │   │   ├── main.py        # FastAPI application entrypoint
│   │   │   ├── config.py      # Configuration management
│   │   │   ├── middleware.py  # CORS and logging middleware
│   │   │   ├── dependencies.py # Dependency injection
│   │   │   ├── routes/        # API route handlers
│   │   │   ├── models/        # Pydantic models
│   │   │   └── services/      # Business logic
│   │   ├── tests/             # API unit and integration tests
│   │   ├── pyproject.toml    # Python dependencies
│   │   └── Dockerfile        # Multi-stage Docker build
│   │
│   ├── ui/                     # React frontend application
│   │   ├── src/
│   │   │   ├── main.tsx       # React entry point
│   │   │   ├── App.tsx        # Root component with routing
│   │   │   ├── pages/         # Page components
│   │   │   ├── components/    # Reusable UI components
│   │   │   ├── services/      # API client and utilities
│   │   │   ├── hooks/         # Custom React hooks
│   │   │   ├── types/         # TypeScript type definitions
│   │   │   ├── styles/        # CSS and Tailwind styles
│   │   │   └── __tests__/     # Component tests
│   │   ├── public/            # Static assets
│   │   ├── index.html         # HTML template
│   │   ├── package.json       # Node dependencies
│   │   ├── vite.config.ts     # Vite configuration
│   │   ├── tsconfig.json      # TypeScript configuration
│   │   └── Dockerfile        # Multi-stage Docker build
│   │
│   ├── functions/              # Azure Functions for background jobs
│   │   ├── src/
│   │   │   ├── functions/     # Function handlers
│   │   │   └── models/        # Data models
│   │   ├── pyproject.toml    # Dependencies
│   │   └── Dockerfile        # Azure Functions Docker image
│   │
│   └── common/                 # Shared Python utilities
│       ├── src/agentic_common/ # Shared models and functions
│       └── pyproject.toml     # Dependencies
│
├── infra/                      # Infrastructure as Code (Bicep)
├── .github/
│   └── workflows/              # GitHub Actions CI/CD pipelines
├── .specify/                   # Specification and planning tools
├── .devcontainer/              # Dev container configuration
├── docker-compose.yml          # Local development orchestration
├── pyproject.toml             # Root Python workspace config
├── package.json               # Root npm workspace config
├── .env.example               # Environment variables template
├── .env.development           # Local development defaults
├── .gitignore                 # Git ignore rules
├── .dockerignore               # Docker ignore rules
└── README.md                  # This file
```

## Technology Stack

### Backend
- **FastAPI** 0.109+ - Modern Python web framework
- **uvicorn** - ASGI web server
- **Pydantic** 2.5+ - Data validation
- **OpenAI Python SDK** - LLM integration
- **Azure SDK for Python** - Azure services integration

### Frontend
- **React** 18.2+ - UI library
- **TypeScript** 5.3+ - Type-safe JavaScript
- **Vite** 5.0+ - Build tool and dev server
- **TailwindCSS** 3.4+ - Utility-first CSS framework

### Infrastructure
- **Azure Container Apps** - Container hosting
- **Azure Cosmos DB** - NoSQL database
- **Azure Service Bus** - Message queue for background jobs
- **Azure Functions** v2 - Serverless compute
- **Bicep** - Infrastructure as Code

### Development
- **uv** - Fast Python package manager
- **pytest** - Python testing framework
- **Vitest** - Lightning-fast unit test framework
- **ESLint** - TypeScript/JavaScript linting
- **Prettier** - Code formatter
- **Black** - Python code formatter

## Development Commands

### Python Commands

```bash
# Run API locally (with auto-reload)
uv run uvicorn apps.api.src.api.main:app --reload

# Run API tests
uv run pytest apps/api/tests -v

# Run with coverage
uv run pytest apps/api/tests --cov=apps/api/src/api

# Format Python code
uv run black apps/

# Lint Python code
uv run ruff check apps/

# Type checking
uv run mypy apps/api/src/api apps/functions/src apps/common/src
```

### Node.js/TypeScript Commands

```bash
# Install dependencies
npm ci

# Development server (React on 5173)
npm run dev

# Build for production
npm run build --workspace=@agentic/ui

# Run tests
npm test --workspace=@agentic/ui

# Lint TypeScript
npm run lint --workspace=@agentic/ui

# Format code
npm run format --workspace=@agentic/ui

# Type checking
npm run type-check --workspace=@agentic/ui
```

### Docker Commands

```bash
# Start local development environment with emulators
docker-compose up

# Run in detached mode
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f api
docker-compose logs -f ui

# Rebuild images
docker-compose build
```

## API Endpoints

### Health Check
- `GET /api/health` - Application health status

**Response**:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "message": "API is healthy"
}
```

### Agents (Future)
- `GET /api/agents` - List all agents
- `POST /api/agents` - Create new agent
- `GET /api/agents/{id}` - Get agent details
- `PUT /api/agents/{id}` - Update agent
- `DELETE /api/agents/{id}` - Delete agent

### Content (Future)
- `GET /api/content` - List content
- `POST /api/content` - Create content
- `GET /api/content/{id}` - Get content
- `PUT /api/content/{id}` - Update content
- `DELETE /api/content/{id}` - Delete content

### AI Services (Future)
- `POST /api/ai/chat` - Chat with OpenAI
- `POST /api/ai/embeddings` - Generate embeddings
- `POST /api/ai/batch` - Batch processing

Full API documentation available at `/docs` (Swagger UI) and `/redoc` (ReDoc)

## Environment Configuration

### Required Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# Azure Cosmos DB
AZURE_COSMOSDB_ENDPOINT=https://...
AZURE_COSMOSDB_KEY=...

# Azure Service Bus (for background jobs)
AZURE_SERVICEBUS_CONNECTION_STRING=Endpoint=sb://...

# Application
API_ENVIRONMENT=development
API_LOG_LEVEL=info
```

Copy `.env.example` to `.env` or `.env.local` and fill in your values.

## Testing

### Run All Tests

```bash
npm test
```

### Run Specific Test Suites

```bash
# Python API tests
uv run pytest apps/api/tests -v

# React component tests
npm test --workspace=@agentic/ui

# Watch mode
npm test --workspace=@agentic/ui -- --watch
```

### Coverage

```bash
# Generate coverage report
uv run pytest apps/api/tests --cov=apps/api/src/api --cov-report=html

# View report
open htmlcov/index.html
```

## CI/CD Pipelines

### GitHub Actions Workflows

1. **test.yml** - Runs on every commit to main/develop
   - Python tests (pytest)
   - JavaScript tests (vitest)
   - Coverage reporting

2. **lint.yml** - Code quality checks
   - Python: ruff, black, mypy
   - TypeScript: eslint, prettier

3. **build.yml** - Builds Docker images on push to main
   - Builds and pushes to GitHub Container Registry

## Deployment

### Local Docker Deployment

```bash
docker-compose up
```

### Azure Deployment

See [quickstart.md](specs/001-fastapi-react-monorepo/quickstart.md) for detailed deployment instructions using Azure Developer CLI.

```bash
# Initialize Azure resources
azd init

# Provision and deploy
azd up

# View logs
azd monitor --logs
```

## Documentation

- [Architecture & Data Model](specs/001-fastapi-react-monorepo/data-model.md)
- [Quick Start Guide](specs/001-fastapi-react-monorepo/quickstart.md)
- [API Specification](specs/001-fastapi-react-monorepo/contracts/openapi.yaml)
- [Research & Design Decisions](specs/001-fastapi-react-monorepo/research.md)
- [Feature Specification](specs/001-fastapi-react-monorepo/spec.md)
- [Implementation Plan](specs/001-fastapi-react-monorepo/plan.md)

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # API
lsof -i :5173  # UI

# Kill process
kill -9 <PID>
```

### Docker Container Issues

```bash
# Clean up containers and volumes
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# Check logs
docker-compose logs <service_name>
```

### Python Dependency Issues

```bash
# Clear cache and reinstall
rm -rf .venv uv.lock
uv sync
```

### Node Dependency Issues

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm ci
```

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Commit changes: `git commit -am 'Add my feature'`
3. Push to branch: `git push origin feature/my-feature`
4. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review GitHub Issues
3. Start a Discussion

## Team

Built with ❤️ by the Agentic AI team

---

**Current Status**: MVP phase - local development environment complete
**Next Steps**: Backend API endpoints, database integration, UI features
