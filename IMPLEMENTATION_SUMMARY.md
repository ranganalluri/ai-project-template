# Chat Application - Implementation Summary

## Folder Tree

```
ai-project-template/
├── apps/
│   ├── api/
│   │   ├── src/
│   │   │   └── api/
│   │   │       ├── main.py
│   │   │       ├── config.py                    # Updated with Foundry settings
│   │   │       ├── middleware.py
│   │   │       ├── routes/
│   │   │       │   ├── __init__.py              # Updated to include chat router
│   │   │       │   ├── health.py                # Updated with Foundry status
│   │   │       │   └── chat.py                  # NEW: Chat endpoints
│   │   │       ├── models/
│   │   │       │   ├── health.py                # Updated with foundry_configured
│   │   │       │   └── chat.py                  # NEW: Chat models
│   │   │       └── services/
│   │   │           ├── foundry_client.py         # NEW: Azure AI Foundry client
│   │   │           ├── chat_service.py          # NEW: Chat streaming service
│   │   │           ├── chat_store.py             # NEW: In-memory store
│   │   │           └── tool_registry.py          # NEW: Tool registry
│   │   └── pyproject.toml                       # Updated with azure-ai-projects
│   │
│   ├── ui/
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   │   ├── Chat.tsx                     # NEW: Main chat page
│   │   │   │   ├── Chat.css                     # NEW
│   │   │   │   ├── Settings.tsx                 # NEW: Settings page
│   │   │   │   └── Settings.css                 # NEW
│   │   │   └── App.tsx                          # Updated with /chat and /settings routes
│   │   └── package.json
│   │
│   └── ui-lib/
│       ├── src/
│       │   ├── components/
│       │   │   ├── ChatShell.tsx                 # NEW
│       │   │   ├── ChatShell.css                 # NEW
│       │   │   ├── MessageList.tsx               # NEW
│       │   │   ├── MessageList.css               # NEW
│       │   │   ├── MessageBubble.tsx             # NEW
│       │   │   ├── MessageBubble.css             # NEW
│       │   │   ├── Composer.tsx                  # NEW
│       │   │   ├── Composer.css                  # NEW
│       │   │   ├── FileUploadButton.tsx          # NEW
│       │   │   ├── FileUploadButton.css          # NEW
│       │   │   ├── ToolApprovalModal.tsx         # NEW
│       │   │   ├── ToolApprovalModal.css         # NEW
│       │   │   ├── Toast.tsx                     # NEW
│       │   │   ├── Toast.css                     # NEW
│       │   │   └── index.ts                      # Updated exports
│       │   ├── api/
│       │   │   ├── apiClient.ts                  # NEW: API client with SSE support
│       │   │   └── index.ts
│       │   ├── types/
│       │   │   ├── chat.types.ts                 # NEW: Chat TypeScript types
│       │   │   └── index.ts                      # Updated exports
│       │   └── index.ts                          # Updated exports
│       ├── tsup.config.ts                        # Updated to include CSS
│       └── package.json
│
├── data/
│   └── uploads/                                  # Created at runtime for file storage
│
├── CHAT_APP_README.md                            # Detailed documentation
└── IMPLEMENTATION_SUMMARY.md                     # This file
```

## Commands to Run

### Development Setup

```bash
# 1. Install Python dependencies
cd apps/api
uv sync

# 2. Install Node dependencies (from root)
npm ci

# 3. Build UI library
cd apps/ui-lib
npm run build

# 4. Start backend (Terminal 1)
cd apps/api
uv run uvicorn src.api.main:app --reload --port 8000

# 5. Start frontend (Terminal 2)
cd apps/ui
npm run dev
```

### Using Docker Compose

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your Foundry connection string

