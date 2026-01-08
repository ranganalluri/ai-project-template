# Tool Call Approval Flow Verification

## Flow Overview

### 1. Tool Call Creation (Status: "pending")
- **Location**: `chat_service.py` → `add_pending_tool_call()`
- **Function Call Document ID**: `fc_{tool_call.id}`
  - Example: If `tool_call.id = "call_F4u2pvFKXuVFmWrmMPnREK4h"`
  - Then document ID = `"fc_call_F4u2pvFKXuVFmWrmMPnREK4h"`
- **Status**: Set to `"pending"` when created
- **Document Structure**:
  ```json
  {
    "id": "fc_call_F4u2pvFKXuVFmWrmMPnREK4h",
    "type": "function_call",
    "status": "pending",
    "call_id": "call_F4u2pvFKXuVFmWrmMPnREK4h",
    "name": "search_users",
    "arguments": "{...}",
    ...
  }
  ```

### 2. UI Approval Request
- **Location**: `Chat.tsx` → `handleToolApprove()`
- **Action**: Calls `approveToolCall(runId, toolCallId, true)`
- **API Call**: `POST /v1/runs/{run_id}/toolcalls/{tool_call_id}`
  - `tool_call_id` = `"call_F4u2pvFKXuVFmWrmMPnREK4h"` (from `toolCall.id`)

### 3. API Endpoint
- **Location**: `routes/chat.py` → `approve_tool_call()`
- **Action**: Calls `chat_store.approve_tool_call(run_id, tool_call_id, approved)`
- **Parameters**:
  - `run_id`: Response ID
  - `tool_call_id`: `"call_F4u2pvFKXuVFmWrmMPnREK4h"`
  - `approved`: `true` or `false`

### 4. Chat Store Approval
- **Location**: `chat_store.py` → `approve_tool_call()`
- **Function Call ID Construction**: `f"fc_{tool_call_id}"`
  - Result: `"fc_call_F4u2pvFKXuVFmWrmMPnREK4h"`
- **Update Process**:
  1. Gets partition info using `_get_partition_info_from_run_id(run_id)` (cross-partition query)
  2. Reads function_call document: `read_item(item="fc_call_F4u2pvFKXuVFmWrmMPnREK4h", partition_key=pk)`
  3. Updates status:
     - `status = "approved"` if `approved=True`
     - `status = "rejected"` if `approved=False`
  4. Sets `approvedAt` timestamp if approved
  5. Saves using `replace_item()` with etag for concurrency control

## Potential Issues

### Issue 1: Cross-Partition Query
- **Problem**: `approve_tool_call()` uses `_get_partition_info_from_run_id()` which performs a cross-partition query
- **Impact**: Higher RU consumption and potential rate limiting
- **Solution**: Pass `conversation_id` to the API endpoint and use it to build partition key directly

### Issue 2: Status Update Verification
- **Current**: Status is updated correctly from "pending" → "approved"/"rejected"
- **Verification**: The document is read, status is updated, and saved with etag matching

## Verification Steps

1. Check function_call document exists with ID `fc_call_F4u2pvFKXuVFmWrmMPnREK4h`
2. Verify status is "pending" before approval
3. After approval API call, verify status is "approved"
4. Check `approvedAt` timestamp is set
5. Verify partition key matches (tenantId|userId|conversationId)




