/** API client for chat operations. */

import type {
  ChatMessage,
  ChatRequest,
  FileUpload,
  SSEEvent,
  ToolCall,
} from '../types/chat.types';

export interface StartChatSSEOptions {
  threadId?: string;
  messages: ChatMessage[];
  files?: FileUpload[];
  onEvent: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

let defaultApiUrl = 'http://localhost:8000';

export function setApiUrl(url: string): void {
  defaultApiUrl = url;
}

export function getApiUrl(): string {
  return defaultApiUrl;
}

/**
 * Start a chat SSE stream.
 */
export async function startChatSSE(options: StartChatSSEOptions): Promise<() => void> {
  const { threadId, messages, files, onEvent, onError, signal } = options;

  const fileIds = files?.map((f) => f.fileId) || [];

  const requestBody: ChatRequest = {
    threadId,
    messages,
    fileIds,
  };

  try {
    const response = await fetch(`${defaultApiUrl}/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const readStream = async (): Promise<void> => {
      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE events
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          let currentEvent: string | null = null;
          let currentData: string | null = null;

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.substring(7).trim();
            } else if (line.startsWith('data: ')) {
              currentData = line.substring(6).trim();
            } else if (line === '' && currentEvent && currentData) {
              // End of event
              try {
                const data = JSON.parse(currentData);
                const event: SSEEvent = {
                  type: currentEvent as SSEEvent['type'],
                  data,
                } as SSEEvent;
                onEvent(event);
              } catch (e) {
                console.error('Error parsing SSE event:', e);
              }
              currentEvent = null;
              currentData = null;
            }
          }
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          // Stream was aborted, this is expected
          return;
        }
        if (onError) {
          onError(error instanceof Error ? error : new Error(String(error)));
        }
      }
    };

    readStream();

    // Return cleanup function
    return () => {
      reader.cancel();
    };
  } catch (error) {
    if (onError) {
      onError(error instanceof Error ? error : new Error(String(error)));
    }
    return () => {}; // No-op cleanup
  }
}

/**
 * Stop a running chat.
 */
export async function stopRun(runId: string): Promise<void> {
  const response = await fetch(`${defaultApiUrl}/v1/runs/${runId}/stop`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to stop run: ${response.status}`);
  }
}

/**
 * Approve or reject a tool call.
 */
export async function approveToolCall(
  runId: string,
  toolCallId: string,
  approved: boolean,
): Promise<void> {
  const response = await fetch(`${defaultApiUrl}/v1/runs/${runId}/toolcalls/${toolCallId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ approved }),
  });

  if (!response.ok) {
    throw new Error(`Failed to approve tool call: ${response.status}`);
  }
}

/**
 * Upload a file.
 */
export async function uploadFile(file: File): Promise<FileUpload> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${defaultApiUrl}/v1/files`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to upload file: ${response.status}`);
  }

  return response.json();
}

/**
 * Check backend health and Foundry connection.
 */
export async function checkHealth(): Promise<{ status: string; foundryConfigured: boolean }> {
  const response = await fetch(`${defaultApiUrl}/api/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  const data = await response.json();
  return {
    status: data.status || 'unknown',
    foundryConfigured: data.foundry_configured || false,
  };
}

