# Quick Start Guide

## Prerequisites

- Python 3.12+
- Node.js 18+
- `uv` (Python package manager)
- Azure CLI (`az login` for local auth)

## Setup (5 minutes)

### 1. Install Dependencies

```bash
# Python dependencies
cd apps/api
uv sync

# Node dependencies (from root)
npm ci

# Build UI library
cd apps/ui-lib
npm run build
```

### 2. Configure Environment

Create `.env` file in project root:

```bash
FOUNDRY_PROJECT_CONNECTION_STRING=your_connection_string_here
FOUNDRY_DEPLOYMENT_NAME=gpt-4
```

Or set environment variables:

```bash
export FOUNDRY_PROJECT_CONNECTION_STRING=your_connection_string_here
export FOUNDRY_DEPLOYMENT_NAME=gpt-4
```

### 3. Authenticate with Azure

```bash
az login
```

### 4. Run Application

**Terminal 1 - Backend:**
```bash
cd apps/api
uv run uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd apps/ui
npm run dev
```

### 5. Open Application

- Navigate to: http://localhost:5173
- Go to `/chat` page
- Start chatting!

## Test the Features

1. **Basic Chat**: Type a message and press Enter
2. **File Upload**: Click 📎 button, upload a file
3. **Tool Call**: Ask "What time is it?" - modal will appear for approval
4. **Stop**: Click "Stop" button during streaming
5. **Settings**: Go to `/settings` to configure API URL

## Troubleshooting

**Foundry Connection Error:**
- Verify `FOUNDRY_PROJECT_CONNECTION_STRING` is set
- Run `az login` to authenticate
- Check health endpoint: `curl http://localhost:8000/api/health`

**SSE Not Working:**
- Check browser console for errors
- Verify CORS is configured (should allow localhost:5173)
- Check network tab for SSE connection

**File Upload Fails:**
- Ensure `./data/uploads/` directory exists
- Check file size limits
- Verify backend is running

## Next Steps

- Read `CHAT_APP_README.md` for detailed documentation
- Read `IMPLEMENTATION_SUMMARY.md` for architecture overview
- Customize tools in `apps/api/src/api/services/tool_registry.py`
- Add authentication for production use

