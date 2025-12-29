/** Chat API client using fetch-event-source for SSE. */

import { fetchEventSource } from '@microsoft/fetch-event-source';
import type {
  ChatMessage,
  ChatRequest,
  FileUpload,
  SSEEvent,
} from '../types/chat.types';
import { getApiUrl } from './config';

export interface StartChatSSEOptions {
  threadId?: string;
  messages: ChatMessage[];
  files?: FileUpload[];
  onEvent: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

/**
 * Start a chat SSE stream using fetch-event-source.
 */
export async function startChatSSE(options: StartChatSSEOptions): Promise<() => void> {
  const { threadId, messages, files, onEvent, onError, signal } = options;

  const fileIds = files?.map((f) => f.fileId) || [];

  const requestBody: ChatRequest = {
    threadId,
    messages,
    fileIds,
  };

  const abortController = new AbortController();
  
  // Combine signals if both are provided
  if (signal) {
    signal.addEventListener('abort', () => {
      abortController.abort();
    });
  }

  // Start the event source in the background
  fetchEventSource(`${getApiUrl()}/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
    signal: abortController.signal,
    openWhenHidden: true,
    async onopen(response) {
      // Check response status before processing
      if (response.ok && response.status >= 200 && response.status < 300) {
        return; // Everything's good
      } else if (response.status >= 400) {
        // HTTP error status
        const errorText = await response.text().catch(() => 'Unknown error');
        const error = new Error(`HTTP ${response.status}: ${errorText}`);
        if (onError) {
          onError(error);
        }
        throw error; // Stop retrying
      }
    },
    onmessage(event) {
      try {
        const data = JSON.parse(event.data);
        const sseEvent: SSEEvent = {
          type: event.event as SSEEvent['type'],
          data,
        } as SSEEvent;
        onEvent(sseEvent);
      } catch (error) {
        console.error('Error parsing SSE event:', error);
        if (onError) {
          onError(error instanceof Error ? error : new Error(String(error)));
        }
      }
    },
    onerror(error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Stream was aborted, this is expected
        return;
      }
      if (onError) {
        onError(error instanceof Error ? error : new Error(String(error)));
      }
      // Don't retry on error - stop the stream
      throw error;
    },
  }).catch((error) => {
    if (error instanceof Error && error.name !== 'AbortError' && onError) {
      onError(error);
    }
  });

  // Return cleanup function immediately
  return () => {
    abortController.abort();
  };
}