# Start all services
docker-compose up
```

## Key Files with Code

### Backend - Chat Route (`apps/api/src/api/routes/chat.py`)

Main endpoints:
- `POST /v1/files` - File upload
- `POST /v1/chat/stream` - SSE streaming chat
- `POST /v1/runs/{runId}/stop` - Stop run
- `POST /v1/runs/{runId}/toolcalls/{toolCallId}` - Approve/reject tool

### Backend - Chat Service (`apps/api/src/api/services/chat_service.py`)

Handles:
- SSE streaming with OpenAI
- Tool call detection and approval flow
- Message conversion to OpenAI format
- Tool result continuation

### Backend - Foundry Client (`apps/api/src/api/services/foundry_client.py`)

- Uses `azure-ai-projects` Python preview
- `AIProjectClient.from_connection_string()`
- `get_openai_client()` for authenticated OpenAI client
- `DefaultAzureCredential` for authentication

### Frontend - Chat Page (`apps/ui/src/pages/Chat.tsx`)

- Manages chat state (messages, files, streaming)
- Handles SSE events
- Shows tool approval modal
- File upload handling

### Frontend - API Client (`apps/ui-lib/src/api/apiClient.ts`)

- `startChatSSE()` - Opens SSE connection and yields events
- `stopRun()` - Stops current run
- `approveToolCall()` - Approves/rejects tool call
- `uploadFile()` - Uploads file
- `checkHealth()` - Health check with Foundry status

## SSE + Stop + Tool Approval Flow

### SSE Flow

1. **Client** calls `startChatSSE()` with messages
2. **Backend** creates run and starts OpenAI streaming
3. **Backend** yields SSE events:
   - `message_delta` - Text chunks as they arrive
   - `message_done` - Complete message
   - `tool_call_requested` - Tool needs approval
   - `tool_call_result` - Tool executed
   - `error` - Error occurred
   - `done` - Stream complete
4. **Client** processes events and updates UI

### Stop Flow

1. **User** clicks "Stop" button
2. **Client** calls `stopRun(runId)`
3. **Backend** marks run as cancelled in store
4. **Backend** streaming loop checks `is_cancelled()` and stops
5. **Client** receives error event and updates UI

### Tool Approval Flow

1. **Model** requests tool call during streaming
2. **Backend** detects tool call in stream
3. **Backend** emits `tool_call_requested` event
4. **Client** pauses UI and shows `ToolApprovalModal`
5. **User** approves/rejects via modal
6. **Client** calls `approveToolCall(runId, toolCallId, approved)`
7. **Backend** stores approval in `chat_store`
8. **Backend** polling loop detects approval:
   - If approved: Execute tool, add result to messages, continue streaming
   - If rejected: Stop streaming with error
9. **Client** receives `tool_call_result` or `error` event

## Azure Container Apps Deployment

### Environment Variables

Set in Container App configuration:

```bash
FOUNDRY_PROJECT_CONNECTION_STRING=<your_connection_string>
FOUNDRY_DEPLOYMENT_NAME=gpt-4
API_ENVIRONMENT=production
API_LOG_LEVEL=info
```

### Managed Identity

- Uses `DefaultAzureCredential`
- Local: `az login`
- Azure: Managed identity automatically

### Container App Settings

**API Service:**
- Port: 8000
- Health check: `/api/health`
- Ingress: Enabled
- Target port: 8000

**UI Service:**
- Port: 80 (production build)
- Environment: `VITE_API_URL=<api_url>`
- Ingress: Enabled

### Build Commands

```bash
# Build images
docker-compose build

# Or use Azure Developer CLI
azd up
```

## Notes

- **In-memory store**: Demo only - replace with database for production
- **File storage**: Local disk - use Azure Blob Storage for production
- **Tool registry**: Dummy implementations - add real tools as needed
- **Error handling**: Basic - enhance for production
- **Authentication**: None - add for production

## Testing

1. **Health Check**: `GET http://localhost:8000/api/health`
2. **File Upload**: Use UI file upload button
3. **Chat**: Send message and watch streaming
4. **Tool Approval**: Ask assistant to use a tool (e.g., "What time is it?")
5. **Stop**: Click stop button during streaming

## Troubleshooting

- **Foundry not configured**: Check `FOUNDRY_PROJECT_CONNECTION_STRING` env var
- **SSE not working**: Check CORS settings and browser console
- **Tool approval stuck**: Check backend logs for approval polling
- **Files not uploading**: Check `./data/uploads/` directory exists

