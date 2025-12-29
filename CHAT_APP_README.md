# Chat Application - Implementation Guide

This document provides step-by-step instructions for the chat application with React (Vite) frontend and FastAPI backend, integrated with Azure AI Foundry.

## Project Structure

```
apps/
├── ui/                    # React app (pages/routes only)
│   └── src/
│       └── pages/
│           ├── Chat.tsx   # Main chat page
│           └── Settings.tsx # Settings page
├── ui-lib/                # React component library
│   └── src/
│       ├── components/    # Shared UI components
│       │   ├── ChatShell.tsx
│       │   ├── MessageList.tsx
│       │   ├── MessageBubble.tsx
│       │   ├── Composer.tsx
│       │   ├── FileUploadButton.tsx
│       │   ├── ToolApprovalModal.tsx
│       │   └── Toast.tsx
│       ├── api/           # API client
│       │   └── apiClient.ts
│       └── types/         # TypeScript types
│           └── chat.types.ts
└── api/                   # FastAPI backend
    └── src/
        └── api/
            ├── routes/
            │   └── chat.py    # Chat endpoints
            ├── services/
            │   ├── foundry_client.py
            │   ├── chat_service.py
            │   ├── chat_store.py
            │   └── tool_registry.py
            └── models/
                └── chat.py
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Install Python dependencies
cd apps/api
uv sync

# Install Node dependencies (from root)
npm ci
```

### 2. Configure Environment Variables

Create a `.env` file in the project root or set environment variables:

```bash
# Azure AI Foundry
FOUNDRY_PROJECT_CONNECTION_STRING=your_connection_string_here
FOUNDRY_DEPLOYMENT_NAME=gpt-4  # Optional, defaults to gpt-4

# API Configuration
API_ENVIRONMENT=development
API_LOG_LEVEL=debug
```

### 3. Build UI Library

```bash
cd apps/ui-lib
npm run build
```

### 4. Run Development Servers

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

The application will be available at:
- **UI**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Features

### Chat Functionality

1. **Send Messages**: Type a message and press Enter or click Send
2. **File Upload**: Click the 📎 button to upload files (PDF, TXT, PNG, JPG)
3. **Streaming Responses**: Assistant responses stream in real-time via SSE
4. **Stop Button**: Click "Stop" to cancel the current streaming response

### Tool Approval Flow

When the assistant requests a tool call:

1. Streaming pauses
2. A modal appears showing:
   - Tool name
   - Tool arguments
   - Run ID
3. User can:
   - **Approve**: Tool executes and streaming continues
   - **Reject**: Tool call is rejected and streaming stops

### Settings Page

- Configure backend API URL
- Test backend connection
- View Foundry connection status
- View required environment variables

## API Endpoints

### Chat Endpoints

- `POST /v1/chat/stream` - Start streaming chat (SSE)
- `POST /v1/files` - Upload a file
- `POST /v1/runs/{runId}/stop` - Stop/cancel a run
- `POST /v1/runs/{runId}/toolcalls/{toolCallId}` - Approve/reject tool call

### Health Check

- `GET /api/health` - Health check with Foundry status

## SSE Event Model

The `/v1/chat/stream` endpoint returns Server-Sent Events (SSE) with the following event types:

- `message_delta` - Streaming text chunk
  ```json
  {"runId": "...", "deltaText": "..."}
  ```

- `message_done` - Message completed
  ```json
  {"runId": "...", "message": {"role": "assistant", "content": "..."}}
  ```

- `tool_call_requested` - Tool call needs approval
  ```json
  {"runId": "...", "toolCall": {"id": "...", "name": "...", "argumentsJson": "..."}}
  ```

- `tool_call_result` - Tool executed
  ```json
  {"runId": "...", "toolCallId": "...", "result": {...}}
  ```

- `error` - Error occurred
  ```json
  {"runId": "...", "message": "..."}
  ```

- `done` - Stream completed
  ```json
  {"runId": "..."}
  ```

## Tool Registry

The backend includes a simple tool registry with two example tools:

1. **search_docs(query)** - Search documentation (dummy implementation)
2. **get_time()** - Get current time (dummy implementation)

Tools are defined in `apps/api/src/api/services/tool_registry.py`. You can add more tools by:
1. Adding a function to the `ToolRegistry` class
2. Adding the tool schema to `get_tools_schema()`

## Stop/Cancel Flow

1. User clicks "Stop" button
2. Frontend calls `POST /v1/runs/{runId}/stop`
3. Backend marks run as cancelled
4. Streaming loop checks cancellation status and stops
5. Frontend receives error event and updates UI

## Tool Approval Flow

1. Model requests tool call during streaming
2. Backend emits `tool_call_requested` event
3. Frontend pauses UI and shows approval modal
4. User approves/rejects via modal
5. Frontend calls `POST /v1/runs/{runId}/toolcalls/{toolCallId}`
6. Backend waits for approval (polls store)
7. If approved:
   - Tool executes
   - Result added to messages
   - Backend continues streaming with tool result
8. If rejected:
   - Streaming stops with error

## File Handling

- Files are uploaded to `./data/uploads/{fileId}`
- File metadata is stored in-memory (for demo)
- When files are attached to a message, a system message is added with file context
- File chips are displayed in the message list

## Deployment to Azure Container Apps

### Environment Variables

Set these in your Container App configuration:

```bash
FOUNDRY_PROJECT_CONNECTION_STRING=<your_connection_string>
FOUNDRY_DEPLOYMENT_NAME=gpt-4
API_ENVIRONMENT=production
```

### Managed Identity

The application uses `DefaultAzureCredential` for authentication:

- **Local**: Uses `az login` credentials
- **Azure**: Uses managed identity automatically

### Container App Configuration

1. **API Service**:
   - Port: 8000
   - Health check: `/api/health`
   - Environment variables: See above

2. **UI Service**:
   - Port: 5173 (dev) or 80 (production build)
   - Environment variable: `VITE_API_URL=<your_api_url>`

### Build and Deploy

```bash
# Build Docker images
docker-compose build

# Or use Azure Developer CLI
azd up
```

## Notes

- **In-memory store**: The current implementation uses in-memory storage for demo purposes. For production, replace with a database (Cosmos DB, PostgreSQL, etc.)
- **File storage**: Files are stored on disk. For production, use Azure Blob Storage
- **Tool execution**: Current tools are dummy implementations. Replace with real tool logic
- **Error handling**: Basic error handling is implemented. Add more robust error handling for production
- **Authentication**: No authentication is implemented. Add authentication/authorization for production

## Troubleshooting

### Foundry Connection Issues

1. Verify `FOUNDRY_PROJECT_CONNECTION_STRING` is set correctly
2. Run `az login` to authenticate
3. Check health endpoint: `GET /api/health` should show `foundry_configured: true`

### SSE Not Working

1. Check browser console for errors
2. Verify CORS is configured correctly (should allow `http://localhost:5173`)
3. Check network tab to see if SSE connection is established

### Tool Approval Not Working

1. Check browser console for API errors
2. Verify backend is receiving approval requests
3. Check backend logs for tool execution errors

## Development Commands

```bash
# Backend
cd apps/api
uv run uvicorn src.api.main:app --reload

# Frontend
cd apps/ui
npm run dev

# UI Library (watch mode)
cd apps/ui-lib
npm run build:watch

# Run tests
cd apps/api
uv run pytest

cd apps/ui
npm test
```

