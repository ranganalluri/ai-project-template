# Azure Functions - Python v2 Isolated Worker

Azure Functions application using Python v2 programming model with isolated worker process.

## Features

- **Isolated Worker Process**: Better performance and isolation
- **Decorator-based Programming**: Clean, modern Python syntax
- **Multiple HTTP Triggers**: Examples of different endpoint patterns
- **Health Monitoring**: Built-in health check endpoint

## Local Development

### Prerequisites

- Python 3.12+
- Azure Functions Core Tools v4
- uv (for dependency management)

### Setup

```powershell
# Install dependencies
uv sync

# Run functions locally
uv run func start
```

### Available Endpoints

Once running, the following endpoints are available:

- `GET/POST http://localhost:7071/api/http_trigger` - Main HTTP trigger with name parameter
- `GET http://localhost:7071/api/health` - Health check endpoint
- `POST http://localhost:7071/api/echo` - Echo endpoint that returns posted JSON

### Testing

```powershell
# Test HTTP trigger
curl "http://localhost:7071/api/http_trigger?name=Azure"

# Test with JSON body
curl -X POST http://localhost:7071/api/http_trigger `
  -H "Content-Type: application/json" `
  -d '{"name":"Azure"}'

# Test health endpoint
curl http://localhost:7071/api/health

# Test echo endpoint
curl -X POST http://localhost:7071/api/echo `
  -H "Content-Type: application/json" `
  -d '{"test":"data"}'
```

## Project Structure

```
apps/functions/
├── function_app.py          # Main function app with all triggers
├── host.json               # Function host configuration
├── local.settings.json     # Local development settings
├── pyproject.toml         # Python dependencies
└── src/
    └── functions/         # Additional function modules (if needed)
```

## Configuration

### host.json

Configures the Functions host runtime with:
- Logging settings
- Application Insights sampling
- Function timeout (5 minutes)
- Health monitoring

### local.settings.json

Local development settings:
- `FUNCTIONS_WORKER_RUNTIME`: Set to "python"
- `PYTHON_ISOLATE_WORKER_DEPENDENCIES`: Enables isolated worker
- `PYTHON_ENABLE_WORKER_EXTENSIONS`: Enables worker extensions
- `AzureWebJobsFeatureFlags`: EnableWorkerIndexing for automatic function discovery

## Deployment

```powershell
# Deploy to Azure
func azure functionapp publish <function-app-name>
```

## Learn More

- [Azure Functions Python developer guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Python v2 programming model](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Capplication-level&pivots=python-mode-decorators)
