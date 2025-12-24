/** Chat-related types. */

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  fileIds?: string[];
  id?: string;
}

export interface FileUpload {
  fileId: string;
  filename: string;
  contentType: string;
  size: number;
}

export interface ToolCall {
  id: string;
  name: string;
  argumentsJson: string;
}

export interface SSEMessageDelta {
  runId: string;
  deltaText: string;
}

export interface SSEMessageDone {
  runId: string;
  message: ChatMessage;
}

export interface SSEToolCallRequested {
  runId: string;
  toolCall: ToolCall;
}

export interface SSEToolCallResult {
  runId: string;
  toolCallId: string;
  result: unknown;
}

export interface SSEError {
  runId: string;
  message: string;
}

export interface SSEDone {
  runId: string;
}

export type SSEEvent =
  | { type: 'message_delta'; data: SSEMessageDelta }
  | { type: 'message_done'; data: SSEMessageDone }
  | { type: 'tool_call_requested'; data: SSEToolCallRequested }
  | { type: 'tool_call_result'; data: SSEToolCallResult }
  | { type: 'error'; data: SSEError }
  | { type: 'done'; data: SSEDone };

export interface ChatRequest {
  threadId?: string;
  messages: ChatMessage[];
  fileIds?: string[];
}

